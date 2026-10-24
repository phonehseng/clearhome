"""Strip SSNs and account numbers from text using their formats. No AI involved.

Usage: python backend/redact.py path/to/file.txt
"""
import re
import sys

# Digit patterns use (?<!\d) and (?!\d) instead of \b so they still match when OCR
# glues words together, e.g. "accountnumber0012345678".

# 123-45-6789, 123 45 6789, 123.45.6789 or "123 - 45 - 6789". Also catches ITINs (9xx-xx-xxxx), which are just as sensitive.
SSN_RE = re.compile(r"(?<!\d)\d{3}(\s*[-.]\s*|\s)\d{2}\1\d{4}(?!\d)")
# Nine digits after an SSN label, e.g. "SSN: 123456789" or "my ssn is 123456789".
SSN_LABELED_RE = re.compile(
    r"(?i)(ssn|ss#|social security(?: number| no\.?| #)?)(\s*(?:[:#]|is|=)?\s*)(\d{9})(?!\d)"
)
# 13 to 19 digits, optionally grouped by spaces or dashes; only redacted if it passes the Luhn check.
CARD_RE = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")
# 4 to 17 digits (possibly masked with X or *) after an account or routing label.
ACCOUNT_LABELED_RE = re.compile(
    r"(?i)(account|acct|routing|aba|iban|member)(\s*(?:number|no\.?|#)?\s*(?:[:#]|is|=)?\s*)([\dX*](?:[ -]?[\dX*]){3,16})(?![\dX*])"
)
# Any unlabeled run of 12 to 17 digits looks like a bank account number.
LONG_NUMBER_RE = re.compile(r"(?<!\d)\d{12,17}(?!\d)")

# Letters OCR often mistakes for digits.
OCR_DIGIT_LOOKALIKES = str.maketrans({"O": "0", "o": "0", "D": "0", "I": "1", "l": "1", "|": "1",
                                      "Z": "2", "S": "5", "s": "5", "B": "8", "g": "9"})
# A run of 7+ digit-like characters (allowing - and spaces) that is mostly real digits.
OCR_NUMBER_RE = re.compile(r"[\dOoDIl|ZSsBg](?:[ -]?[\dOoDIl|ZSsBg]){6,}")


def _fix_ocr_numbers(text):
    """Turn OCR misreads like 'l23-45-67B9' back into digits, but only inside number-like runs."""

    def fix(m):
        s = m.group(0)
        if sum(c.isdigit() for c in s) / len(s.replace(" ", "").replace("-", "")) < 0.6:
            return s  # mostly letters: a real word, leave it alone
        # Only fix chunks that contain a real digit, so "Call 540-..." keeps its "ll".
        return " ".join(
            chunk.translate(OCR_DIGIT_LOOKALIKES) if any(c.isdigit() for c in chunk) else chunk
            for chunk in s.split(" ")
        )

    return OCR_NUMBER_RE.sub(fix, text)


def _luhn_ok(digits):
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def redact(text, ocr=False):
    """Return (redacted_text, counts) where counts says how many of each kind were removed.

    Pass ocr=True for text that came from OCR, so misread digits are repaired first.
    """
    counts = {"ssn": 0, "card": 0, "account": 0}
    if ocr:
        text = _fix_ocr_numbers(text)

    def card(m):
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            counts["card"] += 1
            return "[REDACTED CARD NUMBER]"
        return m.group(0)

    def ssn(m):
        counts["ssn"] += 1
        return "[REDACTED SSN]"

    def ssn_labeled(m):
        counts["ssn"] += 1
        return m.group(1) + m.group(2) + "[REDACTED SSN]"

    def account_labeled(m):
        counts["account"] += 1
        return m.group(1) + m.group(2) + "[REDACTED ACCOUNT NUMBER]"

    def long_number(m):
        counts["account"] += 1
        return "[REDACTED ACCOUNT NUMBER]"

    text = CARD_RE.sub(card, text)
    text = SSN_RE.sub(ssn, text)
    text = SSN_LABELED_RE.sub(ssn_labeled, text)
    text = ACCOUNT_LABELED_RE.sub(account_labeled, text)
    text = LONG_NUMBER_RE.sub(long_number, text)
    return text, counts


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    cleaned, found = redact(open(sys.argv[1]).read())
    print(cleaned)
    print(f"\nRemoved: {found}", file=sys.stderr)
