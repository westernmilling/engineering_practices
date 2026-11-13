# engineering_practices

Engineering standards for Business Apps Engineering, mirrored from Confluence as
markdown so they can be read in-repo, diffed over time, and loaded by tooling.

## Start Here

- **[Engineering Standards](standards/README.md)** — the hub: the 60-second
  summary, how to cite a rule, when a rule can be broken, and the index of all
  fifteen pages.

## Which Page Do I Need?

| Working on | Read |
|---|---|
| Layers, service objects, patterns | [§1 Architecture](standards/01-architecture.md) |
| Style, lint, conventions | [§2 Coding Style](standards/02-coding-style.md) |
| Tests, assertions, invariants | [§3 Testing](standards/03-testing.md) |
| Class, method, variable names | [§4 Naming](standards/04-naming.md) |
| Commits, branches, PRs | [§5 Version Control](standards/05-version-control.md) |
| Reviewing or responding to review | [§6 Code Review](standards/06-code-review.md) |
| Writing a README | [§7 README](standards/07-readme.md) |
| Config, env vars, secrets | [§8 Configuration & Secrets](standards/08-configuration-secrets.md) |
| Sign-in, permissions | [§9 Authentication & Authorization](standards/09-authentication-authorization.md) |
| Vendors, ERP, third-party APIs | [§10 External Integrations](standards/10-external-integrations.md) |
| Dockerfiles, Compose, local setup | [§11 Containers & Local Development](standards/11-containers-local-development.md) |
| Adding or upgrading libraries | [§12 Dependencies](standards/12-dependencies.md) |
| Terraform, provisioning | [§13 Infrastructure](standards/13-infrastructure.md) |
| Pipelines, workflows, checks | [§14 CI/CD](standards/14-ci-cd.md) |
| Deploys, environments | [§15 Deployment](standards/15-deployment.md) |

## Source of Truth

Confluence is authoritative (space `SD`). Each file records the Confluence URL,
page ID, and last-modified date it was mirrored from. When the two disagree,
Confluence wins — and this repo needs re-syncing.
