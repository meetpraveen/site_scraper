from __future__ import annotations

import runpy
import sys
from pathlib import Path


if __name__ == "__main__":
    site_dir = Path(__file__).resolve().parent / "sites" / "mycaseshub"
    sys.path.insert(0, str(site_dir))
    runpy.run_path(str(site_dir / "resanitize_run.py"), run_name="__main__")
