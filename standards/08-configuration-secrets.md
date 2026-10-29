# 8. Configuration & Secrets

> Mirrored from Confluence: [8. Configuration & Secrets](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4920016897/8.+Configuration+Secrets)
> Space `SD` · page `4920016897` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Config, environment variables, and where secrets actually live.

---

## Baseline

**[The Twelve-Factor App, Factor III — Config](https://12factor.net/config)**

What we take from it, and do not restate:

- **Strict separation of config from code.** Config is what varies between deploys; code does
not.
- **Environment variables over config files** — changeable without a code change, hard to commit
by accident, language- and OS-agnostic.
- **Config is never grouped into named environments *inside the codebase*.** Grouping in the
deployment tooling is fine — see §8.3, which is the one place this needs care.
- **The litmus test**, which is the whole standard in one sentence:

> **Could this codebase be made open source right now, without compromising a single
credential?** If not, something is in the wrong place.

---

## 8.1 Environment variables

- **All secrets and connection strings come from environment variables.** No exceptions.
- **Required values use a fetch that raises on a missing key** — `ENV.fetch('KEY')`,
`process.env.KEY ?? throw`. A missing required variable fails at boot, loudly, not at 2am on
the one code path that reads it.
- **Optional values have sensible defaults.**
- **Never commit a `.env` file.** Provide `.env.example`, listing every required variable with
no real values. It is the documentation of what the app needs.

### Environment variables are read in configuration space, nowhere else

**No class or function reads an environment variable.** `ENV` is read once, at the boundary —
an initializer, a settings or configuration object, the framework's own credentials store — and
the resulting values are **injected** into whatever needs them.

```ruby
# Wrong — the class reaches into global state
class ExportPrices
  def call
    client = Agris::Client.new(url: ENV.fetch('AGRIS_URL'))
  end
end

# Right — configuration space reads it; the class is given what it needs
# config/initializers/agris.rb
AgrisConfig = Struct.new(:url, :timeout, keyword_init: true)
AGRIS = AgrisConfig.new(
  url: ENV.fetch('AGRIS_URL'),
  timeout: ENV.fetch('AGRIS_TIMEOUT', 5_000).to_i,
).freeze

class ExportPrices
  def initialize(agris_client)
    @agris_client = agris_client
  end
end
```

**Four reasons, and the first is the one that bites.**

**It is what makes the fail-fast rule above true.** A `fetch` that raises only helps if it runs at
boot. An `ENV.fetch` inside a method runs when that method runs — so a missing variable surfaces
on the one code path nobody exercised, at the worst possible time. **Reading at the boundary turns
a 2am incident into a failed deploy.**

**It is the only way the class is testable.** A class reading `ENV` cannot be exercised with
different configuration without mutating global state or patching it, both of which
[Testing §3.7](03-testing.md) prohibits. Injection is not a nicety here;
without it the rules in Testing cannot be followed.

**The constructor is the contract.** You can read what a class needs from its signature instead of
grepping its body for `ENV`.

**It is dependency injection** ([Architecture §1.2](01-architecture.md)). The class states what it
needs; it does not reach out for it. `ENV` is global state, and §1.2 already prohibits
dependencies arriving that way — this names the most common instance.

> **Testing it.** Never stub `ENV`. Suite-wide test configuration goes in `.env.test`, and a
compliant codebase needs nothing else — nothing reads `ENV` while a test runs. **Have the loader
take the environment as a parameter** (`AgrisConfig.from(ENV)`) and configuration space itself
is testable with a plain hash. ClimateControl is for legacy code and vendor libraries only —
see [Testing §3.7](03-testing.md).

> **The narrow exception.** A third-party library that reads `ENV` itself cannot be stopped, and
that is the vendor case in [the hub](README.md).
Framework-level mode checks — `Rails.env.test?` — are not configuration and are not covered here;
what §8.3 prohibits is using them to select *business* behaviour.

## 8.2 Where secrets live

**The application's configuration lives in AWS. GitHub holds only what the pipeline needs.**

> **The test:** does the **application** read it at runtime? Then it comes from AWS. Does only the
**deploy workflow** read it? Then it lives in GitHub.

Not secret-versus-not — that split scatters one application's configuration across two systems
based on a sensitivity judgment, and leaves you looking in two places to answer "what is this app
configured with?"

|  | Where | Holds |
| --- | --- | --- |
| **Application secrets** | **AWS Secrets Manager**, Terraform-managed | Database URLs and passwords, API keys, encryption keys |
| **Application configuration** | **AWS SSM Parameter Store**, Terraform-managed — **PROPOSED, not in use** | Log levels, domains, SMTP hosts, feature flags — everything else the app reads |
| **Pipeline values** | GitHub Actions environment | OIDC role ARN, region, ECR repository, cluster and service names, task definition path |

> **⚠ Parameter Store is a proposal, not current practice.** A search of the `westernmilling` org
found **no use of SSM Parameter Store anywhere.** Secrets Manager is used widely, with real
Terraform modules (`modules/platform/secrets/`, per-project `infrastructure/terraform/secrets.tf`,
a `create_aws_secrets.rake`). The only `ssm` hit in the org is a spec for **SSM Session Manager
bastion access to RDS** — a different service that shares the prefix.
> 
> **The decision to make:** put non-secret application config in Parameter Store, or put all of it
in Secrets Manager and accept the cost? Secrets Manager charges per secret per month and offers
rotation; Parameter Store's standard tier is free and offers neither, and a log level does not
need rotation. **The ECS task definition's `secrets` block injects from both identically** — a
`secretsmanager:` ARN and an `ssm:` ARN reach the application the same way — so this is purely
a cost and tidiness question, not an architectural one.
> 
> **Simplest answer is probably Secrets Manager for everything**, given it is already there with
Terraform modules, and introducing a second store to save a few dollars a month is its own kind
of two-places-to-look.

**Rules**

- **Everything the application reads comes from AWS**, injected through the task definition's
`secrets` block — Secrets Manager for secrets, Parameter Store for the rest.
- **Nothing the application reads is set in the deploy workflow.** A value injected by the
pipeline is configuration that exists only in a YAML file, invisible to anyone looking at the
environment.
- **AWS authentication in GitHub Actions uses OIDC.** `AWS_GITHUB_ACTIONS_ROLE_ARN` is stored as
a GitHub Actions **variable, not a secret** — a role ARN is not sensitive, and security is
enforced by the IAM OIDC trust policy rather than by hiding the string.
- **Never pass a secret as a Docker `--build-arg`.** It persists in the image layers.
- **Never commit a secret in any form**, including encrypted vault files.

## 8.3 Environment-keyed config in the repository

*§8.2 strengthens this: with the application's whole configuration in AWS and injected as flat
environment variables, the GitHub environment is purely deployment tooling and holds nothing the
application reads.*

**GitHub Actions environments are not a deviation from Twelve-Factor.** The factor's objection
is that *the app knows which group it is in*, with config living in the codebase keyed by
environment name — its stated example is Rails' `config/environments/`. Our grouping sits in the
deployment tooling: the workflow selects an environment, its values are injected as environment
variables, and the application receives a flat orthogonal set. The app never sees an environment
name. That is the model working as intended.

**The real deviation is the Rails-shaped one**, and it is the exact case the factor names:

| Compliant | The anti-pattern |
| --- | --- |
| `database.yml` with per-environment sections whose values are `ENV.fetch(...)` reads | `database.yml` with per-environment sections containing actual hosts, users or passwords |
| `RAILS_ENV` / `NODE_ENV` selecting a framework mode | `RAILS_ENV` selecting business behaviour from committed code |

**The rule:** environment-keyed files in the repository carry **structure, never values.** A
`database.yml` with three sections is fine if every value in it is an environment-variable read.
The moment a real host or credential appears in one of those sections, the config has moved into
the codebase and the litmus test fails.

This is largely unavoidable in Rails — the framework is built around `RAILS_ENV` — so the point
is not to fight it but to keep the environment-keyed layer empty of values.

## 8.4 Database configuration

- Keep environment-specific database config DRY — anchors, inheritance, or shared config.
- **Connection pool size:** match background job concurrency, plus overhead.
- **Connection timeout:** 5000ms default.

## 8.5 Multi-tenancy — when applicable

**The isolation level is a deliberate choice, not a rule.** Three options, each with real costs:

|  | Isolation | Cost |
| --- | --- | --- |
| **Row-level** — a tenant column and scoped queries | Weakest. A missing scope leaks data | Simplest to run. One schema, one migration |
| **Schema-level** — a schema per tenant | Strong | Migrations run N times. Connection pooling gets harder. Tooling here is thin and ageing |
| **Database-level** — a database per tenant | Strongest | Most operational overhead per tenant |

Pick for the blast radius the data actually warrants and the number of tenants you expect.

**Record it as a one-way door.** Changing tenancy isolation after there is data in it is among
the most expensive migrations available.

**What is firm:**

- **Background jobs set tenant context explicitly.** Never inherited implicitly — a job has no
request to inherit from, and a job that guesses its tenant will eventually guess wrong. This
is a correctness rule at any isolation level.
- **Provide a tenant-switching test helper**, whatever the isolation level. Tenancy bugs are
found by tests that cross tenants on purpose.

---

## Related

|  |  |
| --- | --- |
| Terraform managing Secrets Manager | [Infrastructure §13](13-infrastructure.md) |
| OIDC setup and workflow secrets scoping | [CI/CD §14](14-ci-cd.md) |
| Environment tiers and what each is for | [Deployment §15](15-deployment.md) |
| Documenting required variables in the README | [README §7.3](07-readme.md) |
