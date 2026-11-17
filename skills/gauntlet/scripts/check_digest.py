#!/usr/bin/env python3
"""Check the standards digest for drift and for citations to sections that no longer exist.

Exit codes: 0 clean, 1 stale (standards changed since the digest was written),
2 broken citation (a cited section is missing from standards/).
"""
import re
import subprocess
import sys
from pathlib import Path

TREE_LINE = re.compile(r"<!--\s*synced-standards-tree:\s*(\S+)\s*-->")
CITATION = re.compile(r"\[§(\d+)\.(\d+)\]")


def has_heading(standards_dir, page, section):
    for path in standards_dir.glob(f"{page:02d}-*.md"):
        pattern = re.compile(rf"^#{{2,3}} {page}\.{section}\s", re.MULTILINE)
        if pattern.search(path.read_text()):
            return True
    return False


def check(digest_path, standards_dir, current_tree):
    text = digest_path.read_text()
    problems = []

    match = TREE_LINE.search(text)
    if match is None:
        problems.append("STALE: digest has no synced-standards-tree line")
    elif match.group(1) != current_tree:
        problems.append(
            f"STALE: standards changed since the digest was written "
            f"(digest {match.group(1)[:12]}, now {current_tree[:12]})"
        )

    for page, section in sorted(set(CITATION.findall(text)), key=lambda c: (int(c[0]), int(c[1]))):
        if not has_heading(standards_dir, int(page), section):
            problems.append(f"BROKEN: §{page}.{section} is cited but no such heading exists in standards/")

    return problems


def exit_code(problems):
    if any(p.startswith("BROKEN:") for p in problems):
        return 2
    if any(p.startswith("STALE:") for p in problems):
        return 1
    return 0


def main():
    skill_dir = Path(__file__).resolve().parent.parent
    repo_root = skill_dir.parent.parent
    current_tree = subprocess.run(
        ["git", "rev-parse", "HEAD:standards"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout.strip()

    problems = check(skill_dir / "digest.md", repo_root / "standards", current_tree)
    for problem in problems:
        print(problem)
    return exit_code(problems)


if __name__ == "__main__":
    sys.exit(main())
