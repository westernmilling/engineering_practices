import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from post_review import BADGE_URL, build_review, extract_markers, main, marker_id, parse_diff_lines  # noqa: E402

DIFF = """\
diff --git a/app/services/create_contract.rb b/app/services/create_contract.rb
index 111..222 100644
--- a/app/services/create_contract.rb
+++ b/app/services/create_contract.rb
@@ -1,2 +1,4 @@
 class CreateContract
+  def call
+  end
 end
diff --git a/old.rb b/old.rb
deleted file mode 100644
--- a/old.rb
+++ /dev/null
@@ -1,2 +0,0 @@
-gone
-gone
"""

CREDIT = "🤖 Drafted with Claude Code, reviewed and approved by Joe Bridgwater-Rowe before posting."


def draft_with(*comments):
    return {
        "repo": "org/repo",
        "pr": 9,
        "summary": "Treating this as built to stand.",
        "comments": list(comments),
    }


def comment(path="app/a.rb", line=2, body="Was the transaction intentional?"):
    return {"path": path, "line": line, "body": body}


IN_DIFF = {"app/a.rb": {1, 2, 3}}


class ParseDiffLinesTest(unittest.TestCase):
    def test_parse_diff_lines_tracks_added_and_context_lines(self):
        lines = parse_diff_lines(DIFF)

        self.assertEqual({1, 2, 3, 4}, lines["app/services/create_contract.rb"])

    def test_deleted_files_have_no_commentable_lines(self):
        self.assertNotIn("old.rb", parse_diff_lines(DIFF))


    def test_added_line_that_looks_like_a_file_header_stays_content(self):
        diff = (
            "diff --git a/a.rb b/a.rb\n--- a/a.rb\n+++ b/a.rb\n@@ -1,2 +1,4 @@\n"
            " keep\n+++ counter;\n+x = 1\n end\n"
        )

        self.assertEqual({1, 2, 3, 4}, parse_diff_lines(diff)["a.rb"])

    def test_added_line_cannot_invent_a_file(self):
        diff = (
            "diff --git a/a.rb b/a.rb\n--- a/a.rb\n+++ b/a.rb\n@@ -1,1 +1,3 @@\n"
            " keep\n+++ b/other.rb\n+y = 2\n"
        )

        self.assertEqual(["a.rb"], list(parse_diff_lines(diff)))

    def test_a_second_file_after_a_hunk_is_still_recognised(self):
        diff = (
            "diff --git a/a.rb b/a.rb\n--- a/a.rb\n+++ b/a.rb\n@@ -1,1 +1,2 @@\n keep\n+new\n"
            "diff --git a/b.rb b/b.rb\n--- a/b.rb\n+++ b/b.rb\n@@ -1,1 +1,2 @@\n keep\n+new\n"
        )

        self.assertEqual({"a.rb", "b.rb"}, set(parse_diff_lines(diff)))


class BuildReviewTest(unittest.TestCase):
    def test_event_is_always_comment(self):
        review = build_review(draft_with(comment()), "Joe Bridgwater-Rowe", set(), IN_DIFF)

        self.assertEqual("COMMENT", review["event"])

    def test_credit_line_on_summary_only_with_reviewer_name(self):
        review = build_review(draft_with(comment()), "Joe Bridgwater-Rowe", set(), IN_DIFF)

        self.assertTrue(review["body"].endswith(CREDIT))
        self.assertNotIn("Drafted with Claude Code", review["comments"][0]["body"])

    def test_credit_line_names_the_agent_that_drafted_it(self):
        review = build_review(draft_with(comment()), "Joe", set(), IN_DIFF, agent="Codex")

        self.assertIn("Drafted with Codex, reviewed and approved by Joe before posting.", review["body"])
        self.assertNotIn("Claude Code", review["body"])

    def test_summary_embeds_the_badge_before_the_credit_line(self):
        review = build_review(draft_with(comment()), "Joe", set(), IN_DIFF)

        badge = f'<img src="{BADGE_URL}"'
        self.assertIn(badge, review["body"])
        self.assertLess(review["body"].index(badge), review["body"].index("Drafted with Claude Code"))
        self.assertNotIn(badge, review["comments"][0]["body"])

    def test_inline_comment_targets_right_side_and_carries_marker(self):
        review = build_review(draft_with(comment()), "Joe", set(), IN_DIFF)

        inline = review["comments"][0]
        self.assertEqual("RIGHT", inline["side"])
        self.assertEqual(2, inline["line"])
        self.assertIn(
            f"<!-- gauntlet:{marker_id('app/a.rb', 2, 'Was the transaction intentional?')} -->",
            inline["body"],
        )

    def test_comment_outside_diff_moves_to_summary_as_path_line(self):
        outside = comment(path="app/a.rb", line=99, body="Is this constant explained anywhere?")

        review = build_review(draft_with(comment(), outside), "Joe", set(), IN_DIFF)

        self.assertEqual(1, len(review["comments"]))
        self.assertIn("app/a.rb:99", review["body"])
        self.assertIn("Is this constant explained anywhere?", review["body"])

    def test_comment_on_a_file_not_in_the_diff_moves_to_summary(self):
        elsewhere = comment(path="app/other.rb", line=1, body="Same naming issue here.")

        review = build_review(draft_with(comment(), elsewhere), "Joe", set(), IN_DIFF)

        self.assertIn("app/other.rb:1", review["body"])

    def test_existing_marker_is_skipped(self):
        existing = {marker_id("app/a.rb", 2, "Was the transaction intentional?")}
        fresh = comment(line=3, body="Why not a guard clause?")

        review = build_review(draft_with(comment(), fresh), "Joe", existing, IN_DIFF)

        self.assertEqual(["Why not a guard clause?"], [c["body"].split("\n")[0] for c in review["comments"]])

    def test_review_is_pinned_to_the_reviewed_commit(self):
        review = build_review(draft_with(comment()), "Joe", set(), IN_DIFF, head_sha="abc123")

        self.assertEqual("abc123", review["commit_id"])

    def test_returns_none_when_all_comments_exist(self):
        existing = {marker_id("app/a.rb", 2, "Was the transaction intentional?")}

        self.assertIsNone(build_review(draft_with(comment()), "Joe", existing, IN_DIFF))

    def test_returns_none_when_there_are_no_findings(self):
        self.assertIsNone(build_review(draft_with(), "Joe", set(), IN_DIFF))

    def test_extract_markers_finds_ids_in_any_body(self):
        marker = marker_id("app/a.rb", 2, "x")
        bodies = [f"text\n<!-- gauntlet:{marker} -->", "no marker here"]

        self.assertEqual({marker}, extract_markers(bodies))


class FakeGh:
    """Answers gh calls by command shape and records them."""

    def __init__(self, live_head="abc123"):
        self.calls = []
        self.live_head = live_head

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        joined = " ".join(args)
        if args[-1] == ".head.sha":
            out = self.live_head + "\n"
        elif args[:3] == ["gh", "api", "user"]:
            out = "Joe Bridgwater-Rowe\n"
        elif "pulls/9/comments" in joined or "pulls/9/reviews" in joined and "--input" not in args:
            out = "[]"
        elif args[:3] == ["gh", "pr", "diff"]:
            out = DIFF
        else:
            out = "{}"
        return subprocess.CompletedProcess(args, 0, out, "")

    def posted(self):
        return [c for c in self.calls if "--input" in c]


class MainTest(unittest.TestCase):
    def write_draft(self, **extra):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        self.addCleanup(Path(tmp.name).unlink)
        draft = draft_with(comment(path="app/services/create_contract.rb", line=2))
        draft.update({"head_sha": "abc123", **extra})
        json.dump(draft, tmp)
        tmp.close()
        return tmp.name

    def test_dry_run_does_not_post(self):
        fake = FakeGh()

        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["post_review.py", self.write_draft(), "--dry-run"], run=fake)

        self.assertEqual(0, code)
        self.assertEqual([], fake.posted())

    def test_agent_flag_reaches_the_credit_line(self):
        fake = FakeGh()
        out = io.StringIO()

        with contextlib.redirect_stdout(out):
            main(["post_review.py", self.write_draft(), "--dry-run", "--agent", "Codex"], run=fake)

        self.assertIn("Drafted with Codex", json.loads(out.getvalue())["body"])

    def test_real_run_posts_exactly_one_review(self):
        fake = FakeGh()

        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["post_review.py", self.write_draft()], run=fake)

        self.assertEqual(0, code)
        self.assertEqual(1, len(fake.posted()))
        self.assertIn("repos/org/repo/pulls/9/reviews", fake.posted()[0])

    def test_refuses_to_post_when_the_head_has_moved(self):
        fake = FakeGh(live_head="def456")
        stderr = io.StringIO()

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = main(["post_review.py", self.write_draft()], run=fake)

        self.assertEqual(1, code)
        self.assertEqual([], fake.posted())
        self.assertIn("moved", stderr.getvalue())

    def test_dry_run_also_refuses_when_the_head_has_moved(self):
        fake = FakeGh(live_head="def456")

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = main(["post_review.py", self.write_draft(), "--dry-run"], run=fake)

        self.assertEqual(1, code)

    def test_refuses_a_draft_with_no_head_sha(self):
        fake = FakeGh()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = main(["post_review.py", self.write_draft(head_sha=None)], run=fake)

        self.assertEqual(1, code)
        self.assertEqual([], fake.posted())
        self.assertIn("head_sha", stderr.getvalue())

    def test_review_payload_carries_the_commit_id(self):
        out = io.StringIO()

        with contextlib.redirect_stdout(out):
            main(["post_review.py", self.write_draft(), "--dry-run"], run=FakeGh())

        self.assertEqual("abc123", json.loads(out.getvalue())["commit_id"])


if __name__ == "__main__":
    unittest.main()
