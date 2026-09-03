# Version Control Standards

> Mirrored from Confluence: [Version Control Standards](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4812439560/Version+Control+Standards)
> Space `BAE` · page `4812439560` · last modified in Confluence Aug 26, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.
>
> **Under review:** the [Engineering Standards 2026](README.md) hub flags this page as
> assuming spec-driven development and AC-level traceability (the `Spec:`/`AC:` footers
> and spec-slice PR scoping below), which § 2.4 of [Coding Style Rules](practices/coding-style.md)
> now contradicts by treating the code as the source of truth. It also disagrees on
> subject-line format with the older
> [Git Commit Message Standard](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4467687425).
> Both conflicts are unresolved upstream.

## Git Commit Message Policy

Based on [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

### Principles

Conventional Commits governs the **form** of a message. These govern its **substance**. A commit can satisfy every formatting rule on this page and still say nothing — `feat(auth): update handler` is perfectly valid and perfectly useless.

* Commit messages are written for other humans, including your future self.
* Each commit represents a logical, coherent unit of work.
* A commit explains **why** the change was made, not just what changed.
* Multiple commits in a PR tell a coherent story of how the change evolved, so a reviewer can read them incrementally rather than re-parsing the whole diff.
* Do not rely on the PR description alone to explain intent.

**A commit should stand on its own as a clear explanation of a change.** If someone reads the commit history without the PR context, they should still be able to understand what was done and why.

### Format

```
<type>[(scope)][!]: <description>

[optional body]

[optional footer(s)]
```

### Type (Required)

| Type | When to use |
| --- | --- |
| `feat` | New functionality |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behavior change |
| `test` | Adding or updating tests only |
| `docs` | Documentation only |
| `chore` | Build, tooling, dependency updates |
| `ci` | CI/CD pipeline changes |
| `perf` | Performance improvement, no behavior change |
| `style` | Formatting, whitespace — no logic change |

### Scope (Optional)

A noun in parentheses describing the affected section: `feat(auth):`, `fix(parser):`.

### Breaking Changes

* Append `!` after the type/scope to flag a breaking change: `feat(api)!: remove v1 endpoints`.
* Include a `BREAKING CHANGE:` footer with a description of the impact.

### Description Rules

* Use imperative mood: "add", "fix", "refactor" (not "added", "fixes").
* **Lowercase** the first letter (the type prefix provides structure).
* No trailing period.
* Soft limit: 50 characters (total subject including type/scope). Warn if exceeded.
* Hard limit: 72 characters. Requires documented justification if exceeded.

### Body Rules

* Separate subject from body with a blank line.
* Wrap body text at 72 characters.
* Explain **why** the change was made and **what** changed at a high level.
* Do not narrate code edits line-by-line.

### Footer Rules

Footers use `token: value` format (one blank line after body). Standard footers:

* `Spec: SPEC-###` — link to the governing spec.
* `Task: PROJ-42` — link to the Jira issue (or omit in GitHub-only mode).
* `AC: AC-1, AC-2` — acceptance criteria addressed.
* `BREAKING CHANGE: <description>` — required when `!` is used, optional otherwise.
* `Co-Authored-By:` — attribution when applicable.

### Good Examples

```
feat(auth): add login endpoint skeleton

Implement the POST /api/auth/login route with request
validation. Returns 501 until credential logic is added
in the next slice.

Spec: SPEC-003
Task: PROJ-14
AC: AC-1
```

```
fix(auth): correct session token expiry off-by-one

The expiry comparison used `>` instead of `>=`, allowing
tokens to be valid for one second past their TTL. This
caused intermittent 401s in E2E tests.

Spec: SPEC-003
AC: AC-4
```

```
refactor(auth): extract dependency injection for middleware

Extract hardcoded user-store dependency so credential
validation can be tested in isolation. No behavior change.

Spec: SPEC-003
Task: PROJ-15
```

```
feat(api)!: remove deprecated v1 endpoints

All consumers have migrated to v2. The v1 routes returned
sunset headers for 90 days before this removal.

BREAKING CHANGE: /api/v1/* routes no longer exist
Spec: SPEC-010
Task: PROJ-30
```

### Bad Examples

```
fixed stuff
```

Why bad: Missing type prefix, not imperative, no context, no spec reference.

```
feat: Updated the login controller to call the new service method and also changed the test file and updated the mock.
```

Why bad: Exceeds 50-char subject limit, past tense, narrates code edits instead of explaining why, no spec reference.

```
feat: add authentication system, session management, token refresh, and logout endpoint
```

Why bad: Multiple unrelated changes in one commit. Each should be a separate commit tied to a specific task.

```
VF-32 Add some thing
```

Why bad: Jira reference does not belong in the subject line. Use a `Task:` footer instead. Missing type prefix.

### Enforcement

* If you are unsure about the format or scope of a commit message, propose it for feedback before committing.
* Commit message compliance is checked during review and recorded as part of the review evidence.
* Non-compliant commit messages require amend/fixup before the PR can proceed.
* Waiving a commit message violation requires a maintainer's sign-off and a documented reason in the PR description.

---

## PR Title Format

PR titles follow the same conventional commits format as commit subjects. Jira/task references belong in the PR description, **never in the title**.

### Format

```
<type>[(scope)][!]: <description>
```

### Rules

* Same type, scope, and description rules as commit messages.
* The title should describe the overall change the PR delivers.
* **No Jira issue keys or task IDs in the title.** Reference these in the PR body under Spec References.
* For single-commit PRs, the PR title should match the commit subject.

### Good Examples

```
feat(auth): add login endpoint skeleton
fix(parser): handle empty input without panic
refactor(api): extract shared validation middleware
docs: add API usage guide
```

### Bad Examples

```
VF-32 Add login endpoint
```

Why bad: Jira key in the title. Should be `feat(auth): add login endpoint` with `Task: VF-32` in the description.

```
Feature work
```

Why bad: No type prefix, vague description.

---

## Branch Naming Convention

Use the format `{issue-id}/{type}/{short-description}`:

* `{issue-id}` — Jira issue key (e.g., `PROJ-42`) or GitHub issue number. Lowercase.
* `{type}` — Conventional Commits type: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`.
* `{short-description}` — Kebab-case, 2-4 words describing the change.

### Examples

```
proj-42/feat/status-page
proj-12/fix/login-redirect
proj-15/chore/upgrade-rails
proj-8/refactor/extract-auth-service
proj-20/docs/api-usage-guide
```

### Rules

* Always branch from the project's main branch (usually `main`).
* In GitHub-only mode (no Jira), use a short prefix instead of an issue key (e.g., `feat/status-page`).
* No uppercase letters in branch names.
* Every branch uses this format. PRs raised from non-conforming branches are rejected in review.

---

## PR Size and Scope Policy

### Size Constraints

* Target: one testable behavior per PR, in 1–3 commits. This is the Subtask grain from the [Sprint Commitment Process](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4732321798).
* **~200 LOC of meaningful change is the target.** Soft — most PRs should land at or under this.
* **~500 LOC is the firm expectation**, excluding generated files, lockfiles, and snapshots. Past this, split the work — or say in the PR description why you did not.
* A PR bundling multiple features or cross-cutting concerns should be split.

**Nothing here is a hard gate.** These are guidelines. The engineer who signs off owns the judgment and its consequences.

The numbers exist for one reason: every line has to be read by a human, and PR size is what keeps that possible.

### PR Slicing Plan

When work spans more than one logical change, produce a slicing plan before implementation:

1. List each logical slice with its spec/AC references.
2. Define the commit/PR boundary for each slice.
3. Identify ordering dependencies between slices.
4. Get maintainer approval before proceeding.

### PR Must Include

* Spec IDs covered.
* Acceptance criteria checklist.
* Test evidence.
* UX evidence (if applicable).
* PR size justification (explicit statement that the PR is small enough, or a slicing plan reference).

### In Review

* Size is a judgment call, not a gate. A reviewer can push back on a PR too large to review properly — that is a conversation, not a rejection rule.
* Check that the PR delivers one testable behavior.
* Check that each commit references the work it implements.

---

## Task Sizing: Fibonacci Complexity Points

### Allowed Values

1, 2, 3, 5, 8, 13 (Fibonacci sequence).

### What Points Represent

Points measure **complexity, risk, and unknowns** — not time.

| Points | Meaning |
| --- | --- |
| 1 | Trivial change, well-understood, minimal risk |
| 2 | Small change, clear approach, low risk |
| 3 | Moderate change, some moving parts, manageable risk |
| 5 | Significant complexity or unknowns; **must be reviewed for splitting** |
| 8 | High complexity; **must be split** unless a maintainer explicitly approves with documented rationale |
| 13 | Epic-level; **always split** into smaller tasks |

### Splitting Rule

* Tasks estimated at **5 points**: review and decide whether to split before starting.
* Tasks estimated at **8+ points**: split into smaller tasks before work begins.
* If splitting is not possible, document the rationale and accept the risk explicitly.

### Point Voting (Future-Ready)

When team estimation is active:

1. Everyone estimating — whoever implements, plus review and QA, and design when the change is UX-driven — gives a point vote with brief rationale.
2. If votes diverge by more than one Fibonacci step, discussion is required.
3. The maintainer finalizes the estimate and documents the decision.

---

## Complexity Escalation Loop

When implementation reveals that a task is more complex than estimated, or scope is creeping:

### Escalation Steps

1. **Pause** — Stop implementation at the smallest safe checkpoint. Commit work done so far.
2. **Report** — Write a Complexity Report documenting:

    * What was discovered (unknowns, risks, dependencies).
    * Why the task is larger than expected.
    * What has been completed so far.
    * Suggested breakdown if apparent.

3. **Hand back** — Return the task for triage.
4. **Optional gates** — Triage may pull in product or UX input if the complexity is product- or design-driven.
5. **Resume** — Work resumes only once triage has produced an updated task breakdown and the decision is documented.

### Quality Gate

Work does not continue on an over-complex task without a documented triage decision. Continuing without triage is a blocking violation.
