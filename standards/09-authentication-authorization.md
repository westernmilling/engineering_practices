# 9. Authentication & Authorization

> Mirrored from Confluence: [9. Authentication & Authorization](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919787522/9.+Authentication+Authorization)
> Space `SD` · page `4919787522` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

## Baseline

**[OWASP Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/)**
— V2 (Authentication) and V4 (Access Control) — and the
**[OWASP Top Ten](https://owasp.org/www-project-top-ten/)**, whose first entry is broken access
control.

What we take, and do not restate: session management, credential storage, lockout and recovery
requirements, and the principle that **access control is enforced server-side and denies by
default**.

**We do not implement authentication ourselves**, so most of ASVS V2 is a question about the
library and the identity provider rather than about our code.

---

## 9.1 Authentication

- **Use an established auth library.** Never hand-rolled. This is the single highest-leverage rule
on the page: the failure modes in authentication are subtle, well-documented, and already solved.
- **OAuth / OIDC via Microsoft Entra ID** is the provider.
- **Custom callback handling** where a provider needs it.
- **A user–provider association table**, so a user can have more than one identity.
- **A global authentication guard on the base request handler**, with auth routes explicitly
skipped. The guard is opt-out, never opt-in — an opt-in guard protects whatever someone
remembered to annotate.

*In use: Devise with OmniAuth across the Rails projects; Entra ID in the TypeScript interface.*

## 9.2 Authorization

**Policy-based, denying by default.**

- **A base policy denies every action.** A policy that forgets a rule fails closed.
- **A predicate method per action** — `can_create?`, `can_update?`.
- **Related actions delegate**: `can_new?` delegates to `can_create?`, `can_edit?` to
`can_update?`. The form and the thing it submits to cannot disagree about who may use them.
- **Collection filtering goes through a scope class** restricting visible records — authorization
on a list is a query concern, not a per-row check after loading everything.
- **Authorization failures are caught at the request-handler layer** and return an appropriate HTTP
response, not a stack trace.

*Authorization is a layer in [Architecture §1.1](01-architecture.md), and policies are one of the
optional objects there.*

### The direction

**Pundit, with roles as data.** A `Role` carrying a code and a description, a `UserRole` join, and
a `PolicyContext` carrying what policies need beyond the user.

**Roles are rows, not constants.** Adding a role is then data, not a deploy.

**Projects on CanCan converge when they are touched**, not as a migration of their own.
