# Engineering Standards

> Mirrored from Confluence: [Engineering Standards](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4918935555/Engineering+Standards)
> Space `SD` · page `4918935555` · last modified in Confluence Oct 28, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

**Status:** Approved · **Version:** 1.0 · **Revised:** 2026-10-28 · **Owner:** Joe Bridgwater-Rowe
**Supersedes:** Engineering Practices (Jan 2026) · Comprehensive Engineering Standards ·
Engineering Standards 2026 · Technical Practices · Git Commit Message Standard

> **What this is.** The engineering standards the team works to. **Read the page that matches
the work in front of you** — nobody reads all of it, and nothing here assumes you have.

## If you only have sixty seconds

- **Developers drive.** There is no orchestrated pipeline — you own your workflow.
- **The obligation is the result, not the route.** The code meets these standards when it lands.
How you got there is not specified and not inspected.
- **Verify before you open a PR.** Tests cover the change, tests pass, docs updated.
- **One testable behaviour per PR**, ~200 lines soft, ~500 firm.
- **Humans merge.** Never automated away.

## The pages

### Writing code — the daily ones

| § | Page | Read when |
| --- | --- | --- |
| 1 | **[Architecture](01-architecture.md)** | Writing or reviewing application code |
| 2 | **[Coding Style](02-coding-style.md)** | Writing or reviewing any code |
| 3 | **[Testing](03-testing.md)** | Writing or reviewing tests · defining an invariant |
| 4 | **[Naming](04-naming.md)** | Naming anything in code |

### Working together

| § | Page | Read when |
| --- | --- | --- |
| 5 | **[Version Control](05-version-control.md)** | Committing, branching, opening a PR |
| 6 | **[Code Review](06-code-review.md)** | Reviewing, or responding to a review |
| 7 | **[README](07-readme.md)** | Creating or updating a project README |

### Running it

| § | Page | Read when |
| --- | --- | --- |
| 8 | **[Configuration & Secrets](08-configuration-secrets.md)** | Adding config, env vars, or anything secret |
| 9 | **[Authentication & Authorization](09-authentication-authorization.md)** | Building sign-in or permissions |
| 10 | **[External Integrations](10-external-integrations.md)** | Talking to a vendor, ERP, or third-party API |
| 11 | **[Containers & Local Development](11-containers-local-development.md)** | Dockerfiles, Compose, getting a project running |
| 12 | **[Dependencies](12-dependencies.md)** | Adding, upgrading, or choosing a library |
| 13 | **[Infrastructure](13-infrastructure.md)** | Terraform — provisioning anything |
| 14 | **[CI/CD](14-ci-cd.md)** | Pipelines, workflows, checks |
| 15 | **[Deployment](15-deployment.md)** | Deploying apps or configuring environments |

---

## How to cite a rule

Every page owns a **fixed number, never reused** — Architecture is always §1, Testing always §3.
So `Testing §3.4` is unambiguous anywhere: in a review comment, a commit body, a chat message.

This replaces the previous scheme, where numbering was inherited from a single combined document
and then split across pages — leaving README and Deployment both starting at §1.1 and colliding
with Architecture. Any §-reference in an older page or link should be treated as suspect.

## What's binding

**The result is binding. The route to it is not.** Enforcement splits three ways by what can
actually enforce each kind of rule — mechanical to CI, semantic to the agent plus the engineer,
irreversible to a human permanently.

## When a rule can be broken

**These standards describe the code we write.** Some code we do not control, and the patterns
cannot always reach it. Two recognised cases:

**A third party that offers no seam.** A library that reaches for a global, constructs its own
dependencies, or exposes no injection point. Patching it is then the only option available —
`allow_any_instance_of` and its equivalents are the right tool there, not a violation.

**Legacy code where the refactor costs more than the benefit.** Bringing a 2018 controller into
the layered structure to add one field is a bad trade. Comply with the pattern in the code you
are adding; do not rewrite the file to host it.

**What is required instead: say so where you do it.** A comment at the point of deviation naming
the rule and why it does not apply here — which is one of the cases
[Coding Style §2.4](02-coding-style.md) permits a comment for. For a structural deviation, the PR
description. **This is not a waiver and needs nobody's approval.** It is a note, so the next
reader knows it was a decision rather than an oversight, and so a reviewer is not re-litigating
it from scratch.

**What this is not.** "It was hard", "I ran out of time", or "the pattern felt heavy here" are
not this. **The test is whether code you do not control forces it.** If a seam could have
existed and you chose not to build one, that is an ordinary review conversation.

**What is never broken this way.** The carve-out is about *pattern and structure*, not about
safety. A vendor library's shape is no argument about any of these:

- A human reads every line of their own code.
- An attributable sign-off before merge, and a human performing the merge.
- No secret in an image, a repository, or a build argument.
- Anything irreversible is designed so that it does not have to be reversed: schema changes use expand, migrate, contract ([Deployment §15.6](15-deployment.md)), and the step that destroys data is its own deploy.

**Changing a binding standard** is a consequential act, because standards adherence is the one
thing enforced centrally.

## What this set does not cover

- **Process** — nothing on these pages describes how work is planned, committed, executed or
accepted, nor any ceremony, capacity calculation or sign-off.
- **Requirements** — nothing here says what to build. These pages describe how.
- **Estimation** — no page here carries story points, complexity points or sizing. The previous
Version Control Standards page carried a Fibonacci points scheme and a complexity escalation
loop; both are retired, not relocated.

---

## What changed in this consolidation

**Three generations were live at once.** Engineering Practices (Jan 2026) → Comprehensive
Engineering Standards → Technical Practices (Aug 2026). All three were readable and reachable,
and the oldest was the friendliest to read — so it was the one a newcomer would trust. The root
problem was never bad content; it was that nothing retired.

| Change | Why |
| --- | --- |
| Nine topics got their own pages for the first time — configuration, auth, integrations, dependencies, containers, infrastructure, CI/CD, and the deployment material | They existed **only** on the legacy page, so it could never be retired. README §7 mandates a Compose path whose rules lived there; Deployment assumed Terraform modules it never restated |
| Commit format settled on Conventional Commits | Two pages disagreed on subject-line format. Git Commit Message Standard is superseded on format; its principles were already migrated |
| `Spec:` and `AC:` commit footers removed | The spec they referenced no longer exists |
| Estimation and complexity escalation cut from Version Control | Planning material misfiled in an engineering standard |
| Commit and branch compliance becomes a CI check, required for new projects and adopted by existing ones as able | The most mechanisable rules in the corpus were consuming the attention that line-by-line review needs. "Maintainer" — a role appearing nowhere else — went with them |
| Squash-merge stated in Version Control | It was policy only on the oldest page and in a draft artifact, absent from the page that owns merge mechanics |
| Testing gained the invariants convention | Domain invariants need a defined, greppable home. See Testing §3 |
| Review environments extracted | They described nothing that exists, so they were never a standard. The standards run §1–§15 |
| The reading list survived | Beck, Fowler, Metz, thoughtbot, Better Specs — the only orientation material in the corpus, and it was sitting on the most superseded page |
| SOLID and indentation | Declared in generation one, never carried forward. Retired explicitly rather than lost silently |
