"""Cache real catalog photos without exposing a general-purpose image proxy.

Run python backend/listing_photos.py to prefetch unique provider photos locally.
Provider access failures leave an unavailable image, never a synthetic substitute.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from urllib.parse import urlsplit

import requests
from PIL import Image
from catalog import load_catalog

CACHE_DIR = Path(__file__).resolve().parent.parent / '.cache' / 'listing-photos'
ALLOWED_HOSTS = {'media.equityapartments.com', 'medialibrarycfo.entrata.com', 'cdngeneral.rentcafe.com', 'resource.rentcafe.com', 'capi.myleasestar.com', 'cms.broadandwashington.com'}
MAX_BYTES = 8 * 1024 * 1024
_LOCK = threading.Lock()
_LOCKS = {}
_FAILURES = {}

class PhotoUnavailable(ValueError):
    pass

def cached_photo(photo, cache_dir=None):
    """Download only an approved catalog image, validate it, and atomically cache it."""
    url = photo.get('url', '')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):
        raise PhotoUnavailable('Unapproved photo source.')
    key = hashlib.sha256(url.encode()).hexdigest()
    directory = Path(cache_dir or CACHE_DIR)
    path = directory / (key + '.image')
    with _LOCK:
        lock = _LOCKS.setdefault(key, threading.Lock())
    with lock:
        if path.is_file():
            return path
        if _FAILURES.get(key, 0) > time.monotonic():
            raise PhotoUnavailable('Provider photo temporarily unavailable.')
        try:
            # Uses inherited proxy/CA settings. Do not bypass denied provider access.
            with requests.get(url, stream=True, timeout=(5,15), allow_redirects=False) as response:
                response.raise_for_status()
                if not 200 <= response.status_code < 300:
                    raise PhotoUnavailable('Photo source redirected; review the catalog URL.')
                if not response.headers.get('Content-Type','').lower().startswith('image/'):
                    raise PhotoUnavailable('Source did not return an image.')
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content) > MAX_BYTES:
                        raise PhotoUnavailable('Photo exceeds download limit.')
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in {'JPEG','PNG','WEBP','AVIF'} or image.width*image.height > 40_000_000:
                    raise PhotoUnavailable('Unsupported or oversized image.')
                image.verify()
            directory.mkdir(parents=True, exist_ok=True)
            handle = tempfile.NamedTemporaryFile(dir=directory,delete=False)
            try:
                with handle:
                    handle.write(content)
                os.replace(handle.name,path)
            finally:
                Path(handle.name).unlink(missing_ok=True)
            return path
        except (requests.RequestException, OSError, ValueError, Image.DecompressionBombError) as exc:
            _FAILURES[key] = time.monotonic()+60
            raise PhotoUnavailable('Unable to download a valid provider photo.') from exc

def photo_mimetype(path):
    with Image.open(path) as image:
        return Image.MIME.get(image.format, 'application/octet-stream')

if __name__ == '__main__':
    photos = {r['photo']['url']:r for r in load_catalog() if r.get('photo')}
    downloaded = 0
    for row in photos.values():
        try:
            path = cached_photo(row['photo'])
            print(f"OK: {row['community']}")
            downloaded += 1
        except PhotoUnavailable:
            print(f"UNAVAILABLE: {row['community']} — check provider access; no substitute image used.")
    print(f'{downloaded}/{len(photos)} real provider photos cached.')
    raise SystemExit(0 if downloaded == len(photos) else 1)
