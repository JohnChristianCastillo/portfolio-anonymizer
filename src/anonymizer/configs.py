"""The detector configurations, shared by the benchmark and the API."""

from dataclasses import dataclass

from .detectors import hf_model, regex_rules, spacy_model


@dataclass(frozen=True)
class Configuration:
    """A named list of detectors, highest priority first."""

    key: str
    label: str
    detectors: list


CONFIGURATIONS = [
    Configuration("spacy", "spaCy sm", [spacy_model]),
    Configuration("hf", "HF bert", [hf_model]),
    Configuration("spacy+regex", "spaCy+regex", [regex_rules, spacy_model]),
    Configuration("hf+regex", "HF+regex", [regex_rules, hf_model]),
]

# Best F1 in the benchmark, so it is the sensible default for the API.
DEFAULT_KEY = "spacy+regex"


def by_key(key: str) -> Configuration | None:
    """Look up a configuration by its key, or None if there is no such key."""
    for configuration in CONFIGURATIONS:
        if configuration.key == key:
            return configuration
    return None
