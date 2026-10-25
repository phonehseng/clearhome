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
        item = dict(community=row.get('community') or row['name'],
                    record_ids=[r['id'] for r in rows],
                    missing_photo_record_ids=[r['id'] for r in rows if not r.get('photo')],
                    rendering_record_ids=[r['id'] for r in rows if (r.get('photo') or {}).get('kind') == 'rendering'])
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


def coverage_report(download=False):
    """Separate catalog coverage from downloaded-image checks; unknown is not a pass."""
    communities = audit(download)
    record_count = sum(len(c['record_ids']) for c in communities)
    missing_ids = [rid for c in communities for rid in c['missing_photo_record_ids']]
    verified_images = {'large_image', 'needs_larger_original'}
    unchecked = [c['community'] for c in communities
                 if c['status'] not in verified_images and c['status'] != 'missing_official_photo']
    return {
        'summary': {
            'housing_records': record_count,
            'records_with_image': record_count - len(missing_ids),
            'records_without_image': len(missing_ids),
            'records_with_rendering': sum(len(c['rendering_record_ids']) for c in communities),
            'communities': len(communities),
            'communities_without_photo': sum(c['status'] == 'missing_official_photo' for c in communities),
            'communities_with_unconfirmed_delivery': len(unchecked),
            'complete': bool(communities) and not missing_ids and all(c['status'] in verified_images for c in communities),
        },
        'missing_photo_record_ids': missing_ids,
        'communities': communities,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--require-complete', action='store_true',
                        help='Report every housing record and exit 1 for missing or unvalidated photos.')
    args = parser.parse_args()
    if args.require_complete:
        report = coverage_report(args.download)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        raise SystemExit(0 if report['summary']['complete'] else 1)
    print(json.dumps(audit(args.download), indent=2, ensure_ascii=False))
