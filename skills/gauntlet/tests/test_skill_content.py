import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL = (SKILL_DIR / "SKILL.md").read_text()
LENSES = (SKILL_DIR / "lenses.md").read_text()


class SkillContentTest(unittest.TestCase):
    def test_every_file_the_skill_names_exists(self):
        # CLAUDE.md is the target repo's file, not one of ours.
        named = [n for n in re.findall(r"`((?:scripts/)?[\w.-]+\.(?:md|py))`", SKILL) if n != "CLAUDE.md"]

        self.assertTrue(named)
        for name in named:
            self.assertTrue((SKILL_DIR / name).exists(), f"SKILL.md names {name}, which is missing")

    def test_never_list_pins_the_safety_rules(self):
        never = SKILL.split("## Never", 1)[1]

        self.assertIn("always `COMMENT`", never)
        self.assertIn("exact text", never)
        self.assertIn("`issue:`", never)
        self.assertIn("retired rules", never.lower())
        self.assertIn("Edit the target repo", never)

    def test_design_findings_carry_an_alternative_and_a_trade_off(self):
        self.assertIn("another way to do it", SKILL)
        self.assertIn("the trade-off between the two", SKILL)

    def test_caps_are_stated_for_both_tiers(self):
        self.assertIn("at most 6", SKILL)
        self.assertIn("about eight", SKILL)

    def test_posting_requires_a_dry_run_before_approval(self):
        self.assertLess(SKILL.index("--dry-run"), SKILL.index("explicitly approves"))

    def test_analysis_order_is_correctness_then_design_then_details(self):
        order = [SKILL.index(m) for m in ("**Correctness and data integrity.**", "**Design.**", "**Details.**")]

        self.assertEqual(sorted(order), order)

    def test_lenses_cover_every_requested_lens(self):
        for lens in ("SOLID", "POODR", "Tell, don't ask", "Clean Code", "Fowler",
                     "Gang of Four", "Domain-Driven Design"):
            self.assertIn(lens, LENSES)

    def test_every_lens_section_names_a_trade_off(self):
        sections = [s for s in LENSES.split("\n## ")[1:]]

        for section in sections:
            self.assertIn("rade-off", section, section.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
