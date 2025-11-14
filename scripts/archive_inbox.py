#!/usr/bin/env python3
import re
import shutil
from pathlib import Path

# Root of the tracker repository (adjust if needed)
REPO_ROOT = Path(__file__).resolve().parents[1]

INBOX_DIR = REPO_ROOT / "inbox"

TECH_DIRS = {
    "pytorch": REPO_ROOT / "pytorch",
    "cuda": REPO_ROOT / "cuda",
    "isaac_sim": REPO_ROOT / "isaac_sim",
    "isaac_lab": REPO_ROOT / "isaac_lab",
    "isaac_ros": REPO_ROOT / "isaac_ros",
    "nav2": REPO_ROOT / "nav2",
    "moveit2": REPO_ROOT / "moveit2",
    "ros2": REPO_ROOT / "ros2",
    "jetson_l4t": REPO_ROOT / "jetson_l4t",
    "omniverse_kit": REPO_ROOT / "omniverse_kit",
    "replicator": REPO_ROOT / "replicator",
}

MISC_DIR = REPO_ROOT / "misc"


def ensure_dirs():
    for path in TECH_DIRS.values():
        path.mkdir(parents=True, exist_ok=True)
    MISC_DIR.mkdir(parents=True, exist_ok=True)


def extract_technology_from_frontmatter(path: Path) -> str:
    """Look for 'technology: xxx' inside the first YAML frontmatter block."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        return ""

    tech = ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"technology:\s*([A-Za-z0-9_\-]+)", line.strip())
        if m:
            tech = m.group(1).strip()
            break

    return tech


def archive_file(md_path: Path):
    tech = extract_technology_from_frontmatter(md_path)
    if tech in TECH_DIRS:
        target_dir = TECH_DIRS[tech]
    else:
        print(f"[WARN] Unknown or missing technology in {md_path.name}, sending to misc/")
        target_dir = MISC_DIR

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / md_path.name

    print(f"[INFO] Moving {md_path.relative_to(REPO_ROOT)} -> {target_path.relative_to(REPO_ROOT)}")
    shutil.move(str(md_path), str(target_path))


def main():
    ensure_dirs()
    if not INBOX_DIR.exists():
        print("[INFO] Inbox directory does not exist. Nothing to archive.")
        return

    md_files = sorted(INBOX_DIR.glob("*.md"))
    if not md_files:
        print("[INFO] No markdown files in inbox. Nothing to archive.")
        return

    for md_path in md_files:
        archive_file(md_path)


if __name__ == "__main__":
    main()
