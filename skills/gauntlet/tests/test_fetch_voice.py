import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from fetch_voice import fetch_comments  # noqa: E402


def api_comment(author, number, path, body):
    return {
        "user": {"login": author},
        "pull_request_url": f"https://api.github.com/repos/org/repo/pulls/{number}",
        "path": path,
        "body": body,
    }


class FakeGh:
    """Stands in for subprocess.run, answering each call from a queue."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        stdout, returncode, stderr = self.responses.pop(0)
        return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def page(*comments):
    return (json.dumps(list(comments)), 0, "")


def failure(stderr):
    return ("", 1, stderr)


class FetchCommentsTest(unittest.TestCase):
    def test_filters_to_author(self):
        fake = FakeGh(
            page(
                api_comment("josephbridgwaterrowe", 12, "app/a.rb", "Was this intentional?"),
                api_comment("someone-else", 12, "app/a.rb", "Looks good"),
            ),
            page(),
        )

        comments = fetch_comments("org/repo", "josephbridgwaterrowe", run=fake)

        self.assertEqual(
            [{"pr": 12, "path": "app/a.rb", "body": "Was this intentional?"}], comments
        )

    def test_retries_on_502_then_succeeds(self):
        fake = FakeGh(
            failure("gh: Server Error (HTTP 502)"),
            page(api_comment("josephbridgwaterrowe", 7, "app/b.rb", "Why a transaction here?")),
            page(),
        )

        comments = fetch_comments("org/repo", "josephbridgwaterrowe", run=fake)

        self.assertEqual(1, len(comments))
        self.assertEqual(fake.calls[0], fake.calls[1], "the same page is requested again")

    def test_raises_after_retries_exhausted(self):
        fake = FakeGh(*[failure("gh: Server Error (HTTP 502)")] * 3)

        with self.assertRaises(RuntimeError):
            fetch_comments("org/repo", "josephbridgwaterrowe", run=fake, retries=3)

        self.assertEqual(3, len(fake.calls))

    def test_non_server_error_is_not_retried(self):
        fake = FakeGh(failure("gh: Not Found (HTTP 404)"))

        with self.assertRaises(RuntimeError):
            fetch_comments("org/repo", "josephbridgwaterrowe", run=fake)

        self.assertEqual(1, len(fake.calls))

    def test_collects_every_page_until_an_empty_one(self):
        fake = FakeGh(
            page(api_comment("josephbridgwaterrowe", 1, "a.rb", "one")),
            page(api_comment("josephbridgwaterrowe", 2, "b.rb", "two")),
            page(),
        )

        comments = fetch_comments("org/repo", "josephbridgwaterrowe", run=fake)

        self.assertEqual([1, 2], [c["pr"] for c in comments])
        self.assertIn("page=2", fake.calls[1][-1])


if __name__ == "__main__":
    unittest.main()
