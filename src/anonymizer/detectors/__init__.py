"""Detectors.

Every detector module exposes the same two functions, so the rest of the package
never depends on which one produced a span:

    load()                     -> a loaded model (or None for rule-based detectors)
    detect(model, text)        -> list[Span]
"""
