# Naming Rules (Code)

> Mirrored from Confluence: [Naming Rules (Code)](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4812210196/Naming+Rules+Code)
> Space `BAE` · page `4812210196` · last modified in Confluence Aug 24, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

## 1.1 General Rule: Descriptive, Unabbreviated Names

All names - files, classes, methods, variables, database columns, test descriptions - must be descriptive and self-explanatory. Abbreviations are not allowed. A reader should understand what something is or does without looking at its definition or surrounding context.

**Prohibited:**

```
# Files
proc_inv.rb           → process_invoice.rb
bp_matrix_ent.rb      → basis_price_matrix_entry.rb
org_ctrl.rb           → organizations_controller.rb
usr_mgr.ts            → user_manager.ts

# Variables / parameters
bp                    → basis_price
org                   → organization
txn                   → transaction
amt                   → amount
qty                   → quantity
idx                   → index
cb                    → callback
res                   → response (or result - ambiguous either way)
req                   → request
msg                   → message
cfg                   → configuration
tmp                   → (name what it actually holds)
data                  → (too vague - name what data it is: invoice_data, price_records)

# Methods
proc()                → process_invoice()
calc()                → calculate_delivery_price()
chk()                 → check_entity_is_active()
fmt()                 → format_currency()
```

**The only acceptable short names:**

* Single-letter block variables in trivial iterations where the type is obvious: `items.each { |x| x.save }` or `array.map { |i| i + 1 }`. Even here, a descriptive name is preferred when the block body is more than one line.
* Widely understood idioms within a language: `i` in a numeric loop, `e` in a rescue/catch, `t` as a scoped i18n translation helper in test files, `f` in a file operation block.
* `id` (not an abbreviation - it is the full word).

This rule applies everywhere: source code, test code, factory names, migration files, configuration keys, route helpers, API field names.

## 1.2 Service Objects

* Named as verb phrases: `CreateOrganization`, `ProcessBatch`, `ImportPrices`, `ExportInvoice`.
* Namespaced by domain: `Admin::CreateOrganization`, `BatchActions::AttachCsvFile`, `admin/createOrganization.ts`.

## 1.3 Query Objects

* Named as noun phrases with `Query` suffix: `InvoiceQuery`, `ContractPositionsQueryObject`.
* Methods named `with_*` or `by_*`.

## 1.4 Background Jobs

* Named with `Worker` or `Job` suffix: `ProcessBatchJob`, `LoadBatchJob`, `BasisPriceUpdateWorker`.

## 1.5 Presenters

* Named with `Presenter` suffix: `BasisPricePresenter`, `OpenInventoryPresenter`.

## 1.6 Test Factories

* Named after the domain model: `factory :user`, `factory :batch_transaction`.
* Traits/overrides describe the variation: `:admin`, `:with_tenant`, `:processable`.

## 1.7 Integration/Feature Tests

* File names describe the user action: `user_creates_a_new_bank_spec.rb`, `user_signs_in_spec.rb`, `SecureRoute.test.tsx`.
* Scenario descriptions use third person: "they see the details", "they are signed in".

## 1.8 Test Helpers

* Authentication helpers: `sign_in_as(user)` or `sign_in(user)`.
* Translation helpers: `t(key)` scoped to the test file's domain.
* DOM identification: `dom_id(record)` or equivalent.
