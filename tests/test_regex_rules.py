"""Rule-based detection of structured identifiers."""

from anonymizer.detectors import regex_rules


def found(text: str) -> dict[str, list[str]]:
    """Detected spans as {label: [matched text, ...]}, for readable assertions."""
    out: dict[str, list[str]] = {}
    for start, end, label in regex_rules.detect(None, text):
        out.setdefault(label, []).append(text[start:end])
    return out


def test_email_address():
    assert found("write to l.peeters@example.org today") == {
        "EMAIL_ADDRESS": ["l.peeters@example.org"]
    }


def test_url_with_scheme():
    assert found("see https://example.org/a/b for more") == {
        "URL": ["https://example.org/a/b"]
    }


def test_url_does_not_swallow_the_sentence_ending_period():
    # Regression: the path pattern used to run to the next space, taking the final
    # full stop with it.
    assert found("the portal is at www.contoso.example/contracts.") == {
        "URL": ["www.contoso.example/contracts"]
    }


def test_url_needs_a_scheme_or_www_so_plain_words_are_not_matched():
    assert found("meet me at the office. thanks") == {}


def test_phone_number():
    assert found("call +32 471 22 33 44 tomorrow") == {
        "PHONE_NUMBER": ["+32 471 22 33 44"]
    }


def test_a_year_is_not_a_phone_number():
    assert found("the deal closed in 2019") == {}


def test_iban():
    assert found("account BE68 5390 0754 7034 please") == {
        "IBAN": ["BE68 5390 0754 7034"]
    }


def test_national_number_is_an_ssn_not_a_phone_number():
    # Regression: the phone pattern is deliberately permissive and also matches this
    # shape. The more specific pattern must win, or a national number is mislabelled.
    assert found("national number 85.07.12-034.51 on file") == {
        "SSN": ["85.07.12-034.51"]
    }


def test_us_style_ssn():
    assert found("ssn 123-45-6789 recorded") == {"SSN": ["123-45-6789"]}


def test_an_iban_is_not_also_reported_as_a_phone_number():
    labels = found("account BE68 5390 0754 7034").keys()
    assert set(labels) == {"IBAN"}


def test_several_identifiers_in_one_text():
    text = (
        "Mail l.peeters@example.org, call +32 471 22 33 44, pay to BE68 5390 0754 7034."
    )
    assert found(text) == {
        "EMAIL_ADDRESS": ["l.peeters@example.org"],
        "PHONE_NUMBER": ["+32 471 22 33 44"],
        "IBAN": ["BE68 5390 0754 7034"],
    }


def test_detected_spans_never_overlap():
    text = "id 85.07.12-034.51 acct BE68 5390 0754 7034 tel +32 471 22 33 44"
    spans = sorted(regex_rules.detect(None, text))
    for (_, first_end, _), (second_start, _, _) in zip(spans, spans[1:], strict=False):
        assert first_end <= second_start


def test_load_returns_nothing_to_load():
    assert regex_rules.load() is None
