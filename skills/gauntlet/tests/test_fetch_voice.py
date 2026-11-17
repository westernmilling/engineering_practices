import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from fetch_voice import fetch_comments, main  # noqa: E402


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


def no_sleep(_seconds):
    pass


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

        comments = fetch_comments("org/repo", "josephbridgwaterrowe", run=fake, sleep=no_sleep)

        self.assertEqual(1, len(comments))
        self.assertEqual(fake.calls[0], fake.calls[1], "the same page is requested again")

    def test_raises_after_retries_exhausted(self):
        fake = FakeGh(*[failure("gh: Server Error (HTTP 502)")] * 3)

        with self.assertRaises(RuntimeError):
            fetch_comments("org/repo", "josephbridgwaterrowe", run=fake, retries=3, sleep=no_sleep)

        self.assertEqual(3, len(fake.calls))

    def test_retries_on_dropped_connection(self):
        for stderr in ("stream error: stream ID 1; CANCEL; received from peer",
                       "connection reset by peer",
                       "context deadline exceeded (Client.Timeout exceeded)"):
            with self.subTest(stderr=stderr):
                fake = FakeGh(
                    failure(stderr),
                    page(api_comment("josephbridgwaterrowe", 7, "app/b.rb", "Why?")),
                    page(),
                )

                comments = fetch_comments("org/repo", "josephbridgwaterrowe", run=fake, sleep=no_sleep)

                self.assertEqual(1, len(comments))

    def test_waits_longer_before_each_retry(self):
        fake = FakeGh(failure("HTTP 502"), failure("HTTP 502"), page(), )
        waits = []

        fetch_comments("org/repo", "josephbridgwaterrowe", run=fake, sleep=waits.append)

        self.assertEqual(2, len(waits))
        self.assertLess(waits[0], waits[1])

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

    def test_matches_the_author_whatever_the_capitalisation(self):
        fake = FakeGh(
            page(api_comment("josephbridgwaterrowe", 3, "a.rb", "Why?")),
            page(),
        )

        comments = fetch_comments("org/repo", "JosephBridgwaterRowe", run=fake)

        self.assertEqual(1, len(comments))


class MainTest(unittest.TestCase):
    def test_missing_gh_is_a_plain_error_not_a_traceback(self):
        def gh_not_installed(*_args, **_kwargs):
            raise FileNotFoundError(2, "No such file or directory", "gh")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["fetch_voice.py", "org/repo", "someone"], run=gh_not_installed)

        self.assertEqual(1, code)
        self.assertIn("fetch_voice:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
