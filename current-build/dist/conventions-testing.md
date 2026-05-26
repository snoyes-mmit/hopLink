# Testing Conventions

> **Location:** `js-saas-factory-knowledge/conventions/testing-conventions.md`
>
> **Purpose:** Rules for how tests are written, named, organized, and run. Applies to unit tests, integration tests, and end-to-end tests across backend and frontend.
>
> **Audience:** Researcher, Spec Writer, Backend Builder, Frontend Builder, Test, Validate.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

This file is the canonical reference for tests. Every Builder produces unit and component tests alongside its code; the Test Project produces acceptance tests against the user story. Both read this file.

The single highest-leverage section is **section 5 — test data builders**. Inline test setup is the most common cause of flaky, hard-to-read tests. The builder pattern fixes that.

---

## 1. Test runners and tooling

| Tool | Used for |
|---|---|
| **Vitest** | Unit tests, integration tests (both backend and frontend) |
| **@testing-library/react** | Component tests (Vitest + Testing Library) |
| **Playwright** | End-to-end browser tests |
| **`@axe-core/playwright`** | Accessibility checks in e2e tests |
| **`jest-axe` (via `vitest-axe`)** | Accessibility checks in component tests |
| **MSW (Mock Service Worker)** | Mocking HTTP requests at the network layer in component tests |
| **`@testing-library/user-event`** | Simulating realistic user interactions (preferred over `fireEvent`) |

Pick the right tool for the level of test you're writing — unit tests don't need Playwright, e2e tests don't need MSW.

---

## 2. Test file organization

### 2.1 Location

**Co-locate test files with the code they test.** A function in `services/reminders/send-overdue.ts` has its tests in `services/reminders/send-overdue.test.ts`.

Exceptions:

- **End-to-end tests** live in `e2e/` at the project root, organized by feature
- **Test infrastructure** (builders, fixtures, helpers) lives in `test/` at the project root
- **Integration tests that span multiple modules** can live in `tests/integration/` if co-location would be misleading

### 2.2 File naming

| File type | Pattern | Example |
|---|---|---|
| Unit / integration test | `<name>.test.ts` or `.tsx` | `send-overdue.test.ts` |
| End-to-end test | `<feature>.spec.ts` | `e2e/invoice-reminders.spec.ts` |
| Test data builder | `<name>.builder.ts` | `test/builders/invoice.builder.ts` |
| Test fixture | `<name>.fixture.ts` | `test/fixtures/sample-invoices.fixture.ts` |
| Test helper | `<name>.test-helpers.ts` | `test/test-helpers/database.test-helpers.ts` |

The `.spec.ts` suffix is reserved for Playwright e2e tests so the runners can distinguish them by glob.

---

## 3. Test naming

### 3.1 The rule

**Tests are named so a non-developer can understand what they verify.** Test names show up in CI logs, PR descriptions, and (in regulated-adjacent work) audit packs. Make them readable.

### 3.2 The shape

`describe` blocks describe the unit under test. `it` (or `test`) blocks describe the behavior:

```typescript
describe("triggerManualReminder", () => {
  it("sends a reminder when the invoice is overdue and admin and invoice share a tenant", async () => {
    // ...
  });

  it("rejects the request when admin and invoice belong to different tenants", async () => {
    // ...
  });

  it("returns the existing lastReminderSentAt when a reminder was sent in the last hour", async () => {
    // ...
  });
});
```

### 3.3 Good vs. bad names

| Bad | Good |
|---|---|
| `test_403` | `rejects the request when admin and invoice belong to different tenants` |
| `tenant test` | `enforces tenant boundary on the manual reminder endpoint` |
| `should work` | `sends a reminder when the invoice is over 7 days overdue` |
| `error case` | `returns 404 when the invoice does not exist` |

If you can read the test name aloud and have it sound like a sentence describing what the system does, the name is good.

---

## 4. Test structure (Arrange / Act / Assert)

Every test follows the same shape: set up state, perform the action, check the outcome.

```typescript
it("sends a reminder when the invoice is overdue and admin and invoice share a tenant", async () => {
  // Arrange
  const tenant = await buildTenant();
  const admin = await buildUser({ tenant, role: "admin" });
  const invoice = await buildInvoice({ tenant, daysOverdue: 10 });

  // Act
  const result = await triggerManualReminder({
    invoiceId: invoice.id,
    tenantId: admin.tenantId,
    actorId: admin.id,
  });

  // Assert
  expect(result.lastReminderSentAt).toBeInstanceOf(Date);
  expect(emailService.send).toHaveBeenCalledWith(
    expect.objectContaining({ to: invoice.customerEmail }),
  );
});
```

**Rules:**

- Blank lines between the three phases (the lint rule `padding-line-between-statements` can enforce this if needed)
- One logical assertion per test (multiple `expect` calls are fine if they verify one outcome)
- No conditional logic in tests (no `if` statements deciding which assertion to run)
- No loops that produce different test cases — use `it.each` if you need parameterized tests

---

## 5. Test data builders

### 5.1 The rule

**Never write inline setup objects in tests.** Use a builder.

```typescript
// Bad
const invoice = {
  id: "inv_1",
  tenantId: "tenant_1",
  customerId: "cust_1",
  amount: 10000,
  status: "pending",
  daysOverdue: 0,
  createdAt: new Date(),
  updatedAt: new Date(),
  // ... 12 more fields
};

// Good
const invoice = await buildInvoice({ daysOverdue: 10 });
```

Inline setup is fine for one test. By the third test, you're copy-pasting setup blocks. By the tenth, you can't tell which fields matter to which test. Builders fix this: each test specifies only the fields that matter, and the builder fills in sensible defaults for the rest.

### 5.2 Builder structure

A builder is a function that takes a partial input, applies defaults, and returns a real entity (creating it in the database if the test needs a persisted entity):

```typescript
// test/builders/invoice.builder.ts

import { prisma } from "@/lib/prisma";
import { buildTenant } from "./tenant.builder";

type BuildInvoiceInput = Partial<{
  tenantId: string;
  customerEmail: string;
  amount: number;
  status: "pending" | "paid" | "overdue";
  daysOverdue: number;
  lastReminderSentAt: Date | null;
}>;

export async function buildInvoice(input: BuildInvoiceInput = {}) {
  const tenantId = input.tenantId ?? (await buildTenant()).id;

  const daysOverdue = input.daysOverdue ?? 0;
  const createdAt = new Date(Date.now() - daysOverdue * 24 * 60 * 60 * 1000);

  return prisma.invoice.create({
    data: {
      tenantId,
      customerEmail: input.customerEmail ?? "test@example.com",
      amount: input.amount ?? 10000,
      status: input.status ?? (daysOverdue > 7 ? "overdue" : "pending"),
      lastReminderSentAt: input.lastReminderSentAt ?? null,
      createdAt,
    },
  });
}
```

**Notable rules:**

- The input is `Partial<...>` — every field is optional
- Defaults are realistic; they should produce a valid entity without any input
- The builder creates the entity in the database (use `.build` instead of `.create` if you want a plain object without persistence)
- Builders compose: `buildInvoice` calls `buildTenant` if no `tenantId` was provided

### 5.3 Where builders live

All builders live in `test/builders/`. Each entity gets one file. They're exported individually and from an index file for convenience:

```typescript
// test/builders/index.ts
export { buildTenant } from "./tenant.builder";
export { buildUser } from "./user.builder";
export { buildInvoice } from "./invoice.builder";
export { buildPayment } from "./payment.builder";
```

### 5.4 What to put in a builder vs. inline

Use a builder when:

- The entity has more than three or four fields
- The entity is created in more than one test
- The entity has required fields that don't matter to the test logic

Inline values are fine when:

- The value is the subject of the test (the specific string you're parsing)
- The value is a primitive with no defaults to worry about

---

## 6. Mocking policy

### 6.1 What to mock

| Mock | When | How |
|---|---|---|
| External HTTP services | Always in unit/integration tests | MSW for frontend; mock the client module for backend |
| Email sending | Always in unit/integration tests | Vi-mock the `sendEmail` module |
| Time (`Date.now()`, `new Date()`) | When the test depends on a specific time | `vi.useFakeTimers()` + `vi.setSystemTime()` |
| Random values (`crypto.randomUUID()`, `Math.random()`) | When deterministic output is needed | Mock the source |
| File system | Almost never; use a temp directory instead | If you must, mock the specific functions |

### 6.2 What NOT to mock

| Do not mock | Why |
|---|---|
| The database | Use a real test database; mocked databases miss query bugs |
| The framework (Next.js, React, Fastify) | You're testing your code, not theirs |
| The code under test | If you find yourself mocking the thing you're testing, you're testing the mock |
| Zod schemas | Use real schemas with real data |

### 6.3 The "mock the boundary, not the internals" rule

When you mock, mock at the boundary between your code and the external world (HTTP, email, time, file system). Don't mock internal modules; if your code depends on too many internal modules to test, the design is the problem.

---

## 7. Test independence

### 7.1 The rule

Every test sets up its own state and cleans up after itself. Tests must pass when run in any order. They must pass when run alone.

```typescript
// Good
beforeEach(async () => {
  await cleanDatabase(); // truncate all tables
});

it("creates an invoice", async () => {
  const invoice = await buildInvoice();
  // ...
});

it("rejects a duplicate invoice", async () => {
  const existing = await buildInvoice({ id: "inv_dup" });
  await expect(buildInvoice({ id: "inv_dup" })).rejects.toThrow();
});
```

### 7.2 What kills independence

- Shared state between tests (a variable defined outside `it` that one test mutates)
- Tests that rely on the database being in a specific state from a previous test
- `beforeAll` that creates state subsequent tests modify (use `beforeEach` instead, unless the state is truly read-only)
- Tests that depend on execution order (`it.only` left in committed code; tests numbered to enforce order)

### 7.3 The fastest test for independence

Run the file multiple times in random order. If results differ, independence is broken. Vitest can do this with `--sequence.shuffle`.

---

## 8. What to test

### 8.1 Per-feature test coverage expectations

The Test Project produces acceptance tests against the user story. The Builders produce unit tests against their own code. Between them, every feature should have:

- **One test per acceptance criterion** — covers the happy path and the criterion-specific failures
- **One test per failure path called out in the brief** — validation, auth, tenant boundary, not found, conflict
- **One test per edge case listed in the story** — boundary conditions, retries, race conditions

If an acceptance criterion is genuinely untestable (visual consistency, usability), the Test Project's coverage report says so explicitly under "ACCEPTANCE CRITERIA NOT COVERED."

### 8.2 What every backend feature tests

- Success case (the action does what the story says)
- Validation failure (invalid input → 400)
- Auth failure (unauthenticated → 401)
- Authorization failure (wrong role → 403)
- Tenant boundary (different tenant → 403, with the right log entry)
- Not found (missing resource → 404)
- Conflict / idempotency (where applicable → 409)

### 8.3 What every frontend feature tests

- Renders the success state with valid data
- Renders the loading state during async work
- Renders the error state when the API returns an error
- Renders the empty state when there's no data
- Interactive elements are reachable via `getByRole` (accessibility)
- Form submission triggers the expected callback
- Validation errors are displayed and associated with the right input
- Keyboard navigation works (Tab order, Enter to submit, Escape to close)

### 8.4 What NOT to test

- Implementation details (the names of internal state variables, the specific structure of JSX)
- Framework code (you're not testing Next.js's routing)
- Third-party libraries (you're not testing React Query's caching)
- Generated code (Prisma client, generated types)
- Trivial pass-through code (a function that just calls another function)

---

## 9. Acceptance tests vs. unit tests vs. e2e

| Layer | What it tests | Tool | Where it lives |
|---|---|---|---|
| Unit | One function, one module | Vitest | Co-located with code |
| Integration | Multiple modules working together | Vitest | Co-located with code or `tests/integration/` |
| Component | One React component | Vitest + Testing Library | Co-located with component |
| Acceptance | One user story end-to-end at the API level | Vitest | Co-located with feature or `tests/acceptance/` |
| End-to-end (e2e) | One user flow in a real browser | Playwright | `e2e/` at project root |

The Test Project usually writes **acceptance tests at the API level** (faster, more stable) plus a few **e2e tests** for the most critical user flows (slower, more realistic).

---

## 10. Test commands

Every project supports these commands in `package.json`:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

- `pnpm test` — runs all unit, integration, component, and acceptance tests once. This is what CI runs and what the build script runs.
- `pnpm test:watch` — runs in watch mode for development.
- `pnpm test:coverage` — produces a coverage report.
- `pnpm test:e2e` — runs Playwright tests in headless mode.
- `pnpm test:e2e:ui` — opens Playwright's UI for debugging.

---

## 11. CI expectations

The CI pipeline runs in this order, failing fast:

1. `pnpm typecheck` — must pass
2. `pnpm lint` — must pass
3. `pnpm test` — all unit, integration, component, and acceptance tests must pass
4. `pnpm test:e2e` — all e2e tests must pass
5. `pnpm build` — production build must succeed

A failure at any step blocks the PR from merging. There is no "skip CI" option for the test steps.

---

## 12. Common test pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Flaky tests | Sometimes passes, sometimes fails | Look for time-dependent code, network calls, race conditions; use fake timers or proper mocking |
| Tests that pass alone but fail in the suite | Order-dependent state | Clean state in `beforeEach`, not `beforeAll` |
| Tests that pass with `.only` but fail without | Same as above | Same fix |
| Shallow tests (only the happy path) | Bug shipped despite passing tests | Add explicit failure-case tests |
| Tests that test the mock | Refactoring breaks tests even though behavior is identical | Mock at the boundary, not the internals |
| Tests with conditional assertions | `if (x) expect(...)` | Split into separate tests for each case |
| Tests that retry on failure | `retry: 3` in test config | Fix the flakiness instead |
| Tests with `setTimeout` to "wait for things" | Race conditions | Use `await` on the actual promise or use Testing Library's `waitFor` |

---

## 13. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

- If tests come out shallow (happy path only), the example test suite file is the primary lever — but section 8.2 / 8.3 here can also be sharpened with specific examples.
- If tests come out flaky, look for inline setup and time-dependent code. Reinforce sections 5 and 7.
- If the Test Project keeps producing tests without descriptive names, section 3 needs more strong-vs-weak examples.
- This file should stay under three pages of dense content. Detail beyond that belongs in the example test suite file.