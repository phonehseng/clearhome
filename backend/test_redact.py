"""Offline checks for redact(): email addresses and phone numbers are removed before text goes to Gemma."""
import unittest

from redact import redact


class RedactContactTests(unittest.TestCase):
    def test_removes_email_address(self):
        text, counts = redact("my email is jane.doe+housing@example.org, can you help?")
        self.assertNotIn("jane.doe", text)
        self.assertEqual(counts["contact"], 1)

    def test_removes_phone_numbers_in_common_formats(self):
        for phone in ["703-555-0100", "(703) 555-0100", "703.555.0100", "703 555 0100", "+1 703 555 0100"]:
            with self.subTest(phone=phone):
                text, counts = redact(f"call me at {phone} after 5")
                self.assertNotIn("555", text)
                self.assertEqual(counts["contact"], 1)

    def test_keeps_resource_text_and_short_numbers(self):
        message = "Call 211 or 911. Rent is $1,000 for 2 bedrooms."
        text, counts = redact(message)
        self.assertEqual(text, message)
        self.assertEqual(counts["contact"], 0)

    def test_still_removes_ssn_and_card_numbers(self):
        text, counts = redact("SSN 123-45-6789 and card 4111 1111 1111 1111")
        self.assertNotIn("123-45-6789", text)
        self.assertNotIn("4111", text)
        self.assertEqual(counts["ssn"], 1)
        self.assertEqual(counts["card"], 1)


if __name__ == "__main__":
    unittest.main()
