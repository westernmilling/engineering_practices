# Architecture Rules

> Mirrored from Confluence: [Architecture Rules](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4811587586/Architecture+Rules)
> Space `BAE` · page `4811587586` · last modified in Confluence Aug 24, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

## 1.1 Layered Structure

Every project must organize code into explicit layers. Request handlers (controllers, route handlers, API endpoints) never contain business logic.

Required layers:

| Layer | Purpose | Ruby example | TypeScript example |
| --- | --- | --- | --- |
| Request Handlers | HTTP routing, parameter extraction, response formatting only | `app/controllers/` | `src/routers/`, `src/routes/` |
| Services | Business logic, orchestration, command execution | `app/services/` | `src/services/` |
| Domain Models | Persistence, validations, associations, domain rules | `app/models/` | Prisma models, `src/models/` |
| Background Jobs | Async boundaries, background processing | `app/workers/`, `app/sidekiq/` | BullMQ workers, `src/workers/` |

Optional layers (add when the project needs them):

| Layer | Purpose |
| --- | --- |
| Query Objects | Complex read operations, chainable filters, query composition |
| Input Objects / Form Objects | Multi-field input validation, request shaping, create/update param separation |
| Presenters / Formatters | Display logic: currency, date, unit formatting. Keeps models and views clean |
| Policies | Authorization rules, permission checks |
| Interactors | Multi-step command orchestration with rollback semantics |
| Custom Types | Data coercion, type casting for external system values |

## 1.2 Service Object Contract

All service objects expose a single public execution method (`.call`) as the entry point. Services are instantiated with dependencies, then executed.

Rules:

* **One public method**: `.call`. All other methods are non-public.
* **Constructor injection**: Services receive dependencies (clients, loggers, configuration) through the constructor, not through global state or singletons.
* **Transaction safety**: Services wrap multi-step mutations in database transactions.
* **Typed returns**: Services return domain objects or structured result types, never raw hashes or untyped maps.
* **Logger convention**: When a logger is optional, default to stdout.

**Ruby reference:**

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

# Result type when status + data are needed:
Result = Struct.new(:success, :data, :errors, keyword_init: true)
```

**TypeScript reference:**

```typescript
type Result<T> = { success: boolean; data: T; errors?: string[] };

export const createExportRequest = async (
  prisma: PrismaClient,
  data: RequestData,
): Promise<ExportRequest> => {
  // business logic
};
```

## 1.3 Thin Request Handlers

Request handlers (controllers, route handlers) handle only: authentication checks, parameter extraction, service delegation, and response formatting. No business logic.

Rules:

* Handler actions are 2-8 lines of meaningful code (excluding parameter definitions).
* Pass data to templates via explicit arguments, not shared mutable state (instance variables, request-scoped globals).
* Use localized message keys for user-facing feedback, not hardcoded strings.
* Authorization checks happen at the handler layer, before service delegation.

## 1.4 Query Object Pattern

Complex reads (joins, aggregations, multi-table filters) go in dedicated query objects, not in models or request handlers.

Rules:

* Query objects wrap a base query/relation and return `self` (or a new instance) for chaining.
* Methods use descriptive `with_*` or `by_*` naming.
* Query builders or ORM-level abstractions are acceptable for complex SQL; raw SQL strings are not (except in dedicated data-access libraries).

## 1.5 Background Job Pattern

Background jobs are thin wrappers. They fetch the record, delegate to a service, and handle error reporting. Business logic never lives in a job.

Rules:

* Jobs receive only serializable identifiers (IDs, keys), never complex objects.
* Jobs eager-load associations to avoid N+1 queries.
* Error handling: catch, report to error tracker, re-raise for framework retry.
* Complex job logic goes in a nested class or a separate service.

## 1.6 Route/Endpoint Modularization

Routes must be split into domain-specific files once the application serves more than one bounded context.

Rules:

* API routes are versioned (e.g., `/api/v1/`).
* Admin routes live under a dedicated prefix or namespace.
* Nested resource routes use shallow nesting to avoid deep URL hierarchies.
* Custom non-RESTful routes are the exception, not the norm.

## 1.7 Presenter/Decorator Pattern

Display logic (formatting currencies, dates, unit conversions, link generation) belongs in presenter/formatter objects, not in domain models or templates.

Rules:

* Presenters wrap a domain object and a view/formatting context.
* Presenters delegate raw attribute access to the wrapped object.
* Use the Null Object pattern when the wrapped object may be nil.
* Memoize expensive computations.

## 1.8 Input/Form Object Pattern

When a request handler collects input that does not map 1:1 to a domain model, use an input object (form object).

Rules:

* Input objects include validation logic.
* Provide factory methods for building from existing records.
* Separate output methods for different operations: `create_params` vs `update_params`.
* Implement serialization (`to_h` or equivalent).

## 1.9 Processor Pipeline Pattern

When a record must pass through multiple independent transformation steps, use a processor pipeline.

Rules:

* Each processor implements a common interface (e.g., `.call(record)`).
* Processors are assembled as an ordered collection and injected into the orchestrating service.
* Processors accept dependencies (API clients, loggers) through their constructor.

## 1.10 Request Handler Action Order

When a request handler defines multiple CRUD actions, order them alphabetically:

```
create, destroy, edit, index, new, show, update
```

Non-public/helper methods follow after a visibility separator.
