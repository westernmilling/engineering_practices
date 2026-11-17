import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent


def read_frontmatter(path):
    lines = path.read_text().splitlines()
    assert lines[0] == "---", "SKILL.md must start with frontmatter"
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


class SkillFrontmatterTest(unittest.TestCase):
    def test_name_matches_folder_and_says_joe(self):
        fields = read_frontmatter(SKILL_DIR / "SKILL.md")

        self.assertEqual("gauntlet", fields["name"])
        self.assertEqual(SKILL_DIR.name, fields["name"])
        self.assertIn("Joe", fields["description"])
        self.assertIn("on demand", fields["description"])


if __name__ == "__main__":
    unittest.main()
