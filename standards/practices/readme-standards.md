# README Standards

> Mirrored from Confluence: [README Standards](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4813422594/README+Standards)
> Space `BAE` · page `4813422594` · last modified in Confluence Aug 24, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Every project must have a `README.md` at the repository root. The README is the primary onboarding document — a new developer should be able to clone the repo and have a working environment by following it.

## 1.1 Required Sections

Every project README must include the following sections in order:

| Section | Purpose |
| --- | --- |
| **Project overview** | Name, one-line description, what it does, who it's for |
| **Tech stack** | Languages, frameworks, database, key libraries — one line |
| **Development setup** | Two paths: Docker Compose and Conventional (see 1.2) |
| **Authentication** | How to sign in during development (SSO bypass, seed users, etc.) |
| **Production** | How to build the production image, deployment target, environments, secrets (see 1.4) |
| **Project documentation** | Links to specs, ADRs, or other docs in the repo |

## 1.2 Development Setup — Two Paths

Every README must document two ways to run the application locally. Both paths must include every command needed from clone to running app.

**Path A: Docker Compose**

1. Prerequisites (Docker)
2. Copy `.env.example` to `.env`, fill in required values
3. `docker compose up --build`
4. Verify URL
5. How to run tests inside the container
6. How to connect to the compose database from host tools
7. How to stop and reset (`docker compose down`, `docker compose down -v`)

**Path B: Conventional (native runtime + standalone database)**

1. Prerequisites (language version, package manager)
2. Start the database using a standardized standalone container:

```shell
docker run --name pg16 -p 5432:5432 -d --rm \
  -e POSTGRES_PASSWORD=postgres \
  -v ~/PostgresData/16:/var/lib/postgresql/data \
  -v ~/Downloads:/tmp/Downloads \
  postgres:16
```

3. Install dependencies (`bundle install`, `yarn install`, etc.)
4. Set up the database (`db:create db:migrate db:seed`)
5. Start the application server
6. Start background workers (if applicable)
7. Reference `Procfile.dev` with Foreman/Overmind for running all processes at once
8. Run tests and linter commands

Rules:

* Every command must be in a code block — no prose-only instructions.
* Include the standalone database stop/start lifecycle (container uses `--rm`, data persists in `~/PostgresData/{version}/`).
* Path B is preferred for day-to-day development. Path A is preferred for onboarding and CI-like validation.

## 1.3 Project Overview

The overview section must include:

1. **Project name** as the H1 heading.
2. **One-line description** — what the app does in plain language.
3. **Primary users** — who uses this and why (one sentence).
4. **Tech stack line** — bold, formatted as: `Language X.Y / Framework Z / Database / Key UI libs`

Example:

````markdown
# My App

A billing dashboard for operations teams to track invoice status and payment timelines.

**Tech stack:** Ruby 3.3 / Rails 8 / PostgreSQL 16 / Hotwire / Tailwind CSS / Slim
````

Do not include marketing language, badges, or aspirational descriptions. State what the app does today.

## 1.4 Production Section

The production section must cover:

1. **Build command** — how to build the production Docker image.
2. **Image details** — note multi-stage build, excluded gem groups, non-root user, etc.
3. **Deployment target** — where the app is deployed (ECS Fargate, Heroku, etc.).
4. **Environment tiers** — table of environments (production, staging, review) with purpose and deploy trigger.
5. **Secrets management** — how secrets are injected (SSM, Secrets Manager, env vars).
6. **Link to deployment spec** — reference the spec file for full details.

If any of these are not yet configured, say so explicitly with a `> **Status:** Not yet configured.` callout. Do not omit the section — document the intended architecture even if it's not built yet.

## 1.5 README Anti-Patterns (Prohibited)

| Anti-Pattern | Problem |
| --- | --- |
| "Run `rails s` to start the app" with no database setup | New developer gets an immediate error |
| Only documenting Docker Compose, not conventional path | Developers who prefer native tooling are blocked |
| Only documenting conventional path, not Docker Compose | Onboarding friction for developers without the runtime installed |
| Stale commands that no longer work | Worse than no README — actively misleading |
| Placeholder README from framework generator | Signals the project is not maintained |
| Including secrets or real credentials | Security risk, even in examples |
| Including CI badges, code coverage shields, or marketing copy | Noise that obscures the useful content |

## 1.6 Maintenance

The README must be updated whenever:

* The development setup process changes (new env vars, new services, etc.).
* The deployment target or environment tiers change.
* The authentication method changes.

Reviewer must check README accuracy when reviewing PRs that change `docker-compose.yml`, `.env.example`, or deployment configuration.
