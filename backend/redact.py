"""Strip SSNs and account numbers from text using their formats. No AI involved.

Usage: python backend/redact.py path/to/file.txt
"""
import re
import sys

# 123-45-6789 or 123 45 6789. Also catches ITINs (9xx-xx-xxxx), which are just as sensitive.
SSN_RE = re.compile(r"\b\d{3}([- ])\d{2}\1\d{4}\b")
# Nine digits right after an SSN label, e.g. "SSN: 123456789".
SSN_LABELED_RE = re.compile(
    r"(?i)\b(ssn|ss#|social security(?: number| no\.?| #)?)(\s*[:#]?\s*)(\d{9})\b"
)
# 13 to 19 digits, optionally grouped by spaces or dashes; only redacted if it passes the Luhn check.
CARD_RE = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
# 4 to 17 digits (possibly masked with X or *) after an account or routing label.
ACCOUNT_LABELED_RE = re.compile(
    r"(?i)\b(account|acct|routing|aba|iban|member)(\s*(?:number|no\.?|#)?\s*[:#]?\s*)([\dX*](?:[ -]?[\dX*]){3,16})\b"
)
# Any unlabeled run of 12 to 17 digits looks like a bank account number.
LONG_NUMBER_RE = re.compile(r"\b\d{12,17}\b")


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


def redact(text):
    """Return (redacted_text, counts) where counts says how many of each kind were removed."""
    counts = {"ssn": 0, "card": 0, "account": 0}

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
