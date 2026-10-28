# 11. Containers & Local Development

> Mirrored from Confluence: [11. Containers & Local Development](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4918968324/11.+Containers+Local+Development)
> Space `SD` · page `4918968324` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Every project is containerized. The Dockerfile serves two purposes — production deployment and
local development portability. **A developer should be able to clone a repo, run one command,
and have a working environment.**

---

## Baseline

**[Docker's Dockerfile best practices](https://docs.docker.com/build/building/best-practices/)**
and **[the Compose Specification](https://compose-spec.io/)**.

What we take, and do not restate: multi-stage builds · layer cache ordering · `.dockerignore`
semantics · `USER` for non-root · combining `apt-get update` with `install` in one `RUN` ·
`ENTRYPOINT` for the command and `CMD` for its default flags.

*Docker's page is unversioned. It is vendor documentation for their own tool, so it will not
vanish, but it does shift — if it changes materially, the deltas below are where that shows up.*

---

## 11.1 Dockerfile structure

Every project has a `Dockerfile` at the repository root, in this order:

1. **Base image**, pinned.
2. **System dependencies** — one `RUN` layer.
3. **Non-root user** created and switched to **before application code is copied**.
4. **Application dependencies** — installed before application code, so the cache survives a
code change.
5. **Application code**, copied last.
6. **Entrypoint script** for runtime initialisation.
7. **Default command.**

## 11.2 Our deltas

|  | Ours | The baseline |
| --- | --- | --- |
| **Pinning** | Exact version tag — `ruby:3.2.1-slim-bullseye`, `node:20-alpine`. Never `latest`, never a loose range | Recommends pinning to a **digest** (`alpine:3.21@sha256:…`) for true reproducibility |
| **Image variant** | Prefer `-slim-bullseye` for Ruby, `-alpine` for Node. A full image needs a specific system library to justify it | No preference stated |
| **Port** | `EXPOSE` a variable defaulting to `3000` | Unspecified |
| **Ruby bundle** | `bundle config set --local without 'development test'` before install. Never ship test gems | N/A |

**On pinning:** a version tag is weaker than a digest — the tag can be repointed upstream. We
take the tag for legibility and because Dependabot manages the upgrades. If a build ever needs
to be byte-reproducible, the digest is the answer.

**Cache cleanup** happens in the same `RUN` as the install — `rm -rf /var/lib/apt/lists/*` or
the `apk` equivalent. A cleanup in a later layer removes nothing from the image.

**No secrets in the image.** Secrets are injected at runtime as environment variables, never
baked in with `ENV` at build time. Build-time `ARG` values are acceptable **only** where asset
precompilation requires a placeholder, and must be dummy values overridden at runtime — see
[Configuration & Secrets §8](08-configuration-secrets.md).

## 11.3 Multi-stage builds — TypeScript monorepos

Three stages, so build tooling, devDependencies and source never reach the production image:

| Stage | Does |
| --- | --- |
| **builder** | Install turbo, copy source, prune to the target package |
| **installer** | Install from the pruned lockfile, run the build |
| **runner** | Copy only built output, run as non-root |

## 11.4 Entrypoint scripts

Every Rails application has a `bin/docker-entrypoint` handling runtime initialisation:

```bash
#!/bin/bash
set -e

rm -f /app/tmp/pids/server.pid

bundle exec rails db:migrate

exec bundle exec "$@"
```

- Starts with `set -e` — fail on any error.
- Uses `exec`, so the application replaces the shell process and receives signals correctly.
- **Asset precompilation belongs in the build, not here.** It is a build concern.
- For Node projects the `CMD` is usually enough; use a script only when there is real runtime
initialisation, such as Prisma migrations.

> **Migrations are moving out of the entrypoint.** The direction is a discrete ECS task in the
deploy pipeline, which runs once rather than once per container and fails as a deploy step
rather than a crash loop — see [Deployment §15.6](15-deployment.md). Where a project has moved,
its entrypoint does not migrate and the script above is just the PID cleanup and `exec`.
Projects still migrating on start carry the grace-period and only-the-web-task rules in §15.6.

## 11.5 `.dockerignore`

Every project with a Dockerfile has one. Mandatory exclusions:

```
.git
.dockerignore
.byebug_history
.env*
!.env.project
!.env.vault
log/*
tmp/*
infrastructure/*
coverage/*
spec/*
test/*
node_modules/
.bundle/
vendor/bundle/
```

**`infrastructure/` is the one that matters most** — it keeps Terraform state, secrets and
configuration out of the build context and therefore out of the image.

## 11.6 Compose — local development only

Compose files here are for **local development**. Production is ECS Fargate
([Deployment §15](15-deployment.md)). A project needing a production-oriented compose file for
on-premise deployment puts it in `docker/production/docker-compose.yml`, separate from the
development one.

> **Corrected against the current spec.** The superseded page called for Compose v3 syntax and an
optional `version: "3"` key. The Compose Specification has **removed** `version` — it is
obsolete and current Compose warns on it. **Omit it.**

The development `docker-compose.yml` at the repo root mounts source as a volume for live reload,
includes development tooling, and exposes service ports to the host for debugging.

**Services**, in three categories:

|  |  |
| --- | --- |
| **Application** — built from the project Dockerfile | `web` (maps the app port to the host) · `worker` where there are background jobs, same image, different command |
| **Infrastructure** — official images | `postgres` / `mysql` (pin the major version) · `redis` · `mssql` where AGRIS or legacy integration needs it |
| **Third-party** | Anything the app depends on at runtime — e.g. `graphql-engine` for Hasura |

**Rules**

| Rule | Why |
| --- | --- |
| Named volumes for all persistent data | Survives `docker compose down` |
| `depends_on` with `condition: service_healthy` | The app starts after the database is actually ready, not merely running |
| Health checks on infrastructure services | What makes the above work |
| Source mounted as a volume in development | Live reload without a rebuild |
| A dependency cache volume — `bundle_cache` or equivalent | No reinstalling gems on every restart |
| Infrastructure images pinned to a major version | Patches flow, breaking changes do not |
| All configuration from a `.env` file | One source of truth, and it matches the production pattern |
| `restart: unless-stopped` on app services | Recovers from a crash mid-session |
| **Never** `network_mode: host` | Not portable across operating systems. Use explicit port mappings |
| **Never** a hardcoded password | `.env` file or an environment variable default |

## 11.7 The standalone database — for Path B

The native development path ([README §7.3](07-readme.md)) uses a standalone database container
rather than Compose. The standard invocation:

```bash
docker run --name pg16 -p 5432:5432 -d --rm \
  -e POSTGRES_PASSWORD=postgres \
  -v ~/PostgresData/16:/var/lib/postgresql/data \
  -v ~/Downloads:/tmp/Downloads \
  postgres:16
```

`--rm` removes the container on stop; the data persists in `~/PostgresData/{version}/`, so the
container is disposable and the database is not. The `~/Downloads` mount exists for importing
and exporting dumps.

One container serves every project on that major version — which is the point, and the reason
the name and path are conventions rather than per-project choices.

## 11.8 Anti-patterns

| Anti-pattern | Problem |
| --- | --- |
| `FROM ruby:2.5` — no variant, loose minor | Unpinned, full-size image |
| Baking secrets as `ARG` then `ENV` | **Secrets persist in the image layers** and are recoverable from any registry that holds it |
| `apt-get install` across several layers | Larger image, cache busted |
| `COPY . .` before installing dependencies | Every code change reinstalls everything |
| Running as root | No privilege separation |
| Legacy TLS configuration — `SECLEVEL=1` | Weakens transport security |
