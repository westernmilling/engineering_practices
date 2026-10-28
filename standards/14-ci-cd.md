# 14. CI/CD

> Mirrored from Confluence: [14. CI/CD](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919623683/14.+CI+CD)
> Space `SD` · page `4919623683` · last modified in Confluence Oct 28, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

All projects use GitHub Actions. Workflows are modular and reusable.

---

## Baseline

**[GitHub — Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)**

What we take, and do not restate: **OIDC instead of long-lived cloud credentials** · **least
privilege on `GITHUB_TOKEN`** · **untrusted input never interpolated into a shell script** ·
self-hosted runners carry risks we avoid by not using them.

**We deviate on action pinning** — see §14.7.

---

## 14.1 Workflow architecture

**Reusable workflows do the work; composition workflows trigger them.**

| File | Trigger | Purpose |
| --- | --- | --- |
| `lint.yml` | `workflow_call` | Linter |
| `test.yml` | `workflow_call` | Test suite, with database services |
| `deploy.yml` | `workflow_call`, `workflow_dispatch` | Build, push to ECR, deploy to ECS |
| `pull_request.yml` | `pull_request` | Calls lint + test |
| `main.yml` | `push` to `main` | Calls lint + test + deploy to staging |

- **Reusable workflows are never triggered directly by events** — only `workflow_call`.
- **`deploy` declares `needs: [lint, test]`** and runs only if both pass.
- **Merges to main auto-deploy to staging.**
- **Production receives the image that passed staging; it is promoted, not rebuilt.** A successful staging deploy is what makes the production deploy available ([Deployment §15.3](15-deployment.md)). **This is the standard for new projects.**
- **Existing projects deploy to production by manual `workflow_dispatch`** until they have feature flags and keystones in place, and adopt promotion as they get them.
- **Every production deploy, promoted or manual, runs against a protected `production` environment:** required reviewers, deployment limited to `main`, and the OIDC trust for the production role pinned to that environment ([Configuration §8.2](08-configuration-secrets.md)).
- **Migrations are their own job**, between build and deploy, with the service deployments
depending on it — see [Deployment §15.6](15-deployment.md).

```yaml
# pull_request.yml
name: Pull Request checks
on: [pull_request]
jobs:
  lint:
    uses: ./.github/workflows/lint.yml
  test:
    uses: ./.github/workflows/test.yml
```

> **The table above is the older shape.** Newer repositories use a combined **`quality.yml`** with
jobs for lint, test and security scanning — the required status checks in §14.10 are
`quality / lint`, `quality / test`, `quality / scan_ruby`, `quality / scan_js` — plus a
separate `terraform-ci.yml` where the repo carries infrastructure.
> 
> **That is the newer convention, not drift**, and this table should be rewritten around it.
Flagged rather than done, because it needs someone to confirm which shape new projects should
start from.

## 14.2 Lint

```yaml
name: Linting
on: [workflow_call]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with:
          bundler-cache: true
      - run: bundle exec rubocop
```

TypeScript equivalent runs `yarn format-check` and `yarn lint` after a frozen-lockfile install.

## 14.3 Test

The test workflow runs the full suite against **real database services** — consistent with
[Testing §3.7](03-testing.md), which prohibits mocking the database.

- **Service containers carry health checks.** Without them, tests race the database starting and
fail intermittently, which is worse than failing consistently.
- **PostgreSQL uses `tmpfs` for its data directory** — RAM-backed, meaningfully faster, and the
data is disposable by definition.
- **No hardcoded values.** Environment comes from GitHub Actions variables.
- Install SQL client tools only where the project integrates with MSSQL.

```yaml
services:
  postgres:
    image: postgres:15
    options: >-
      --mount type=tmpfs,destination=/var/lib/postgresql/data
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

## 14.4 Security scanning

**Scanners run as required status checks. A finding blocks the merge.**

| Scanner | Job | Covers |
| --- | --- | --- |
| **`bin/brakeman`** | `scan_ruby` | Static analysis for Rails vulnerabilities — SQL injection, XSS, mass assignment, unsafe redirects |
| **`bin/bundler-audit`** | `scan_ruby` | Known CVEs in gems, against the ruby-advisory-db |
| **`bin/importmap audit`** | `scan_js` | Known vulnerabilities in pinned JavaScript dependencies |
| **Dependabot** | — | Weekly PRs for `bundler` and `github-actions` |

These are the scanners Rails 8 generates, kept rather than removed. **That is the standard: a new
Rails project keeps its generated security jobs and wires them into the required checks.**

**Rules**

- **A finding is fixed, or explicitly ignored with a reason.** A Brakeman ignore entry carries a
note saying why it is not exploitable here. An unexplained ignore is indistinguishable from
someone silencing a real finding to get a merge through.
- **Dependabot PRs get merged, not accumulated.** An unmerged dependency PR is exactly the
staleness that major-version pinning (§14.7) exists to avoid — leaving them open forfeits the
reason for that choice.
- **Dependabot covers `github-actions` as well as the language ecosystem**, which is what keeps
version tags current without anyone tracking releases.

## 14.5 Deploy

1. Checkout.
2. **Authenticate to AWS with OIDC.**
3. Log in to ECR.
4. Build and push the image, tagged `${{ github.sha }}`.
5. Run migrations as a separate job ([Deployment §15.6](15-deployment.md)).
6. Download the current task definition, render it with the new image, deploy.
7. Wait for service stability.

**Rules**

- **Image tags are the git SHA. Never `latest`** for a deployment.
- **AWS authentication is OIDC** — `role-to-assume` with `AWS_GITHUB_ACTIONS_ROLE_ARN` as a
GitHub *variable*. No `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` secrets.
- **Secrets reach the container through the task definition's `secrets` block**, from AWS. Never
as a `--build-arg`, never in the workflow's `env`.
- **Nothing the application reads is injected by the workflow.** Not secrets, and not
configuration either — see [Configuration & Secrets §8.2](08-configuration-secrets.md).
- Each service type (web, worker) gets its own download, render and deploy steps.
- **`wait-for-service-stability: true`**, so the workflow fails when the deployment does rather
than reporting success and leaving a broken service.

> **Two corrections to the superseded page.** Its reference workflow authenticated with
`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — long-lived credentials, which the baseline
advises against and which current repositories no longer use. And it injected non-secret
configuration through `environment-variables` on the render step, which §8.2 now places in AWS
with everything else the application reads.

## 14.6 Path filtering for monorepos

Where a repository holds both application and infrastructure code, filter paths so application CI
does not run on Terraform-only changes.

```yaml
- uses: dorny/paths-filter@v3
  id: path
  with:
    filters: |
      non_terraform:
        - '**'
        - '!infrastructure/terraform/**'
```

Downstream jobs gate on the filter output.

## 14.7 Action pinning

**Pin to major versions** — `actions/checkout@v4`. Never `@main`, never `@latest`.

|  | Ours | The baseline |
| --- | --- | --- |
| Action references | Major version tag | **Full-length commit SHA** — "the only way to use an action as an immutable release" |

**The baseline's concern is real.** A tag can be repointed. A compromised maintainer account can
move `@v4` and every workflow picks it up on the next run; a SHA cannot be moved.

**We use tags anyway, for two reasons.**

**Patches arrive without a merge.** A security fix inside `v4` reaches us on the next run. Under
SHA pinning it waits for a Dependabot PR and someone to merge it — and an unmerged dependency PR
is a realistic failure mode on a small team, which turns an immutability win into a staleness
loss.

**Our risk surface is small.** Every action in the list below is published by GitHub, AWS or the
Ruby org. The compromises that make SHA pinning compelling — `tj-actions/changed-files` in March
2025 being the clearest — have been individual-maintainer actions, and we use almost none.

> **The trigger to revisit.** That second reason holds only while it is true. **When a workflow
takes a dependency on a third-party action maintained by an individual or a small project, pin
that one to a SHA** — the argument above does not cover it. `dorny/paths-filter` in §14.6 is
already the exception.

*Considered and not adopted: SHA-pinning everything with Dependabot maintaining a trailing version
comment. Recorded so it is not reopened without new information — a third-party action entering a
workflow would be new information.*

Minimum versions: `actions/checkout@v4` · `ruby/setup-ruby@v1` · `actions/setup-node@v4` ·
`aws-actions/configure-aws-credentials@v4` · `aws-actions/amazon-ecr-login@v2` ·
`aws-actions/amazon-ecs-render-task-definition@v1` ·
`aws-actions/amazon-ecs-deploy-task-definition@v2`.

## 14.8 Permissions

**Least privilege on `GITHUB_TOKEN`.** Declare permissions explicitly per workflow rather than
inheriting a broad default:

```yaml
permissions:
  id-token: write      # only where OIDC is used
  contents: read
```

`id-token: write` belongs only in workflows that authenticate to AWS.

## 14.9 Untrusted input

**Never interpolate untrusted values directly into a shell script.** A PR title, branch name or
issue body is attacker-controlled on a public contribution, and `${{ }}` interpolation happens
before the shell sees it.

Pass them as arguments to an action, or assign them to an intermediate environment variable first.

## 14.10 The ruleset

**Every repository has the same ruleset on its default branch. One pattern, no variations.**

| Rule | Setting |
| --- | --- |
| **Required approvals** | **1** |
| Dismiss stale approvals on push | yes |
| **Approval of the most recent reviewable push** | **yes** |
| Require a pull request | yes |
| Required status checks | lint · test · security scans |
| Restrict who can merge | maintainers of the repository, no bots |
| Auto-merge | **disabled** |
| Block deletion | yes |
| Block non-fast-forward | yes |
| **Bypass actors** | **none** |

**No bypass actors.** A rule that admins skip is not a rule, and the people who merge most often
are admins.

**One approval, for now.** It may move to 2 as the team grows or to 0 if review moves elsewhere —
but it is one number across every repository, changed deliberately in one place, not drifted into
per repo.

> **This is what makes attributable sign-off real.** A named human must approve a change before
it merges, and the ruleset is the only thing that enforces it.

**Agent-authored work is approved by someone who did not drive the agent.** An agent pushing under an engineer's identity is indistinguishable from that engineer to the ruleset, so the rule is procedural: the approver is a different human, and the author never approves their own agent's output. Dependency-bot PRs still need a named human to merge.

**The required checks differ by project** because the workflows differ — `quality / lint`,
`quality / test`, `quality / scan_ruby`, `quality / scan_js` on the Rails apps. The *rule* does
not differ. Add every check the project runs.

> **This is what makes the mechanical tier real.** Commit format, branch format and lint belong
to CI so they stop consuming review attention. The mechanism exists and blocks merges
today. Commit and branch format are required additions for every repository; existing projects adopt them as able ([Version Control §5.7](05-version-control.md)).

**Security scanning is part of the required set** — see §14.4.

## 14.11 Anti-patterns

| Anti-pattern | Problem |
| --- | --- |
| Secrets as Docker `--build-arg` | Baked into image layers, recoverable from the registry |
| Hardcoded secrets in a workflow `env` block | Not rotatable, and visible in logs |
| Long-lived AWS access keys | Use OIDC |
| Service containers without health checks | Flaky tests from races against database startup |
| `bundler-cache: false` | Slow builds for no benefit |
| Different language versions across projects | The superseded page recorded Ruby 2.5, 3.1.2 and 3.2.1 in use simultaneously |
