# 2. Coding Style

> Mirrored from Confluence: [2. Coding Style](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919951361/2.+Coding+Style)
> Space `SD` · page `4919951361` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

## Baseline

| Source | What we take |
| --- | --- |
| **[Ruby Style Guide](https://rubystyle.guide/)** | The reference RuboCop is built on. It deliberately leaves some choices open — §2.1 records where we closed them |
| **[Prettier](https://prettier.io/)** | TypeScript and JavaScript formatting, entire. It is opinionated by design, which is the point: no formatting discussion has ever improved a codebase |
| **`eslint:recommended`** and **typescript-eslint** | The TypeScript rule baseline |

**No baseline for §2.4 (Comments).** "Comment why, not what" exists everywhere as an adage and
nowhere as a usable standard. §2.4 is ours, and it is the most load-bearing section on this page —
three other pages depend on it.

---

## 2.1 The linter config is the standard

**Every project has a linter configuration checked into the repo, and that file — not this page —
is the source of truth for style.** Style is enforced by tooling, not by convention, and not by
reviewers reading diffs for quote characters.

This page documents only two things: **where we closed a choice the baseline left open**, and
**what a linter cannot check** (§2.3, §2.4).

**Rules about the config itself:**

- **Metric limits stay enabled** — method length, complexity, class size. Exclusions target
specific files (migrations, generated code, tests), never whole rule categories.
- **New projects adopt the strictest feasible defaults** and relax deliberately, because relaxing
is a decision and tightening later is a migration.

### Where an exception goes

**Config for policy. Inline for one-offs.** These are different things and putting both in the
config is what makes exclusions grow.

|  | Goes in | Why |
| --- | --- | --- |
| **Policy** — "block length is not enforced in specs" | The config file | A standing decision about a class of files. It belongs somewhere auditable, in one place, where you can read what has been turned off |
| **One-off** — "this particular method genuinely needs to be long" | An inline suppression | A config exclusion has to name a file or a path, and then **silently covers everything added to that file afterwards** — including code written next year that nobody decided anything about |

An inline suppression is surgical, sits where a reader can see why it applies, and stops at the
matching re-enable. That is more precise than a path exclusion, and more honest about how narrow
the exception really is.

**An inline suppression carries a reason:**

```ruby
# rubocop:disable Metrics/MethodLength -- vendor response shape; splitting hides the mapping
```

A bare `disable` with no reason is the thing that actually rots — nobody can tell later whether
it was considered or copied, so nobody removes it. **Re-enable explicitly** rather than letting a
suppression run to the end of the file.

> **Where these settings should actually live.** A table of RuboCop settings in a wiki page is two
sources of truth, and the one that runs will win. These belong in **a shared config package
consumed by every repo** — which exists for TypeScript and, as far as this consolidation can
tell, does not yet for Ruby. Until it does, the tables below are the specification for it, and
they are hand-applied per repo, which means they drift. **Creating that package is the fix, not
maintaining this table.**

### Ruby

**RuboCop with `rubocop-rails`** as the minimum. New projects add `rubocop-rspec` and
`rubocop-capybara`.

Where we closed a choice the Ruby Style Guide leaves open:

|  | Ours | The guide |
| --- | --- | --- |
| **String literals** | Single quotes | No community consensus — "pick one and apply it consistently" |
| **Method chain line breaks** | Leading dot | Leading and trailing both acceptable |
| **Boolean operators** | `&&` / `\|\|` always | `&&` / `\|\|` for logical expressions; permits `and` / `or` for control flow |
| **Multiline call indentation** | Indented | — |
| **Block length** | Excluded for test and config files | — |
| **Class documentation** | Excluded for test and migration files | — |

**On `and` / `or`:** the guide permits them for control-flow sequencing. We do not, anywhere.
Their precedence differs from `&&` / `||` in ways that produce working code with the wrong
meaning, and one rule you can apply without thinking beats two rules you have to choose between.

### TypeScript

**ESLint with the shared config package**, extending `eslint:recommended` and `prettier`.

|  | Ours |
| --- | --- |
| **Type definitions** | `type`, not `interface` |
| **Strict mode** | `strict: true`, `strictNullChecks: true` |
| **Type imports** | `import type { X } from "..."` |
| **Module resolution** | `NodeNext` |

**`type` over `interface` is a genuine deviation** — much of the TypeScript community prefers
`interface` for object shapes, or is neutral. We pick one so that a reader never has to wonder
why this file chose differently, and `type` is the one that covers every case, including unions
and mapped types, without switching syntax.

## 2.2 No whitespace alignment

Do not use extra whitespace to vertically align values, attributes, hash rockets, assignments or
comments. **Each line stands on its own.**

```ruby
# Wrong                      # Right
short_name  = 'foo'          short_name = 'foo'
longer_name = 'bar'          longer_name = 'bar'
```

Aligned columns look tidy and produce diffs where renaming one variable touches every adjacent
line, burying the real change.

**This is a linter rule, not a review rule** — `Layout/ExtraSpacing` in Ruby, and Prettier handles
it automatically in TypeScript. It appears here as an example of §2.1: the page names the choice,
the config enforces it.

## 2.3 Language conventions

What a linter cannot check.

**Ruby**

- Memoize expensive computations: `@var ||= ...`.
- `options.fetch(:key, default)` for required and optional parameters — `fetch` without a default
raises, which is what you want for a required one.
- `protected` for methods subclasses may need; `private` for strictly internal.
- `delegate` for forwarding to composed objects.
- `Struct` or an equivalent value type for lightweight return types. **Freeze all constant
collections.**
- `described_class` in tests rather than repeating the class name.

**TypeScript**

- **Explicit return types on all exported functions.** Inference is fine internally; an export is
a contract.
- Union types for domain variants; discriminated unions where the variant carries data.
- `Partial<T>` for optional subsets.
- `const` arrow functions for module-level functions.
- Optional chaining `?.` and nullish coalescing `??` over manual null checks.
- `throw new Error("descriptive message")` with try-catch.
- Factory functions for test data:
`const makeRecord = (args?: Partial<T>): T => ({ ...defaults, ...args })`.

## 2.4 Comments

> **The code is the source of truth. A comment is not a place to restate it.**

Write code whose intent is clear from its structure and its names — that is the primary mechanism
for conveying what code does. Do not restate in a comment what the code already says, and do not
paraphrase ticket text, requirements or acceptance criteria into the code. **Two copies of one
statement drift apart, and the copy that runs is the code.**

**Write a comment only when the *why* is non-obvious:**

- A hidden constraint the code cannot express — *"batch size capped at 500; the query planner
regresses past this."*
- A workaround for a specific upstream bug. Link the issue.
- A subtle invariant a future editor could break without noticing — *"order matters: `apply_tax`
must run before `apply_discount`."*
- Behaviour that would surprise a reader who already has the domain knowledge the file assumes.

**If removing the comment would not confuse a competent reader of the code, do not write it.**

**Never write:**

- Comments narrating the next few lines — `# Set the user's name`, `# Loop through orders`.
- Comments referencing a task, ticket or PR — `# Added for VF-215`. Those belong in the commit
message, and in the code they rot as ownership and context change.
- Blocks reproducing ticket descriptions, requirements or acceptance criteria.
- Section banners — `# ===== SETUP =====`. A file needing section banners needs splitting.
- Commented-out code. Delete it. **Version control is the archive.**

**Test files follow the same rule, with one exception:** the AAA structure comments required by
[Testing §3.2](03-testing.md) are mandated. Everything above still applies to any other comment
in a test file.

> **This section is depended on elsewhere.** It is what permits the *why* beside a domain
invariant's assertion ([Testing §3.18](03-testing.md)) and the note recording a deviation for a
vendor library ([the hub](README.md)). Both are the
first case above — a constraint the code cannot express.

## 2.5 Monorepo structure

When a project contains multiple deployable applications:

- **Workspace management** — Yarn or npm workspaces, or equivalent.
- **Task orchestration** — Turborepo or equivalent, for build, test and lint pipelines.
- **Shared packages** for linter config, language config, test presets, logging, database clients.
- `apps/` for deployable applications, `packages/` for shared libraries.
- **Environment variables enumerated in pipeline config**, so builds are reproducible.

*The shared linter-config package here is the same idea §2.1 wants across repositories — inside a
monorepo it already works.*
