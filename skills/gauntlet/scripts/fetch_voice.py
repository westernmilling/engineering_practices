#!/usr/bin/env python3
"""Fetch an author's inline PR review comments from a repo, as JSON on stdout.

Usage: fetch_voice.py <owner/repo> <github-login> > comments.json

Pages manually so a server error retries one page, not the whole fetch.
"""
import json
import subprocess
import sys

PER_PAGE = 100


def fetch_page(repo, page, run, retries):
    endpoint = f"repos/{repo}/pulls/comments?per_page={PER_PAGE}&page={page}"
    command = ["gh", "api", endpoint]
    for _ in range(retries):
        result = run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        if "HTTP 5" not in result.stderr:
            raise RuntimeError(f"gh api failed: {result.stderr.strip()}")
    raise RuntimeError(f"gh api still failing after {retries} attempts: {result.stderr.strip()}")


def fetch_comments(repo, author, run=subprocess.run, retries=3):
    comments = []
    page = 1
    while True:
        batch = fetch_page(repo, page, run, retries)
        if not batch:
            return comments
        for comment in batch:
            if comment["user"]["login"] == author:
                comments.append(
                    {
                        "pr": int(comment["pull_request_url"].rsplit("/", 1)[-1]),
                        "path": comment["path"],
                        "body": comment["body"],
                    }
                )
        page += 1


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    json.dump(fetch_comments(argv[1], argv[2]), sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
