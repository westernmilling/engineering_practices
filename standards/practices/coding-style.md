# Coding Style Rules

> Mirrored from Confluence: [Coding Style Rules](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4812996626/Coding+Style+Rules)
> Space `BAE` · page `4812996626` · last modified in Confluence Aug 24, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

## 2.1 Linter-Enforced Style

Every project must have a linter configuration checked into the repo. Style rules are enforced by tooling, not by convention alone.

Rules:

* All lint exceptions must be declared in config files, not scattered as inline suppression comments (except where truly unavoidable).
* Metric limits (method length, complexity, class size) are kept enabled. Exclusions target specific files (migrations, generated code, test files), not entire rule categories.
* New projects adopt the strictest feasible defaults and relax intentionally.

**Ruby**: RuboCop with `rubocop-rails` minimum. New projects add `rubocop-rspec` and `rubocop-capybara`.

Mandatory Ruby style settings:

| Rule | Setting |
| --- | --- |
| String literals | Single quotes |
| Method chain line breaks | Leading dot |
| Boolean operators in conditionals | `&&`/`\|\|` (not `and`/`or`) |
| Multiline call indentation | Indented |
| Block length | Exclude test and config files |
| Class documentation | Exclude test and migration files |

**TypeScript**: ESLint with shared config packages, extended from `eslint:recommended` and `prettier`.

Mandatory TypeScript settings:

| Rule | Setting |
| --- | --- |
| Type definitions | `type` keyword (not `interface`) |
| Strict mode | `strict: true`, `strictNullChecks: true` |
| Type imports | `import type { X } from "..."` |
| Module resolution | `NodeNext` |

## 2.2 No Whitespace Alignment

Do not use extra whitespace to vertically align values, attributes, hash rockets, assignments, or comments. Each line stands on its own.

**Wrong:**

```ruby
short_name  = 'foo'
longer_name = 'bar'
```

```typescript
const port    = 3000;
const timeout = 5000;
```

**Right:**

```ruby
short_name = 'foo'
longer_name = 'bar'
```

```typescript
const port = 3000;
const timeout = 5000;
```

This applies to all languages. Most linters have a rule for this (Ruby: `Layout/ExtraSpacing`, TypeScript/JS: Prettier handles it automatically). Enable the linter rule rather than relying on convention alone.

## 2.3 Language-Specific Conventions

**Ruby:**

* Memoize expensive computations: `@var ||= ...`.
* Use `options.fetch(:key, default)` for required/optional parameters.
* Use `protected` for methods subclasses may need. Use `private` for strictly internal methods.
* Use `delegate` for forwarding methods to composed objects.
* Use `Struct` (or equivalent value type) for lightweight return types. Freeze all constant collections.
* In tests, use `described_class` instead of repeating the class name.

**TypeScript:**

* Explicit return types on all exported functions.
* Union types for domain variants; discriminated unions when appropriate.
* `Partial<T>` for optional subsets.
* `const` arrow functions for module-level functions.
* Optional chaining (`?.`) and nullish coalescing (`??`) over manual null checks.
* `throw new Error("descriptive message")` with try-catch blocks.
* Factory functions for test data: `const makeRecord = (args?: Partial<T>): T => ({ ...defaults, ...args })`.

## 2.4 Comments

**The code is the source of truth. Comments are not a place to restate it.**

Write code whose intent is clear from its structure and its names — that is the primary mechanism for conveying what the code does. Do not restate in a comment what the code already says, and do not paraphrase ticket text, requirements, or acceptance criteria into the code. Two copies of the same statement drift apart, and the code is the copy that runs.

**Only write a comment when the WHY is non-obvious:**

* A hidden constraint the code cannot express (e.g. "batch size capped at 500 — Postgres query planner regresses past this").
* A workaround for a specific bug in an upstream library or platform (link the issue).
* A subtle invariant a future editor could break without noticing (e.g. "order matters — `apply_tax` must run before `apply_discount`").
* Behavior that would surprise a reader with the domain knowledge already assumed by the file.

If removing the comment would not confuse a competent reader of the code, do not write it.

**Never write:**

* Comments that narrate the next few lines (`# Set the user's name`, `# Loop through orders`). The code says this.
* Comments that reference the current task, ticket, or PR (`# Added for VF-215`, `# Handles the case from ticket #123`). Those belong in the commit message and PR description. In the code they rot as ownership and context change.
* Multi-line commentary blocks that reproduce ticket descriptions, requirement text, or acceptance-criteria lists. Reference the ticket in the commit message or PR description instead.
* Section banner comments (`# ============ SETUP ============`). If a file needs section banners it needs to be split.
* Commented-out code. Delete it. Version control is the archive.

**Test files follow the same rule, with one exception:** the AAA structure comments (`# Arrange`, `# Act`, `# Assert`) required by the [Testing Rules](testing.md) page § 3.1 are mandated. Everything above still applies to any other comments in test files.

## 2.5 Monorepo Structure (multi-app projects)

When a project contains multiple deployable applications, use a monorepo with:

* **Workspace management** (Yarn workspaces, npm workspaces, or equivalent).
* **Task orchestration** (Turborepo or equivalent) for build/test/lint pipelines.
* **Shared packages** for: linter config, language config, test presets, logging, database clients.
* `apps/` directory for deployable applications.
* `packages/` directory for shared libraries.
* **Environment variables** enumerated in pipeline config for reproducible builds.
