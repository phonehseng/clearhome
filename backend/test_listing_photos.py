"""Offline tests for photo caching and serving. Fixtures are not production photos."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
from PIL import Image
import listing_photos
from listing_photos import cached_photo, PhotoUnavailable

class Response:
    def __init__(self, data, content_type='image/png'):
        self.data=data
        self.headers={'Content-Type':content_type}
        self.status_code=200
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def raise_for_status(self): pass
    def iter_content(self,size): yield self.data

class PhotoTests(unittest.TestCase):
    def test_catalog_photo_sources_are_attributed_and_allowed(self):
        from catalog import load_catalog
        for row in load_catalog():
            photo = row.get('photo')
            if not photo:
                continue
            with self.subTest(resource=row['id']):
                parsed = urlsplit(photo['url'])
                self.assertEqual(parsed.scheme, 'https')
                self.assertIn(parsed.hostname, listing_photos.ALLOWED_HOSTS)
                self.assertFalse(parsed.username or parsed.password)
                self.assertIn(parsed.port, (None, 443))
                self.assertEqual(urlsplit(photo['source_url']).scheme, 'https')
                for field in ('alt', 'credit', 'reviewed_on', 'caption'):
                    self.assertTrue(photo.get(field))

    def test_photo_review_queue_matches_missing_communities(self):
        from catalog import load_catalog, community_key, HOUSING_TYPES
        directory = Path(__file__).resolve().parent.parent / 'data'
        rows = [r for r in load_catalog() if r['type'] in HOUSING_TYPES]
        photographed = {community_key(r) for r in rows if r.get('photo')}
        missing = {r['id'] for r in rows if community_key(r) not in photographed}
        queue = json.loads((directory / 'photo_review.json').read_text())
        self.assertEqual({rid for c in queue['communities'] for rid in c['record_ids']}, missing)
        manifest = json.loads((directory / 'photo_sources.json').read_text())
        by_id = {r['id']: r for r in rows}
        for item in manifest['communities']:
            for rid in item['record_ids']:
                with self.subTest(resource=rid):
                    if item['status'] == 'official_photo_source_reviewed':
                        self.assertEqual(by_id[rid]['photo']['url'], item['image_url'])
                        self.assertEqual(by_id[rid]['photo']['source_url'], item['source_url'])
                    else:
                        self.assertIn(rid, missing)

    def setUp(self):
        listing_photos._FAILURES.clear()
        buffer=io.BytesIO()
        Image.new('RGB',(2,2),'white').save(buffer,format='PNG')
        self.png=buffer.getvalue()
        self.photo={'url':'https://resource.rentcafe.com/image/upload/test.png'}

    def test_original_bytes_cached_without_redownload(self):
        with tempfile.TemporaryDirectory() as directory, patch('listing_photos.requests.get',return_value=Response(self.png)) as get:
            path=cached_photo(self.photo,directory)
            self.assertEqual(path.read_bytes(),self.png)
            self.assertEqual(cached_photo(self.photo,directory),path)
            self.assertEqual(get.call_count,1)

    def test_bad_sources_and_non_images_are_rejected(self):
        for url in ['http://resource.rentcafe.com/photo','https://localhost/photo','https://evil.test/photo','https://user:pass@resource.rentcafe.com/photo']:
            with self.assertRaises(PhotoUnavailable): cached_photo({'url':url})
        with tempfile.TemporaryDirectory() as directory, patch('listing_photos.requests.get',return_value=Response(b'<html>denied</html>','text/html')):
            with self.assertRaises(PhotoUnavailable): cached_photo(self.photo,directory)
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_failure_has_no_fake_replacement_and_throttles_retries(self):
        with tempfile.TemporaryDirectory() as directory, patch('listing_photos.requests.get',return_value=Response(b'invalid')) as get:
            for _ in range(2):
                with self.assertRaises(PhotoUnavailable):cached_photo(self.photo,directory)
            self.assertEqual(get.call_count,1)
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_photo_route_returns_image_or_explicit_failure(self):
        from app import app
        client=app.test_client()
        # Route behavior must not depend on a live property's photo surviving source review.
        rows=[{'id':'test-home','photo':self.photo}, {'id':'no-photo'}]
        with patch('app.load_catalog',return_value=rows):
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'photo.image';path.write_bytes(self.png)
                with patch('app.cached_photo',return_value=path):
                    response=client.get('/media/listings/test-home')
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(response.mimetype,'image/png')
                    self.assertEqual(response.data,self.png)
                    response.close()
            with patch('app.cached_photo',side_effect=PhotoUnavailable('blocked')):
                self.assertEqual(client.get('/media/listings/test-home').status_code,503)
            self.assertEqual(client.get('/media/listings/no-photo').status_code,404)
            self.assertEqual(client.get('/media/listings/missing').status_code,404)

if __name__=='__main__': unittest.main()
