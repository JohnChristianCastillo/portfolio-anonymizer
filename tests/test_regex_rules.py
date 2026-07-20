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


def test_a_machine_timestamp_is_left_for_the_models():
    # Regression: a hand-written phone pattern matched "2022-12-27 08" and cut the
    # timestamp in half, so the models never got the chance to label it DATE_TIME.
    # Validation is what fixes this: that string is a valid number in no region.
    assert found("written on 2022-12-27 08:26:49.21 exactly") == {}


def test_a_phone_number_written_without_a_country_code():
    # Only reachable because the number is parsed against the expected regions.
    assert found("call 015 29 58 58 today") == {"PHONE_NUMBER": ["015 29 58 58"]}


def test_a_foreign_iban_is_not_split_into_a_phone_number():
    # Regression: "NL91 ABNA 0417 1643 00" contains "0417 1643 00", which is a
    # plausible number on its own, so IBANs must be claimed before telephones.
    assert found("pay to NL91 ABNA 0417 1643 00 please") == {
        "IBAN": ["NL91 ABNA 0417 1643 00"]
    }


def test_a_postal_code_before_a_town_is_a_location():
    # The models consistently return the town but not the code in front of it.
    assert found("at Voorbeeldstraat 12, 3500 Hasselt today") == {"LOCATION": ["3500"]}


def test_a_bare_four_digit_number_is_not_a_postal_code():
    # The rule requires a following capitalised word, or every year would match.
    assert found("the depot holds 2019 registered bicycles") == {}


def test_check_digits_are_reported_but_never_used_to_reject():
    # A mistyped account number is still an account number, so detection stands
    # whatever the check digits say, and validity is only reported alongside it.
    text = "account NL91 ABNA 0417 1643 09 please"
    assert found(text) == {"IBAN": ["NL91 ABNA 0417 1643 09"]}
    assert regex_rules.is_valid_identifier("IBAN", "NL91 ABNA 0417 1643 09") is False
    assert regex_rules.is_valid_identifier("IBAN", "NL91 ABNA 0417 1643 00") is True


def test_validity_is_stricter_than_detection_needs_to_be():
    # "BE68 5390 0754 7034" is the example IBAN found in most documentation. It
    # passes the international mod-97 check but fails Belgium's own account-number
    # rule, so a validity gate would have discarded a textbook account number.
    # Detection has to stand on its own for exactly this reason.
    assert found("account BE68 5390 0754 7034") == {"IBAN": ["BE68 5390 0754 7034"]}
    assert regex_rules.is_valid_identifier("IBAN", "BE68 5390 0754 7034") is False


def test_load_returns_nothing_to_load():
    assert regex_rules.load() is None
