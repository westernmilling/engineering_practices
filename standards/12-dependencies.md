# 12. Dependencies

> Mirrored from Confluence: [12. Dependencies](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4920049665/12.+Dependencies)
> Space `SD` · page `4920049665` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

What every project needs, and what we reach for.

---

## Baseline

**[Semantic Versioning 2.0.0](https://semver.org/)** — the contract a version number makes, and
what a major bump is telling you.

**Dependency currency is automated**, not scheduled: Dependabot raises weekly PRs for the language
ecosystem and for GitHub Actions ([CI/CD §14.4](14-ci-cd.md)), and `bundler-audit` fails the build
on a known CVE. **This page is about what to choose; keeping it current is a pipeline concern.**

---

## 12.1 Required capabilities

Every project has tooling for each of these. The tool is a preference (§12.2); **the capability is
not optional.**

| Capability | For |
| --- | --- |
| Linter / formatter | Style enforced mechanically ([Coding Style §2.1](02-coding-style.md)) |
| Test framework | Unit and integration tests |
| Test data factory | Structured object creation ([Testing §3.6](03-testing.md)) |
| Fake data generator | Realistic values |
| Database cleanup | Test isolation ([Testing §3.12](03-testing.md)) |
| HTTP mock | Stubbing external calls ([Testing §3.7](03-testing.md)) |
| Browser automation | Feature tests, where a UI exists |
| Coverage reporter | Visibility, not a target |
| REPL / debugger | Interactive debugging |

**A project missing one of these has a gap, not a preference.** The commonest is an HTTP mock —
without one, either the suite reaches the network or external calls go untested.

## 12.2 Preferences by language

**Preferences, not mandates.** A project with a good reason to differ should differ and say why;
a project differing because nobody checked is drift.

**Ruby**

|  |  |
| --- | --- |
| Linter | RuboCop + `rubocop-rails`, `rubocop-rspec` |
| Tests | RSpec |
| Factory | FactoryBot |
| Fake data | Faker |
| HTTP mock | WebMock |
| Browser | Capybara + Selenium |
| Coverage | SimpleCov |
| Background jobs | Sidekiq |
| Auth | Devise + OmniAuth ([§9](09-authentication-authorization.md)) |
| Search / filter | Ransack |
| Pagination | Kaminari |
| Forms | SimpleForm |

**TypeScript**

|  |  |
| --- | --- |
| Linter | ESLint + Prettier |
| Tests | Jest (backend), Vitest (Vite frontend) |
| HTTP testing | Supertest |
| React testing | `@testing-library/react` + `jest-dom` |
| End-to-end | Cypress |
| Fake data | `@faker-js/faker` |
| Mocking | Jest built-ins; Sinon where they do not reach |
| ORM | **Prisma — not settled.** See below |
| Logging | Pino |
| Type checking | TypeScript strict mode ([Coding Style §2.1](02-coding-style.md)) |

> **⚠ Prisma is not locked in.** It is what the TypeScript projects use, and the team has known
concerns about it that are **not written down anywhere.** Treat it as the current choice rather
than the standard: a new TypeScript project should expect this to be revisited, and should not
take the listing here as the question being closed.
> 
> **Two things this needs.** First, **the concerns recorded** — an unwritten reservation about a
load-bearing dependency gets rediscovered the expensive way, usually by whoever is midway
through depending on it. Second, **a decision or a trigger for one**: either an alternative is
evaluated, or the conditions under which we would switch are stated.
> 
> **An ORM is the clearest one-way door in this page.** Its types and idioms spread through every
query, model and test, so replacing one is not a dependency swap — it is a migration. Per §12.3
any project adopting it records that as a one-way door, with an honest posture.

## 12.3 Adding a dependency

A dependency is a long-term commitment made in a moment. Before adding one:

- **Does an existing dependency already do it?** Two libraries covering the same ground is how a
codebase ends up with both Pundit and CanCan.
- **Is it maintained?** Recent releases, open issues being answered, more than one maintainer where
it matters.
- **What does removing it look like?** A library behind a thin wrapper is replaceable; one whose
types and idioms spread through the codebase is a one-way door — record it as such if it is
load-bearing.
- **Does it earn its weight in a container image?** See [Containers §11.2](11-containers-local-development.md).

**Major version bumps are not routine.** SemVer says a major bump is a promise being broken — read
the changelog rather than merging the Dependabot PR on green, because green only means our tests
did not exercise whatever changed.
