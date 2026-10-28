# 5. Version Control

> Mirrored from Confluence: [5. Version Control](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919984129/5.+Version+Control)
> Space `SD` · page `4919984129` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Commits, branches, pull requests, merges.

---

## Baseline

**[Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)** — pinned.

```
<type>[(scope)][!]: <description>

[optional body]

[optional footer(s)]
```

The spec governs the **form** of a commit message. It mandates less than people assume: only
`feat` and `fix` as types, a footer token format, and `BREAKING CHANGE` in uppercase. Casing,
length and punctuation are left open — so everything in §5.2 below is ours, not inherited.

---

## 5.1 Principles — what the spec does not cover

Conventional Commits governs form. These govern **substance**. A commit can satisfy every
formatting rule and still say nothing: `feat(auth): update handler` is perfectly valid and
perfectly useless.

- Commit messages are written for other humans, including your future self.
- Each commit is a logical, coherent unit of work.
- A commit explains **why** the change was made, not just what changed.
- Multiple commits in a PR tell the story of how the change evolved, so a reviewer can read them
incrementally rather than re-parsing the whole diff.
- Do not rely on the PR description alone to carry intent.

> **A commit stands on its own.** If someone reads the history without the PR, they should still
understand what was done and why.

**This matters more now, not less.** With no durable spec and the code AI-written, the commit
body is one of the few durable, append-only places the *why* can live.

## 5.2 Our deltas

|  | Ours | The spec |
| --- | --- | --- |
| **Allowed types** | `feat` `fix` `refactor` `test` `docs` `chore` `ci` `perf` `style` | Only `feat` and `fix` required; others allowed but unlisted |
| **Description case** | Lowercase first letter — the type prefix already provides structure | Any casing, "best to be consistent" |
| **Length** | 50 chars soft (warn), 72 hard (needs a stated reason) | No limit |
| **Trailing period** | None | Unspecified |
| **Body** | Wrap at 72. Explain **why** and what changed at a high level. Do not narrate edits line by line | Unspecified |

The type list is closed by convention now, and by the hook once it exists. Adding one is a
conversation, not a violation.

**Scope** is a noun in parentheses naming the affected area: `feat(auth):`, `fix(parser):`.
Optional.

**Breaking changes** take `!` after the type or scope, plus a `BREAKING CHANGE:` footer
describing the impact: `feat(api)!: remove v1 endpoints`.

### Footers

| Token | Use |
| --- | --- |
| `Task: PROJ-42` | The Jira issue. Omit in GitHub-only mode |
| `BREAKING CHANGE: <description>` | Required when `!` is used |
| `Co-Authored-By:` | Attribution |

There is no `Spec:` or `AC:` footer. The numbered spec they referenced no longer exists.

### Worked examples

```
feat(auth): add login endpoint skeleton

Implement POST /api/auth/login with request validation. Returns 501
until credential logic lands in the next slice.

Task: PROJ-14
```

```
fix(auth): correct session token expiry off-by-one

The comparison used `>` instead of `>=`, so tokens stayed valid for
one second past their TTL. Caused intermittent 401s in E2E tests.
```

**Why these fail:**

| Bad | Problem |
| --- | --- |
| `fixed stuff` | No type, not imperative, no context |
| `feat: Updated the login controller to call the new service method and also changed the test` | Over 50 chars, past tense, narrates edits instead of explaining why |
| `feat: add auth system, session management, token refresh, and logout` | Four unrelated changes. Four commits |
| `VF-32 Add some thing` | Jira key belongs in a `Task:` footer, not the subject. No type |

## 5.3 PR titles

Same format as commit subjects, same rules. The title describes the overall change the PR
delivers; for a single-commit PR it matches the commit subject.

**No Jira keys or task IDs in the title.** They go in the PR description.

## 5.4 Branch naming

`{issue-id}/{type}/{short-description}` — all lowercase.

```
proj-42/feat/status-page
proj-12/fix/login-redirect
proj-8/refactor/extract-auth-service
```

- `{issue-id}` — Jira key, or a GitHub issue number. In GitHub-only mode use just the type:
`feat/status-page`.
- `{type}` — a Conventional Commits type from §5.2.
- `{short-description}` — kebab-case, 2–4 words.

Always branch from the project's main branch.

## 5.5 PR size and scope

**One testable behaviour per PR**, in 1–3 commits.

|  |  |
| --- | --- |
| **\~200 lines** of meaningful change | The target. Most PRs should land here or below |
| **\~500 lines** | The firm expectation, excluding generated files, lockfiles and snapshots. Past this, split it — or say in the description why you didn't |

**None of this is a hard gate.** The engineer who signs off owns the judgment and its
consequences. A reviewer can push back on a PR too large to review properly — that is a
conversation, not a rejection rule.

The numbers exist for one reason: **every line has to be read by a human**, and PR size is what
keeps that possible. It is the one rule whose violation directly threatens the only real control
in the system.

**When work spans more than one logical change**, plan the slices before implementing: list each
slice, define its boundary, and identify ordering dependencies.

## 5.6 Merging

- **Squash-merge.** `main` gets one clean commit per PR.
- **A human merges.** Always — agents never do. The blast radius is irreversible, so this stays
a human action permanently.
- **The PR page keeps the full trail** — commits, diffs and review conversation survive the
squash permanently. That is what makes correcting in the PR (rather than locally) worth doing.

## 5.7 Enforcement

Everything on this page except §5.1 is **mechanical** — every rule here *can* be a hook or a CI
check, which is what would take the page out of review entirely.

### Today

**CI already blocks merges** — default branches carry rulesets with lint, test and security scans
as required status checks ([CI/CD §14.10](14-ci-cd.md)). What is missing is only the
**commit-format check itself**: no repository runs `commitlint`.

So format is checked by whoever is reviewing, alongside everything else they are carrying. A
malformed commit message is a review comment like any other, and the author amends.

**Adding it is small**, because the enforcement mechanism is already there and already blocking:
add the hook, add its context to the ruleset's required checks.

### Once the commit-format check exists

| Checked by CI | Checked by a human |
| --- | --- |
| Commit format, type, case, length | Whether the message says anything useful (§5.1) |
| Branch name format | Whether the PR is one testable behaviour |
| Diff size — as a non-blocking warning | Whether the size is reasonable for this change |

A failing format check is then fixed with an amend or fixup, not waived — there is no approval
path for a malformed commit message, because there is nothing to judge.

**Size never becomes a blocking check.** A warning informs the signing engineer's judgment; it
does not override it.

**Why this matters more than it looks.** These are the most mechanisable rules in the corpus,
and while they sit with human reviewers they consume exactly the attention that reading every
line requires. Moving them to CI is not a control on the engineer — it is what makes their
accountability tractable.

---

## Removed from this page

Recorded so these are not reintroduced as oversights.

| Removed | Why |
| --- | --- |
| **Task Sizing: Fibonacci Complexity Points** (1/2/3/5/8/13, splitting rules, point voting) | Estimation is dissolved. Planning material does not belong in an engineering standard |
| **Complexity Escalation Loop** (pause / report / hand back / triage gate) | Scope change is not an engineering concern |
| **`Spec:` and `AC:` footers**, and spec-slice PR scoping | The durable spec they referenced is retired |
| **Maintainer sign-off to waive a commit violation** | Once the check is a hook there is nothing to waive — and "maintainer" was a role appearing nowhere else in the corpus. Removed now rather than later, because a waiver process for a rule nobody enforces is pure ceremony |
| **"PRs from non-conforming branches are rejected in review"** | Rejection is the wrong response to a fixable format error. Renaming a branch is cheap; the review continues. Kept as a review check until CI takes it (§5.7) |
