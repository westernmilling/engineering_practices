import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_digest import check, exit_code  # noqa: E402


def write_standards(root, pages):
    for filename, headings in pages.items():
        (root / filename).write_text("\n".join(headings) + "\n")


def write_digest(path, tree, entries):
    lines = [f"<!-- synced-standards-tree: {tree} -->", ""]
    lines += [f"- [{section}] {text}" for section, text in entries]
    path.write_text("\n".join(lines) + "\n")


class CheckDigestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.standards = self.root / "standards"
        self.standards.mkdir()
        self.digest = self.root / "digest.md"

    def test_clean_digest_returns_no_problems(self):
        write_standards(self.standards, {"03-testing.md": ["## 3.4 Inline variables only"]})
        write_digest(self.digest, "abc123", [("§3.4", "No let.")])

        problems = check(self.digest, self.standards, "abc123")

        self.assertEqual([], problems)

    def test_stale_tree_is_reported(self):
        write_standards(self.standards, {"03-testing.md": ["## 3.4 Inline variables only"]})
        write_digest(self.digest, "abc123", [("§3.4", "No let.")])

        problems = check(self.digest, self.standards, "def456")

        self.assertEqual(1, len(problems))
        self.assertTrue(problems[0].startswith("STALE:"))

    def test_citation_to_missing_section_is_reported(self):
        write_standards(self.standards, {"03-testing.md": ["## 3.4 Inline variables only"]})
        write_digest(self.digest, "abc123", [("§3.99", "Invented rule.")])

        problems = check(self.digest, self.standards, "abc123")

        self.assertEqual(1, len(problems))
        self.assertTrue(problems[0].startswith("BROKEN:"))
        self.assertIn("§3.99", problems[0])

    def test_headings_at_levels_two_and_three_count(self):
        write_standards(
            self.standards,
            {
                "03-testing.md": ["## 3.4 Inline variables only"],
                "01-architecture.md": ["### 1.2 Service object contract"],
            },
        )
        write_digest(self.digest, "abc123", [("§3.4", "No let."), ("§1.2", "One public call.")])

        problems = check(self.digest, self.standards, "abc123")

        self.assertEqual([], problems)

    def test_missing_tree_line_is_reported_as_stale(self):
        write_standards(self.standards, {"03-testing.md": ["## 3.4 Inline variables only"]})
        self.digest.write_text("- [§3.4] No let.\n")

        problems = check(self.digest, self.standards, "abc123")

        self.assertTrue(any(p.startswith("STALE:") for p in problems))

    def test_exit_code_prefers_broken_citation_over_stale(self):
        self.assertEqual(0, exit_code([]))
        self.assertEqual(1, exit_code(["STALE: tree differs"]))
        self.assertEqual(2, exit_code(["STALE: tree differs", "BROKEN: §3.99 not found"]))


if __name__ == "__main__":
    unittest.main()
