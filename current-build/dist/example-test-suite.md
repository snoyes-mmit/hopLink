# Example: Test Suite — Invoice Reminders

> **Location:** `js-saas-factory-knowledge/examples/example-test-suite.md`
>
> **Purpose:** One complete, realistic test file shown end to end, demonstrating the team's test patterns against the feature from `example-backend-feature.md`. **This is the highest-leverage file in the knowledge base for test code.**
>
> **Audience:** Backend Builder, Frontend Builder, Test.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

The Backend Builder, Frontend Builder, and Test Project all read this file. The Builders mirror the unit-test patterns shown here when writing tests alongside their code; the Test Project mirrors the acceptance-test patterns when writing acceptance tests against the story.

**The most important property of this file is that the depth of testing shown here is what the chain will mirror.** If this file shows only happy-path tests, the chain produces happy-path tests. If this file shows success + validation + auth + tenant + idempotency + edge cases, the chain produces that depth. The example sets the bar.

This file pairs with:

- `examples/example-backend-feature.md` (the feature being tested)
- `examples/example-frontend-feature.md` (the UI being tested at the component level)
- `conventions/testing-conventions.md` (the rules)

---

## 1. Feature being tested

The feature is the **invoice reminders** feature from `example-backend-feature.md`. The tests cover:

- **Service-level unit/integration tests** for `triggerManualReminder` (the manual-trigger service)
- **API-level acceptance tests** for `POST /api/admin/invoices/:id/remind` (the route handler)
- **Component-level tests** for `SendReminderButton` (the UI action)
- **A coverage report** in the format the Test Project produces

The tests verify every acceptance criterion in the user story plus the edge cases the story lists, plus the standard failure-path coverage (auth, tenant boundary, validation, not found, conflict) that every backend feature gets.

---

## 2. File layout

```
src/
├── services/reminders/
│   ├── trigger-manual-reminder.ts                    (the service under test)
│   ├── trigger-manual-reminder.test.ts               (unit/integration test — section 3)
│   ├── helpers.ts
│   └── helpers.test.ts                               (pure helper test — section 4)
├── app/api/admin/invoices/[id]/remind/
│   ├── route.ts                                      (the route under test)
│   └── route.test.ts                                 (acceptance test at API level — section 5)
└── app/(admin)/invoices/_components/
    ├── SendReminderButton.tsx                        (the component under test)
    └── SendReminderButton.test.tsx                   (component test — section 6)

test/
├── builders/
│   ├── tenant.builder.ts                             (test data builder)
│   ├── user.builder.ts                               (test data builder)
│   ├── customer.builder.ts                           (test data builder)
│   └── invoice.builder.ts                            (test data builder — section 7)
└── test-helpers/
    └── database.test-helpers.ts                      (clean state between tests)
```

---

## 3. Service-level unit/integration test

This is the test file the Backend Builder produces alongside `trigger-manual-reminder.ts`. It exercises the service against a real test database, mocking only the external email service (Resend).

### 3.1 `src/services/reminders/trigger-manual-reminder.test.ts`

```typescript
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { sendReminderEmail } from "@/services/email/send-reminder-email";
import { triggerManualReminder } from "@/services/reminders";
import {
  TenantMismatchError,
  InvoiceNotFoundError,
  ReminderAlreadySentError,
  InvoiceNotEligibleForReminderError,
} from "@/lib/errors";

import { buildCustomer } from "@test/builders/customer.builder";
import { buildInvoice } from "@test/builders/invoice.builder";
import { buildTenant } from "@test/builders/tenant.builder";
import { buildUser } from "@test/builders/user.builder";
import { cleanDatabase } from "@test/test-helpers/database.test-helpers";

// Mock the external email service at the module boundary.
// We do NOT mock the database (see testing-conventions.md section 6.2).
vi.mock("@/services/email/send-reminder-email", () => ({
  sendReminderEmail: vi.fn().mockResolvedValue({ messageId: "msg_test_123" }),
}));

const sendReminderEmailMock = vi.mocked(sendReminderEmail);

describe("triggerManualReminder", () => {
  beforeEach(async () => {
    await cleanDatabase();
    sendReminderEmailMock.mockClear();
  });

  describe("success cases", () => {
    it("sends a reminder when the admin and invoice share a tenant and the invoice is overdue", async () => {
      // Arrange
      const tenant = await buildTenant();
      const admin = await buildUser({ tenant, role: "admin" });
      const customer = await buildCustomer({ tenant });
      const invoice = await buildInvoice({
        tenant,
        customer,
        status: "overdue",
        daysOverdue: 10,
      });

      // Act
      const result = await triggerManualReminder({
        invoiceId: invoice.id,
        tenantId: admin.tenantId,
        actorId: admin.id,
      });

      // Assert
      expect(result.lastReminderSentAt).toBeInstanceOf(Date);
      expect(sendReminderEmailMock).toHaveBeenCalledOnce();
      expect(sendReminderEmailMock).toHaveBeenCalledWith({
        invoice: expect.objectContaining({ id: invoice.id }),
        customerName: customer.displayName,
      });
    });

    it("updates the invoice's lastReminderSentAt to a fresh timestamp", async () => {
      const tenant = await buildTenant();
      const admin = await buildUser({ tenant, role: "admin" });
      const invoice = await buildInvoice({
        tenant,
        status: "overdue",
        daysOverdue: 10,
        lastReminderSentAt: null,
      });

      const before = new Date();
      const result = await triggerManualReminder({
        invoiceId: invoice.id,
        tenantId: admin.tenantId,
        actorId: admin.id,
      });
      const after = new Date();

      expect(result.lastReminderSentAt.getTime()).toBeGreaterThanOrEqual(before.getTime());
      expect(result.lastReminderSentAt.getTime()).toBeLessThanOrEqual(after.getTime());
    });
  });

  describe("tenant isolation", () => {
    it("rejects the request with TenantMismatchError when the admin's tenant differs from the invoice's tenant", async () => {
      const tenantA = await buildTenant();
      const tenantB = await buildTenant();
      const adminInA = await buildUser({ tenant: tenantA, role: "admin" });
      const invoiceInB = await buildInvoice({ tenant: tenantB, status: "overdue", daysOverdue: 10 });

      await expect(
        triggerManualReminder({
          invoiceId: invoiceInB.id,
          tenantId: adminInA.tenantId,
          actorId: adminInA.id,
        }),
      ).rejects.toThrow(TenantMismatchError);

      expect(sendReminderEmailMock).not.toHaveBeenCalled();
    });

    it("does not send an email when tenant isolation rejects the request", async () => {
      // Covered above; this test reinforces that the email service is never called
      // on a tenant mismatch. The Validator will check that the side-effect is
      // verified, not just the thrown error.
      const tenantA = await buildTenant();
      const tenantB = await buildTenant();
      const adminInA = await buildUser({ tenant: tenantA, role: "admin" });
      const invoiceInB = await buildInvoice({ tenant: tenantB, status: "overdue", daysOverdue: 10 });

      await expect(
        triggerManualReminder({
          invoiceId: invoiceInB.id,
          tenantId: adminInA.tenantId,
          actorId: adminInA.id,
        }),
      ).rejects.toThrow();

      expect(sendReminderEmailMock).not.toHaveBeenCalled();
    });
  });

  describe("not found", () => {
    it("throws InvoiceNotFoundError when the invoice does not exist", async () => {
      const tenant = await buildTenant();
      const admin = await buildUser({ tenant, role: "admin" });

      await expect(
        triggerManualReminder({
          invoiceId: "00000000-0000-0000-0000-000000000000",
          tenantId: admin.tenantId,
          actorId: admin.id,
        }),
      ).rejects.toThrow(InvoiceNotFoundError);

      expect(sendReminderEmailMock).not.toHaveBeenCalled();
    });
  });

  describe("eligibility", () => {
    it("throws InvoiceNotEligibleForReminderError when the invoice is paid", async () => {
      const tenant = await buildTenant();
      const admin = await buildUser({ tenant, role: "admin" });
      const invoice = await buildInvoice({ tenant, status: "paid", daysOverdue: 10 });

      await expect(
        triggerManualReminder({
          invoiceId: invoice.id,
          tenantId: admin.tenantId,
          actorId: admin.id,
        }),
      ).rejects.toThrow(InvoiceNotEligibleForReminderError);

      expect(sendReminderEmailMock).not.toHaveBeenCalled();
    });

    it("throws InvoiceNotEligibleForReminderError when the invoice is cancelled", async () => {
      const tenant = await buildTenant();
      const admin = await buildUser({ tenant, role: "admin" });
      const invoice = await buildInvoice({ tenant, status: "cancelled", daysOverdue: 10 });

      await expect(
        triggerManualReminder({
          invoiceId: invoice.id,
          tenantId: admin.tenantId,
          actorId: admin.id,
        }),
      ).rejects.toThrow(InvoiceNotEligibleForReminderError);

      expect(sendReminderEmailMock).not.toHaveBeenCalled();
    });
  });

  describe("idempotency", () => {
    it("throws ReminderAlreadySentError when a reminder was sent within the last 24 hours", async () => {
      const tenant = await buildTenant();
      const admin = await buildUser({ tenant, role: "admin" });
      const invoice = await buildInvoice({
        tenant,
        status: "overdue",
        daysOverdue: 10,
        lastReminderSentAt: new Date(Date.now() - 60 * 60 * 1000), // 1 hour ago
      });

      await expect(
        triggerManualReminder({
          invoiceId: invoice.id,
          tenantId: admin.tenantId,
          actorId: admin.id,
        }),
      ).rejects.toThrow(ReminderAlreadySentError);

      expect(sendReminderEmailMock).not.toHaveBeenCalled();
    });

    it("allows a reminder when the previous reminder was sent more than 24 hours ago", async () => {
      const tenant = await buildTenant();
      const admin = await buildUser({ tenant, role: "admin" });
      const invoice = await buildInvoice({
        tenant,
        status: "overdue",
        daysOverdue: 10,
        lastReminderSentAt: new Date(Date.now() - 25 * 60 * 60 * 1000), // 25 hours ago
      });

      const result = await triggerManualReminder({
        invoiceId: invoice.id,
        tenantId: admin.tenantId,
        actorId: admin.id,
      });

      expect(result.lastReminderSentAt).toBeInstanceOf(Date);
      expect(sendReminderEmailMock).toHaveBeenCalledOnce();
    });
  });

  describe("edge cases", () => {
    it("treats an invoice exactly 24 hours after its last reminder as in-window (does not send)", async () => {
      const tenant = await buildTenant();
      const admin = await buildUser({ tenant, role: "admin" });
      const exactlyOneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000 + 100); // a touch under 24h
      const invoice = await buildInvoice({
        tenant,
        status: "overdue",
        daysOverdue: 10,
        lastReminderSentAt: exactlyOneDayAgo,
      });

      await expect(
        triggerManualReminder({
          invoiceId: invoice.id,
          tenantId: admin.tenantId,
          actorId: admin.id,
        }),
      ).rejects.toThrow(ReminderAlreadySentError);
    });

    it("does not modify the invoice when the email service fails", async () => {
      const tenant = await buildTenant();
      const admin = await buildUser({ tenant, role: "admin" });
      const invoice = await buildInvoice({
        tenant,
        status: "overdue",
        daysOverdue: 10,
        lastReminderSentAt: null,
      });

      sendReminderEmailMock.mockRejectedValueOnce(new Error("Resend timeout"));

      await expect(
        triggerManualReminder({
          invoiceId: invoice.id,
          tenantId: admin.tenantId,
          actorId: admin.id,
        }),
      ).rejects.toThrow("Resend timeout");

      // Verify the invoice's lastReminderSentAt was NOT updated despite the attempt.
      const refetched = await import("@/repositories/invoice.repository").then((m) =>
        m.invoiceRepository.findById(invoice.id),
      );
      expect(refetched?.lastReminderSentAt).toBeNull();
    });
  });
});
```

### 3.2 Annotations on the service test

| Pattern | Where |
|---|---|
| `describe` blocks group tests by the category of behavior | "success cases," "tenant isolation," "not found," "eligibility," "idempotency," "edge cases" |
| `it` blocks read as sentences | `it("sends a reminder when the admin and invoice share a tenant and the invoice is overdue")` |
| Arrange / Act / Assert with blank lines separating phases | Every test |
| Test data builders, never inline setup | `buildTenant()`, `buildUser()`, `buildInvoice()`, `buildCustomer()` |
| State is cleaned in `beforeEach`, never `beforeAll`, so order does not matter | Top of the suite |
| Only external boundaries are mocked (email); the database is real | `vi.mock("@/services/email/send-reminder-email")` |
| Side-effect verification on negative paths (`expect(sendReminderEmailMock).not.toHaveBeenCalled()`) | Tenant mismatch, not found, eligibility, idempotency tests |
| Edge cases get their own `describe` block, not lumped into other categories | "edge cases" section |
| Time-sensitive tests use explicit timestamps relative to `Date.now()`, not magic dates | Idempotency and edge case tests |
| A test that verifies "no side effect on failure" reads back the state to confirm | Last test in "edge cases" |

---

## 4. Pure helper test

Pure functions test cleanly with no setup. This is what `helpers.test.ts` looks like.

### 4.1 `src/services/reminders/helpers.test.ts`

```typescript
import { describe, expect, it } from "vitest";

import { isOverdueForReminder, wasRecentlySent } from "./helpers";

describe("wasRecentlySent", () => {
  it("returns false when there is no previous reminder", () => {
    expect(wasRecentlySent(null)).toBe(false);
  });

  it("returns true when the previous reminder was 1 hour ago", () => {
    const now = new Date("2026-05-26T12:00:00Z");
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
    expect(wasRecentlySent(oneHourAgo, now)).toBe(true);
  });

  it("returns false when the previous reminder was 25 hours ago", () => {
    const now = new Date("2026-05-26T12:00:00Z");
    const twentyFiveHoursAgo = new Date(now.getTime() - 25 * 60 * 60 * 1000);
    expect(wasRecentlySent(twentyFiveHoursAgo, now)).toBe(false);
  });

  it("returns true at exactly 23 hours 59 minutes 59 seconds (boundary, inside the window)", () => {
    const now = new Date("2026-05-26T12:00:00Z");
    const justUnder = new Date(now.getTime() - (24 * 60 * 60 * 1000 - 1000));
    expect(wasRecentlySent(justUnder, now)).toBe(true);
  });

  it("returns false at exactly 24 hours (boundary, outside the window)", () => {
    const now = new Date("2026-05-26T12:00:00Z");
    const exactly24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    expect(wasRecentlySent(exactly24h, now)).toBe(false);
  });
});

describe("isOverdueForReminder", () => {
  it("returns false when the invoice is 6 days past due", () => {
    const now = new Date("2026-05-26T12:00:00Z");
    const sixDaysAgo = new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000);
    expect(isOverdueForReminder(sixDaysAgo, now)).toBe(false);
  });

  it("returns true when the invoice is 8 days past due", () => {
    const now = new Date("2026-05-26T12:00:00Z");
    const eightDaysAgo = new Date(now.getTime() - 8 * 24 * 60 * 60 * 1000);
    expect(isOverdueForReminder(eightDaysAgo, now)).toBe(true);
  });

  it("returns false at exactly 7 days (boundary, not yet overdue enough)", () => {
    const now = new Date("2026-05-26T12:00:00Z");
    const exactly7Days = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    expect(isOverdueForReminder(exactly7Days, now)).toBe(false);
  });

  it("returns false for an invoice with a future due date", () => {
    const now = new Date("2026-05-26T12:00:00Z");
    const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);
    expect(isOverdueForReminder(tomorrow, now)).toBe(false);
  });
});
```

### 4.2 Annotations on the helper test

| Pattern | Where |
|---|---|
| Pure functions test without any setup, builders, or database | All tests in this file |
| Time-dependent functions take an injectable `now`; tests pass an explicit value | Every test |
| Boundary conditions are tested explicitly (just-inside, just-outside) | "boundary" tests in both groups |
| The constant `24 * 60 * 60 * 1000` appears inline rather than imported, because it makes the test self-explanatory at a glance | Throughout |
| Test names read as statements of fact | "returns false when the invoice is 6 days past due" |

---

## 5. API-level acceptance test

This is the test file the Test Project produces against the user story. It exercises the route end-to-end with a real database, real auth, and the email service mocked.

### 5.1 `src/app/api/admin/invoices/[id]/remind/route.test.ts`

```typescript
import { describe, expect, it, vi, beforeEach } from "vitest";

import { sendReminderEmail } from "@/services/email/send-reminder-email";

import { buildCustomer } from "@test/builders/customer.builder";
import { buildInvoice } from "@test/builders/invoice.builder";
import { buildTenant } from "@test/builders/tenant.builder";
import { buildUser } from "@test/builders/user.builder";
import {
  cleanDatabase,
  signInAs,
  testFetch,
} from "@test/test-helpers/database.test-helpers";

vi.mock("@/services/email/send-reminder-email", () => ({
  sendReminderEmail: vi.fn().mockResolvedValue({ messageId: "msg_test_123" }),
}));

describe("POST /api/admin/invoices/:id/remind (acceptance)", () => {
  beforeEach(async () => {
    await cleanDatabase();
    vi.mocked(sendReminderEmail).mockClear();
  });

  // Maps directly to acceptance criterion #1 in the user story.
  it("returns 200 with the updated timestamp when an admin triggers a reminder on a valid overdue invoice", async () => {
    const tenant = await buildTenant();
    const admin = await buildUser({ tenant, role: "admin" });
    const invoice = await buildInvoice({ tenant, status: "overdue", daysOverdue: 10 });

    const response = await testFetch(`/api/admin/invoices/${invoice.id}/remind`, {
      method: "POST",
      session: await signInAs(admin),
    });

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body).toMatchObject({
      success: true,
      lastReminderSentAt: expect.any(String),
    });
    expect(new Date(body.lastReminderSentAt).getTime()).toBeGreaterThan(Date.now() - 5000);
  });

  // Maps to acceptance criterion #2: only admins can trigger.
  it("returns 401 when called without a session", async () => {
    const tenant = await buildTenant();
    const invoice = await buildInvoice({ tenant, status: "overdue", daysOverdue: 10 });

    const response = await testFetch(`/api/admin/invoices/${invoice.id}/remind`, {
      method: "POST",
    });

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ error: "unauthenticated" });
  });

  it("returns 401 when called by a non-admin user", async () => {
    const tenant = await buildTenant();
    const nonAdmin = await buildUser({ tenant, role: "viewer" });
    const invoice = await buildInvoice({ tenant, status: "overdue", daysOverdue: 10 });

    const response = await testFetch(`/api/admin/invoices/${invoice.id}/remind`, {
      method: "POST",
      session: await signInAs(nonAdmin),
    });

    // The auth helper returns 401 for any session that fails the admin check.
    expect(response.status).toBe(401);
  });

  // Maps to acceptance criterion #3: tenant boundary enforced.
  it("returns 404 when the admin and invoice belong to different tenants", async () => {
    const tenantA = await buildTenant();
    const tenantB = await buildTenant();
    const adminInA = await buildUser({ tenant: tenantA, role: "admin" });
    const invoiceInB = await buildInvoice({ tenant: tenantB, status: "overdue", daysOverdue: 10 });

    const response = await testFetch(`/api/admin/invoices/${invoiceInB.id}/remind`, {
      method: "POST",
      session: await signInAs(adminInA),
    });

    // 404, not 403, to avoid revealing that the invoice exists in another tenant.
    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ error: "invoice_not_found" });
    expect(vi.mocked(sendReminderEmail)).not.toHaveBeenCalled();
  });

  // Maps to acceptance criterion #4: invalid invoice ID handled.
  it("returns 404 when the invoice id is not a valid UUID", async () => {
    const tenant = await buildTenant();
    const admin = await buildUser({ tenant, role: "admin" });

    const response = await testFetch(`/api/admin/invoices/not-a-uuid/remind`, {
      method: "POST",
      session: await signInAs(admin),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ error: "invoice_not_found" });
  });

  it("returns 404 when the invoice does not exist", async () => {
    const tenant = await buildTenant();
    const admin = await buildUser({ tenant, role: "admin" });

    const response = await testFetch(
      `/api/admin/invoices/00000000-0000-0000-0000-000000000000/remind`,
      {
        method: "POST",
        session: await signInAs(admin),
      },
    );

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ error: "invoice_not_found" });
  });

  // Maps to acceptance criterion #5: idempotency.
  it("returns 409 when a reminder was sent within the last 24 hours", async () => {
    const tenant = await buildTenant();
    const admin = await buildUser({ tenant, role: "admin" });
    const invoice = await buildInvoice({
      tenant,
      status: "overdue",
      daysOverdue: 10,
      lastReminderSentAt: new Date(Date.now() - 60 * 60 * 1000),
    });

    const response = await testFetch(`/api/admin/invoices/${invoice.id}/remind`, {
      method: "POST",
      session: await signInAs(admin),
    });

    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({ error: "reminder_already_sent_in_window" });
    expect(vi.mocked(sendReminderEmail)).not.toHaveBeenCalled();
  });

  // Maps to acceptance criterion #6: paid invoices are not eligible.
  it("returns 409 with invoice_not_eligible when the invoice is paid", async () => {
    const tenant = await buildTenant();
    const admin = await buildUser({ tenant, role: "admin" });
    const invoice = await buildInvoice({ tenant, status: "paid", daysOverdue: 10 });

    const response = await testFetch(`/api/admin/invoices/${invoice.id}/remind`, {
      method: "POST",
      session: await signInAs(admin),
    });

    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({ error: "invoice_not_eligible" });
    expect(vi.mocked(sendReminderEmail)).not.toHaveBeenCalled();
  });

  // Maps to edge case from the story: email service failure.
  it("returns 500 and does not mark the invoice as reminded when the email service fails", async () => {
    const tenant = await buildTenant();
    const admin = await buildUser({ tenant, role: "admin" });
    const invoice = await buildInvoice({
      tenant,
      status: "overdue",
      daysOverdue: 10,
      lastReminderSentAt: null,
    });

    vi.mocked(sendReminderEmail).mockRejectedValueOnce(new Error("Resend timeout"));

    const response = await testFetch(`/api/admin/invoices/${invoice.id}/remind`, {
      method: "POST",
      session: await signInAs(admin),
    });

    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({ error: "internal_error" });

    // The invoice's lastReminderSentAt was not updated.
    const refetched = await import("@/repositories/invoice.repository").then((m) =>
      m.invoiceRepository.findById(invoice.id),
    );
    expect(refetched?.lastReminderSentAt).toBeNull();
  });
});
```

### 5.2 Annotations on the acceptance test

| Pattern | Where |
|---|---|
| Each test is annotated with the acceptance criterion or edge case it covers | Comments above each `it` block |
| `testFetch` is a helper that creates an authenticated request against the route | All HTTP-level tests |
| `signInAs(user)` returns a session that the helper attaches to the request | All authenticated tests |
| The response body shape is verified against the schema's enum identifiers | `expect(...).toEqual({ error: "..." })` |
| Tenant isolation test verifies BOTH the status code AND the absence of the side effect | "404 when the admin and invoice belong to different tenants" |
| Idempotency, not-found, validation, paid-invoice, and email failure cases all verify the email service was NOT called | Throughout |
| One test per acceptance criterion, plus tests for edge cases | The whole suite |
| The 404-not-403 design decision is called out in a comment | Tenant mismatch test |

---

## 6. Component test

This is the test file the Frontend Builder produces alongside `SendReminderButton.tsx`. It exercises the component in isolation with the API call mocked.

### 6.1 `src/app/(admin)/invoices/_components/SendReminderButton.test.tsx`

```typescript
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { triggerManualReminder } from "@/lib/api/reminders";
import { ApiError } from "@/lib/error-messages";

import { SendReminderButton } from "./SendReminderButton";

vi.mock("@/lib/api/reminders", () => ({
  triggerManualReminder: vi.fn(),
}));

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const triggerManualReminderMock = vi.mocked(triggerManualReminder);

describe("SendReminderButton", () => {
  beforeEach(() => {
    triggerManualReminderMock.mockClear();
  });

  it("renders an accessible button labeled with the invoice id", () => {
    render(<SendReminderButton invoiceId="abc12345-0000-0000-0000-000000000000" onSent={vi.fn()} />);

    const button = screen.getByRole("button", { name: /send reminder for invoice abc12345/i });
    expect(button).toBeEnabled();
  });

  it("calls the API with the invoice id when clicked", async () => {
    triggerManualReminderMock.mockResolvedValueOnce({
      success: true,
      lastReminderSentAt: new Date().toISOString(),
    });

    const user = userEvent.setup();
    render(<SendReminderButton invoiceId="abc12345-0000-0000-0000-000000000000" onSent={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /send reminder/i }));

    expect(triggerManualReminderMock).toHaveBeenCalledWith(
      "abc12345-0000-0000-0000-000000000000",
    );
  });

  it("calls onSent with the new timestamp when the API succeeds", async () => {
    const expectedTimestamp = new Date().toISOString();
    triggerManualReminderMock.mockResolvedValueOnce({
      success: true,
      lastReminderSentAt: expectedTimestamp,
    });

    const onSent = vi.fn();
    const user = userEvent.setup();
    render(<SendReminderButton invoiceId="abc" onSent={onSent} />);

    await user.click(screen.getByRole("button", { name: /send reminder/i }));

    await waitFor(() => {
      expect(onSent).toHaveBeenCalledWith(expectedTimestamp);
    });
  });

  it("disables the button while the request is in flight", async () => {
    let resolveRequest: (value: { success: true; lastReminderSentAt: string }) => void = () => {};
    triggerManualReminderMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );

    const user = userEvent.setup();
    render(<SendReminderButton invoiceId="abc" onSent={vi.fn()} />);

    const button = screen.getByRole("button", { name: /send reminder/i });
    await user.click(button);

    // Mid-flight: button is disabled and shows the loading label.
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("button")).toHaveTextContent(/sending/i);

    // Resolve the request and confirm the button re-enables.
    resolveRequest({ success: true, lastReminderSentAt: new Date().toISOString() });

    await waitFor(() => {
      expect(button).toBeEnabled();
      expect(button).not.toHaveAttribute("aria-busy", "true");
    });
  });

  it("does not call onSent when the API throws", async () => {
    triggerManualReminderMock.mockRejectedValueOnce(
      new ApiError("reminder_already_sent_in_window", 409),
    );

    const onSent = vi.fn();
    const user = userEvent.setup();
    render(<SendReminderButton invoiceId="abc" onSent={onSent} />);

    await user.click(screen.getByRole("button", { name: /send reminder/i }));

    await waitFor(() => {
      expect(triggerManualReminderMock).toHaveBeenCalled();
    });
    expect(onSent).not.toHaveBeenCalled();
  });

  it("re-enables the button after an error so the user can retry", async () => {
    triggerManualReminderMock.mockRejectedValueOnce(new ApiError("internal_error", 500));

    const user = userEvent.setup();
    render(<SendReminderButton invoiceId="abc" onSent={vi.fn()} />);

    const button = screen.getByRole("button", { name: /send reminder/i });
    await user.click(button);

    await waitFor(() => {
      expect(button).toBeEnabled();
    });
  });

  it("is reachable via keyboard (Tab focuses, Enter activates)", async () => {
    triggerManualReminderMock.mockResolvedValueOnce({
      success: true,
      lastReminderSentAt: new Date().toISOString(),
    });

    const user = userEvent.setup();
    render(<SendReminderButton invoiceId="abc" onSent={vi.fn()} />);

    await user.tab();
    expect(screen.getByRole("button", { name: /send reminder/i })).toHaveFocus();

    await user.keyboard("{Enter}");
    expect(triggerManualReminderMock).toHaveBeenCalled();
  });
});
```

### 6.2 Annotations on the component test

| Pattern | Where |
|---|---|
| `getByRole` and `name` queries that mirror assistive technology, not implementation details | Every test |
| `userEvent.setup()` for realistic user interactions (preferred over `fireEvent`) | Every interaction test |
| The component's external dependencies (API client, toast) are mocked at the module boundary | Top of file |
| `aria-busy` and `disabled` are both verified during in-flight state | "disables the button while the request is in flight" |
| The keyboard accessibility test exercises `Tab` and `Enter` | "is reachable via keyboard" |
| Loading state is tested by holding the promise open until `resolveRequest` is called | "disables the button while the request is in flight" |
| Error paths verify the callback was NOT called, plus the UI recovers (button re-enables) | "does not call onSent when the API throws" and "re-enables the button after an error" |

---

## 7. Test data builders

This is what `test/builders/invoice.builder.ts` looks like. Other builders follow the same shape.

### 7.1 `test/builders/invoice.builder.ts`

```typescript
import { prisma } from "@/lib/prisma";

import { buildCustomer } from "./customer.builder";
import { buildTenant } from "./tenant.builder";

import type { Invoice, InvoiceStatus, Tenant, Customer } from "@prisma/client";

type BuildInvoiceInput = Partial<{
  tenant: Tenant;
  customer: Customer;
  status: InvoiceStatus;
  amount: number;
  daysOverdue: number;
  lastReminderSentAt: Date | null;
}>;

/**
 * Creates an Invoice in the test database with sensible defaults.
 * Override any field by passing it in.
 */
export async function buildInvoice(input: BuildInvoiceInput = {}): Promise<Invoice> {
  const tenant = input.tenant ?? (await buildTenant());
  const customer = input.customer ?? (await buildCustomer({ tenant }));

  const daysOverdue = input.daysOverdue ?? 0;
  const dueDate = new Date(Date.now() - daysOverdue * 24 * 60 * 60 * 1000);

  const status: InvoiceStatus = input.status ?? (daysOverdue > 7 ? "overdue" : "pending");

  return prisma.invoice.create({
    data: {
      tenantId: tenant.id,
      customerId: customer.id,
      customerEmail: customer.email,
      amount: input.amount ?? 10000,
      status,
      dueDate,
      lastReminderSentAt: input.lastReminderSentAt ?? null,
    },
  });
}
```

### 7.2 Annotations on the builder

| Pattern | Where |
|---|---|
| Input type is `Partial<...>`; every field optional | `BuildInvoiceInput` |
| Defaults produce a valid entity without any input | The whole function |
| Composing builders: if no `tenant` is passed, one is built | `input.tenant ?? (await buildTenant())` |
| Defaults are realistic and policy-aware (status defaults to "overdue" if `daysOverdue > 7`) | `status` default |
| Money default uses an integer (10000 cents = $100), matching the schema | `input.amount ?? 10000` |

---

## 8. Coverage report

After running the test suite, the Test Project produces a coverage report in this exact shape and saves it as `06-test-report.md`.

### 8.1 Sample coverage report for this feature

```markdown
# Test Coverage Report — Invoice Reminders

ACCEPTANCE CRITERIA COVERED
- Criterion 1: "An admin can trigger a reminder for an overdue invoice" — covered by `route.test.ts > returns 200 with the updated timestamp...` and `trigger-manual-reminder.test.ts > sends a reminder when the admin and invoice share a tenant...`
- Criterion 2: "Only admins can trigger reminders" — covered by `route.test.ts > returns 401 when called without a session` and `returns 401 when called by a non-admin user`
- Criterion 3: "Tenant isolation is enforced" — covered by `route.test.ts > returns 404 when the admin and invoice belong to different tenants` and `trigger-manual-reminder.test.ts > rejects the request with TenantMismatchError...`
- Criterion 4: "Invalid invoice IDs return 404" — covered by `route.test.ts > returns 404 when the invoice id is not a valid UUID` and `returns 404 when the invoice does not exist`
- Criterion 5: "A reminder cannot be sent twice within 24 hours" — covered by `route.test.ts > returns 409 when a reminder was sent within the last 24 hours` and `trigger-manual-reminder.test.ts > throws ReminderAlreadySentError...`
- Criterion 6: "Paid or cancelled invoices are not eligible for reminders" — covered by `trigger-manual-reminder.test.ts > throws InvoiceNotEligibleForReminderError when the invoice is paid` and `... when the invoice is cancelled`

ACCEPTANCE CRITERIA NOT COVERED
- All acceptance criteria covered.

EDGE CASES COVERED
- 24-hour boundary (just inside / just outside the dedup window) — `helpers.test.ts > returns true at exactly 23 hours 59 minutes 59 seconds` and `returns false at exactly 24 hours`
- 7-day overdue boundary — `helpers.test.ts > returns false at exactly 7 days` and `returns true when the invoice is 8 days past due`
- Email service failure — `trigger-manual-reminder.test.ts > does not modify the invoice when the email service fails` and `route.test.ts > returns 500 and does not mark the invoice as reminded when the email service fails`
- Future-dated invoices — `helpers.test.ts > returns false for an invoice with a future due date`

EDGE CASES NOT COVERED
- All edge cases covered.

LIKELY DEFECTS NOTICED WHILE WRITING TESTS
- No likely defects noticed.
```

### 8.2 Annotations on the report

| Pattern | Notes |
|---|---|
| Every acceptance criterion is mapped to specific test names | This is the audit trail — "we tested criterion 1 by running test X" |
| Every section appears even when there is nothing to report | "All acceptance criteria covered" / "No likely defects noticed" — silence is not allowed |
| Edge cases get their own section so a reviewer can see boundary coverage separately from criterion coverage | "EDGE CASES COVERED" |
| Test names are descriptive enough that a non-developer can map them back to the criterion | Sentence-shaped names |

---

## 9. What this example demonstrates

The Builders and Test Project should pick up these patterns from this example:

| Pattern | Where shown |
|---|---|
| Test files colocated with code (`*.test.ts` next to `*.ts`) | All test files |
| Descriptive `describe` / `it` naming, sentence-shaped | Throughout |
| Arrange / Act / Assert with blank-line separation | Section 3 |
| Test data builders, never inline setup objects | Sections 3, 5, 7 |
| Database is real; only external boundaries are mocked | `vi.mock("@/services/email/...")` |
| Side-effect verification on negative paths (`expect(mock).not.toHaveBeenCalled()`) | Sections 3, 5 |
| Boundary conditions tested explicitly (just-inside / just-outside) | Section 4 |
| Time-dependent helpers accept an injectable `now`; tests pass an explicit value | Sections 3, 4 |
| Component tests use `getByRole` and `userEvent`, not implementation-detail queries | Section 6 |
| Accessibility behavior (keyboard, ARIA) is tested, not just visible behavior | Section 6 |
| Loading states tested by holding the promise open until manually resolved | Section 6 |
| Error paths verify the callback is NOT called and the UI recovers | Section 6 |
| Each acceptance test is annotated with the criterion it covers | Section 5 |
| The coverage report maps every criterion to specific test names | Section 8 |
| Empty sections in the coverage report are filled with "All X covered" / "No Y noticed", never omitted | Section 8 |
| Tests are independent (`beforeEach` cleans state; no shared variables between tests) | Throughout |

---

## 10. What this example deliberately omits

These patterns exist in the team's broader test infrastructure but are not shown here to keep the example focused:

- **End-to-end tests with Playwright.** This file covers unit, integration, and acceptance tests. A full e2e suite for this feature would live in `e2e/invoice-reminders.spec.ts` and cover the full user flow in a real browser. The conventions are similar; Playwright provides its own `expect` and `page` APIs.
- **Visual regression tests.** Not part of this team's testing approach by default; for design-system components, the team uses Storybook with Chromatic if visual testing is needed.
- **Mutation testing.** Not used by default. Mutation testing is a meta-test (do the tests catch real bugs?); the team relies on code review and the validator instead.
- **Property-based testing.** Not shown here. For features with non-trivial input domains (parsers, validators, mathematical functions), the team uses `fast-check` for property-based tests. The invoice-reminders feature does not benefit from it.
- **Snapshot tests.** Not used by default. Snapshot tests tend to be fragile and uninformative; the team prefers explicit assertions about the parts of the output that matter.
- **Performance tests.** Not part of unit/component test files. Performance is measured in CI via separate tooling (Lighthouse for frontend, k6 or similar for backend load), and the results are reviewed at the spec stage, not during testing.

If a feature needs any of the above, the Test Project must surface it in the coverage report as an "ACCEPTANCE CRITERIA NOT COVERED" entry with the reason ("this criterion is verified by performance testing, not unit tests"), so the audit trail records that the chain considered it.

---

## 11. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

- **This file pairs with `example-backend-feature.md` and `example-frontend-feature.md`.** If those examples evolve, walk this file to confirm helper names, types, and APIs still match.
- **If the chain consistently produces shallow tests** (happy path only, no failure-path coverage), the lever is to add more failure tests here. The chain mirrors the depth of the example.
- **If tests come back without descriptive names**, the lever is more strong-vs-weak examples in `conventions/testing-conventions.md` section 3, plus more sentence-shaped names in this file.
- **If component tests consistently use the wrong query types** (`getByTestId` instead of `getByRole`), the lever is more examples in section 6 plus a stronger rule in `conventions/testing-conventions.md` section 1.
- **If coverage reports come back missing sections**, the rule is reinforced in section 8 here plus in the Test role file (`06-test.md`). The fix is usually to add a concrete example of what an empty section should look like ("All acceptance criteria covered" / "No likely defects noticed").