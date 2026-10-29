# 1. Architecture

> Mirrored from Confluence: [1. Architecture](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919394307/1.+Architecture)
> Space `SD` · page `4919394307` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Layering, and the objects each layer is made of.

---

## Baseline

| Source | What we take |
| --- | --- |
| **[Fowler, PoEAA catalog](https://www.martinfowler.com/eaaCatalog/)** | Service Layer · Query Object · Unit of Work · Transaction Script · Data Mapper — the vocabulary and the problems each solves |
| **[Code Climate — 7 patterns to refactor fat ActiveRecord models](https://codeclimate.com/blog/7-ways-to-decompose-fat-activerecord-models)** | The Rails-specific set: value, service, form, query, view, policy and decorator objects, and the composition-over-concerns framing |
| **[Sandi Metz — The Wrong Abstraction](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction)** | The guard below |

**Two patterns here appear in neither** and are ours: the **Interactor** (multi-step command with
rollback semantics — closest relative is Transaction Script) and the **Processor Pipeline** (§1.9).

---

## How to read this page

**These are patterns available, not a checklist to satisfy.** A page listing ten of them invites
applying all ten, which is the failure mode Metz describes: an abstraction extracted before the
duplication has shown its shape is harder to remove than the duplication was.

> **Reach for a pattern when the code has the problem the pattern solves.** A controller action
with four lines of logic does not need a service object. A single scope does not need a query
object.

What is **not** optional is §1.1 — the layers, and business logic staying out of request handlers.
Everything after that is a named solution to a specific problem, to be used when you have it.

**One principle explains most of this page.** Services, query objects, presenters, form objects and
the rest are all the same move: **a distinct reason to change, pulled out into its own class.**
That is single responsibility in the formulation that is useful — *one reason to change*, not
*does one thing*. A handler changes when HTTP concerns change; a service when a business rule
changes; a presenter when the display changes. Keep them together and every one of those reasons
reaches into the same file.

**Count reasons to change, not verbs.** A service that authenticates, calls and parses is doing
three things for one reason, and splitting it buys three files that always change together.

## 1.1 Layered structure

Code is organised into explicit layers. **Request handlers never contain business logic.**

**Required:**

| Layer | Purpose | Ruby | TypeScript |
| --- | --- | --- | --- |
| **Request handlers** | HTTP routing, parameter extraction, response formatting — only | `app/controllers/` | `src/routers/`, `src/routes/` |
| **Services** | Business logic, orchestration, command execution | `app/services/` | `src/services/` |
| **Domain models** | Persistence, validations, associations, domain rules | `app/models/` | Prisma models, `src/models/` |
| **Background jobs** | Async boundaries | `app/workers/`, `app/sidekiq/` | BullMQ workers, `src/workers/` |

**Optional — add when the project has the problem:**

| Layer | Solves | Named in |
| --- | --- | --- |
| **Query objects** | Complex reads, chainable filters, query composition | PoEAA · Code Climate |
| **Input / form objects** | Multi-field validation, input not matching one model | Code Climate |
| **Presenters / formatters** | Display logic — currency, dates, units | Code Climate (view objects) |
| **Policies** | Authorization rules, permission checks | Code Climate |
| **Interactors** | Multi-step orchestration with rollback | *ours* |
| **Custom types** | Coercion and casting for external system values | Code Climate (value objects) |

> **The baseline's framing, which fits ours.** Code Climate argues for composition over
mixins and concerns — logic distributed into focused objects rather than mixed into a model.
That is the same objection as the one to `include` in tests
([Testing §3.4](03-testing.md)): a mixed-in method reads as if it belongs to the object, so
the call site stops saying where behaviour comes from.

### Dependency direction — `lib/` must not reference application code

**Code in `lib/` MUST NOT reference anything in `app/`.** That is a dependency pointing the
wrong way.

`lib/` holds code that does not know what application it is in — an API client, a protocol
adapter, a generic utility. `app/` holds this product. **Generic may not depend on specific.**
The moment a file in `lib/` names a class from `app/`, it has stopped being general-purpose and
is now a part of the application filed in the wrong place.

**The test:** could this file be lifted into a gem, unchanged, and used by another project? If
not, it does not belong in `lib/`.

**When a `lib/` class needs something from the application, it is injected** — passed in by the
caller, never reached for. This is the same rule as
[External Integrations §10.1](10-external-integrations.md) and the same direction argument as
[Configuration & Secrets §8.1](08-configuration-secrets.md): the boundary resolves
dependencies, the inner code receives them.

> **Beyond Rails.** The principle is not about the folder name. Shared, reusable or
library-tier code must not depend on application-tier code, whatever the two are called in a
given project.

**`lib/tasks/` is the exception.** Rake tasks are application glue, not library code — their
whole job is to reach into the application and do something to it. They may name anything in
`app/`. The rule applies to the rest of `lib/`.

**The common way this slips through:** a `lib/` class and the `app/` class it reaches for sit
in the same module namespace, so Rails autoloading resolves the constant and nothing
complains. Being in the same namespace is not the same as being in the same layer.

**The fix is always injection** — the caller is application code, and may name application
classes, so let it do the resolving and pass the result in.

## 1.2 Service object contract

One public entry point: **`.call`**. Services are instantiated with dependencies, then executed.

- **One public method.** Everything else is non-public.
- **Constructor injection** — clients, loggers, configuration arrive through the constructor,
never from global state or a singleton. This is dependency injection: the
service is handed what it needs rather than reaching for a specific implementation. *It is also what makes the object testable without
patching ([Testing §3.7](03-testing.md)).*
**`ENV` is global state** — no class reads an environment variable, ever. Configuration is read
at the boundary and injected; see [Configuration & Secrets §8.1](08-configuration-secrets.md).
- **Transaction safety** — multi-step mutations are wrapped in a database transaction.
- **Typed returns** — a domain object or a structured result type. Never a raw hash or untyped map.
- **Logger** — when optional, default to stdout.

```ruby
class CreateOrganization
  def initialize(attributes)
    @attributes = attributes
  end

  def call
    Organization.transaction do
      # business logic
    end
    @organization
  end
end

Result = Struct.new(:success, :data, :errors, keyword_init: true)
```

```typescript
type Result<T> = { success: boolean; data: T; errors?: string[] };

export const createExportRequest = async (
  prisma: PrismaClient,
  data: RequestData,
): Promise<ExportRequest> => {
  // business logic
};
```

**`.call` is ours** — PoEAA's Service Layer says nothing about the entry point's name. It is
worth having because a uniform entry point means any service can be composed, injected or
stubbed without knowing its shape.

## 1.3 Thin request handlers

A handler does four things: authentication checks, parameter extraction, service delegation,
response formatting. **No business logic.**

- **Actions are 2–8 lines of meaningful code**, excluding parameter definitions.
- **Pass data to templates as explicit arguments**, not shared mutable state — no instance
variables, no request-scoped globals. An instance variable can be set in a callback or a
helper, so the template cannot tell you where its data came from.
- **Localised message keys** for user-facing text, not hardcoded strings.
- **Authorization happens at the handler**, before delegating.

## 1.4 Query objects

Complex reads — joins, aggregations, multi-table filters — live in query objects, not in models
and not in handlers.

- A query object wraps a base query or relation and returns `self` (or a new instance) so it
chains.
- Method naming is in [Naming §4.3](04-naming.md).
- **Query builders and ORM abstractions are fine; raw SQL strings are not** — except inside a
dedicated data-access library, where SQL is the point.

## 1.5 Background jobs

Jobs are thin wrappers: fetch the record, delegate to a service, handle error reporting.
**Business logic never lives in a job.**

- Jobs receive **only serializable identifiers** — ids and keys, never objects. A serialized
object is a snapshot that was already stale when the job ran.
- **Eager-load associations** to avoid N+1 queries.
- **Error handling:** catch, report to the error tracker, re-raise so the framework retries.
- Complex job logic goes in a nested class or a separate service.

### Jobs are idempotent

**A job must be safe to run more than once with the same input.** Running it twice produces the
same end state as running it once.

This is not defensive; it follows from the rule above. **We re-raise so the framework retries**,
and queues deliver at least once — a worker that completes the work and dies before
acknowledging will run it again. Neither of those is an error condition. A job that assumes it
runs exactly once is wrong on a normal Tuesday.

**How:**

- **Check state before acting.** Has this already been done? A `processed_at`, a status, the
existence of the record you were about to create.
- **Prefer naturally idempotent operations** — upsert over insert, set-to-value over increment.
Increments, appends and counters are the classic trap: correct once, wrong twice.
- **Guard side effects with a record**, written in the same transaction as the effect where
possible. A unique constraint is a better guard than a check-then-act, which races.
- **Use the vendor's idempotency key** on external calls that offer one.
- **Notifications count.** Sending an email or a message twice is not a silent failure — it is
the failure the recipient sees.

> **Where this is not optional.** Anything touching money, inventory or a vendor. *No invoice is
paid twice* is a domain invariant precisely because a retried payment job would break it — and
the invariant's test ([Testing §3.18](03-testing.md)) is what proves the job's guard actually
works.

**Where the work genuinely cannot be made idempotent** — an external system with no
idempotency key and no way to query what it already received — the guard is a record written on
our side before the call and checked before retrying, and that trade is worth a comment saying so.

## 1.6 Route and endpoint modularisation

Routes split into domain-specific files once the application serves more than one bounded context.

- **API routes are versioned** — `/api/v1/`.
- **Admin routes** live under a dedicated prefix or namespace.
- **Shallow nesting** for nested resources, to avoid deep URL hierarchies.
- Custom non-RESTful routes are the exception, not the norm.

## 1.7 Presenters and decorators

Display logic — currency, dates, unit conversion, link generation — belongs in a presenter, not in
a domain model and not in a template.

- A presenter wraps a domain object and a view or formatting context.
- It **delegates raw attribute access** to the wrapped object.
- Use the **Null Object** pattern when the wrapped object may be nil.
- **Memoize** expensive computations.

## 1.8 Input and form objects

When a handler collects input that does not map 1:1 to a domain model, use an input object.

- It carries its own validation.
- Provide factory methods for building from an existing record.
- **Separate output per operation** — `create_params` and `update_params` rather than one method
with a flag.
- Implement serialisation — `to_h` or equivalent.

## 1.9 Processor pipeline

When a record must pass through several independent transformation steps, assemble a pipeline.

- Each processor implements a common interface — `.call(record)`.
- Processors are an **ordered collection injected into the orchestrating service**, so the order
is data rather than control flow.
- Processors take their dependencies — API clients, loggers — through the constructor.

**Why the order is data and not control flow.** Adding, removing or reordering a step changes the
collection passed in — it does not change the orchestrating service. That is
[open/closed](https://en.wikipedia.org/wiki/Open%E2%80%93closed_principle): extend the behaviour
without modifying the thing that runs it. A pipeline built as a sequence of method calls has the
same steps and none of that property.

**Ours, not in either baseline.** The nearest named relative is Chain of Responsibility, which
differs in that a chain stops at the first handler that copes; a pipeline runs every step.

## 1.10 Handler action order

When a handler defines multiple CRUD actions, order them alphabetically:

```
create, destroy, edit, index, new, show, update
```

Non-public methods follow after a visibility separator.

**Arbitrary, and that is the point.** Any order would do; having one means nobody spends review
attention on where an action should go, and every handler in every project reads the same way.
