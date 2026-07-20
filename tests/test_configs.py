"""The detector configurations.

The exercise asked for a comparison of two pre-trained NER models. Models explored
afterwards must not quietly join that comparison or change its result, so the split
between the required set and the rest is asserted here rather than left to care.
"""

from anonymizer import configs
from anonymizer.detectors import regex_rules


def test_the_required_comparison_is_exactly_these_four():
    assert [c.key for c in configs.CORE_CONFIGURATIONS] == [
        "spacy",
        "hf",
        "spacy+regex",
        "hf+regex",
    ]


def test_the_required_comparison_uses_two_distinct_models():
    models = set()
    for configuration in configs.CORE_CONFIGURATIONS:
        for detector in configuration.detectors:
            # Compare the module, not its name, so renaming the rule layer cannot
            # silently let it count as a third model.
            if detector is not regex_rules:
                models.add(detector.MODEL_NAME)
    assert len(models) == 2


def test_every_core_configuration_is_marked_core():
    assert all(c.core for c in configs.CORE_CONFIGURATIONS)


def test_no_extended_configuration_is_marked_core():
    assert not any(c.core for c in configs.EXTENDED_CONFIGURATIONS)


def test_the_default_configuration_covers_every_required_label():
    """The app is asked to handle all twelve entity types, so its default must.

    This deliberately does not require the default to come from the required
    comparison: every configuration in that comparison scores zero on JOB and
    UNIVERSITY, because no standard NER scheme contains those classes.
    """
    default = configs.by_key(configs.DEFAULT_KEY)
    assert default is not None
    assert configs.DEFAULT_KEY == configs.FULL_COVERAGE_KEY


def test_keys_are_unique():
    keys = [c.key for c in configs.CONFIGURATIONS]
    assert len(keys) == len(set(keys))


def test_configurations_is_core_followed_by_extended():
    assert (
        configs.CONFIGURATIONS
        == configs.CORE_CONFIGURATIONS + configs.EXTENDED_CONFIGURATIONS
    )


def test_core_configurations_need_no_optional_package():
    assert all(c.requires is None for c in configs.CORE_CONFIGURATIONS)
    assert all(c.available() for c in configs.CORE_CONFIGURATIONS)


def test_runnable_filters_out_unavailable_configurations():
    runnable = configs.runnable(configs.CONFIGURATIONS)
    assert all(c.available() for c in runnable)
    # The required comparison must always be runnable.
    for configuration in configs.CORE_CONFIGURATIONS:
        assert configuration in runnable


def test_by_key_returns_none_for_an_unknown_key():
    assert configs.by_key("no-such-config") is None
