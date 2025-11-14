#!/usr/bin/env python3
import hashlib
import json
import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import urllib.request
import urllib.error

# --- Configuration ---------------------------------------------------------

# Root of the tracker repository (adjust if needed)
REPO_ROOT = Path(__file__).resolve().parents[1]

INBOX_DIR = REPO_ROOT / "inbox"
STATE_DIR = REPO_ROOT / ".state"

# Technologies to track and their docs URLs.
TECH_CONFIG: Dict[str, List[str]] = {
    "pytorch": [
        "https://pytorch.org/docs/stable/index.html",
        "https://pytorch.org/blog/",
    ],
    "cuda": [
        "https://docs.nvidia.com/cuda/index.html",
    ],
    "isaac_sim": [
        "https://docs.isaacsim.omniverse.nvidia.com",
    ],
    "isaac_lab": [
        "https://github.com/isaac-sim/IsaacLab",
    ],
    "isaac_ros": [
        "https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_common",
        "https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_visual_slam",
        "https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox",
    ],
    "nav2": [
        "https://github.com/ros-planning/navigation2",
    ],
    "moveit2": [
        "https://github.com/ros-planning/moveit2",
    ],
    "ros2": [
        "https://github.com/ros2/ros2",
    ],
    "jetson_l4t": [
        "https://developer.nvidia.com/embedded/jetson-linux",
    ],
    "omniverse_kit": [
        "https://github.com/NVIDIA-Omniverse/kit-app-template",
    ],
    "replicator": [
        "https://docs.omniverse.nvidia.com/py/replicator/source/overview.html",
    ],
}

# --------------------------------------------------------------------------


def fetch_url(url: str) -> bytes:
    """Fetch raw bytes for a URL, with basic error handling."""
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        print(f"[WARN] Failed to fetch {url}: {e}")
        return b""


def hash_bytes(data: bytes) -> str:
    """Return a stable hex digest for the given bytes."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def load_state(tech: str) -> Dict[str, str]:
    """Load previous hash state for a technology, if any."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path = STATE_DIR / f"{tech}.json"
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(tech: str, state: Dict[str, str]) -> None:
    """Persist hash state for a technology."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path = STATE_DIR / f"{tech}.json"
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def compute_combined_hash(tech: str) -> (str, Dict[str, str]):
    """
    Fetch all URLs for a technology, compute per-URL hashes,
    and a combined hash over all.
    """
    url_hashes: Dict[str, str] = {}
    hasher = hashlib.sha256()

    urls = TECH_CONFIG.get(tech, [])
    if not urls:
        raise ValueError(f"No URLs configured for tech={tech}")

    for url in urls:
        content = fetch_url(url)
        url_hash = hash_bytes(content)
        url_hashes[url] = url_hash
        # Mix into combined hash: url string + hash
        hasher.update(url.encode("utf-8"))
        hasher.update(url_hash.encode("utf-8"))

    combined = hasher.hexdigest()
    return combined, url_hashes


def format_sources(urls: List[str]) -> str:
    return "\n".join(f"- {u}" for u in urls)


def generate_note_content(
    date: datetime, tech: str, urls: List[str], changed: bool, previous_hash: str, new_hash: str
) -> str:
    """Produce a markdown note with a consistent engineering-devlog layout."""
    date_str = date.date().isoformat()
    title = f"{tech.replace('_', ' ').title()} docs – daily check"

    # Frontmatter
    frontmatter = {
        "date": date_str,
        "technology": tech,
        "title": title,
        "tags": ["docs-change" if changed else "docs-check", "auto-generated"],
        "sources": urls,
        "hash_previous": previous_hash or "",
        "hash_current": new_hash,
        "layout": "engineering-devlog",
    }

    fm_lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, list):
            fm_lines.append(f"{key}:")
            for item in value:
                fm_lines.append(f"  - {item}")
        else:
            fm_lines.append(f"{key}: {value}")
    fm_lines.append("---")
    fm = "\n".join(fm_lines)

    # Body: fixed sections to look like a serious engineering log
    if changed:
        summary = textwrap.dedent(
            f"""
            # {title}

            ## Context

            Daily documentation scan for **{tech.replace('_', ' ').title()}**.
            This note is part of the continuous tracking of upstream changes across the stack.

            ## Observed changes

            - Upstream documentation content changed (hash comparison only).
            - The exact diff is not stored here; the goal is to flag the day as
              "docs changed" so it can be reviewed manually when needed.

            ## Technical details

            - Previous combined hash: `{previous_hash or 'N/A'}`
            - New combined hash: `{new_hash}`

            ### Tracked sources

            {format_sources(urls)}

            ## Impact

            - Potentially affects local notes, learning material, or code relying on
              the documented APIs/behaviour.
            - Recommended to skim the relevant sections if actively working with this
              technology this week.

            ## Follow-up

            - [ ] Review the upstream docs and identify the most relevant changes.
            - [ ] Update local notes or examples if any breaking or important behavioural
                  changes are found.
            - [ ] (Optional) Capture a short manual summary in a separate note if the
                  change is substantial.
            """
        ).strip()
    else:
        summary = textwrap.dedent(
            f"""
            # {title}

            ## Context

            Daily documentation scan for **{tech.replace('_', ' ').title()}**.
            On this run, no relevant content drift was detected based on hash comparison.

            ## Observed changes

            - No significant differences in the tracked documentation sources.

            ## Technical details

            - Combined hash: `{new_hash}`

            ### Tracked sources

            {format_sources(urls)}

            ## Impact

            - Local notes and examples are still aligned with the current upstream docs
              (as far as this coarse check can tell).

            ## Follow-up

            - [ ] No immediate action required.
            - [ ] (Optional) Skim the docs if you are about to start new work related
                  to this technology.
            """
        ).strip()

    return f"{fm}\n\n{summary}\n"


def write_note(tech: str, content: str, date: datetime) -> Path:
    """Write the note to inbox with a consistent filename."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    date_str = date.date().isoformat()
    filename = f"{date_str}_{tech}_docs_update.md"
    path = INBOX_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"[INFO] Wrote note for {tech}: {path.relative_to(REPO_ROOT)}")
    return path


def process_tech(tech: str, now: datetime) -> None:
    print(f"[INFO] Processing technology: {tech}")
    old_state = load_state(tech)
    old_combined_hash = old_state.get("combined_hash", "")

    combined_hash, url_hashes = compute_combined_hash(tech)

    changed = combined_hash != old_combined_hash

    note_content = generate_note_content(
        date=now,
        tech=tech,
        urls=TECH_CONFIG[tech],
        changed=changed,
        previous_hash=old_combined_hash,
        new_hash=combined_hash,
    )
    write_note(tech, note_content, now)

    # Save state
    new_state = {"combined_hash": combined_hash, "url_hashes": url_hashes}
    save_state(tech, new_state)


def main() -> None:
    now = datetime.now(timezone.utc)
    print(f"[INFO] Starting docs tracking at {now.isoformat()}")

    for tech in sorted(TECH_CONFIG.keys()):
        process_tech(tech, now)

    print("[INFO] Done.")


if __name__ == "__main__":
    main()
