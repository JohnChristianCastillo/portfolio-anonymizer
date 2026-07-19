"""The detector configurations, shared by the benchmark and the API."""

from dataclasses import dataclass

import hf_detector
import regex_detector
import spacy_detector


@dataclass(frozen=True)
class Configuration:
    """A named list of detectors, highest priority first."""

    key: str
    label: str
    detectors: list


CONFIGURATIONS = [
    Configuration("spacy", "spaCy sm", [spacy_detector]),
    Configuration("hf", "HF bert", [hf_detector]),
    Configuration("spacy+regex", "spaCy+regex", [regex_detector, spacy_detector]),
    Configuration("hf+regex", "HF+regex", [regex_detector, hf_detector]),
]

# Best F1 in the benchmark, so it is the sensible default for the API.
DEFAULT_KEY = "spacy+regex"


def by_key(key: str) -> Configuration | None:
    """Look up a configuration by its key, or None if there is no such key."""
    for configuration in CONFIGURATIONS:
        if configuration.key == key:
            return configuration
    return None
