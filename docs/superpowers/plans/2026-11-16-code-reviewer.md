# Joe's Code Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An on-demand Claude Code skill, `joe-review`, that reviews a Rails diff in Joe's voice and, only after Joe approves the exact text, posts it to the PR as a comment-only GitHub review.

**Architecture:** A markdown skill (`SKILL.md` plus lenses, a standards digest and voice examples) does the reasoning. Three small Python scripts do the deterministic parts: fetch Joe's past comments, check the digest for drift, and build and post the review. The skill folder lives in this repo and is symlinked into `~/.claude/skills/`, as `jira-agent` already is.

**Tech Stack:** Markdown skill, Python 3 stdlib (`unittest`, `subprocess`, `json`), `gh` CLI, `jq`. No `bats`, `shellcheck` or Ruby on this machine.

**Spec:** `docs/superpowers/specs/2026-11-16-code-reviewer-design.md` (both spec and plan are removed from the branch before merge)

## Global Constraints

- Review event is `COMMENT` only. The tool never approves or requests changes.
- Nothing is posted without Joe's approval of the exact text. `--dry-run` first, real post second.
- One GitHub review with inline comments. Re-running on the same PR must not repost a comment already there.
- The review summary ends with: `🤖 Drafted with Claude Code, reviewed and approved by <name> before posting.` The name comes from `gh`, never hard-coded. The credit is on the summary only.
- No Conventional Comments prefixes (`issue:`, `nitpick:`). Weight is stated in plain words inside the sentence.
- Findings are phrased as questions, with the trade-off and the plain-words weight, and cite a principle only when it changes the decision.
- Order: correctness and data integrity, then design, then naming and tests. Drop anything RuboCop enforces.
- Testing hot points are Better Specs with the standards' deviations (Testing §3). It does not push "one expectation per test".
- Retired rules (spec-driven contract, "invent behavior") are never enforced. Repo-specific rules come from the target repo's `CLAUDE.md`.
- Ruby/Rails only, ActiveRecord first, Sequel supported. The tool never edits the target repo.
- Draft PRs get direction, risk and design feedback, not polish (Standards §6.3).
- The skill's name and description say it is Joe's reviewer.

## Review Focus

Failure modes the spec implies but no requirement tests. Each has a test in the owning task.

1. **Inline comment on a line outside the diff.** GitHub returns 422 for the whole review. Expected: that comment moves into the summary as `path:line`. (Task 4)
2. **Re-run on the same PR.** Expected: no duplicate comments, and no review at all if nothing is new. (Task 4)
3. **No findings.** Expected: the skill says so and posts nothing. (Task 5, eval `clean`)
4. **Digest stale or citing a section that no longer exists.** Expected: loud warning at the top of the review. (Task 2)
5. **Target repo has no `CLAUDE.md`.** Expected: review proceeds on lenses and digest alone, and says repo rules were unavailable. (Task 5)

## File Structure

```
skills/joe-review/
  SKILL.md                  entry point: flow, modes, output rules
  lenses.md                 design lenses as trade-off prompts
  digest.md                 standards hot points, each citing its section
  voice-examples.md         Joe's real comments, chosen and approved by Joe
  scripts/check_digest.py   drift and citation check
  scripts/fetch_voice.py    pulls Joe's comments with gh, retrying 5xx
  scripts/post_review.py    builds the review payload and posts it
  tests/                    unittest files, one per script, plus frontmatter
  evals/                    fixture diffs and the pass criteria
```

Run all tests: `python3 -m unittest discover -s skills/joe-review/tests -v`

---

### Task 1: Skill scaffold and install

**Files:**
- Create: `skills/joe-review/SKILL.md` (frontmatter and a one-line body for now)
- Create: `skills/joe-review/tests/test_skill_frontmatter.py`

**Interfaces:**
- Produces: the folder `skills/joe-review/`, which every later task adds to.

- [ ] **Step 1: Write the failing test** `test_name_matches_folder_and_says_joe`: reads `SKILL.md` frontmatter, asserts `name == "joe-review"` and that `description` contains `"Joe"` and `"on demand"`.
- [ ] **Step 2: Run it**: `python3 -m unittest discover -s skills/joe-review/tests -v`. Expected: FAIL, no `SKILL.md`.
- [ ] **Step 3: Create `SKILL.md`** with frontmatter `name: joe-review` and a description stating it is Joe's personal on-demand Rails reviewer, used when Joe asks to review a PR or branch.
- [ ] **Step 4: Run it.** Expected: PASS.
- [ ] **Step 5: Install**: `ln -s "$PWD/skills/joe-review" ~/.claude/skills/joe-review`. Verify with `ls -l ~/.claude/skills/joe-review`. Expected: points into this repo.
- [ ] **Step 6: Commit** `feat(reviewer): scaffold joe-review skill`.

### Task 2: Standards digest and drift check

**Files:**
- Create: `skills/joe-review/scripts/check_digest.py`, `skills/joe-review/digest.md`
- Test: `skills/joe-review/tests/test_check_digest.py`

**Interfaces:**
- Produces: `check(digest_path: Path, standards_dir: Path, current_tree: str) -> list[str]`, returning problem messages (empty list means clean). CLI `check_digest.py` exits 0 clean, 1 stale, 2 broken citation, and prints the problems. `current_tree` comes from `git rev-parse HEAD:standards`, run from the repo root found via `Path(__file__).resolve()` so it works through the symlink.
- Digest format: first line `<!-- synced-standards-tree: <sha> -->`, then entries `- [§3.4] rule in one sentence`.

- [ ] **Step 1: Write failing tests** against a temp standards dir: `test_clean_digest_returns_no_problems`, `test_stale_tree_is_reported`, `test_citation_to_missing_section_is_reported` (digest cites `[§3.99]`, no such heading), `test_headings_at_levels_two_and_three_count` (a `### 3.4.1`-style or `## 3.4` heading both resolve).
- [ ] **Step 2: Run them.** Expected: FAIL, module missing.
- [ ] **Step 3: Implement `check`.** A citation `[§N.M]` resolves if `standards/NN-*.md` has a `##` or `###` heading beginning `N.M `. Page number is zero-padded for the filename.
- [ ] **Step 4: Run tests.** Expected: PASS.
- [ ] **Step 5: Write `digest.md`.** Read `standards/` pages 01, 02, 03, 04, 05 and 12 in full. Keep only rules a diff can break: layering and service contract (§1), comments and alignment (§2), testing including the deviations table (§3), naming (§4), PR size and scope, migration separation, titles and branches (§5), adding a dependency (§12). Skip lifecycle and process rules. One sentence per rule, each citing its section. Skim pages 06–11 and 13–15 for diff-visible rules (Dockerfile, CI, secrets in config) and add any. The testing entries are Better Specs with the §3 deviations, so they flag `let`/`let!`, explicit `subject`, setup hooks, cross-file shared examples, message expectations, mocking the database, `reload`, and `allow_any_instance_of` without a named vendor reason. Set the first line from `git rev-parse HEAD:standards`.
- [ ] **Step 6: Run the CLI.** `python3 skills/joe-review/scripts/check_digest.py`. Expected: exit 0, no output.
- [ ] **Step 7: Joe reviews `digest.md`** and cuts or edits entries before the commit.
- [ ] **Step 8: Commit** `feat(reviewer): standards digest with drift check`.

### Task 3: Voice examples

**Files:**
- Create: `skills/joe-review/scripts/fetch_voice.py`, `skills/joe-review/voice-examples.md`
- Test: `skills/joe-review/tests/test_fetch_voice.py`

**Interfaces:**
- Produces: `fetch_comments(repo: str, author: str, run=subprocess.run, retries: int = 3) -> list[dict]`, each dict with `pr`, `path`, `body`. It pages with `gh api --paginate`, retries a page on an HTTP 5xx, and raises after `retries`. CLI: `fetch_voice.py westernmilling/contracto josephbridgwaterrowe > comments.json`.

- [ ] **Step 1: Write failing tests** with a fake `run`: `test_retries_on_502_then_succeeds`, `test_raises_after_retries_exhausted`, `test_filters_to_author`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement `fetch_comments`.** Pass the author filter through `--jq`; treat a non-zero exit with `HTTP 5` in stderr as retryable.
- [ ] **Step 4: Run tests.** Expected: PASS.
- [ ] **Step 5: Fetch the real set** into the scratchpad directory, not the repo. Expected: roughly 47 or more comments, no error.
- [ ] **Step 6: Choose 8–12 examples** spanning the traits in spec §6.1 (intent and failure-mode questions, domain-model questions, naming, pointing to prior art, weight in plain words, backing off). Write `voice-examples.md`: a short description of the voice, then each example as the comment text plus one line on what it shows. Strip names of colleagues to roles.
- [ ] **Step 7: Joe approves the chosen examples** before the commit.
- [ ] **Step 8: Commit** `feat(reviewer): voice examples and fetch script`.

### Task 4: Posting

**Files:**
- Create: `skills/joe-review/scripts/post_review.py`
- Test: `skills/joe-review/tests/test_post_review.py`

**Interfaces:**
- Produces:
  - `parse_diff_lines(diff_text: str) -> dict[str, set[int]]`: new-side line numbers present in each file's hunks.
  - `build_review(draft: dict, reviewer: str, existing_markers: set[str], diff_lines: dict[str, set[int]]) -> dict | None`. `draft` is `{"repo", "pr", "summary", "comments": [{"path", "line", "body"}]}`. Returns the GitHub payload `{"event": "COMMENT", "body", "comments": [{"path", "line", "side": "RIGHT", "body"}]}`, or `None` when nothing is new.
  - CLI `post_review.py draft.json [--dry-run]`: dry-run prints the payload and posts nothing. Without it, posts to `repos/{repo}/pulls/{pr}/reviews`. The reviewer name is `gh api user --jq '.name // .login'`.
- Each comment body ends with a hidden marker `<!-- joe-review:<first 12 hex of sha1(path:line:body)> -->`.

- [ ] **Step 1: Write failing tests**: `test_event_is_always_comment`; `test_credit_line_on_summary_only_with_reviewer_name`; `test_comment_outside_diff_moves_to_summary_as_path_line` (focus 1); `test_existing_marker_is_skipped` and `test_returns_none_when_all_comments_exist` (focus 2); `test_parse_diff_lines_tracks_added_and_context_lines`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement the three functions.** `parse_diff_lines` walks `@@ -a,b +c,d @@` headers and counts added and context lines on the new side. Existing markers come from the PR's existing review comments in `main`.
- [ ] **Step 4: Run tests.** Expected: PASS.
- [ ] **Step 5: Smoke test `--dry-run`** on a small real PR in this org with a one-comment draft. Expected: payload printed, nothing appears on the PR.
- [ ] **Step 6: Commit** `feat(reviewer): comment-only review posting with dedupe`.

### Task 5: Review logic

**Files:**
- Modify: `skills/joe-review/SKILL.md`
- Create: `skills/joe-review/lenses.md`

**Interfaces:**
- Consumes: `digest.md`, `voice-examples.md`, `check_digest.py`, `post_review.py` (Tasks 2–4).

- [ ] **Step 1: Write `lenses.md`.** For each of SOLID, POODR, Clean Code, Fowler's PoEAA, GoF, DDD and Tell Don't Ask / Law of Demeter: two or three short questions the reviewer can ask of a diff, and the trade-off each exposes. Include the contracto mapping (service object, query object, base service) to PoEAA. State that each lens is a way of reasoning, never a rule.
- [ ] **Step 2: Write the `SKILL.md` flow**, in this order:
  1. **Preflight:** run `check_digest.py` and put any problem at the top of the output (focus 4). Read the target repo's `CLAUDE.md` if present, and say so if absent (focus 5).
  2. **Mode:** `gh pr view --json author,isDraft`. The author equal to `gh api user` login means self mode, otherwise teammate mode. No PR means self mode, report-only. Joe can override.
  3. **Gather:** `gh pr diff` for a PR, `git diff main...HEAD` otherwise.
  4. **Analyse:** correctness and data integrity first, then design through `lenses.md`, then naming and tests through `digest.md`. Drop what RuboCop enforces. Draft PRs get direction, risk and design only.
  5. **Write findings:** at most 6, ranked. Each has file and line, the question, the trade-off, and the weight in plain words, in the voice of `voice-examples.md`. A cap above 6 is a tuning decision made in Task 6.
  6. **Teammate vs self wording:** addressed to the author, or to Joe in the terminal and to later readers if posted.
  7. **No findings:** say so, post nothing (focus 3).
  8. **Post:** write `draft.json`, run `post_review.py --dry-run`, show Joe, and run the real post only after Joe explicitly approves the exact text.
- [ ] **Step 3: Add a "Never" list** to `SKILL.md` copied from Global Constraints: approve or request changes, post unapproved text, use Conventional Comments prefixes, enforce retired rules, edit the target repo.
- [ ] **Step 4: Re-run the unit tests.** Expected: PASS, including the frontmatter test.
- [ ] **Step 5: Commit** `feat(reviewer): review flow and design lenses`.

### Task 6: Evaluation

**Files:**
- Create: `skills/joe-review/evals/partial-transaction.diff`, `let-in-spec.diff`, `rubocop-only.diff`, `clean.diff`, `evals/README.md`

- [ ] **Step 1: Write the four fixture diffs** as small realistic Rails changes:
  - `partial-transaction`: a service that saves a contract and its schedules in separate writes, so a schedule failure leaves a committed contract.
  - `let-in-spec`: a new spec using `let` and an explicit `subject`.
  - `rubocop-only`: only line-length and trailing-comma violations.
  - `clean`: a small, well-formed service with a spec following the standards.
- [ ] **Step 2: Write `evals/README.md`** with the expected result per fixture: `partial-transaction` is flagged first and as a question; `let-in-spec` cites Testing §3.4; `rubocop-only` produces no findings; `clean` produces none or one minor point. Add the standing checks: at most 6 findings, no Conventional Comments prefixes, nothing posted without approval, no assertion without a file and line.
- [ ] **Step 3: Run the skill** on each fixture in a fresh Claude Code session, plus two or three past contracto PRs where Joe's real comments are the reference.
- [ ] **Step 4: Joe judges** the output against the spec's anti-goals. Adjust the cap, `lenses.md` and `SKILL.md` wording until Joe is satisfied, re-running the affected fixtures.
- [ ] **Step 5: Commit** `test(reviewer): eval fixtures and pass criteria`.

---

## Self-review

- **Spec coverage:** goals 1–5 map to Tasks 5, 5, 2, 5 and 4. Modes and draft-PR behaviour are in Task 5. Voice is Task 3, the digest is Task 2, and posting and the credit line are Task 4. Distribution is Task 1. Definition of done is Task 6. Non-goals need no task.
- **Type consistency:** `check`, `fetch_comments`, `build_review`, `parse_diff_lines` and the `draft.json` shape are used identically wherever they appear.
- **Proportion:** the plan is a little over the spec's length, and contains no function bodies.
