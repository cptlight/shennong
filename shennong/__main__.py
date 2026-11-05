"""Allow ``python -m shennong <stage> …`` as an alias for ``python -m shennong.cli``."""

from __future__ import annotations

from shennong.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
