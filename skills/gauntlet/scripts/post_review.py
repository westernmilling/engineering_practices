#!/usr/bin/env python3
"""Build a comment-only GitHub review from a draft and post it.

Usage: post_review.py draft.json [--dry-run] [--agent NAME]

draft.json: {"repo": "owner/repo", "pr": 9, "head_sha": "<PR head commit>", "summary": "...",
             "comments": [{"path": "...", "line": 12, "body": "..."}]}

--agent names the tool that drafted the review in the credit line (default "Claude Code").
The script refuses to run if the PR's head is no longer head_sha, and pins the review to it.
--dry-run prints the review payload and posts nothing. Always run it first and show
the result to the user: a real run posts under their name.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys

MARKER = re.compile(r"<!-- gauntlet:([0-9a-f]{12}) -->")
HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
BADGE_URL = (
    "https://github.com/westernmilling/engineering_practices/blob/main/"
    "skills/gauntlet/assets/badge.png?raw=true"
)
BADGE = f'<p align="center"><img src="{BADGE_URL}" width="72" alt="The Gauntlet"></p>'
DEFAULT_AGENT = "Claude Code"
CREDIT = "🤖 Drafted with {agent}, reviewed and approved by {reviewer} before posting."


def marker_id(path, line, body):
    return hashlib.sha1(f"{path}:{line}:{body}".encode()).hexdigest()[:12]


def marker_comment(path, line, body):
    return f"<!-- gauntlet:{marker_id(path, line, body)} -->"


def extract_markers(bodies):
    found = set()
    for body in bodies:
        found.update(MARKER.findall(body or ""))
    return found


def parse_diff_lines(diff_text):
    """New-side line numbers present in each file's hunks (added and context lines).

    Hunk headers say how many old and new lines follow, so a content line that looks like a
    file header (an added "++ x" shows as "+++ x") is read as content while a hunk is open.
    """
    lines_by_path = {}
    path = None
    new_line = 0
    old_left = new_left = 0
    for line in diff_text.splitlines():
        if old_left > 0 or new_left > 0:
            marker = line[:1]
            if marker == " ":
                old_left -= 1
                new_left -= 1
                if path is not None:
                    lines_by_path[path].add(new_line)
                new_line += 1
            elif marker == "+":
                new_left -= 1
                if path is not None:
                    lines_by_path[path].add(new_line)
                new_line += 1
            elif marker == "-":
                old_left -= 1
            continue
        if line.startswith("+++ "):
            target = line[4:]
            path = target[2:] if target.startswith("b/") else None
            if path is not None:
                lines_by_path[path] = set()
        elif (hunk := HUNK.match(line)):
            old_left = int(hunk.group(1) if hunk.group(1) is not None else 1)
            new_left = int(hunk.group(3) if hunk.group(3) is not None else 1)
            new_line = int(hunk.group(2))
    return lines_by_path


def build_review(draft, reviewer, existing_markers, diff_lines, agent=DEFAULT_AGENT, head_sha=None):
    inline = []
    moved = []
    for comment in draft["comments"]:
        path, line, body = comment["path"], comment["line"], comment["body"]
        if marker_id(path, line, body) in existing_markers:
            continue
        marker = marker_comment(path, line, body)
        if line in diff_lines.get(path, set()):
            inline.append(
                {"path": path, "line": line, "side": "RIGHT", "body": f"{body}\n\n{marker}"}
            )
        else:
            moved.append(f"- `{path}:{line}` — {body} {marker}")

    if not inline and not moved:
        return None

    summary = BADGE + "\n\n" + draft["summary"]
    if moved:
        summary += "\n\nComments on lines outside the diff:\n" + "\n".join(moved)
    summary += "\n\n" + CREDIT.format(agent=agent, reviewer=reviewer)
    review = {"event": "COMMENT", "body": summary, "comments": inline}
    if head_sha:
        review["commit_id"] = head_sha
    return review


def gh(run, *args, stdin=None):
    result = run(["gh", *args], capture_output=True, text=True, input=stdin)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def paginated_bodies(run, endpoint):
    pages = json.loads(gh(run, "api", "--paginate", "--slurp", endpoint) or "[]")
    items = [item for page in pages for item in (page if isinstance(page, list) else [page])]
    return [item.get("body") or "" for item in items]


def main(argv, run=subprocess.run):
    parser = argparse.ArgumentParser(prog="post_review.py", description=__doc__.split("\n")[0])
    parser.add_argument("draft")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--agent", default=DEFAULT_AGENT)
    options = parser.parse_args(argv[1:])
    dry_run = options.dry_run

    with open(options.draft) as handle:
        draft = json.load(handle)
    repo, pr = draft["repo"], draft["pr"]

    head_sha = draft.get("head_sha")
    if not head_sha:
        print("post_review: the draft has no head_sha. Record the PR's head commit when "
              "gathering it, so the review is pinned to the code you read.", file=sys.stderr)
        return 1
    live_head = gh(run, "api", f"repos/{repo}/pulls/{pr}", "--jq", ".head.sha").strip()
    if live_head != head_sha:
        print(f"post_review: the PR head has moved since this review was drafted "
              f"(drafted against {head_sha[:12]}, now {live_head[:12]}). Re-run the review "
              f"against the current head.", file=sys.stderr)
        return 1

    reviewer = gh(run, "api", "user", "--jq", ".name // .login").strip()
    existing = extract_markers(
        paginated_bodies(run, f"repos/{repo}/pulls/{pr}/comments")
        + paginated_bodies(run, f"repos/{repo}/pulls/{pr}/reviews")
    )
    diff_lines = parse_diff_lines(gh(run, "pr", "diff", str(pr), "-R", repo))

    review = build_review(draft, reviewer, existing, diff_lines, agent=options.agent, head_sha=head_sha)
    if review is None:
        print("Nothing new to post.")
        return 0

    if dry_run:
        print(json.dumps(review, indent=2, ensure_ascii=False))
        return 0

    gh(run, "api", f"repos/{repo}/pulls/{pr}/reviews", "--method", "POST", "--input", "-",
       stdin=json.dumps(review))
    print(f"Posted review with {len(review['comments'])} inline comment(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
