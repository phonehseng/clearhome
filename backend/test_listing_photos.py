"""Offline tests for photo caching and serving. Fixtures are not production photos."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
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
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'photo.image';path.write_bytes(self.png)
            with patch('app.cached_photo',return_value=path):
                response=client.get('/media/listings/indigo-studio-std')
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.mimetype,'image/png')
                self.assertEqual(response.data,self.png)
                response.close()
        with patch('app.cached_photo',side_effect=PhotoUnavailable('blocked')):
            self.assertEqual(client.get('/media/listings/indigo-studio-std').status_code,503)
        self.assertEqual(client.get('/media/listings/missing').status_code,404)

if __name__=='__main__': unittest.main()
