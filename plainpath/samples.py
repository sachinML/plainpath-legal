"""Load bundled fictional sample documents."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT / "data" / "samples"

SAMPLE_FILES: tuple[tuple[str, str], ...] = (
    ("Oakridge lease (sample A)", "oakridge_lease.txt"),
    ("Oakridge renewal (sample B — compare against A)", "oakridge_renewal.txt"),
    ("Harborline employment agreement", "harborline_employment.txt"),
    ("CloudNest consumer terms", "cloudnest_terms.txt"),
)


def list_samples() -> tuple[str, ...]:
    """Return sample display names."""
    return tuple(name for name, _ in SAMPLE_FILES)


def load_sample(name: str) -> str:
    """Load a sample by display name. Raises FileNotFoundError if missing."""
    for label, filename in SAMPLE_FILES:
        if label == name:
            path = SAMPLES_DIR / filename
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(name)


def load_sample_pair() -> tuple[str, str]:
    """Lease + renewal used by the compare demo."""
    return load_sample(SAMPLE_FILES[0][0]), load_sample(SAMPLE_FILES[1][0])
