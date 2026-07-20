"""The detector configurations, shared by the benchmark and the API.

Deliberately split in two.

CORE is the comparison the exercise asked for: two pre-trained NER models measured
against each other, plus each one paired with the rule layer. Those numbers are the
result being reported, so nothing is added to this list.

EXTENDED is exploration that came afterwards, kept separate so it cannot be confused
with the required comparison or quietly change it.
"""

from dataclasses import dataclass

from .detectors import (
    gliner_model,
    hf_model,
    hf_ontonotes,
    regex_rules,
    spacy_model,
)


@dataclass(frozen=True)
class Configuration:
    """A named list of detectors, highest priority first."""

    key: str
    label: str
    detectors: list
    # False for configurations added after the required comparison.
    core: bool = True
    # Set when a configuration needs a package that is not in the lock file.
    requires: str | None = None

    def available(self) -> bool:
        """Whether this configuration can actually run in this environment."""
        if self.requires == "gliner":
            return gliner_model.is_available()
        return True

    @property
    def uses_rules(self) -> bool:
        """Whether the rule layer is part of this configuration.

        Kept separable because the rules only cover five of the twelve labels, so a
        configuration that includes them measures a system rather than a model.
        """
        return regex_rules in self.detectors


CORE_CONFIGURATIONS = [
    Configuration("spacy", "spaCy sm", [spacy_model]),
    Configuration("hf", "HF bert", [hf_model]),
    Configuration("spacy+regex", "spaCy+regex", [regex_rules, spacy_model]),
    Configuration("hf+regex", "HF+regex", [regex_rules, hf_model]),
]

EXTENDED_CONFIGURATIONS = [
    # A transformer trained on OntoNotes rather than CoNLL, so it competes on the
    # same label scheme as spaCy. Answers the fair objection that the CoNLL model
    # lost on coverage rather than on architecture.
    Configuration("onto", "HF onto", [hf_ontonotes], core=False),
    Configuration("onto+regex", "HF onto+regex", [regex_rules, hf_ontonotes], core=False),
    # Zero-shot, and the only configuration that can reach JOB and UNIVERSITY.
    Configuration("gliner", "GLiNER", [gliner_model], core=False, requires="gliner"),
    Configuration(
        "gliner+regex",
        "GLiNER+regex",
        [regex_rules, gliner_model],
        core=False,
        requires="gliner",
    ),
]

CONFIGURATIONS = CORE_CONFIGURATIONS + EXTENDED_CONFIGURATIONS

# Best F1 in the required comparison, so it is the sensible default for the API.
DEFAULT_KEY = "spacy+regex"


def by_key(key: str) -> Configuration | None:
    """Look up a configuration by its key, or None if there is no such key."""
    for configuration in CONFIGURATIONS:
        if configuration.key == key:
            return configuration
    return None


def runnable(configurations: list[Configuration]) -> list[Configuration]:
    """Those configurations whose optional dependencies are installed."""
    return [c for c in configurations if c.available()]


def models_only(configurations: list[Configuration]) -> list[Configuration]:
    """Configurations that are a model on its own, with no rule layer.

    This is what a model-against-model comparison must be built from: the rules
    cover only five of the twelve labels, so including them measures the system
    rather than the model, and inflates every score with the same easy wins.
    """
    return [c for c in configurations if not c.uses_rules]


def with_rules(configurations: list[Configuration]) -> list[Configuration]:
    """Configurations that pair a model with the rule layer."""
    return [c for c in configurations if c.uses_rules]
