# Code Reviewer — Design

Status: **draft for review** · 2026-11-16 · not committed

## 1. Intent

Joe wants an on-demand code reviewer for Ruby on Rails work that reviews the way Joe
reviews: curious, question-led, focused on design and on what breaks under partial
failure, and honest about how much each point matters. It is a sparring partner and a
drafting aid. It is not a gate and not a substitute for a human reading every line
(Standards §6, "the human reads every line").

It exists because Joe's review style is currently only in Joe's head and in past PR
comments. The reviewer makes that style repeatable, and adds a design-reasoning layer
(SOLID, POODR, Clean Code, Fowler's PoEAA, GoF, DDD, Tell Don't Ask) that explains
trade-offs rather than issuing rules.

## 2. Goals

1. Review a diff and report the few findings that matter, ranked, each with its reasoning
   and trade-offs.
2. Reason from design principles as lenses, never as rules. Say when breaking a
   principle is the right call.
3. Check a change against a condensed digest of the engineering standards (see §6.3) and
   against the target repo's own `CLAUDE.md`.
4. Work in two modes from one analysis (see §5): reviewing a teammate's PR, and checking
   the user's own branch or PR.
5. Post the findings to a PR as a GitHub review, only after the user approves the exact text.

## 3. Non-goals

- Approving or requesting changes. It never chooses the verdict.
- Automatic or CI-triggered review. On demand only, for now.
- Enforcing anything RuboCop already enforces.
- Languages other than Ruby/Rails in v1. Primary focus ActiveRecord, with Sequel supported.
  TypeScript, Terraform and others are out of scope until asked.
- Resolving the open decision in Standards §6.4 on automated pre-review. This tool fits the
  "optional" option but does not settle it.
- Editing the target repo's code or its `CLAUDE.md`.

## 4. Anti-goals (a failure even if it technically works)

Each of these is something Joe said would make them wince:

| Failure | Design response |
| --- | --- |
| Sounds certain when wrong | Phrase as questions. State uncertainty plainly. Never assert a violation without showing the evidence in the diff |
| Noise: dozens of comments, style points RuboCop catches | Cap and rank findings. Drop anything a configured linter enforces |
| Preaching the books | Cite a principle only when it changes the decision, and always with the trade-off |
| Misses the real problem while discussing naming | Correctness first: partial failure, transactions, data integrity, edge cases are examined before naming and style |
| Enforces stale or wrong rules | Every digest rule carries its source and sync date. Superseded rules are excluded. Conflicts between sources are flagged, not resolved silently |
| Something embarrassing posted under Joe's name | Nothing is posted without explicit approval of the exact text |

## 5. Modes

One analysis, two deliveries. The mode is inferred from the target and can be overridden.

| | Teammate mode | Self mode |
| --- | --- | --- |
| Target | A PR authored by someone else | The user's own branch or PR |
| In the terminal | Draft comments addressed to the author | Findings addressed to the user. May ask what the user intended |
| If posted | Inline comments in Joe's voice to the author | Inline notes in Joe's voice for later readers, for example "I wasn't sure whether X; flagging for a second opinion" |
| Needs a PR to post | Yes | Yes. With no PR it only reports in the terminal |

**Draft PRs** (Standards §6.3): feedback is directional (design, risk, complexity), not
polish. This applies in both modes. *(Assumed by the designer, not stated by Joe.)*

## 6. Behaviour

### 6.1 Voice, from Joe's past reviews

Derived from 47 inline comments across 72 PRs on `westernmilling/contracto`. One request
returned a 502, so the sample may be slightly incomplete.

- Mostly questions: "Was the transaction here intentional?", "Is there a reason you…?"
- Asks about intent and failure modes (partial creation, error attribution to child records).
- Questions whether the domain model matches the business.
- Asks for names and test descriptions that say what the code does.
- Points to how similar problems are solved elsewhere in the org.
- States weight in plain words ("minor", "curiosity", "wouldn't block for me").
- Backs off when the author gives a good reason.
- Silent on matters a linter or an unagreed style preference would cover.

No Conventional Comments prefixes (`issue:`, `nitpick:`). Standards §6 considered and did not
adopt them, and the first word of a comment is reserved for a proposed cause tag. Weight is
expressed in plain words inside the sentence.

### 6.2 Lenses

Design reasoning (explain trade-offs, never prescribe): SOLID, POODR (Sandi Metz), Clean Code,
Fowler's *Patterns of Enterprise Application Architecture*, Gang of Four, Domain-Driven Design,
Tell Don't Ask / Law of Demeter.

Repo rules: read from the target repo's `CLAUDE.md` (for contracto: layering, thin controllers,
query objects, PR size, migrations in their own PR, queue separation). Repo rules are
repo-specific. "Never ActiveRecord" is a contracto rule, not a general one.

Ruby/Rails focus: ActiveRecord first, Sequel supported. Which one applies comes from the repo.

### 6.3 Standards digest

A condensed set of hot points, held in the skill, covering only rules a diff can break.
Process rules (review lifecycle, deployment) are excluded.

- Each hot point cites its section (for example "Testing §3.4").
- The digest records which standards version and sync date it was written from.
- The digest lives in this repo beside `standards/`, so a standards change shows up in the
  same PR as the digest update.
- Confluence is the source of truth. The reviewer says "per the mirrored standards".

**Testing hot points are Better Specs as the base with the standards' deviations** (§3 table).
Examples the reviewer flags: `let`/`let!`, explicit `subject`, setup hooks, shared examples
across files, message expectations, mocking the database, `reload`, `allow_any_instance_of`
without a documented vendor reason. It does **not** push "one expectation per test": the
standard is one outcome per test, several assertions allowed.

*(Candidate pages to draw hot points from: 01 architecture, 02 coding style, 03 testing,
04 naming, 05 version control, 12 dependencies. The builder reads the rest for anything
diff-visible, for example Docker or CI files.)*

### 6.4 Ranking and volume

Correctness and data-integrity risks first, then design, then naming and tests. Few
findings, each with: what was seen (file and line), the question, the trade-off, and the
weight in plain words. The exact cap is left to the builder, tuned against real diffs.

### 6.5 Posting

1. Draft comments are shown to the user.
2. The user edits, drops, or approves each.
3. On approval, the skill submits one GitHub review with inline comments, event type
   `COMMENT` only.
4. The review summary ends with a credit line. Joe approved crediting AI. Assumed wording:
   > 🤖 Drafted with Claude Code, reviewed and approved by [user] before posting.
5. The credit goes on the summary only, not on each inline comment.

## 7. Constraints

- On demand only.
- Posting is the only outward action and always needs approval of the exact text.
- Uses `gh` for PR data and for posting. No new services.
- Must not post the same comment twice if re-run on the same PR.
- Standards §6.7: no drive-by or vague comments. Every comment explains why.

## 8. Decided by the designer, not by Joe

Joe should confirm or change these.

- **Form:** a skill invoked on demand. Whether it dispatches subagents is a planning decision.
- **Home:** this repo (`engineering_practices`), with each target repo adding its own rules
  through its `CLAUDE.md`.
- **Verdict:** `COMMENT` only.
- **Draft PR behaviour** in §5.
- **Credit line** wording in §6.5.
- **Mode inference** from PR authorship, with override.
- **Distribution:** the skill is installed at user level (`~/.claude/skills/`) as a symlink
  to the skill folder in this repo, so it is available from any target repo and edits here
  take effect immediately. The digest lives inside the skill folder, so the skill is
  self-contained and the "same PR updates standards and digest" guarantee holds in this
  repo. Other machines or people would need a plugin instead (see §11).
- **Voice evidence:** the builder re-fetches Joe's inline review comments from
  `westernmilling/contracto` with `gh` (author `josephbridgwaterrowe`), retrying the failed
  page, and picks a small set of real comments as few-shot examples in the skill. The
  bullet list in §6.1 is a summary, not the source. Joe approves the chosen examples.
- **Definition of done:** the skill is evaluated against a handful of past contracto PRs
  where Joe's actual comments are the reference, plus one or two deliberately flawed diffs
  (a transaction that commits half a record, a `let` in a spec). Joe judges the output
  against the §4 anti-goals. Passing means: finds the planted flaw, stays under the
  finding cap, posts nothing without approval, and asserts nothing without evidence.

## 9. Left to the builder

- Skill name, file layout, and how the digest is structured and stored.
- How the digest is checked for drift against `standards/`.
- Finding cap and ranking heuristics.
- How the review is submitted via `gh` (single review with inline comments) and how
  duplicates are detected.
- How to tell "reading a diff" from "reading the whole file" when context is needed.

## 11. Audience: Joe only, with room to grow

**Is this for Joe alone, or will teammates run it too?** (The standards describe a team of
four.) It changes what gets built:

- **Joe only:** the voice is hard-coded as Joe's, distribution is a symlink, and the credit
  line names Joe.
- **Teammates too:** distribution becomes a plugin or shared install, the reviewer's name
  comes from `gh`, and the voice needs a decision: Joe's voice for everyone, or a neutral
  version of it.

**Decided (Joe):** v1 is Joe's reviewer, in Joe's voice, and the skill says so plainly in its
name and description. It is designed so it can later move to a shared voice (the standards'
§6.7 expectations plus Joe's question-led habits) and then to per-person voices. Seams built
in now:

- Voice examples live in their own file, separate from the review logic.
- The reviewer's name for the credit line comes from `gh`, never hard-coded.
- Distribution starts as a symlink and can become a plugin without changing the skill.

Not built in v1: a shared voice, per-person voices, or any teammate onboarding.

## 10. Known issues found while scoping

- Contracto's `CLAUDE.md` still contains the retired "Spec-Driven Contract" and the
  matching Agent Hard Rules. The reviewer must not enforce them. The file itself is not
  changed by this work.
- Standards §6.4 has an unresolved decision on automated pre-review.
- A memory note mentions a CLAUDE.md footer-rule conflict that may remain. This repo has no
  `CLAUDE.md`. Not investigated here.
- Two copies of contracto exist locally (`~/Development/contracto` and
  `~/Development/otto-mono/contracto`). The reviewer reads whichever repo it is run in.
