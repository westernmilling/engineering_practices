# 15. Deployment

> Mirrored from Confluence: [15. Deployment](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4918673413/15.+Deployment)
> Space `SD` · page `4918673413` · last modified in Confluence Oct 27, 2026.
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
| **Staging** | Exact replica of production, for validation before release | 1 per project | Permanent | Managed RDS, its own data — **never production's** |

**Staging is an exact infrastructure replica of production** — same Terraform modules, same task
sizes, same service topology. The only differences are the domain, the database and the
environment variable values. That is Factor X, and it is what makes staging validation mean
anything.

**Staging never connects to a production database.** It has its own RDS instance with its own
data.

## 15.3 Promotion

```
Developer branch
  │
  ├─ PR opened ──────────────► lint + test. No deploy.
  │
  ├─ merge to main ──────────► lint + test ──► auto-deploy to STAGING
  │
  └─ manual trigger ─────────► deploy to PRODUCTION
```

- **Staging deploys automatically on merge to main.** Nothing further is required to make merged
work visible there.
- **Production deploys are triggered deliberately**, via `workflow_dispatch`. Secrets live in
AWS Secrets Manager, not in the GitHub environment — see
[Configuration & Secrets §8.2](08-configuration-secrets.md).

> **⚠ Open for discussion — promote or rebuild?**
> 
> The superseded page states promotion: *the same image, the same SHA tag, moves from staging to
production; images are never rebuilt.* **This is flagged rather than carried forward, because
it is not purely a preference — it depends on something about our builds that nobody has
confirmed.**
> 
> **The question underneath it:** does anything environment-specific get baked at build time? If
nothing does, promotion is strictly better. If something does, promotion cannot work until that
moves to runtime.
> 
> **The case for promoting**
> 
> - What was validated is what ships. A rebuild means staging tested a different artifact.
> - **Our base images are pinned to version tags, not digests** ([Containers §11.2](11-containers-local-development.md)).
A tag can be repointed upstream, so two builds of the *same commit* can genuinely differ. With
rebuild, that difference lands in production untested.
> - Rollback stays trivial — the previous image is in ECR. A rebuild-based rollback means
rebuilding an old commit, which may no longer build.
> - Faster production deploys, and it is Factor V's immutable release.
> 
> **The case for rebuilding**
> 
> - It permits environment-specific build-time configuration — asset host, CDN URL, anything
compiled in.
> - Each deploy workflow is self-contained, with no registry promotion or tag discipline to get
right.
> 
> **What to check before deciding.** Our Rails Dockerfile sets `ARG RAILS_ENV="production"` and
runs `assets:precompile` at build. If precompiled assets embed anything that differs between
staging and production — a domain, an asset host — then one image cannot serve both today, and
promotion requires moving that to runtime first. §15.2 says staging differs from production in
"the domain, the database and the environment variable values", which is exactly where that
would bite.

**This flow has no review-environment branches — that design is unbuilt (§15.4).** Today a
PR runs lint and test, and nothing else.

## 15.4 Review environments — not built

**There is no review tier.** A design exists — a PR label spins an environment up, pushes rebuild
it, closing the PR tears it down — but nothing has been built and it is not a standard, so it is
not described here.

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

**Destructive migrations deploy in two phases**, under either pattern. First deploy removes the
code that references the column or table. Second deploy — once you are confident there is no
rollback — drops it. One phase means a rollback lands on a schema that no longer has what the old
code needs.

## 15.7 Rollback

| Situation | Response |
| --- | --- |
| **Bad release** | Re-deploy the previous image SHA via `workflow_dispatch`. Tags are immutable git SHAs, so the last known-good image is always in ECR. *Depends on the promote-vs-rebuild decision in §15.3 — a rebuild-based rollback rebuilds an old commit instead* |
| **Bad configuration, not code** | ECS retains previous task definition revisions. Update and force a new deployment |
| **Bad migration** | **Write a new reverse migration and deploy it forward.** Never `rails db:rollback` in production |

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
| **ECR lifecycle policies** | Expire old images. |
| **Log retention** | Per §15.8 |
| **`cache.t3.micro` Redis** | Smallest ElastiCache node for non-production |

**The review-environment cost controls** — label gating, auto-teardown of merged and stale PRs,
`db.t3.micro` review databases, a shared ALB with host-based routing, review environments sharing
staging's Redis — are all part of the unbuilt design, and are not listed here: a cost control for
infrastructure that does not exist is a design note, not a standard.
