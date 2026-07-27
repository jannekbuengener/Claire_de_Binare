"""python -m ci.publisher entrypoint."""

from __future__ import annotations

from ci.publisher.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
