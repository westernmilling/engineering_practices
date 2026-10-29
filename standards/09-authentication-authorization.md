# 9. Authentication & Authorization

> Mirrored from Confluence: [9. Authentication & Authorization](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919787522/9.+Authentication+Authorization)
> Space `SD` · page `4919787522` · last modified in Confluence Oct 28, 2026.
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
- **Authorization is opt-out, like authentication.** The base request handler verifies that every action authorized: `after_action :verify_authorized`, and `after_action :verify_policy_scoped` on index actions (Pundit). An action that never called the policy raises, in tests and in production. **This is required for new projects; existing projects adopt it as able.** CanCan projects meet the same result with `check_authorization` in the base controller.
- **Fetching a record by id goes through the policy scope** (`policy_scope(Invoice).find(id)`, or `Invoice.accessible_by(current_ability)` in CanCan), then `authorize`. A bare `Invoice.find(params[:id])` followed by an update is the failure this rule exists to prevent.
- **Skipping is explicit and visible:** `skip_authorization` (CanCan: `skip_authorization_check`) with a comment saying why, which is the only way to opt an action out.

*Authorization is a layer in [Architecture §1.1](01-architecture.md), and **policies are required wherever authorization applies**; they are optional in Architecture §1.1 only for code with no authorization concern.*

### The direction

**Pundit, with roles as data.** A `Role` carrying a code and a description, a `UserRole` join, and
a `PolicyContext` carrying what policies need beyond the user.

**Roles are rows, not constants.** Adding a role is then data, not a deploy.

**Projects on CanCan converge when they are touched**, not as a migration of their own. Until they do, §9.2 still applies to them through the CanCan equivalents above, on the same new-project, adopt-as-able footing.
