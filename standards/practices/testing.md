# Testing Rules

> Mirrored from Confluence: [Testing Rules](https://westernmilling.atlassian.net/wiki/spaces/BAE/pages/4812668933/Testing+Rules)
> Space `BAE` · page `4812668933` · last modified in Confluence Aug 25, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

## Test-First Development

All behavior changes require a failing test before implementation code.
For bug fixes, start with a failing test that reproduces the bug before writing the fix.
Write one test, watch it fail, write minimal code to pass, repeat.
Do not batch all tests then all implementation — work one behavior at a time.

### 3.1 Test Structure: AAA with Explicit Comments

Every test that has distinct setup, execution, and verification phases must use explicit AAA comments: `// Arrange`, `// Act`, `// Assert` (or `# Arrange`, `# Act`, `# Assert`).

**Ruby:**

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

**TypeScript:**

```typescript
it("returns the created record", async () => {
  // Arrange
  const org = await prisma.organization.create({ data: { ... } });

  // Act
  const result = await createExportRequest(prisma, requestData);

  // Assert
  expect(result).toEqual(expect.objectContaining({ ... }));
});
```

One-liner declarative assertions do not need AAA comments:

```ruby
it { is_expected.to validate_presence_of(:name) }
```

### 3.2 No Global Variables in Tests

Tests must not declare or depend on global variables. All state is scoped to the individual test using inline variables.

### 3.3 Setup/Teardown Hooks Are Prohibited

Setup and teardown hooks (`before`, `beforeEach`, `beforeAll`, `after`, `afterEach`, `afterAll`, `setUp`, `tearDown`) are prohibited for domain setup. All test setup belongs inline in each test case using the Arrange phase of AAA.

**The only acceptable uses of hooks:**

* Database cleaning strategy configuration (e.g., `DatabaseCleaner` in a support file).
* `jest.restoreAllMocks()` in `afterEach` for TypeScript test suites (see 3.7.8).

**Prohibited — no exceptions:**

* `before(:each)` / `beforeEach` for creating domain objects, setting up state, or configuring test data.
* `before(:all)` / `beforeAll` for shared mutable state.
* `after` / `afterEach` for anything other than mock restoration.
* `around` blocks of any kind.

If setup is identical across tests, extract a helper method and call it explicitly in each test's Arrange phase. Do not use hooks to hide shared setup.

### 3.4 Inline Variables Only — No Lazy Declarations

`let` and `let!` (Ruby) are prohibited in all tests. Always use inline variables within each test case.

**Required pattern:**

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

**Prohibited:**

```ruby
# NEVER — no let declarations
let(:batch) { create(:batch, status: :pending) }
let(:service) { described_class.new(batch) }

# NEVER — no let! declarations
let!(:batch) { create(:batch, status: :pending) }
```

**TypeScript:** Use `const` within each test function body. Do not declare shared `const` or `let` at `describe` scope.

If multiple tests need the same setup, extract a helper method that returns the constructed objects. Call it explicitly in each test's Arrange phase:

```ruby
def build_pending_batch
  create(:batch, status: :pending)
end

it 'processes the batch' do
  # Arrange
  batch = build_pending_batch
  service = described_class.new(batch)
  # ...
end
```

Define test helper methods in the same file where they are used. Do not silently include shared helper modules into test files — if a helper is needed across files, use a clearly-named module with an explicit `include` so the origin is visible.

This keeps every test self-contained and readable without hidden state.

### 3.5 Test Grouping Hierarchy

Follow a consistent nesting convention:

```
Top level: unit under test (class, module, component)
  Second level: method or behavior being tested
    Third level: scenario or precondition (prefixed with "when", "with", "without")
      Leaf level: expected outcome
```

Rules:

* The scenario level always starts with `when`, `with`, or `without`.
* Leaf-level descriptions describe the expected outcome from the user's perspective.
* Integration/feature tests may use domain language (`scenario`, `feature`) instead of generic `describe`/`it`.
* Nesting depth should not exceed 4 levels.

### 3.6 Test Data Factories

Use a factory/builder library for creating test data. Do not use raw constructors or fixtures for anything beyond trivial setup.

Rules:

* Use `build` (in-memory) for objects that don't need persistence. Use `create` (persisted) only when persistence is required.
* Use bulk creation helpers for collections (e.g., `create_list`).
* Use **traits** for test variations (e.g., `:admin`, `:with_tenant`, `:processable`).
* Use **sequences** for unique values.
* Use **transient attributes** for parameterizing factory behavior.
* Use a fake-data library (Faker or equivalent) for realistic dynamic values.
* Define relationships in the factory, not in the test.
* For TypeScript: use factory functions with `Partial<T>` for overrides.

### 3.7 Mocking and Stubbing

The team follows strict, consistent rules for test isolation. These are not guidelines - they are invariants observed across every project.

#### 3.7.1 Stub in Arrange, Verify in Assert - Never Mix

All stubbing (`allow`, `jest.spyOn(...).mockX`) happens in the **Arrange** phase. All mock verification (`have_received`, `toHaveBeenCalledWith`) happens in the **Assert** phase. Never combine setup and verification in the same statement.

**Ruby:**

```ruby
it 'sends a status email' do
  # Arrange - stub here
  delivery = double.tap { |stub| allow(stub).to receive(:deliver_now) }
  allow(BatchMailer).to receive(:status_changed).and_return(delivery)

  # Act
  instance.call

  # Assert - verify here
  expect(BatchMailer).to have_received(:status_changed).with(batch)
end
```

**TypeScript:**

```typescript
it("authenticates using the entra token", async () => {
  // Arrange - spy here
  const verifySpy = jest.spyOn(verify, "verifyToken").mockResolvedValue(true);

  // Act
  const response = await request(app)
    .get("/auth")
    .set("x-entra-access-token", "token");

  // Assert - verify here
  expect(verifySpy).toHaveBeenCalledWith("token");
  expect(response).toMatchObject({ status: 200 });
});
```

#### 3.7.2 Never Use Message Expectations

**Prohibited (Ruby):** `expect(object).to receive(:method)` - this sets up a verification _before_ the action runs, coupling Arrange and Assert.

**Required instead:** `allow(object).to receive(:method)` in Arrange + `expect(object).to have_received(:method)` in Assert.

This rule has zero exceptions across all examined projects. `expect(...).to receive(...)` does not appear in any test file.

#### 3.7.3 Named Doubles

All test doubles must have a descriptive name for debugging purposes.

**Ruby:** Pass a symbol name as the first argument to `double`, declared inline in the Arrange phase:

```ruby
it 'adds the entry to the invoice' do
  # Arrange
  context = double(:context, success?: true, invoice_line: InvoiceLine.new)
  entry = double(:entry, merge_hash: {}, to_h: {}, valid?: true)
  instance = described_class.new(context, entry)

  # Act
  result = instance.call

  # Assert
  expect(result).to have_attributes(success: true)
end
```

Anonymous doubles are acceptable only as throwaway return values in `.and_return(double)` when the return value's interface is not exercised.

#### 3.7.4 Type-Safe Doubles

Prefer type-safe doubles that enforce the real object's interface.

**Ruby:** Use `instance_double(ClassName)` instead of `double` when the real class is available:

```ruby
user = instance_double(User, id: 1)
organization = instance_double(Organization, id: 1)
```

**TypeScript:** Use `Partial<T>` and cast at the call site:

```typescript
const request: Partial<Request> = { headers: { email: "test@test.com" } };
await handler(request as Request, response as Response, next);
```

#### 3.7.5 `spy` vs `double`

`spy` (Ruby) / `jest.fn()` (TS): Use when you need to verify the object was called but don't care about configuring return values. Typical for loggers and message publishers.

```ruby
logger = spy
instance = described_class.new(batch, logger)
```

`double` (Ruby) / `jest.spyOn` (TS): Use when you need to control the return value of a specific method.

#### 3.7.6 Complex Stubs: The `.tap` Pattern (Ruby)

When a double needs both configured behavior and to be returned from another stub, build it with `.tap`:

```ruby
service = double.tap do |stub|
  allow(stub).to receive(:call)
end
allow(Admin::SendWelcomeEmail).to receive(:new).and_return(service)
```

This keeps the double and its stubbed behavior in a single expression, so the whole thing sits in the Arrange phase without spilling into extra setup lines or a helper method.

**TypeScript equivalent:** Use helper functions or inline chaining:

```typescript
const spy = jest.spyOn(global, "fetch");
mockRequests(spy, mockedRequests); // helper encapsulates complex mock setup
```

#### 3.7.7 Dependency Injection Over Patching

Doubles are passed as constructor arguments or function parameters. Never use `allow_any_instance_of` (Ruby) or patch instances after creation.

**Correct** - inject the double:

```ruby
runner = described_class.new(
  configuration:,
  logger:,
  message_publisher: publisher,  # injected double
  source:
)
```

**Correct** - stub the constructor to return a pre-configured double:

```ruby
allow(Admin::SendWelcomeEmail).to receive(:new).and_return(service)
```

**Prohibited:**

```ruby
allow_any_instance_of(SomeClass).to receive(:method)  # NEVER
```

`allow_any_instance_of` does not appear in any test file across all projects.

#### 3.7.8 Mock Restoration (TypeScript)

Every TypeScript test suite that uses `jest.spyOn` must restore mocks after each test to prevent state leakage:

```typescript
afterEach(() => {
  jest.restoreAllMocks();
});
```

This is one of the few acceptable uses of `afterEach` (see 3.3 Setup/Teardown Hooks Are Prohibited).

#### 3.7.9 HTTP Mocking

External HTTP calls are stubbed inline in the Arrange phase, never in shared setup.

**Ruby (WebMock):**

```ruby
stub_request(:get, "#{api_url}/v1/ap/checks_issued?#{filter_hash.to_query}")
  .with(headers:)
  .to_return(body: { data: [check_data] }.to_json, headers: response_headers)
```

**TypeScript (jest.spyOn on fetch):**

```typescript
const mockFetch = jest.spyOn(global, "fetch");
mockFetch.mockResolvedValueOnce({
  json: async () => ({ status: "SUCCESS" }),
} as any);
```

#### 3.7.10 Never Mock the Database

Tests use real database operations through factories and ORM calls, not database mocks. The database cleaning strategy (3.12) handles isolation.

**Correct:**

```ruby
organization = create(:organization, :with_tenant)
log = create(:import_log, import_data: data, status: :initialized)
```

```typescript
const org = await prisma.organizationConfiguration.create({ data: { ... } });
```

**Prohibited:** Mocking ActiveRecord/Prisma query methods, stubbing `.find`, `.where`, `.create`, etc.

### 3.8 Assert Behavior, Not Implementation

Tests verify observable outcomes — what the system does — not how it does it internally. A test should not break when you refactor internals without changing behavior.

**Assert these (observable):** return values, side effects (records created, emails sent), HTTP responses, rendered content, error messages, state changes visible to callers.

**Do not assert these (implementation):** which private methods were called, internal variable values, execution order of internal steps, specific SQL queries generated.

If a refactor that preserves all external behavior breaks a test, that test was asserting implementation.

### 3.9 Assertion Patterns

Use structured matchers for assertions, not manual field-by-field comparisons.

**Object inspection**: Assert on object shape/attributes, not equality of the entire object.
**Collection matching**: Assert on collection contents without depending on order.
**Partial matching**: Assert on a subset of keys/fields when you don't care about every field.
**Error testing**: Assert on both the error type and message.

**Ruby reference matchers:** `have_attributes`, `contain_exactly`, `include`, `be_empty`, `raise_error`, shoulda matchers (`validate_presence_of`, `belong_to`).

**TypeScript reference matchers:** `toEqual(expect.objectContaining(...))`, `toMatchObject`, `toHaveBeenCalledWith`, `rejects.toThrow`.

### 3.10 Integration/Feature Test Patterns

Rules:

* Use **page objects** (or equivalent abstraction) to encapsulate DOM traversal and UI interaction. Never scatter CSS selectors across test files.
* Use **value objects** for form-filling data in integration tests.
* Define a local translation helper to scope i18n lookups within a test file.
* Provide an authentication helper (`sign_in_as(user)`) that abstracts the auth mechanism.
* Stub external services using a fluent builder pattern.
* Assert UI content using localization keys, not hardcoded strings.
* Tag tests that require a browser/JS runtime so they can use the appropriate test driver.

### 3.11 Test Configuration Standards

Every project must configure:

* **Randomized test order** with a reproducible seed.
* **Verified/type-safe mocks** (partial double verification or typed mocks).
* **Automatic support file loading** from a shared support directory.
* **Database isolation**: transaction-based cleanup by default, truncation for integration tests that run app and test in separate threads.
* **Coverage reporting** enabled.

**Ruby reference (spec_helper.rb):**

```ruby
RSpec.configure do |config|
  config.disable_monkey_patching!
  config.order = :random
  Kernel.srand config.seed
  config.expect_with :rspec do |expectations|
    expectations.syntax = :expect
  end
  config.mock_with :rspec do |mocks|
    mocks.verify_partial_doubles = true
  end
end
```

**TypeScript reference (jest.config / vitest.config):**

```javascript
{
  roots: ["<rootDir>"],
  testMatch: ["**/?(*.)+(spec|test).+(ts|tsx|js|jsx)"],
  preset: "ts-jest",
  // or for Vitest: globals: true, environment: "jsdom"
}
```

### 3.12 Database Cleanup Strategy

Projects with a database must use a cleaning strategy that:

* **Default**: wraps each test in a transaction that rolls back (fast).
* **Integration/browser tests**: truncates tables (required when test and app run in separate threads or processes).
* **Suite start**: truncates once before all tests to start clean.

### 3.13 Linter Relaxations for Test Files

The following rules must be relaxed for test files:

* **Test length limits**: disabled. AAA tests with complex Arrange phases are naturally long.
* **Multiple assertions per test**: allowed. The Assert phase of an AAA test often checks multiple properties.
* **Block/function length**: excluded for test files.
* **Named subject requirements**: disabled. Not all tests benefit from named subjects.

### 3.14 No Request Specs (Rails)

Do not generate or write request specs (`spec/requests/`) in Rails projects for UI-driven features. Request specs duplicate coverage already provided by controller specs and system/feature specs, adding cognitive overhead for reviewers without catching additional bugs.

**Exception — API endpoints:** Request specs are the correct testing layer for API-only controllers (e.g., `Api::` namespaced controllers, JSON endpoints). Use request specs to verify status codes, response bodies, authentication, and content negotiation for APIs.

**Hard rule:** Every functionality should be tested exactly once at the appropriate layer. For UI features, request specs sit between controller specs and feature specs without adding unique value. For API endpoints, request specs _are_ the appropriate layer.

When generating Rails scaffolds or resources for UI features, always pass `--no-request-specs` or configure generators to skip them:

```ruby
# config/application.rb
config.generators do |g|
  g.request_specs false
end
```

If an existing project has request specs for UI features, do not add new ones. Migrate coverage to the appropriate layer (controller or system spec) when touching those files.

### 3.15 Mutating Methods Must Return Evaluable State

Mutating methods in our own code should return the mutated state so callers and tests can evaluate the result directly. Do not force tests to re-query or reload to verify the outcome — that's a sign the method's interface isn't testable.

Reserve re-querying for legacy code or vendor libraries where you don't control the return value.

### 3.16 Never Use `reload!` or `reload`

Never call `reload!` or `.reload` on ActiveRecord objects in tests. If a test needs the latest database state, query for the object fresh:

**Prohibited:**

```ruby
record.reload
record.reload!
```

**Required — query fresh:**

```ruby
result = MyModel.find(record.id)
expect(result.status).to eq('completed')
```

This makes the test's data flow explicit and avoids hidden state mutation.

### 3.17 Test File Organization

Test directory structure mirrors the source directory structure:

```
tests/                          # or spec/
├── factories/                  # Test data factories
├── features/ or integration/   # End-to-end / acceptance tests
├── models/                     # Domain model unit tests
├── services/                   # Service object unit tests
├── controllers/ or routes/     # Request handler tests
├── workers/ or jobs/           # Background job tests
├── form_objects/               # Input/form object tests
├── presenters/                 # Presenter tests
├── lib/                        # Library/utility tests
└── support/
    ├── database cleanup config
    ├── factory/fixture config
    ├── browser driver config
    ├── auth helper
    ├── http mock config
    ├── matchers/               # Custom assertion matchers
    ├── page_objects/           # Page objects for feature tests
    ├── value_objects/          # Value objects for test data
    └── helpers/                # Domain-specific test helpers
```
