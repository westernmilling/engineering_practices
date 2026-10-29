# 7. README

> Mirrored from Confluence: [7. README](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919459854/7.+README)
> Space `SD` · page `4919459854` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Every project has a `README.md` at the repository root. It is the primary onboarding document:
**a new developer should be able to clone the repo and have a working environment by following
it.**

---

## Baseline

**None adopted.** The public conventions —
[Standard Readme](https://github.com/RichardLitt/standard-readme) and
[makeareadme.com](https://www.makeareadme.com/) — are generic section lists aimed at open-source
libraries. They have nothing to say about the two things that make this standard work: the
**two-path setup requirement**, and documenting production even when it does not exist yet.

Recorded so the omission reads as a decision rather than an oversight. Here the delta is the
whole page.

---

## 7.1 Required sections

In this order:

| Section | Purpose |
| --- | --- |
| **Project overview** | Name, one-line description, what it does, who it is for |
| **Tech stack** | Languages, frameworks, database, key libraries — one line |
| **Development setup** | Both paths (§7.3) |
| **Authentication** | How to sign in during development — SSO bypass, seed users |
| **Production** | Build, deployment target, environments, secrets (§7.4) |
| **Project documentation** | Links to docs in the repo, including the invariants location ([Testing §3](03-testing.md)) |

## 7.2 Project overview

1. **Project name** as the H1.
2. **One-line description** — what the app does, in plain language.
3. **Primary users** — who uses it and why, one sentence.
4. **Tech stack line** — bold: `Language X.Y / Framework Z / Database / key UI libs`.

```markdown
# My App

A billing dashboard for operations teams to track invoice status and payment timelines.

**Tech stack:** Ruby 3.3 / Rails 8 / PostgreSQL 16 / Hotwire / Tailwind CSS / Slim
```

No marketing language, no badges, no aspirational description. **State what the app does
today.**

## 7.3 Development setup — two paths

Every README documents **two** ways to run the application locally, each complete from clone to
running app.

|  | Recommended for |
| --- | --- |
| **Path A — Docker Compose** | **Anyone who is not doing daily development** — QA, onboarding, a stakeholder wanting a look, CI-like validation. One command, no toolchain to install, same result every time |
| **Path B — Native runtime + standalone database** | Daily development — fast feedback, a debugger you can attach, direct access to logs and the console |

> **⚠ Needs confirming with QA before publishing.** The paragraph below assumes QA works
mainly on staging and only occasionally locally. That assumption is mine, not something any
source states — and if it is wrong, Path A is QA's daily environment and deserves more
attention than it gets here.

**QA's primary environment is staging**, not local — merged work is deployed there
automatically and validated there ([Deployment §15](15-deployment.md)). On that assumption, Path
A covers the occasions QA needs it locally: reproducing something, or testing a branch before it
merges.

**Path A** covers: prerequisites · copy `.env.example` to `.env` and fill it · bring the stack
up · the verify URL · running tests inside the container · connecting to the database from host
tools · stopping and resetting, including how to drop volumes.

**Path B** covers: prerequisites with versions · starting the standalone database using the
standard container convention from [Containers §11](11-containers-local-development.md) · installing dependencies ·
database create/migrate/seed · starting the app server · starting background workers ·
`Procfile.dev` with Foreman or Overmind · test and lint commands.

**Rules**

- **Every command is in a code block.** No prose-only instructions.
- Include the database container's stop/start lifecycle and where its data persists.
- Keep both paths working. A project where one has silently rotted has one path, not two —
which is worth knowing, and worth saying in the README if it happens.

> **Why two paths.** Documenting only Compose blocks developers who prefer native tooling;
documenting only native blocks anyone without the runtime installed. The cost is keeping both
working — which is the point, because a path nobody runs is a path that is already broken.

## 7.4 Production

Cover, in order: the **build command** for the production image · **image details** (multi-stage,
excluded dependency groups, non-root user) · the **deployment target** · the **environment
tiers** with purpose and deploy trigger · **secrets management** · a **link to the deployment
detail** in [Deployment §15](15-deployment.md).

**If something is not configured yet, say so explicitly** — do not omit the section:

```markdown
> **Status:** Not yet configured.
```

Document the intended architecture even when it is not built. A missing section reads as an
oversight; a marked one reads as a decision.

> **There is no review tier.** Document production and staging only. A review tier has been
proposed but not built, and is not covered by these standards.

## 7.5 Anti-patterns

| Anti-pattern | Problem |
| --- | --- |
| "Run `rails s` to start the app", with no database setup | New developer hits an immediate error |
| Only the Compose path | Blocks developers who prefer native tooling |
| Only the native path | Onboarding friction for anyone without the runtime |
| Stale commands that no longer work | **Worse than no README** — actively misleading |
| The framework generator's placeholder README | Signals the project is unmaintained |
| Secrets or real credentials, even in examples | Security risk |
| CI badges, coverage shields, marketing copy | Noise obscuring the useful content |

## 7.6 Maintenance

The README is updated when any of these change:

- The development setup — new env vars, new services, changed versions.
- The deployment target or environment tiers.
- The authentication method.

**At review time**, check README accuracy on any PR touching `docker-compose.yml`,
`.env.example`, or deployment configuration.

> **Candidate for the mechanical tier.** A non-blocking CI warning when one of those files
changes and `README.md` does not would move this off human attention — the same treatment as
diff size in [Version Control §5.7](05-version-control.md). It is a heuristic and would
sometimes fire wrongly, which is why it warns rather than blocks. Not built; noted as the
obvious next step.

---

## Moved off this page

|  | Now in |
| --- | --- |
| The standalone database container command and its lifecycle | [Containers §11](11-containers-local-development.md) — it is a shared convention, not a README rule |
| Environment tier definitions | [Deployment §15](15-deployment.md) — this page says *document them*, that page says *what they are* |
