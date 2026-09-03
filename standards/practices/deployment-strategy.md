# Deployment Strategy

> Mirrored from Confluence: [Deployment Strategy](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4812603432/Deployment+Strategy)
> Space `BAE` · page `4812603432` · last modified in Confluence Aug 24, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

## 1.1 Target Platform: AWS ECS Fargate

All new projects and project migrations must deploy to AWS ECS Fargate. The following deployment targets are deprecated:

| Platform | Status | Projects Using It |
| --- | --- | --- |
| AWS ECS Fargate | **Standard** | `payment_manager`, `commodity_prices` |
| Heroku | **Deprecated** | `masas`, `masas-mono/masas-agris-interface.ts` |
| AWS Elastic Beanstalk | **Deprecated** | `contracto` |
| Bare metal / VM Docker | **Deprecated** | `ap-workflow` |

Migration priority: Projects on Heroku and Elastic Beanstalk should migrate to ECS Fargate as schedules allow.

## 1.2 Environment Tiers

Production and staging are in use today. The review tier is a proposed design that has not been built yet — see § 1.4.

| Tier | Purpose | Count | Lifecycle | Database |
| --- | --- | --- | --- | --- |
| **Production** | Live customer-facing application | 1 per project | Permanent | Managed RDS, production data |
| **Staging** | Exact replica of production for final validation before release | 1 per project | Permanent | Managed RDS, staging data (never shares production DB) |
| **Review** — **`UNPROVEN`** | Ephemeral per-PR environment for QA and business validation of in-progress features | 0-N per project | Ephemeral (hours to days) | Snapshot of staging DB, isolated per environment |

Rules:

* Staging is an **exact infrastructure replica** of production: same Terraform modules, same ECS task sizes, same service topology. The only differences are the domain name, the database, and the environment variable values.
* Staging **never** connects to a production database. Staging has its own RDS instance with its own data.
* Review environments are **structurally identical** to staging but use smaller Fargate task sizes and single-node databases for cost optimization.
* A review environment must never share a database with staging or production. Each review environment gets its own database restored from a staging snapshot.

## 1.3 Environment Promotion Flow

```
Developer Branch
  │
  ├─ Pull Request opened → lint + test (CI only, no deploy)
  │
  ├─ Label `review-deploy` added → spin up review environment from PR branch
  │     │
  │     ├─ PR updated (new commits pushed) → rebuild and redeploy to existing review env
  │     │
  │     ├─ Label removed → tear down review environment + notify
  │     │
  │     └─ PR merged or closed → tear down review environment + notify
  │
  ├─ Merge to main → lint + test → auto-deploy to STAGING
  │
  └─ Manual trigger (workflow_dispatch) → deploy to PRODUCTION
```

Rules:

* Staging deploys are automatic on merge to main.
* Production deploys are manual (workflow_dispatch) and require explicit approval.
* The same Docker image (same SHA tag) is promoted from staging to production. Images are never rebuilt for production.
* GitHub Actions environments are used to scope secrets and add required reviewers for production.
* The review-environment branches of this flow are part of the unproven design in § 1.4 — today a PR runs lint and test only.

## 1.4 Review Environments

**Not yet built.** Review environments are a proposed design, not something that exists today. Everything this page says about the review tier — the label trigger, the per-PR database, the shared ALB, the cost figures — describes that proposal. See the [Review Environments](deployment-review-envs.md) page, which is a guide for building them rather than a description of current infrastructure.

## 1.5 Secrets Strategy

Secrets are managed at three levels, reflecting the three environment tiers:

| Level | Tool | What Lives Here | Used By |
| --- | --- | --- | --- |
| Infrastructure secrets | AWS Secrets Manager (managed by Terraform) | Database URLs, API keys that rarely change | Production, Staging |
| Deployment configuration | GitHub Actions environment variables/secrets | Non-secret config, SMTP settings, feature flags | All tiers |
| Review environment secrets | GitHub Actions `review` environment secrets | Review DB credentials, shared review config | Review only |

Rules:

* Secrets that are truly secret (database passwords, API keys, encryption keys) go into AWS Secrets Manager and are injected into ECS tasks via the `secrets` block in the task definition.
* Configuration that varies by environment but is not secret (log levels, domains, SMTP hosts) is injected as environment variables during the deploy workflow via `amazon-ecs-render-task-definition`.
* AWS authentication in GitHub Actions uses OIDC — `AWS_GITHUB_ACTIONS_ROLE_ARN` is stored as a GitHub Actions environment **variable** (not a secret). The role ARN is not sensitive; security is enforced by the IAM OIDC trust policy.
* Review environment database credentials use a single shared set of credentials (stored in the GitHub `review` environment) — each review DB is a separate RDS instance but with the same master username/password for simplicity.
* Secrets are never passed as Docker `--build-arg` values.
* Secrets are never committed to the repository in any form (including encrypted vault files for production).
* `.env.example` files document all required environment variables without real values.

## 1.6 Procfile Convention

Every project must have a `Procfile.dev` at the source root for local development with Foreman (or Overmind).

Required process types:

```
web: bundle exec rails server -p 3000       # or equivalent
worker: bundle exec sidekiq                  # when the project uses background jobs
css: bin/rails tailwindcss:watch[debug]      # when the project uses Tailwind CSS
log: tail -f log/development.log             # optional convenience
```

The `Procfile.dev` is for local development only. Production process management is handled by ECS task definitions (each process type is a separate ECS service).

## 1.7 Database Migration Strategy

Database migrations run as part of the Docker entrypoint script when the container starts.

Rules:

* Migrations run before the application starts accepting traffic.
* The ECS health check grace period (`health_check_grace_period_seconds`) must be set high enough to allow migrations to complete before health checks begin.
* Destructive migrations (dropping columns, tables) must be deployed in two phases: first deploy removes the code reference, second deploy (after confirming no rollback is needed) runs the destructive migration.
* For projects with multiple ECS tasks sharing the same database, only the web task should run migrations (workers start after the web task is stable).
* Review environment databases are restored from staging snapshots. Migrations run automatically on container start via the entrypoint script, applying any migrations in the PR branch that are not yet in staging.

## 1.8 Rollback Strategy

* **Immediate rollback**: Re-deploy the previous image SHA via `workflow_dispatch`. Since image tags are immutable git SHAs, the previous known-good image is always available in ECR.
* **Task definition rollback**: AWS ECS retains previous task definition revisions. If the issue is configuration (not code), update the task definition and force a new deployment.
* **Database rollback**: If a migration must be rolled back, write a new reverse migration and deploy it forward. Never use `rails db:rollback` in production.
* **Review environment rollback**: Not applicable. If a review environment is broken, destroy it (remove the label) and re-add the label to get a fresh one.

## 1.9 Monitoring and Observability

| Concern | Tool | Configuration |
| --- | --- | --- |
| Application logging | CloudWatch Logs | `awslogs` driver in ECS task definition |
| Error tracking | Rollbar (Ruby), AppSignal (TypeScript), or Datadog | Configured via environment variables — check the project's configuration for which tool is in use |
| Container monitoring | ECS Container Insights | Enabled on the ECS cluster |
| Infrastructure monitoring | CloudWatch Metrics | Automatic with ECS and ALB |
| APM / distributed tracing | **`NOT IN PLACE`** — to evaluate | No APM today. Candidates to evaluate: AWS X-Ray, or CloudWatch Application Signals for request tracing and service-level metrics on ECS. Decide before the next project goes to production. |
| Log retention | CloudWatch Log Groups | 14 days production, 7 days non-production, 3 days review |
| Review env notifications | GitHub PR comments | Every lifecycle event (see the [Review Environments](deployment-review-envs.md) page, § 1.1.8) |

## 1.10 Cost Optimization

| Strategy | Details |
| --- | --- |
| FARGATE_SPOT | Use for non-production and non-critical workloads. Weight 100% SPOT for staging and review, 50/50 FARGATE/SPOT for production. |
| Right-sized tasks | Start with minimum Fargate size (256 CPU / 512 MiB). Monitor and scale up only when needed. Review environments always use minimum size. |
| Single NAT gateway | Acceptable for development/staging/review. Use one per AZ in production. |
| ECR lifecycle policies | Set image expiration rules to clean up old images. Review images (`review-pr*`) expire after 30 days. |
| CloudWatch log retention | 14 days for production, 7 days for staging, 3 days for review. |
| `cache.t3.micro` Redis | Start with the smallest ElastiCache node for non-production. Review environments share the staging Redis instance. |
| Label-gated review environments | Review environments only exist when explicitly requested via PR label — no surprise costs. |
| Auto-teardown review environments | Merged/closed PRs and 48h-stale PRs are cleaned up automatically. |
| `db.t3.micro` for review databases | Smallest RDS instance for ephemeral review environments. `skip-final-snapshot` on deletion. |
| Shared ALB for review environments | All review environments share the staging ALB via host-based routing rules — no per-environment ALB cost. |
