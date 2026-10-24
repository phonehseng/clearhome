"""Report missing, unavailable, or small official catalog images.

python backend/photo_audit.py              # inspect locally cached originals
python backend/photo_audit.py --download   # also fetch recorded official URLs

This never assigns an image, changes listing dates, or substitutes another home.
"""
import argparse
import json
from PIL import Image
from catalog import load_catalog, community_key, HOUSING_TYPES
from listing_photos import cached_photo, PhotoUnavailable, CACHE_DIR
import hashlib


def audit(download=False):
    communities = {}
    for row in load_catalog():
        if row['type'] in HOUSING_TYPES:
            communities.setdefault(community_key(row), []).append(row)
    report = []
    for rows in communities.values():
        row = next((r for r in rows if r.get('photo')), rows[0])
        photo = row.get('photo')
        item = dict(community=row.get('community') or row['name'], record_ids=[r['id'] for r in rows])
        if not photo:
            item['status'] = 'missing_official_photo'
        else:
            item.update(source_url=photo['source_url'], image_url=photo['url'])
            try:
                path = cached_photo(photo) if download else CACHE_DIR / (hashlib.sha256(photo['url'].encode()).hexdigest() + '.image')
                if not path.is_file():
                    item['status'] = 'dimensions_not_checked'
                else:
                    with Image.open(path) as image:
                        width, height = image.size
                    item.update(width=width, height=height,
                                status='large_image' if width >= 1200 and height >= 675 else 'needs_larger_original')
            except (PhotoUnavailable, OSError, ValueError):
                item['status'] = 'image_unavailable'
        report.append(item)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    print(json.dumps(audit(args.download), indent=2, ensure_ascii=False))
