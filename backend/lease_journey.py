"""Retrieve public lease references only from a selected catalog provider.

No accounts are accessed, no applications or signatures are submitted, and no
uploaded document is saved. A public sample is never a renter's final contract.
"""
import io
import ipaddress
import re
import socket
import threading
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit

import requests
from pypdf import PdfReader

from catalog import HOUSING_TYPES, community_key, effective_availability, load_catalog
from redact import redact

MAX_DOCUMENT_BYTES = 3 * 1024 * 1024
MAX_TEXT_CHARS = 120000
MAX_PAGES = 80
MAX_HTML_BYTES = 512 * 1024
_CACHE = {}
_LOCK = threading.Lock()


class ProviderUnavailable(ValueError):
    pass


class PublicDocumentAuth(requests.auth.AuthBase):
    def __call__(self, request):
        request.headers.pop('Authorization', None)
        return request


def _allowed_url(url, hosts):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == 'https' and parsed.hostname in hosts and not parsed.username
                and not parsed.password and parsed.port in (None, 443))
    except (TypeError, ValueError):
        return False


def _public_host(host):
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
    except (OSError, ValueError):
        return False


def _download(url, hosts, limit, deadline):
    if time.monotonic() >= deadline or not _allowed_url(url, hosts) or not _public_host(urlsplit(url).hostname):
        raise ProviderUnavailable('Provider address is unavailable.')
    remaining = max(1, min(5, deadline - time.monotonic()))
    # Keep inherited proxy/CA settings. Never send cookies, credentials, or follow
    # redirects into sign-in portals, unrelated hosts, or private addresses.
    try:
        with requests.get(url, stream=True, timeout=(min(3, remaining), remaining), allow_redirects=False,
                          auth=PublicDocumentAuth(),
                          headers={'Accept': 'text/html,application/pdf', 'User-Agent': 'ClearHouse-PublicLeaseReader/1.0'}) as response:
            if not 200 <= response.status_code < 300:
                raise ProviderUnavailable('The public provider page could not be read.')
            content = bytearray()
            for chunk in response.iter_content(32768):
                if time.monotonic() >= deadline:
                    raise ProviderUnavailable('Provider check timed out.')
                content.extend(chunk)
                if len(content) > limit:
                    raise ProviderUnavailable('Provider document exceeds the size limit.')
            return bytes(content), response.headers.get('Content-Type', '').split(';')[0].lower()
    except requests.RequestException as exc:
        raise ProviderUnavailable('The public provider page could not be read.') from exc


class DocumentLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href', ''), dict(attrs).get('aria-label', '')]

    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += ' ' + data

    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(tuple(self.current))
            self.current = None


def _candidate(url, label):
    parsed = urlsplit(url)
    name = unquote(parsed.path).lower()
    words = re.sub(r'[_\-/]+', ' ', name + ' ' + label.lower())
    # Application forms, fee sheets, brochures, and addenda are not full leases.
    excluded = r'\b(application|apply|brochure|privacy|handbook|addendum|renewal|commercial)\b'
    return (parsed.path.lower().endswith('.pdf') and re.search(r'\blease\b|\brental agreement\b', words)
            and not re.search(excluded, words))


def _pdf_text(data):
    if not data.startswith(b'%PDF-'):
        raise ProviderUnavailable('The linked document is not a readable PDF.')
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted or len(reader.pages) > MAX_PAGES:
            raise ProviderUnavailable('The document is protected or too long. Request a readable copy from the provider.')
        parts, length = [], 0
        for page in reader.pages:
            text = page.extract_text() or ''
            length += len(text) + 2
            if length > MAX_TEXT_CHARS:
                raise ProviderUnavailable('The document is too long to import in full. Request a smaller document or upload a section.')
            parts.append(text)
        text = '\n\n'.join(parts).strip()
        if not text:
            raise ProviderUnavailable('The public PDF has no readable text. Upload a clear copy for text extraction.')
        normalized = ' '.join(text.lower().split())
        if not (re.search(r'lease\s+agreement|rental\s+agreement|residential\s+lease', normalized)
                and 'tenant' in normalized and ('landlord' in normalized or 'owner' in normalized)):
            raise ProviderUnavailable('The linked PDF could not be identified as a lease. Request the actual lease from leasing.')
        return redact(text)[0]
    except ProviderUnavailable:
        raise
    except Exception as exc:
        raise ProviderUnavailable('The provider PDF could not be read. Request a copy from leasing.') from exc


def retrieve_public_document(row):
    """Inspect up to two known provider pages, without inferring final-lease terms."""
    pages = list(dict.fromkeys(u for u in (row.get('website'), row.get('source_url')) if isinstance(u, str) and u.startswith('https://')))
    hosts = {urlsplit(u).hostname for u in pages}
    key = tuple(pages)
    now = time.monotonic()
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and cached[0] > now:
            return cached[1]
    deadline = now + 12
    checked, unavailable = [], False
    result = None
    for page in pages[:2]:
        try:
            data, content_type = _download(page, hosts, MAX_HTML_BYTES, deadline)
            if content_type not in {'text/html', 'application/xhtml+xml'}:
                unavailable = True
                continue
            parser = DocumentLinks()
            parser.feed(data.decode('utf-8', errors='replace'))
            checked.append(page)
            links = [(urljoin(page, url), label) for url, label in parser.links]
            candidates = list(dict.fromkeys(url for url, label in links if _allowed_url(url, hosts) and _candidate(url, label)))
            for url in candidates[:2]:
                try:
                    document, content_type = _download(url, hosts, MAX_DOCUMENT_BYTES, deadline)
                    if content_type not in {'application/pdf', 'application/octet-stream'}:
                        raise ProviderUnavailable('Provider document is not a PDF.')
                    text = _pdf_text(document)
                    result = dict(status='public_reference', message='A public lease reference was found on the provider’s website. It may be a sample or an older form; it is not your final lease.',
                                  checked_urls=checked[:], document=dict(text=text, kind='public_reference', source_url=url,
                                  filename=unquote(urlsplit(url).path.rsplit('/', 1)[-1]), retrieved_at=datetime.now(timezone.utc).isoformat()))
                    break
                except ProviderUnavailable:
                    unavailable = True
            if result:
                break
        except ProviderUnavailable:
            unavailable = True
    if result is None:
        result = dict(status='unavailable' if unavailable else 'not_found', document=None, checked_urls=checked,
                      message='We couldn’t complete the public-document check. Ask leasing for your full proposed lease and all addenda.' if unavailable else
                              'No public lease PDF was found on the provider pages checked. Ask leasing for your full proposed lease and all addenda.')
    with _LOCK:
        if len(_CACHE) >= 128:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = (time.monotonic() + (60 if result['status'] == 'unavailable' else 1800), result)
    return result


def journey_context(resource_id, check_provider=False):
    rows = load_catalog()
    row = next((r for r in rows if r['id'] == resource_id and r['type'] in HOUSING_TYPES), None)
    if row is None:
        return None
    availability = effective_availability(row)
    options = [r for r in rows if r['type'] in HOUSING_TYPES and community_key(r) == community_key(row)
               and (r['id'] == resource_id or effective_availability(r).get('status') not in {'closed', 'needs_recheck'})]
    fields = ('id', 'name', 'community', 'floor_plan', 'address', 'phone', 'source_url', 'website', 'monthly_rent',
              'cost', 'requirements', 'who_it_serves', 'minimum_age', 'last_verified')
    selected = {field: row.get(field) for field in fields}
    selected['availability'] = availability
    return dict(listing=selected, options=[{field: option.get(field) for field in ('id', 'name', 'floor_plan', 'monthly_rent')} for option in options],
                provider_document=retrieve_public_document(row) if check_provider else
                dict(status='not_checked', document=None, message='Checking public provider pages…'))
