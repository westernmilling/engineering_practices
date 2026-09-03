# Technical Practices

> Mirrored from Confluence: [Technical Practices](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4811915282/Technical+Practices)
> Space `BAE` · page `4811915282` · last modified in Confluence Aug 25, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Each page below is self-contained and focused on a single concern. Read the one that matches the task rather than working through all of them.

## Pages

| Page | Content | Read when |
| --- | --- | --- |
| [Architecture Rules](architecture.md) | Layering, service objects, query objects, presenters, background jobs, request handlers | Writing or reviewing application code |
| [Coding Style Rules](coding-style.md) | Linter enforcement, language conventions, comment discipline, monorepo structure | Writing or reviewing any code |
| [Testing Rules](testing.md) | Test-first development, AAA structure, mocking, assertions, integration tests, database cleanup | Writing or reviewing tests |
| [Naming Rules (Code)](naming.md) | Naming for services, queries, jobs, presenters, factories, and tests | Naming anything in code |
| [Version Control Standards](../version-control-standards.md) | Commit message format, branch naming, PR titles, PR size policy, complexity points | Committing, branching, or opening a PR |
| [README Standards](readme-standards.md) | Required README sections, the two developer paths, anti-patterns | Creating or updating a project README |
| [Deployment Strategy](deployment-strategy.md) | Environment tiers, secrets, migrations, rollback, monitoring, cost | Deploying apps or configuring environments |
| [Review Environments](deployment-review-envs.md) — **`UNPROVEN`** | PR-triggered review environments — lifecycle, naming, infrastructure, workflows, cleanup. **A proposed design, not an agreed standard — nothing here has been built yet.** | Designing or building preview environments |

---

**Note on file layout:** Confluence files *Version Control Standards* as a child of this page. In this repo it sits one level up at [`../version-control-standards.md`](../version-control-standards.md) to match the standards path used by tooling. Content is unchanged.
