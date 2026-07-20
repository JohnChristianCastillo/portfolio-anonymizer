"""Download the model weights into the cache, with progress, before serving.

    uv run python -m anonymizer.warm

The API loads its models at startup, so without a populated cache the first boot
blocks on a download of roughly two gigabytes. Running this first turns that into a
visible, resumable step instead of a service that looks hung.

In the deployment HF_HOME points at a named volume, so this is needed once and the
weights survive later rebuilds:

    docker compose run --rm anonymizer /app/.venv/bin/python -m anonymizer.warm

Only the configurations this instance will actually serve are fetched, so setting
ANONYMIZER_CONFIGS also narrows what gets downloaded.
"""

import os
import sys
import time

from .api import _enabled_configurations


def main() -> None:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    print(f"cache: {os.environ.get('HF_HOME', '(default)')}")
    print(f"token: {'set' if token else 'not set, downloads may be rate limited'}")

    detectors = []
    for configuration in _enabled_configurations():
        for detector in configuration.detectors:
            if detector not in detectors:
                detectors.append(detector)

    failed = []
    for index, detector in enumerate(detectors, start=1):
        name = detector.MODEL_NAME
        # The library prints its own warnings while loading, so the result goes on
        # its own line rather than being appended to this one.
        print(f"[{index}/{len(detectors)}] {name}", flush=True)
        started = time.monotonic()
        try:
            detector.load()
        except Exception as error:  # noqa: BLE001 - report and continue to the next
            print(f"    FAILED  {error.__class__.__name__}: {error}", flush=True)
            failed.append(name)
            continue
        print(f"    ready in {time.monotonic() - started:.0f}s", flush=True)

    if failed:
        print(f"\n{len(failed)} model(s) could not be fetched: {', '.join(failed)}")
        print("Re-run to resume; completed downloads are kept.")
        sys.exit(1)

    print(f"\n{len(detectors)} model(s) ready.")


if __name__ == "__main__":
    main()
