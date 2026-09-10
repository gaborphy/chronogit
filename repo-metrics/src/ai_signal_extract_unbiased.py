"""ai_signal_extract.py, pointed at the unbiased vintage cohort.

The scan itself (commit-trailer + marker-file signals) is identical --
it only needs repo_full_name/clone_url/snapshot_sha/vintage_quarter,
which output/vintage_unbiased/packages.csv provides in the same shape as
output/vintage/packages.csv. This wrapper just redirects the I/O paths
so the two cohorts' AI-signal scans land in separate output trees and
neither run's resumability state can collide with the other's.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_signal_extract as base  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
base.VINTAGE_DIR = ROOT / "output" / "vintage_unbiased"
base.AI_SIGNAL_DIR = ROOT / "output" / "ai_signal_unbiased"
base.CLONES_DIR = ROOT / "clones-ai-signal-unbiased"

if __name__ == "__main__":
    base.main()
