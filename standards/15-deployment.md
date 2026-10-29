# 15. Deployment

> Mirrored from Confluence: [15. Deployment](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4918673413/15.+Deployment)
> Space `SD` · page `4918673413` · last modified in Confluence Oct 28, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Where applications run, how they get there, and how to get back.

---

## Baseline

**[Twelve-Factor V — Build, release, run](https://12factor.net/build-release-run)** and
**[Factor X — Dev/prod parity](https://12factor.net/dev-prod-parity)**.

What we take, and do not restate:

- **Three separated stages.** Build produces an artifact; release combines it with config; run
executes it. **Code cannot be changed at runtime**, because there is no path back to the build.
- **Releases are immutable.** A release cannot be mutated once created — any change makes a new
one — and each has a unique identifier.
- **The run stage stays simple.** Build can be complex because developers are present; run
happens without them.
- **Keep environments similar.** Divergence between staging and production is where surprises
come from.

*This page is largely those two factors applied to ECS: an immutable image, promoted rather than
rebuilt, into tiers that match.*

**Secrets are in [Configuration & Secrets §8](08-configuration-secrets.md)**, not here.

---

## 15.1 Target platform

**All new projects and migrations deploy to AWS ECS Fargate.**

| Platform | Status |
| --- | --- |
| **AWS ECS Fargate** | **Standard** |
| Heroku | Deprecated |
| AWS Elastic Beanstalk | Deprecated |
| Bare metal / VM Docker | Deprecated |

Projects on deprecated platforms migrate as schedules allow.

## 15.2 Environment tiers

Production and staging are in use, and they are the whole estate. A review tier has been
proposed but not built, and is not covered by these standards.

| Tier | Purpose | Count | Lifecycle | Database |
| --- | --- | --- | --- | --- |
| **Production** | Live, customer-facing | 1 per project | Permanent | Managed RDS, production data |
| **Staging** | Replica of production, for validation before release | 1 per project | Permanent | Managed RDS, its own data — **never production's** |

**Staging is a structural replica of production** — same Terraform modules, same task
definitions, same service topology. The differences are the domain, the database, the
environment variable values, and the cost controls in §15.9: spot capacity, a single NAT
gateway, and a smaller Redis node. That is Factor X, and it is what makes staging validation mean
anything.

**Staging never connects to a production database.** It has its own RDS instance with its own
data.

## 15.3 Promotion

```
Developer branch
  │
  ├─ PR opened ──────────────► lint + test. No deploy.
  │
  └─ merge to main ──────────► lint + test ──► auto-deploy to STAGING
                                                  │
                                                  └─ staging deploy succeeds ──► production deploy (same image, same SHA tag)
```

- **Staging deploys automatically on merge to main.** Nothing further is required to make merged
work visible there.
- **Production is deployed from the image that was deployed to staging.** What was validated is what ships. Images are never rebuilt for production. **This is the standard for new projects.**
- **Promotion needs nothing environment-specific baked into the image.** If anything is compiled in (an asset host, a CDN URL, a domain), it moves to runtime configuration first.
- **Safety comes from feature flags and keystones,** so a promoted change can be switched off without a deploy.
- **Existing projects stay on manual production deploys via `workflow_dispatch`, from `main` only, against the protected `production` environment ([CI/CD §14.1](14-ci-cd.md)), until they have those safeguards, and adopt promotion as they get them.** Secrets live in
AWS Secrets Manager, not in the GitHub environment — see
[Configuration & Secrets §8.2](08-configuration-secrets.md).

> **⚠ Open: define feature flags and keystones**
> 
> They are the safety mechanism promotion relies on, and this page does not define them. **Link to where they are defined, or define them here, before any project adopts promotion.**

> **⚠ Open: confirm nothing environment-specific is baked at build time**
> 
> Our Rails Dockerfile sets `ARG RAILS_ENV="production"` and runs `assets:precompile` at build. **Confirm that output does not differ between staging and production before a project adopts promotion.** §15.2 says staging differs from production in "the domain, the database and the environment variable values", which is exactly where that would bite.

Today a PR runs lint and test, and nothing else.

## 15.4 Review environments — not a standard

**There is no review tier.** Nothing is built and nothing in these standards governs one.

## 15.5 Procfile convention

Every project has a `Procfile.dev` at the source root, for local development with Foreman or
Overmind:

```
web: bundle exec rails server -p 3000
worker: bundle exec sidekiq                  # when the project has background jobs
css: bin/rails tailwindcss:watch[debug]      # when the project uses Tailwind
log: tail -f log/development.log             # optional
```

**`Procfile.dev` is local only.** Production process management is ECS task definitions — each
process type is a separate ECS service.

## 15.6 Database migrations

**Migrations run as a discrete ECS task in the deploy pipeline, before any service updates.**
This is [Twelve-Factor XII](https://12factor.net/admin-processes) — an admin process run as a
one-off process in an environment identical to the application's.

```
build ──► migrate ──► deploy-web
              └─────► deploy-worker
```

The migrate job runs a dedicated ECS task family and the service deployments declare a dependency
on it, so **nothing updates until migrations have succeeded.**

**Why this rather than migrating on container start:**

|  | Discrete task | Entrypoint |
| --- | --- | --- |
| **How often it runs** | Once | Once per task that starts |
| **Concurrency** | Not possible | Needs a rule that only the web task migrates |
| **Failure looks like** | A failed deploy step, with logs | A container crash loop |
| **Health check grace period** | Irrelevant | Must exceed migration time, or the deploy kills itself |
| **Workers** | Wait for it by declared dependency | Start whenever, hopefully after |

### Schema changes: expand, migrate, contract

**A schema change that the running code depends on is never made in one step.** It is made in three, each its own deploy. This is the *parallel change* pattern (Fowler's [Parallel Change](https://www.martinfowler.com/bliki/ParallelChange.html) names the three phases; for databases, see [Liquibase](https://www.liquibase.com/technical-glossary/expand-contract-pattern) and [Prisma](https://www.prisma.io/dataguide/types/relational/expand-and-contract-pattern)).

| Phase | What ships | Reversible? |
| --- | --- | --- |
| **Expand** | Add the new column, table or index alongside the old. Nothing is removed or renamed. Old code is unaffected | Yes |
| **Migrate** | Write to both, backfill the new from the old, then move reads to the new. The old structure still exists and is still correct | Yes: roll the code back and the old structure is intact |
| **Contract** | Drop the old column or table, once nothing reads or writes it | **No.** This is the irreversible step |

**Why.** During any deploy, old and new code run against the same database. A single-step rename or drop breaks whichever side is not yet updated, and a rollback lands on a schema that no longer has what the old code needs.

**Worked example: replacing `price` with `price_cents`.**

1. *Expand:* add `price_cents`. Code is unchanged.
2. *Migrate:* write both columns; backfill `price_cents` from `price`; switch reads to `price_cents`; stop writing `price`.
3. *Contract:* after it has served traffic, drop `price`. In Rails, have the model ignore the column in an earlier deploy first.

**Rules**

- **Renames, type changes, and column or table removal are never a single migration.**
- **The contract step is its own pull request and its own deploy,** after the new structure has run in production long enough that you would not want to go back.
- **A backfill that rewrites data keeps the original until contract.** Never overwrite the only copy.
- **Rails projects use `strong_migrations`** so unsafe operations fail in development and CI rather than review.

## 15.7 Rollback

| Situation | Response |
| --- | --- |
| **Bad release** | Re-deploy the previous image SHA via `workflow_dispatch`. Tags are immutable git SHAs, so the last known-good image is always in ECR. *Promotion makes this a re-deploy of an existing image, not a rebuild. ECR lifecycle policies must keep at least the last N production SHAs, and repository tags are immutable.* |
| **Bad configuration, not code** | ECS retains previous task definition revisions. Update and force a new deployment |
| **Bad migration** | **Before the contract step, roll the code back: the old structure is intact.** After contract, write a new migration and deploy it forward. Never `rails db:rollback` in production |

*Immutable image tags are what make the first row possible, and they are Factor V's unique release
identifier doing its job.*

## 15.8 Monitoring and observability

| Concern | Tool | Notes |
| --- | --- | --- |
| Application logging | CloudWatch Logs | `awslogs` driver in the task definition |
| Error tracking | Rollbar (Ruby), AppSignal (TypeScript), or Datadog | Configured by environment variable — check the project for which |
| Container monitoring | ECS Container Insights | Enabled on the cluster |
| Infrastructure | CloudWatch Metrics | Automatic with ECS and ALB |
| Log retention | CloudWatch Log Groups | 14 days production · 7 days non-production |

## 15.9 Cost

| Strategy |  |
| --- | --- |
| **FARGATE\_SPOT** | 100% spot for staging; 50/50 spot and on-demand for production |
| **Right-sized tasks** | Start at the minimum (256 CPU / 512 MiB) and scale up on evidence |
| **Single NAT gateway** | Acceptable for non-production. One per AZ in production |
| **ECR lifecycle policies** | Expire old images, but always retain the last N production-deployed SHAs; `image_tag_mutability = IMMUTABLE`. |
| **Log retention** | Per §15.8 |
| **`cache.t3.micro` Redis** | Smallest ElastiCache node for non-production |
