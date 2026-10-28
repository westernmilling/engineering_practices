# 3. Testing

> Mirrored from Confluence: [3. Testing](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4918607887/3.+Testing)
> Space `SD` · page `4918607887` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

## Baseline

| Source | What we take |
| --- | --- |
| **[Fowler, *Mocks Aren't Stubs*](https://martinfowler.com/articles/mocksArentStubs.html)** (and Meszaros' vocabulary) | The test-double taxonomy — dummy, fake, stub, spy, mock — and the distinction between **state verification** and **behaviour verification** |
| **Kent Beck on TDD** | Test-first: one failing test, minimal code to pass, repeat |
| **Arrange–Act–Assert** | The three phases of a test |
| **[thoughtbot — *Let's Not*](https://thoughtbot.com/blog/lets-not)** and **[*My issues with Let*](https://thoughtbot.com/blog/my-issues-with-let)** | The argument behind §3.4 |

**Where we sit on Fowler's spectrum.** Fowler presents classical and mockist testing as a
genuine choice and does not pick. **We pick classical** — assert the outcome, not the
interactions that produced it (§3.8).

Verifying an interaction is allowed where the interaction *is* the outcome — a message published,
mail sent — but it is written in state-verification shape: stubbed in Arrange, verified in Assert,
never as a pre-programmed expectation. That single choice explains most of §3.7.

*Fowler's term for asserting interactions is "behaviour verification". That is not what §3.8
means by behaviour — see the note there.*

### Considered and not adopted

**[Better Specs](https://www.betterspecs.org/)** — the best-known RSpec convention collection,
and we contradict it on three of its recommendations:

| Better Specs says | We say |
| --- | --- |
| Use `let` for lazy-loaded setup | **`let` is prohibited** (§3.4) |
| One expectation per unit test | Multiple assertions are allowed (§3.13) |
| Use shared examples to remove duplication | Explicit helpers with visible `include` (§3.4) |

Citing it as a baseline would mean citing a document that disagrees with us on the rules we most
care about. Listed here so its absence reads as a decision.

---

## 3.1 Test-first

**Every behaviour change starts with a failing test.** For a bug fix, the first test reproduces
the bug.

Write one test, watch it fail, write the minimal code to pass, repeat. **Do not batch all the
tests and then all the implementation** — work one behaviour at a time.

## 3.2 AAA with explicit comments

Every test with distinct setup, execution and verification phases carries explicit comments:
`# Arrange`, `# Act`, `# Assert`.

```ruby
it 'returns the processed result' do
  # Arrange
  batch = create(:batch)
  logger = spy
  instance = described_class.new(batch, logger)

  # Act
  result = instance.call

  # Assert
  expect(result).to have_attributes(status: 'completed')
end
```

**The mandatory comments are ours, not the pattern's.** AAA is usually a convention about
structure; we require it be marked. The phases then also define where stubbing and verification
are allowed to appear (§3.7).

One-liner declarative assertions need no comments: `it { is_expected.to validate_presence_of(:name) }`.

*This is the one exception to the comment discipline in [Coding Style §2.4](02-coding-style.md).*

## 3.3 Setup and teardown hooks are prohibited

`before`, `beforeEach`, `beforeAll`, `after`, `afterEach`, `afterAll`, `setUp`, `tearDown`,
`around` — **none of them, for domain setup.** All setup is inline, in the Arrange phase.

**Two acceptable uses, and no others:**

- Database cleaning strategy configuration, in a support file.
- `jest.restoreAllMocks()` in `afterEach` for TypeScript suites (§3.7).
- A third-party test library that genuinely requires one — the vendor exception in
[the hub](README.md), with a comment naming it.

If setup is identical across tests, **repeat the factory call** in each Arrange phase — that is
not duplication worth removing. Where it is genuinely complex, use a trait or a named builder
(§3.4). Do not use a hook to hide shared setup.

## 3.4 Inline variables only — no `let`

`let` and `let!` are prohibited. Use inline variables in each test. In TypeScript, `const`
inside the test function body — never at `describe` scope.

```ruby
it 'processes the batch' do
  # Arrange
  batch = create(:batch, status: :pending)
  service = described_class.new(batch)

  # Act
  result = service.call

  # Assert
  expect(result).to have_attributes(status: 'completed')
end
```

**Why, since this is the deviation people will question.** `let` is lazily evaluated and
overridable in nested contexts, so as a spec grows it stops being obvious where a variable comes
from or which override is in effect — and a `let` redefined in two contexts has defeated the
DRY-ing it was there for. The thoughtbot posts in the baseline make the full argument.

### Call factories directly

**`create(:batch, status: :pending)` is already the builder.** Do not wrap it. A
`build_pending_batch` method hides the attributes it sets, adds a name the reader has to go and
look up, and buys nothing.

**If you want a name for that variation, it belongs in the factory as a trait** —
`create(:batch, :pending)` — where every spec gets it and the definition has one home. See §3.6.

### When extraction is genuinely warranted

Some setup is real work: several objects wired together, an external dependency configured, a
fixture file loaded. Then extract — but **into an explicitly named builder or factory called
through its name**, never a bare method:

```ruby
# Good — the call site says where this comes from
batch = BatchBuilder.pending_with_transactions(count: 3)

# Bad — a bare method; the reader has no idea where it is defined
batch = pending_batch_with_transactions(3)
```

### Never `include` domain-object helpers

**Do not `include` a module that produces domain objects**, even a clearly named one. An
`include` makes its methods look local, so the call site stops saying where anything comes from —
which is the same problem as `let`, one level up.

**`include` is for DSL extensions**, where the thing being added is testing vocabulary rather
than domain data:

| `include` is fine | Call it by name instead |
| --- | --- |
| Custom matchers | Anything that builds domain objects |
| Assertion helpers | Anything that sets up domain state |
| Third-party test DSLs — `FactoryBot::Syntax::Methods` | Anything project-specific producing records |

**The test:** does it extend the *language* of a test, or supply the *subject* of one? Language
can be included, because a matcher reads as a matcher. A subject is named at the point of use.

## 3.5 Grouping hierarchy

```
Unit under test (class, module, component)
  └─ Method or behaviour
       └─ Scenario or precondition — starts with when / with / without
            └─ Expected outcome, from the user's perspective
```

Maximum four levels. Integration and feature tests may use domain language — `scenario`,
`feature` — instead of `describe` / `it`.

## 3.6 Factories

Use a factory library. No fixtures, no raw constructors beyond the trivial.

- `build` for objects that need no persistence; `create` only when persistence is required.
- **Traits** for variations (`:admin`, `:with_tenant`, `:processable`); **sequences** for unique
values; **transient attributes** to parameterise behaviour.
- **A trait is where a named variation belongs** — not a wrapper method in a spec file. If two
specs want "a pending batch", that is `:pending` on the factory, defined once.
- A fake-data library (Faker or equivalent) for realistic values.
- **Relationships are defined in the factory, not the test.**
- TypeScript: factory functions with `Partial<T>` for overrides.

## 3.7 Test doubles

**These hold across every project** — for code we control.

> **Where they do not reach.** A third-party library with no injection seam, or legacy code
whose refactor costs more than the benefit, is the recognised exception in
[the hub](README.md). Patching is then the tool
available, and `allow_any_instance_of` is the right answer rather than a violation — **with a
comment saying which library and why there is no seam.** §3.15 already carves this out for
re-querying; it is the same exception.

| Rule |  |
| --- | --- |
| **Stub in Arrange, verify in Assert** | Never combine setup and verification in one statement |
| **Never use message expectations** | `expect(obj).to receive(:m)` is prohibited — it verifies before the action runs. Use `allow(...)` in Arrange plus `expect(...).to have_received(...)` in Assert |
| **Name every double** | `double(:context, …)`. An anonymous double is acceptable only as a throwaway return value whose interface is never exercised |
| **Prefer type-safe doubles** | `instance_double(ClassName)` when the real class exists. TypeScript: `Partial<T>` cast at the call site |
| **`spy` when you only verify the call** | Loggers, publishers. `double` when you need to control a return value |
| **Inject, never patch** | Doubles arrive as constructor arguments or parameters. `allow_any_instance_of` is prohibited — it appears in no test file across any project |
| **Stub HTTP inline** | In Arrange, never in shared setup |
| **Never mock the database** | Real operations through factories and the ORM. Never stub `.find`, `.where`, `.create` |
| **Restore mocks — TypeScript** | `jest.restoreAllMocks()` in `afterEach`, one of the two permitted hooks |

> **Never stub `ENV`.** `allow(ENV).to receive(:fetch)` is patching global state, which the row
above prohibits — and it only works if the code happens to call the method you stubbed, so
`ENV['KEY']` sails straight past a stubbed `fetch`.
> 
> It is also usually a symptom: **if a unit test needs to stub `ENV`, the class under test is
reading configuration it should have been given** — the fix is
[Configuration & Secrets §8.1](08-configuration-secrets.md), not a cleverer stub. A class
reading `ENV` cannot be exercised with different configuration without a global mutation (§3.2)
or a patch (this section), and both are prohibited here. **Injection is what makes these rules
followable.**

### Environment variables in tests

**`.env.test` holds whatever the suite needs.** Not an exception to anything — it is how the test
environment gets configured.

**Beyond that, a compliant codebase does not need to change `ENV` in a test at all.** Configuration
is read at boot and injected (§8.1), so nothing reads `ENV` while a test runs — and a feature test
cannot be affected by changing a variable that was read before it started.

**Including configuration space itself**, if the loader takes the environment as a parameter:

```ruby
# The boundary is still the only thing that touches ENV —
# but it is handed the environment rather than reaching for it.
AgrisConfig.from(ENV)          # in config/initializers
AgrisConfig.from(described_class::EMPTY)   # in a test — a plain hash
```

Then the config loader is tested like anything else, with no global manipulation and no gem.

### ClimateControl — for code we have not fixed yet

**[ClimateControl](https://github.com/thoughtbot/climate_control)** sets the real variable and
restores it, so any read form works and nothing leaks. It has exactly two uses:

- **Legacy classes still reading `ENV` directly**, pending the §8.1 migration.
- **Vendor libraries that read `ENV` themselves** and cannot be injected — the carve-out in
[the hub](README.md).

```ruby
it 'retries when the vendor client times out' do
  # Arrange
  ClimateControl.modify VENDOR_TIMEOUT_MS: '1' do
    # the gem reads ENV itself; we cannot inject it
  end
end
```

**Inline, inside the example — never as an `around` hook.** The usual idiom is
`around { |ex| ClimateControl.modify(...) { ex.run } }`, and **§3.3 prohibits `around` blocks of
any kind.**

> **Reaching for it is a diagnostic.** Outside those two cases, needing ClimateControl means the
code under test is reading `ENV` — and the fix is §8.1, not the gem. As the migration completes,
uses of it should trend to zero and stay there.

**The `.tap` pattern** builds a double that needs both configured behaviour and to be returned
from another stub, keeping it a single expression inside Arrange:

```ruby
service = double.tap { |stub| allow(stub).to receive(:call) }
allow(Admin::SendWelcomeEmail).to receive(:new).and_return(service)
```

> **Why "never mock the database" matters more than it reads.** Fowler's article notes that
mockist tests couple to the *calls* a unit makes, so changing how collaborators are called
breaks tests that were not testing that. A mocked ORM is the worst case — it couples every
test to query construction, and no refactor of a query is safe.

## 3.8 Assert outcomes, not implementation

**A test should not know how the thing under test produced its result — only that the result is
correct.** We trust the outcome, not the route to it.

| Assert | Do not assert |
| --- | --- |
| Return values · side effects (records created, mail sent) · HTTP responses · rendered content · error messages · state visible to callers | Which private methods ran · internal variable values · the order of internal steps · the SQL generated |

**Why: brittleness.** A test that reaches into private internals is coupled to things that are
*supposed* to change — changing them is what refactoring is. When they change, the test fails
while the behaviour is still correct. Now you pay twice: once to work out that the failure is
spurious, and again to rewrite a test that was never testing anything a caller cares about.

The compounding cost is worse than the individual failures. A suite that breaks on every internal
change teaches people not to make internal changes. At that point the tests have stopped being a
safety net and become a tax on improving the code — the exact opposite of the reason they exist.

**The test for whether a test has this problem:** if a refactor that preserves all external
behaviour breaks it, it was asserting implementation.

> **A note on the word "behaviour", which is overloaded in testing.** This section is often
called "assert behaviour, not implementation" — there, *behaviour* means the observable outcome.
In Fowler's vocabulary (see the baseline), **behaviour verification** means asserting the
*calls* a unit made, which is the thing this section warns against. Two opposite meanings, one
word. This page says **outcome** when it means the result, and **interaction** when it means
the calls.

*This is the test-level form of the principle in [the hub](README.md):
the result is binding, the route to it is not.*

## 3.9 Assertion patterns

Structured matchers, not field-by-field comparison. Assert on object shape rather than whole-object
equality; on collection contents without depending on order; on a subset of fields when the rest
do not matter; and on **both the type and the message** of an error.

*Ruby:* `have_attributes`, `contain_exactly`, `include`, `be_empty`, `raise_error`, shoulda matchers.
*TypeScript:* `toEqual(expect.objectContaining(…))`, `toMatchObject`, `toHaveBeenCalledWith`,
`rejects.toThrow`.

## 3.10 Integration and feature tests

- **Page objects** encapsulate DOM traversal. Never scatter CSS selectors across test files.
- **Value objects** for form-filling data.
- A local translation helper scoping i18n lookups to the file.
- An authentication helper — `sign_in_as(user)` — abstracting the mechanism.
- External services stubbed through a fluent builder.
- Assert UI content by **localisation key**, not hardcoded string.
- Tag tests needing a browser so they get the right driver.

## 3.11 Configuration

Every project configures: **randomised order with a reproducible seed** · **verified or type-safe
mocks** · automatic support-file loading · **database isolation** (transactional by default,
truncation for integration tests running app and test in separate threads) · **coverage
reporting**.

## 3.12 Database cleanup

Transaction-and-rollback per test by default. Truncation for integration and browser tests, where
test and app run in different threads or processes. Truncate once at suite start.

## 3.13 Linter relaxations for test files

Disabled for tests: test length limits · multiple-assertion limits · block and function length ·
named subject requirements.

AAA tests with real Arrange phases are long, and the Assert phase legitimately checks several
properties. A linter tuned for application code will fight both.

## 3.14 No request specs for UI features — Rails

**Every piece of functionality is tested exactly once, at the appropriate layer.** For UI
features, request specs sit between controller specs and system specs without adding unique
value — duplicate coverage, extra reviewer load, no additional bugs caught.

**Exception: API endpoints.** For `Api::`-namespaced controllers and JSON endpoints, request specs
*are* the right layer — status codes, response bodies, authentication, content negotiation.

Configure generators to skip them: `g.request_specs false`. In a project that already has them for
UI features, add no more; migrate coverage when touching those files.

## 3.15 Mutating methods return evaluable state

A mutating method in our own code returns the mutated state, so callers and tests can evaluate the
result directly. **A test forced to re-query to verify an outcome is telling you the method's
interface is not testable.**

Re-querying is for legacy code and vendor libraries whose return values we do not control.

## 3.16 Never `reload`

`record.reload` and `reload!` are prohibited. Query fresh instead:

```ruby
result = MyModel.find(record.id)
expect(result.status).to eq('completed')
```

This makes the data flow explicit and avoids hidden mutation of a local.

## 3.17 File organisation

Test directories mirror source directories:

```
spec/                       # or tests/
├── factories/
├── invariants/             # §3.18
├── features/               # or integration/
├── models/
├── services/
├── controllers/            # or routes/
├── workers/                # or jobs/
├── form_objects/
├── presenters/
├── lib/
└── support/
    ├── database cleanup · factory config · browser driver · auth helper · http mocks
    ├── matchers/
    ├── page_objects/
    ├── value_objects/
    └── helpers/
```

## 3.18 Domain invariants

An invariant is **captured where the project records its rules** and **enforced here.** This
section is what an *"Enforced at"* reference points to.

**Location:** `spec/invariants/` — one file per invariant.

**The `describe` string states the rule in plain words. No IDs.**

```ruby
describe 'net weight equals gross minus tare' do
  it 'holds for a standard inbound load' do
    # Arrange / Act / Assert
  end

  it 'holds when tare is captured after gross' do
    # ...
  end
end
```

**No `KEY-INV-#` in the test.** The ID belongs to whatever captured the invariant — a
delivery-time record for one feature, while the invariant outlives it. A durable test carrying a
transient document's identifier is the same mistake as the `Spec:` commit footer, retired for the
same reason. **The test is the source of truth; it does not cite the document that produced it.**

The link runs one way, transient to durable: the *Enforced at* reference points at this file.
Nothing needs to point back.

**Where the *why* lives.** The rule is self-describing in the test name; the reason it holds
usually is not. Put that in a comment at the assertion — it is exactly
[Coding Style §2.4](02-coding-style.md)'s "hidden constraint the code cannot express":

```ruby
# Tare is captured at scale-in, before the load is disturbed. Capturing it
# after unload includes residue and overstates net by 20-40 lbs per load.
```

**Not in the capturing document alone.** That is where an invariant is *captured*; it is not where
the reasoning can live permanently, because the feature it belongs to will be finished and
archived while the invariant is still true.

**Why a directory rather than scattering them** among the units they touch: discoverability.
Someone defining a new feature needs to find the invariants that already exist, and a grep over
one directory answers that. Scattered through the suite, they are invisible.

**An invariant test is not a unit test.** It asserts a property that must hold wherever the code
touches it — so it tests the rule, not one path through it. Where an invariant is genuinely
universal, property-based testing fits well. **Not required**; example-based tests covering the
cases that could break it are enough.
