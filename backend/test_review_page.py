"""The hand-review page: decisions save locally, hidden records leave every answer, the hosted copy can't write.

Run: python backend/test_review_page.py
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as server
import catalog


class ReviewPageTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.path = Path(tempfile.mkdtemp()) / "listing_review.json"
        for target in (patch.object(catalog, "REVIEW_PATH", self.path), patch.object(server, "REVIEW_PATH", self.path),
                       patch.object(server, "READ_ONLY", False)):
            target.start()
            self.addCleanup(target.stop)

    def post(self, body, addr="127.0.0.1"):
        return self.client.post("/api/review", json=body, environ_base={"REMOTE_ADDR": addr})

    def test_hide_removes_a_record_everywhere_and_clear_brings_it_back(self):
        rid = catalog.filter_catalog(catalog.load_catalog(), {"types": ["rental_listing"]})[0]["id"]
        self.assertEqual(self.post({"id": rid, "state": "hidden", "note": "wrong phone"}).status_code, 200)
        self.assertNotIn(rid, {r["id"] for r in catalog.load_catalog()})
        listed = self.client.get("/api/listings").get_json()["listings"]
        self.assertNotIn(rid, {r["id"] for r in listed})
        review = self.client.get("/api/review").get_json()
        self.assertEqual(review["decisions"][rid]["note"], "wrong phone")
        self.assertFalse(next(r for r in review["records"] if r["id"] == rid)["shown"])
        self.post({"id": rid, "state": "clear"})
        self.assertIn(rid, {r["id"] for r in catalog.load_catalog()})

    def test_only_a_local_copy_can_save(self):
        rid = catalog.load_catalog()[0]["id"]
        self.assertEqual(self.post({"id": rid, "state": "verified"}, addr="203.0.113.9").status_code, 403)
        with patch.object(server, "READ_ONLY", True):
            self.assertEqual(self.post({"id": rid, "state": "verified"}).status_code, 403)
            self.assertFalse(self.client.get("/api/review").get_json()["can_edit"])
        self.assertFalse(self.path.exists())

    def test_bad_requests_are_refused(self):
        rid = catalog.load_catalog()[0]["id"]
        for body in ({"id": rid, "state": "deleted"}, {"id": rid, "state": "flagged", "note": "x" * 501}, {"state": "verified"}):
            self.assertEqual(self.post(body).status_code, 400)
        self.assertEqual(self.post({"id": "no-such-record", "state": "verified"}).status_code, 404)

    def test_page_is_served(self):
        self.assertEqual(self.client.get("/review").status_code, 200)


if __name__ == "__main__":
    unittest.main()
