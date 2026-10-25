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
# Exact image hosts reviewed in data/photo_sources.json and existing catalog sources.
ALLOWED_HOSTS = {
    'www.goparkproperties.com',  # Park Properties, manager of Fieldstone and The Highlands (Blacksburg)
    'alateoldtown.com',
    'cms.oakvilleva.com',
    'cms.skymarkreston.com',
    'gravelcdn.nyc3.digitaloceanspaces.com',
    'lawsoncompanies.com',
    'tgmmoorefield.com',
    'www.arha.us',
    'www.brexxblacksburg.com',
    'www.carrprop.com',
    'www.regentsparkapartments.com',
    'fitchirick.com',
    'www.qpmgmt.com',
    'ahcommunities.org',
    'alexandriava.gov',
    'alight-blacksburg.com',
    'altanovaapts.com',
    'aspirehuntingtonstation.com',
    'assets.apartmenthomeliving.com',
    'assets.macerichepicenter.com',
    'assets.website-files.com',
    'avalonbay-avalon-communities-prod.cdn.arcpublishing.com',
    'blvdcommons.com',
    'blvdgramercyeast.com',
    'blvdhaley.com',
    'blvdreston.com',
    'capi.myleasestar.com',
    'cdn.carmel-apartments.com',
    'cdn.fairfieldresidential.com',
    'cdn.rentcafe.com',
    'cdngeneral.rentcafe.com',
    'cmgleasing.com',
    'cms.broadandwashington.com',
    'cms.oakvilleva.com',
    'communitylodgings.org',
    'cortland.com',
    'd1kldynkubiuhd.cloudfront.net',
    'd1uty3jitgnf7i.cloudfront.net',
    'embed-ssl.wistia.com',
    'emersonlife.com',
    'g5-assets-cld-res.cloudinary.com',
    'images.cdn.appfolio.com',
    'images.ctfassets.net',
    'images.squarespace-cdn.com',
    'images1.apartments.com',
    'lirp.cdn-website.com',
    'liveatnotch8.com',
    'livehaden.com',
    'liveloren.com',
    'livenouvelle.com',
    'lowe-re.com',
    'lumentysons.com',
    'media.apts247.info',
    'media.equityapartments.com',
    'medialibrarycf.entrata.com',
    'medialibrarycfo.entrata.com',
    'preserveatwestfields.com',
    'lyvwellapartments.com',  # Lyv Well, Brookfield's new name for The Parker and 8421 Broad
    'res.cloudinary.com',
    'residentialone.mystagingwebsite.com',
    'resource.rentcafe.com',
    'russellapts.com',
    'rylantysons.com',
    's7d9.scene7.com',
    'static.wixstatic.com',
    'thearborathalleyrise.com',
    'theearlapartments.com',
    'thefitzapts.com',
    'thewaycroft.com',
    'truegroundhousing.org',
    'uat-strapi-uploads-bozzuto-revamp.s3.us-west-2.amazonaws.com',
    'upload.wikimedia.org',
    'vistafairfaxcorner.com',
    'wesleyhousing.org',
    'wesleypropertymanagement.com',
    'windyhillfoundation.org',
    'www.alexandriava.gov',
    'www.arha.us',
    'www.arlingtonva.us',
    'www.armigermanagement.com',
    'www.avanath.com',
    'www.bellashburnfarms.com',
    'www.belloldtown.com',
    'www.blacksburgmill.com',
    'www.bxp.com',
    'www.carmelpartners.com',
    'www.communityhousingpartners.org',
    'www.davisconstruction.com',
    'www.evergreenreg.com',
    'www.fairfaxcounty.gov',
    'www.gables.com',
    'www.harborgroupmanagement.com',
    'www.housingalexandria.org',
    'www.huduser.gov',
    'www.liveaperture.com',
    'www.liveheming.com',
    'www.placemakr.com',
    'www.simpsonpropertygroup.com',
    'www.theblakealexandria.com',
    'www.udr.com',
    'www.westbroad.com',
}
MAX_BYTES = 8 * 1024 * 1024
# Photos saved in the project (data/listing-photos) for providers whose servers refuse our requests. The catalog keeps the
# provider's own address; when that address is listed here, the saved copy is served instead.
LOCAL_DIR = Path(__file__).resolve().parent.parent / 'data' / 'listing-photos'
LOCAL_FILES = {
    'https://images.cdn.appfolio.com/granitesl/images/58ae3dd2-aa42-46be-9e2a-7c448412ed38/medium.jpg': 'university-terrace-condos.jpg',
    'https://images.cdn.appfolio.com/granitesl/images/38cacbed-5a2b-4faa-b0e0-882ad851b20b/medium.jpg': 'carlton-scott-apartments.jpg',
    'https://images.cdn.appfolio.com/granitesl/images/d29d0416-54cb-43c5-94a8-12db1d50f687/medium.jpg': '300-mcdonald-street.jpg',
    'https://images.cdn.appfolio.com/granitesl/images/35a06a0e-592f-4f3f-a682-ba0f3bb6d496/medium.jpg': 'fourteen35.jpg',
    'https://images.cdn.appfolio.com/granitesl/images/37530107-91e8-4339-9ff4-3849ca7c5d36/medium.jpeg': '1203-north-main-street.jpeg',
    'https://www.communityhousingpartners.org/wp-content/uploads/2026/06/LegacyOnMain-July2026.jpg': 'legacy-on-main.jpg',
}
_LOCK = threading.Lock()
_LOCKS = {}
_FAILURES = {}

class PhotoUnavailable(ValueError):
    pass

def cached_photo(photo, cache_dir=None):
    """Download only an approved catalog image, validate it, and atomically cache it."""
    url = photo.get('url', '')
    if LOCAL_FILES.get(url) and (LOCAL_DIR / LOCAL_FILES[url]).is_file():
        return LOCAL_DIR / LOCAL_FILES[url]
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
                if image.format not in {'JPEG','PNG','WEBP','AVIF','GIF'} or image.width*image.height > 40_000_000:
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
