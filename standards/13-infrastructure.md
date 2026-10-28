# 13. Infrastructure

> Mirrored from Confluence: [13. Infrastructure](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919263234/13.+Infrastructure)
> Space `SD` · page `4919263234` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Terraform. **All AWS infrastructure is defined as code — no resource is created by hand in the
console.**

---

## Baseline

**[HashiCorp — Terraform style guide](https://developer.hashicorp.com/terraform/language/style)**
for file layout, naming, and formatting. `terraform fmt` settles formatting; this page does not.

**[AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)** for the
reasoning behind the security and reliability choices below, where we have had to pick.

---

## 13.1 Directory structure

Terraform lives in `infrastructure/terraform/`, **one concern per file**, named after the AWS
service it manages:

```
infrastructure/terraform/
├── README.md            # architecture overview, prerequisites, usage
├── main.tf              # provider config and locals — nothing else
├── versions.tf          # Terraform and provider constraints
├── variables.tf   outputs.tf   data.tf
├── vpc.tf   subnets.tf   gateways.tf   route_tables.tf   security_groups.tf
├── acm.tf   route53.tf   alb.tf
├── ecs.tf   ecr.tf   iam.tf   cloudwatch.tf   secrets.tf
├── s3.tf   db.tf        # when applicable
└── example.tfvars       # placeholder values, committed, no secrets
```

- **One resource concern per file.** Do not combine unrelated resources.
- **Providers are declared only in `main.tf`.** No inline provider configuration elsewhere.
- **`.terraform/` and `*.tfstate*` are gitignored.** State is never committed.
- **A README is required** in every `infrastructure/terraform/`. Without one, the next person
reads twenty files to find out what the stack is.

> **At least one repository uses a module structure instead** — `infrastructure/terraform/modules/platform/…`
with modules for IAM, secrets and the rest. The flat layout above is what the superseded page
documented. **Unreconciled:** either flat is the convention and modules are an experiment, or
modules are the direction and this section is stale. Worth settling before publishing — a
shared-module approach would also give the organisation one place to fix a security-group
pattern rather than twenty.

## 13.2 Provider and versions

`main.tf` holds the provider and a `locals` block. The `application_name` local prefixes every
resource name, and a standard `tags` map goes on everything:

```hcl
locals {
  application_name = "ApplicationName"
  tags = {
    Application = local.application_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Team        = "DevTeam"
  }
}
```

**Every resource carries `local.tags`.** Untagged resources cannot be attributed to a project, and
cost questions then become archaeology.

**Version constraints** in `versions.tf`:

- **Terraform:** a minimum — `>= 1.7.0`.
- **AWS provider:** a pessimistic constraint on the major — `~> 6.0`, so patches arrive and
breaking changes do not.
- An exact pin is acceptable while actively developing a stack, and relaxed once stable.

> **Correction to the superseded page.** It instructed provider authentication via
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables. **Authentication is
Terraform Cloud workspace credentials, and OIDC in CI** ([CI/CD §14.5](14-ci-cd.md)). Long-lived
access keys are not the pattern anywhere else in these standards and should not be here.

## 13.3 Variables

- **Every variable has a `type` and a `description`.**
- **Sensitive values are marked `sensitive = true`** — otherwise they appear in plan output and CI
logs.
- **Defaults for what is consistent across environments** — region, port, instance count.
- **No defaults for what varies** — VPC CIDR, domain, database URL. A default on an
environment-specific value is a production outage waiting for someone to forget an override.
- Typed lists — `list(string)`, not bare `list`.
- **`example.tfvars` is committed**, with placeholders and no secrets.

## 13.4 Data sources and IAM

- Shared data sources live in `data.tf`.
- **IAM policies use the `aws_iam_policy_document` data source**, not inline `jsonencode` — it is
type-checked, and a malformed policy fails at plan rather than apply. Simple single-statement
policies may be inline.
- **Never `Resource = "*"` on a write action.** Scope to ARN patterns.

## 13.5 Networking and the load balancer

- **Security group rules carry a `description`.** A rule nobody can explain is a rule nobody will
remove.
- **The ALB redirects HTTP to HTTPS** — a port 80 listener that redirects, always.
- **`drop_invalid_header_fields = true`** on the ALB, against request smuggling.
- Single NAT gateway is acceptable below production; one per availability zone in production
([Deployment §15.9](15-deployment.md)).

## 13.6 State

- **Terraform Cloud manages state** for staging and production.
- **Secret variables live in Terraform Cloud workspace variables**, never in a `.tfvars` file.
- **Local `plan` and `apply` are for development only.** Running them against a managed environment
is how state drifts from reality.

## 13.7 Anti-patterns

| Anti-pattern | Problem |
| --- | --- |
| Inline `access_key` / `secret_key` in the provider | Credentials land in the state file |
| `Resource = "*"` on write actions | Permissions far beyond the need |
| Exact version pin on the AWS provider | Cannot receive patches |
| Security group rule without a `description` | Unauditable |
| Resources without `tags` | No cost attribution |
| No HTTP→HTTPS redirect on the ALB | Plaintext access remains possible |
| `drop_invalid_header_fields` unset | Request smuggling exposure |
| No Terraform README | Nobody can onboard to the stack |

*Terraform changes are a `terraform-ci.yml` concern in repositories that carry infrastructure, and
application CI is path-filtered to skip them ([CI/CD §14.6](14-ci-cd.md)).*
