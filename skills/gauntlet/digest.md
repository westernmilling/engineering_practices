<!-- synced-standards-tree: d3cc82ffc186135d3218605f46824325eddc7cb4 -->

# Standards digest

Hot points from `standards/` that a diff can break. Cite the section when raising one, and say
"per the mirrored standards": Confluence is the source of truth and this copy can lag. Each rule is
a prompt for a question, not a verdict. Where a rule and the target repo's `CLAUDE.md` disagree,
flag the conflict and do not pick a side. Run `scripts/check_digest.py` to see whether this digest
has drifted.

## Architecture

- [§1.1] Request handlers hold no business logic: parameter extraction, service delegation and response formatting only.
- [§1.1] `lib/` must not reference `app/` (except `lib/tasks/`). If a `lib/` class needs an application class, it is injected.
- [§1.2] A service has one public entry point, `.call`, with dependencies injected through the constructor and no reads of `ENV`.
- [§1.2] Multi-step mutations in a service are wrapped in a transaction, and the service returns a domain object or structured result, never a raw hash.
- [§1.3] Handler actions are 2–8 lines and pass data to templates as explicit arguments, not instance variables.
- [§1.4] Complex reads live in query objects, not models or handlers, and raw SQL strings are out except in a data-access library.
- [§1.5] Jobs are thin wrappers taking only serializable identifiers, and a job must be safe to run twice (check state first, prefer upsert, guard side effects).
- Patterns are used when the code has the problem the pattern solves, not as a checklist (the Wrong Abstraction guard in Architecture, "How to read this page"). Do not ask for a service or query object where the code has no such problem.

## Coding style

- [§2.1] The linter config is the style standard. Inline suppressions carry a reason and are re-enabled explicitly.
- [§2.4] Comments explain a non-obvious why only. Never narration, ticket or PR references, banners or commented-out code.
- [§2.3] Memoize expensive computations, use `fetch` for required options, freeze constant collections, and prefer `delegate` for forwarding.

## Testing (Better Specs as the base, with the standards' deviations)

- [§3.1] Every behaviour change starts with a failing test, and a bug fix starts with a test that reproduces it.
- [§3.2] Tests carry explicit `# Arrange`, `# Act`, `# Assert` comments, except one-line declarative matchers.
- [§3.3] No `before`, `after` or `around` hooks for domain setup. Repeat the factory call in each test.
- [§3.4] No `let` or `let!` (a Better Specs deviation). Use inline variables.
- [§3.4] No explicit `subject { }` block. The implicit subject is fine for one-line `is_expected` matchers (a Better Specs deviation, adopted on docs/adopt-better-specs).
- [§3.4] Shared examples are defined in the spec that uses them, except a behavioural contract several implementations satisfy (a Better Specs deviation, adopted on docs/adopt-better-specs).
- [§3.4] Do not wrap factories in helper methods, use a trait, and never `include` a module that builds domain objects.
- [§3.5] `describe '.class_method'` and `describe '#instance_method'`, contexts start with `when`, `with` or `without`, and descriptions never say "should" (Better Specs, adopted).
- [§3.6] Factories, not fixtures, with `build` unless persistence is needed and relationships defined in the factory.
- [§3.7] No `expect(...).to receive`: stub with `allow` in Arrange and verify with `have_received` in Assert.
- [§3.7] No `allow_any_instance_of` unless it is a vendor library with no injection seam, with a comment saying which and why.
- [§3.7] Never mock the database (`.find`, `.where`, `.create`) and never stub `ENV`.
- [§3.7] Name every double and prefer `instance_double`. Stub HTTP inline in Arrange.
- [§3.16] Never `reload`: query fresh (`Model.find(record.id)`) instead.
- [§3.15] A mutating method in our own code returns the mutated state. A test that must re-query is a sign the interface is hard to test.
- [§3.9] Tests cover the valid, edge and invalid cases, and assert both the type and the message of an error.
- [§3.8] Assert outcomes, not implementation. If a behaviour-preserving refactor would break the test, it asserts the wrong thing.
- [§3.13] One outcome per test, which may need several assertions. Do not push "one expectation per test" (a Better Specs deviation).

## Naming

- [§4.1] No abbreviations in names, including tests and migrations. `data` and `tmp` need a name for what they hold. `id` and trivial block variables are fine.
- [§4.2] Services are verb phrases namespaced by domain. If the name needs "and", it should be split.
- [§4.3] Query objects are noun phrases ending in `Query`, with `with_*` and `by_*` methods.
- [§4.4] Jobs end in `Job` or `Worker`, one suffix per project.
- [§4.7] Feature spec files describe the user's action, in the third person.

## Version control and PRs

- [§5.2] Commit subjects use a closed type list, a lowercase description, 50 characters soft and 72 hard, and no trailing period. Bodies explain why.
- [§5.3] PR titles follow the commit format, with no Jira key or task ID in the title.
- [§5.5] One testable behaviour per PR, about 200 lines of meaningful change as the target and about 500 as the firm expectation (not a hard gate).
- [§5.6] The PR description becomes the squash body, so it states the change and why. A human merges.

## Configuration, secrets and integrations

- [§8.1] `ENV` is read only in configuration space and injected from there.
- [§8.2] Never commit a secret in any form, never a `.env` file, and never a secret as a `--build-arg`.
- [§10.1] External API clients live in their own layer. The vendor's types do not reach services.
- [§9.2] Authorization is opt-out: the base handler verifies every action authorized.

## Dependencies, containers, CI and deploys (only when the diff touches them)

- [§12.3] A new dependency answers: does an existing one do it, is it maintained, what does removing it cost. A major bump means reading the changelog.
- [§11.2] Pin image tags exactly, never `latest`. No secrets in the image, and no test gems in the production bundle.
- [§14.7] Pin actions to a major version, never `@main` or `@latest`.
- [§14.9] Never interpolate untrusted values (PR title, branch name) directly into a shell script.
- [§15.6] Renames, type changes and column or table removal are never a single migration: expand, migrate, contract.

## Retired: do not enforce

Spec-driven delivery (a durable spec as the source of truth, `Spec:` and `AC:` commit footers, spec-slice PR scoping) and "invent no behaviour not in a spec". The standards removed these. A target repo's `CLAUDE.md` may still mention them.
