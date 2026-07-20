"""Rule-based detection of structured identifiers.

Same detector interface as the model-based ones: `load()` and
`detect(model, text) -> list[Span]`. There is no model to load, so `load()` returns
None and `detect` ignores its `model` argument.

Scope: only entity types identifiable by their *form* rather than their meaning. An
IBAN is an IBAN because of its shape and check digits, whatever sentence surrounds
it. People, organisations and job titles are the opposite, and are left to the
models, which is why the two approaches cover disjoint labels.

Where an identifier is standardised, the standard's own library does the work rather
than a pattern invented here:

- `phonenumbers` (Google's libphonenumber) parses and *validates* telephone numbers
  for every country. This matters beyond coverage: a hand-written pattern loose
  enough to accept the many ways a number is written also matched the timestamp
  "2022-12-27 08" and the national number "85.07.12-034.51", mislabelling both.
  Validation removes a whole class of collision that no amount of pattern-tweaking
  reliably fixes.
- `python-stdnum` knows the structure and check digits of standardised numbers
  (IBAN, national identifiers, VAT and more) across dozens of countries, so support
  is not limited to the formats that happened to occur to one developer.
"""

import re

import phonenumbers
from stdnum import iban
from stdnum.be import nn as be_national_number

from ..spans import Span

MODEL_NAME = "rules + phonenumbers/stdnum"

# Regions to try when a number is written without an international prefix, e.g.
# "015 29 58 58". Ordered by how likely the data is to come from each.
PHONE_REGIONS = ("BE", "NL", "FR", "DE", "GB", "ES", "IT", "US")

# Patterns for the formats that have no standards library: an email address, a web
# address, and the shape of a national identifier before it is validated.
PATTERNS = [
    ("EMAIL_ADDRESS", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    # Requires a scheme or www., so a bare word is never matched. The path may end
    # on a slash but not on sentence punctuation, hence the narrower final class:
    # "www.contoso.example/contracts." is a URL followed by a full stop.
    (
        "URL",
        re.compile(
            r"(?:https?://|www\.)[\w-]+(?:\.[\w-]+)+"
            r"(?:/(?:[\w\-.~%?=&#+/]*[\w\-~%=&#+/])?)?"
        ),
    ),
    # Candidate IBANs: two letters, two digits, then groups. Validated below.
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{2,4}){2,8}\b")),
    # Candidate national identifiers. The Belgian rijksregisternummer and the
    # US pattern; other countries would each add a shape here.
    ("SSN", re.compile(r"\b\d{2}\.\d{2}\.\d{2}-\d{3}\.\d{2}\b|\b\d{3}-\d{2}-\d{4}\b")),
    # A postal code attached to a town, which the models consistently miss. Kept
    # narrow (it must be followed by a capitalised word) so bare numbers are safe.
    ("LOCATION", re.compile(r"\b\d{4}(?:\s?[A-Z]{2})?\s+(?=[A-Z])")),
]


def _overlaps(start: int, end: int, spans: list[Span]) -> bool:
    """True if [start, end) overlaps a span already claimed."""
    for other_start, other_end, _ in spans:
        if start < other_end and other_start < end:
            return True
    return False


def is_valid_identifier(label: str, value: str) -> bool:
    """Whether a candidate passes its standard's check digits.

    Reported as a signal, never used to reject a detection. For anonymisation a
    miss is a leak while an unnecessary redaction costs almost nothing, so a
    mistyped account number is still replaced.
    """
    try:
        if label == "IBAN":
            return bool(iban.is_valid(value))
        if label == "SSN":
            return bool(be_national_number.is_valid(value))
    except Exception:
        return False
    return False


def find_phone_numbers(text: str) -> list[Span]:
    """Find telephone numbers that are valid in at least one expected region."""
    spans: list[Span] = []
    seen: set[tuple[int, int]] = set()
    for region in PHONE_REGIONS:
        for match in phonenumbers.PhoneNumberMatcher(text, region):
            key = (match.start, match.end)
            if key in seen:
                continue
            seen.add(key)
            spans.append((match.start, match.end, "PHONE_NUMBER"))
    return spans


def load(model_name: str = MODEL_NAME):
    """Nothing to load: the patterns are compiled at import time."""
    return None


def detect(model, text: str) -> list[Span]:
    """Return (start, end, label) spans for every rule match in `text`.

    Precedence runs from the most self-identifying format to the least, and the
    first claim on a stretch of text keeps it:

    1. Email and web addresses, which are unmistakable.
    2. IBANs and national identifiers, which carry a country prefix or a fixed
       punctuation shape.
    3. Telephone numbers. These come after the account numbers because an IBAN
       contains a long run of digits that is a plausible telephone number on its
       own: "NL91 ABNA 0417 1643 00" hides "0417 1643 00" inside it.
    4. A postal code, the least distinctive of all, so it only fills gaps.
    """
    spans: list[Span] = []

    def claim(start: int, end: int, label: str) -> None:
        if not _overlaps(start, end, spans):
            spans.append((start, end, label))

    by_label = dict(PATTERNS)

    for label in ("EMAIL_ADDRESS", "URL", "IBAN", "SSN"):
        for match in by_label[label].finditer(text):
            claim(match.start(), match.end(), label)

    for start, end, label in find_phone_numbers(text):
        claim(start, end, label)

    # A postal code match runs up to the town name, so trim the trailing space.
    for match in by_label["LOCATION"].finditer(text):
        end = match.end() - (len(match.group()) - len(match.group().rstrip()))
        claim(match.start(), end, "LOCATION")

    return spans
