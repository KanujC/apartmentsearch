"""
Seen-listings store.
Persists a set of listing IDs to seen_ids.json so we never email the same flat twice.
In GitHub Actions the file is committed back to the repo after each run.
"""

import json
import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

STORE_PATH = Path(os.environ.get("SEEN_STORE", "seen_ids.json"))


def load_seen() -> set[str]:
    if STORE_PATH.exists():
        try:
            return set(json.loads(STORE_PATH.read_text()))
        except Exception as e:
            log.warning(f"Could not load seen store: {e}")
    return set()


def save_seen(ids: set[str]):
    try:
        STORE_PATH.write_text(json.dumps(sorted(ids), indent=2))
        log.info(f"Saved {len(ids)} seen IDs to {STORE_PATH}")
    except Exception as e:
        log.error(f"Could not save seen store: {e}")


def filter_new(listings, seen: set[str]) -> list:
    return [l for l in listings if l.id not in seen]
