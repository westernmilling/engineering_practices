# Engineering Standards 2026

> Mirrored from Confluence: [Engineering Standards 2026](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4813160453/Engineering+Standards+2026)
> Space `BAE` · page `4813160453` · last modified in Confluence Aug 24, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

**What this is:** the engineering standards the team works to. Read the page that matches the work in front of you — nobody needs to read all of it at once.

## If You Only Have 60 Seconds

* **Developers drive.** There is no orchestrated pipeline — developers own their workflow.
* **Verify before you open a PR.** Tests cover the change, tests pass, docs updated.
* **One testable behavior per PR.** Target under ~200 LOC.
* **Humans merge.** Merges are never automated away.

## What's Here

[Technical Practices](practices/README.md) holds the binding engineering rules — architecture, coding style, testing, code naming, version control, README structure, deployment, and review environments. Each page is self-contained; read the one that matches the task.

**In flux:** the source-of-truth question is being revisited — see § 2.4 of [Coding Style Rules](practices/coding-style.md), which now treats the code rather than the spec as the source of truth. Several pages under Technical Practices still assume spec-driven development and AC-level traceability ([Version Control Standards](version-control-standards.md) in particular, with its `Spec:` and `AC:` commit footers and spec-slice PR scoping). Treat those as under review until reconciled.

## Relationship to Other Pages in This Space

**Overlap worth knowing about.** Three points of contact with existing pages in Business Apps Engineering:

1. [Comprehensive Engineering Standards for Project Development and Deployment](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4273963009) is the ancestor of the Technical Practices pages here. Where the two disagree, these pages are newer — they add test-first development, prohibit setup/teardown hooks outright, require inline test variables, and add comment discipline. That page also still holds material these pages do not cover: Docker, Docker Compose, Terraform, CI/CD, authentication, configuration, and dependency standards.

2. [Git Commit Message Standard](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4467687425) and the [Version Control Standards](version-control-standards.md) page here differ on subject-line format. That page asks for a capitalised subject with no prefix; this one mandates Conventional Commits (`feat(scope): lowercase description`). Pick one before enforcing either in review.

3. [Code Review Communication Standard](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4467556353) covers how review feedback is delivered, which nothing in this tree duplicates.
