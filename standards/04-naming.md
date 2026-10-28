# 4. Naming

> Mirrored from Confluence: [4. Naming](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919525385/4.+Naming)
> Space `SD` · page `4919525385` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

## Baseline

**[Ruby Style Guide — naming](https://rubystyle.guide/#naming-conventions)** for language-level
conventions: `snake_case` for methods and variables, `CamelCase` for classes and modules,
`SCREAMING_SNAKE_CASE` for constants, predicate methods ending in `?`, dangerous methods ending
in `!`. Enforced by RuboCop; not restated here.

**Everything below is ours.** The abbreviation prohibition and the suffix conventions have no
external source worth citing — the public guides cover casing and stop.

---

## 4.1 Descriptive, unabbreviated names

**All names — files, classes, methods, variables, database columns, test descriptions — are
descriptive and self-explanatory. Abbreviations are not used.** A reader understands what
something is or does without looking at its definition or the surrounding context.

**Prohibited:**

```
# Files
proc_inv.rb           → process_invoice.rb
bp_matrix_ent.rb      → basis_price_matrix_entry.rb
org_ctrl.rb           → organizations_controller.rb
usr_mgr.ts            → user_manager.ts

# Variables and parameters
bp                    → basis_price
org                   → organization
txn                   → transaction
amt                   → amount
qty                   → quantity
idx                   → index
cb                    → callback
res                   → response (or result — ambiguous either way, which is the point)
req                   → request
msg                   → message
cfg                   → configuration
tmp                   → name what it actually holds
data                  → name what data it is: invoice_data, price_records

# Methods
proc()                → process_invoice()
calc()                → calculate_delivery_price()
chk()                 → check_entity_is_active()
fmt()                 → format_currency()
```

**The only acceptable short names:**

- **Single-letter block variables in trivial iterations** where the type is obvious —
`items.each { |x| x.save }`. Even here, prefer a descriptive name once the block body runs to
more than one line.
- **Widely understood language idioms** — `i` in a numeric loop, `e` in a rescue or catch, `t`
as a scoped i18n helper in tests, `f` in a file block.
- **`id`** — not an abbreviation. It is the whole word.

**This applies everywhere:** source, tests, factory names, migration files, configuration keys,
route helpers, API field names.

> **Why this matters more than it used to.** A name is the densest signal available about intent,
and the author of most of our code is now a model that has no other access to what you meant.
`bp` tells it nothing; `basis_price` tells it the domain, the unit, and what it must not be
confused with. Our own abbreviations are the worst case — a model has seen `req` and `cfg` a
million times, and has never seen `bp` mean basis price.

## 4.2 Service objects

**Verb phrases** — `CreateOrganization`, `ProcessBatch`, `ImportPrices`, `ExportInvoice`.

**Namespaced by domain** — `Admin::CreateOrganization`, `BatchActions::AttachCsvFile`,
`admin/createOrganization.ts`.

*A service does one thing and its name is that thing. If the verb phrase needs an "and", the
service needs splitting — see [Architecture §1.2](01-architecture.md).*

## 4.3 Query objects

**Noun phrase with a `Query` suffix** — `InvoiceQuery`, `ContractPositionsQueryObject`.

**Methods named `with_*` or `by_*`** — `with_open_positions`, `by_delivery_month`. The prefix
says whether you are filtering on a property the record has or a value you are supplying, and it
keeps chains readable: `InvoiceQuery.new.with_outstanding_balance.by_customer(customer)`.

## 4.4 Background jobs

**`Worker` or `Job` suffix** — `ProcessBatchJob`, `LoadBatchJob`, `BasisPriceUpdateWorker`.

Pick one suffix per project and keep it. Two conventions in one codebase means every reader
checks which this is.

## 4.5 Presenters

**`Presenter` suffix** — `BasisPricePresenter`, `OpenInventoryPresenter`.

## 4.6 Test factories

**Named after the domain model** — `factory :user`, `factory :batch_transaction`.

**Traits describe the variation** — `:admin`, `:with_tenant`, `:processable`. A trait name says
what is different about this instance, not how it was built.

*Traits are also where a named variation belongs, rather than a helper in a spec file — see
[Testing §3.6](03-testing.md).*

## 4.7 Integration and feature tests

**File names describe the user's action** — `user_creates_a_new_bank_spec.rb`,
`user_signs_in_spec.rb`, `SecureRoute.test.tsx`.

**Scenario descriptions use third person** — "they see the details", "they are signed in".

*Third person rather than "I" because the test describes a user, not the person who wrote it —
and it reads correctly whoever is reading the failure.*

## 4.8 Test helpers

| Helper | Convention |
| --- | --- |
| Authentication | `sign_in_as(user)` or `sign_in(user)` |
| Translation | `t(key)`, scoped to the test file's domain |
| DOM identification | `dom_id(record)` or equivalent |

These are DSL extensions, so they may be included — unlike helpers that build domain objects,
which are called by name ([Testing §3.4](03-testing.md)).
