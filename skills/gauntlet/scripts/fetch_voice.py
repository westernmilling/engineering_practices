#!/usr/bin/env python3
"""Fetch an author's inline PR review comments from a repo, as JSON on stdout.

Usage: fetch_voice.py <owner/repo> <github-login> > comments.json

Pages manually so a server error retries one page, not the whole fetch.
"""
import json
import subprocess
import sys
import time

PER_PAGE = 100
TRANSIENT = ("HTTP 5", "stream error", "connection reset", "timeout", "deadline exceeded", "EOF")


def is_transient(stderr):
    return any(marker in stderr for marker in TRANSIENT)


def fetch_page(repo, page, run, retries, sleep):
    endpoint = f"repos/{repo}/pulls/comments?per_page={PER_PAGE}&page={page}"
    command = ["gh", "api", endpoint]
    for attempt in range(retries):
        result = run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        if not is_transient(result.stderr):
            raise RuntimeError(f"gh api failed: {result.stderr.strip()}")
        if attempt < retries - 1:
            sleep(2 ** attempt)
    raise RuntimeError(f"gh api still failing after {retries} attempts: {result.stderr.strip()}")


def fetch_comments(repo, author, run=subprocess.run, retries=3, sleep=time.sleep):
    comments = []
    wanted = author.lower()
    page = 1
    while True:
        batch = fetch_page(repo, page, run, retries, sleep)
        if not batch:
            return comments
        for comment in batch:
            if comment["user"]["login"].lower() == wanted:
                comments.append(
                    {
                        "pr": int(comment["pull_request_url"].rsplit("/", 1)[-1]),
                        "path": comment["path"],
                        "body": comment["body"],
                    }
                )
        page += 1


def main(argv, run=subprocess.run):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        comments = fetch_comments(argv[1], argv[2], run=run, retries=5)
    except (RuntimeError, OSError) as error:
        print(f"fetch_voice: {error}", file=sys.stderr)
        return 1
    json.dump(comments, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
