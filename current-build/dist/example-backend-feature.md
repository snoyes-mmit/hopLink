# Example: Backend Feature — Invoice Reminders

> **Location:** `js-saas-factory-knowledge/examples/example-backend-feature.md`
>
> **Purpose:** One complete, realistic backend feature shown end to end, with annotations on the patterns the Backend Builder should mirror. **This is the highest-leverage file in the knowledge base for backend code.**
>
> **Audience:** Spec Writer, Backend Builder.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

The Backend Builder reads this file at the start of every conversation. It mirrors the patterns shown here — file structure, layering, naming, error handling, logging, tenant isolation, testing — when producing code for new features.

**The single most important property of this file is that it represents what the team actually wants to ship.** If the example diverges from your real codebase, the chain's output diverges with it. Update this file when your real conventions evolve.

This file does not stand alone. It works alongside:

- `conventions/backend-conventions.md` (the rules)
- `conventions/js-conventions.md` (the language rules)
- `conventions/testing-conventions.md` (test-specific rules)
- `examples/example-test-suite.md` (test-side example for this same feature)

---

## 1. Feature description

The feature is **invoice reminders**: the system sends an email reminder to the customer when an invoice is more than seven days overdue, and an admin can manually trigger a reminder for a specific invoice from the admin UI.

This feature is a good representative of the team's backend work because it exercises:

- **Service layer with business logic** (deduplication, status checks, tenant validation)
- **Repository layer with database access** (queries, updates, indexes)
- **API route layer** (Zod validation, auth, error mapping)
- **Background job** (scheduled scan for overdue invoices)
- **External service integration** (email via Resend)
- **Tenant isolation** at the service level
- **Idempotency** (don't send duplicate reminders in the same window)
- **Audit-relevant action** (reminder sent, with structured log entry)
- **Custom error classes** mapped to HTTP statuses
- **Unit tests** with builders, covering success and failure paths

If the chain can mirror this example well, it can build most production features.

---

## 2. File layout

The feature touches the following backend files. Frontend files are covered in `example-frontend-feature.md`; test files are covered in `example-test-suite.md`.

```
prisma/
└── schema.prisma                                  (modified — add column)
prisma/migrations/
└── 20260525143000_add_last_reminder_sent_at/
    └── migration.sql                              (new)

src/
├── lib/
│   ├── errors.ts                                  (modified — add error classes)
│   └── logger.ts                                  (existing — no change)
├── repositories/
│   └── invoice.repository.ts                      (modified — add update method)
├── services/
│   ├── reminders/
│   │   ├── index.ts                               (new)
│   │   ├── trigger-manual-reminder.ts             (new)
│   │   ├── send-overdue-reminders.ts              (new)
│   │   ├── helpers.ts                             (new — pure helpers)
│   │   └── types.ts                               (new)
│   └── email/
│       └── send-reminder-email.ts                 (new)
├── schemas/
│   └── reminder.schema.ts                         (new — shared with frontend)
├── app/api/admin/invoices/[id]/remind/
│   └── route.ts                                   (new)
└── workers/
    └── overdue-reminders.worker.ts                (new)
```

Tests live alongside each source file with the `.test.ts` suffix (see `example-test-suite.md`).

---

## 3. The files, in order

### 3.1 `prisma/schema.prisma` (modified — show the changed model)

Only the changed portion of the schema is shown. The full file contains other models.

```prisma
model Invoice {
  id                  String    @id @default(uuid())
  tenantId            String    @map("tenant_id")
  customerId          String    @map("customer_id")
  customerEmail       String    @map("customer_email")
  amount              Int       // stored as cents
  status              InvoiceStatus
  dueDate             DateTime  @map("due_date")
  lastReminderSentAt  DateTime? @map("last_reminder_sent_at")
  createdAt           DateTime  @default(now()) @map("created_at")
  updatedAt           DateTime  @updatedAt @map("updated_at")

  tenant              Tenant    @relation(fields: [tenantId], references: [id])
  customer            Customer  @relation(fields: [customerId], references: [id])

  @@index([tenantId, status, dueDate])
  @@index([tenantId, lastReminderSentAt])
  @@map("invoices")
}

enum InvoiceStatus {
  pending
  paid
  overdue
  cancelled
}
```

**Annotations:**

- **`tenantId` is on every model** that contains tenant-scoped data. It is the first column in all relevant indexes.
- **Indexes are explicit and named for the queries they serve.** The `(tenantId, status, dueDate)` index serves the overdue-invoice scan; `(tenantId, lastReminderSentAt)` serves the deduplication check.
- **Money is stored as integer cents**, not floats. This is non-negotiable for financial data.
- **`@map` directives** keep database columns in snake_case while the Prisma client uses camelCase. This is a team-wide convention.
- **`lastReminderSentAt` is nullable**, with `null` meaning "no reminder has ever been sent."

---

### 3.2 `prisma/migrations/20260525143000_add_last_reminder_sent_at/migration.sql` (new)

```sql
-- AlterTable
ALTER TABLE "invoices"
  ADD COLUMN "last_reminder_sent_at" TIMESTAMP(3);

-- CreateIndex
CREATE INDEX "invoices_tenant_id_last_reminder_sent_at_idx"
  ON "invoices"("tenant_id", "last_reminder_sent_at");
```

**Annotations:**

- **Migrations are append-only** (see `conventions/backend-conventions.md` section 6.3 and `compliance/do-not-modify.md` section 5). Once this migration is merged, it must never be edited.
- **The column is nullable**, so the migration does not require backfill.
- **The index supports the deduplication query** introduced by this feature.
- **The migration filename includes a UTC timestamp** for unambiguous ordering.

---

### 3.3 `src/lib/errors.ts` (modified — show only the added classes)

```typescript
// Existing error classes appear above.

export class InvoiceNotFoundError extends Error {
  constructor(invoiceId: string) {
    super(`Invoice not found: ${invoiceId}`);
    this.name = "InvoiceNotFoundError";
  }
}

export class TenantMismatchError extends Error {
  constructor(message = "Tenant boundary violation") {
    super(message);
    this.name = "TenantMismatchError";
  }
}

export class ReminderAlreadySentError extends Error {
  constructor(invoiceId: string) {
    super(`Reminder already sent recently for invoice ${invoiceId}`);
    this.name = "ReminderAlreadySentError";
  }
}

export class InvoiceNotEligibleForReminderError extends Error {
  constructor(invoiceId: string, status: string) {
    super(`Invoice ${invoiceId} is not eligible for reminder (status: ${status})`);
    this.name = "InvoiceNotEligibleForReminderError";
  }
}
```

**Annotations:**

- **One class per failure mode**, named after the failure rather than the HTTP status. The route handler maps classes to statuses.
- **Each class sets `name`** to its class name. This makes `instanceof` checks and error logging consistent.
- **Constructor signatures take just enough to produce a meaningful message.** The message goes into logs and developer-facing errors; it is never returned to end users (see route handler).
- **`TenantMismatchError` has a generic default message** that does not reveal which tenants were involved. The detail goes in the structured log entry.

---

### 3.4 `src/schemas/reminder.schema.ts` (new — shared with frontend)

```typescript
import { z } from "zod";

/**
 * Response shape for the manual-trigger endpoint.
 * Imported by both the route handler (validation) and the frontend
 * (response parsing).
 */
export const TriggerManualReminderResponseSchema = z.object({
  success: z.literal(true),
  lastReminderSentAt: z.string().datetime(),
});

export type TriggerManualReminderResponse = z.infer<
  typeof TriggerManualReminderResponseSchema
>;

/**
 * Error response shape, for any failure case.
 */
export const ReminderErrorResponseSchema = z.object({
  error: z.enum([
    "tenant_mismatch",
    "invoice_not_found",
    "reminder_already_sent_in_window",
    "invoice_not_eligible",
    "internal_error",
    "unauthenticated",
    "forbidden",
  ]),
});

export type ReminderErrorResponse = z.infer<typeof ReminderErrorResponseSchema>;
```

**Annotations:**

- **Schema files end in `.schema.ts`** by convention.
- **Schemas that cross the boundary** between backend and frontend live in `src/schemas/`. Backend-only schemas live next to their consumer.
- **The error response is an enum of stable identifiers.** These are not user-facing messages; the frontend maps them via `getUserFacingMessage` (see `example-frontend-feature.md`).
- **The success response uses `z.literal(true)`** for the `success` field. This makes the success case unambiguous in TypeScript discriminated unions.
- **`exports` are named.** Schemas export their value (`...Schema`) and their type (`...`); the type uses `z.infer`.

---

### 3.5 `src/services/reminders/types.ts` (new)

```typescript
export type TriggerManualReminderInput = {
  invoiceId: string;
  tenantId: string;
  actorId: string;
};

export type TriggerManualReminderResult = {
  lastReminderSentAt: Date;
};

export type SendOverdueRemindersResult = {
  scanned: number;
  sent: number;
  skippedDueToWindow: number;
  failed: number;
};
```

**Annotations:**

- **Types for a service module live next to the service**, not in a global types file.
- **Input and result types are named after the operation** (`TriggerManualReminderInput`, not `Input`).
- **Inputs are objects with named fields**, not positional parameters. This matters at the call site for readability and resilience to refactoring.
- **`tenantId` is in every service input** that operates on tenant-scoped data. The service uses it to enforce the tenant boundary.
- **Results are typed explicitly** rather than inferred from implementation.

---

### 3.6 `src/services/reminders/helpers.ts` (new — pure helpers)

```typescript
const REMINDER_DEDUP_WINDOW_MS = 24 * 60 * 60 * 1000; // 24 hours
const OVERDUE_THRESHOLD_DAYS = 7;

/**
 * Returns true if a reminder was sent inside the current dedup window
 * (24 hours by default). Used to prevent duplicate sends within a short
 * time, e.g. when an admin triggers manually shortly after the daily
 * worker also sent one.
 */
export function wasRecentlySent(lastReminderSentAt: Date | null, now: Date = new Date()): boolean {
  if (lastReminderSentAt === null) return false;
  return now.getTime() - lastReminderSentAt.getTime() < REMINDER_DEDUP_WINDOW_MS;
}

/**
 * Returns true if the invoice's due date is more than 7 days in the past.
 */
export function isOverdueForReminder(dueDate: Date, now: Date = new Date()): boolean {
  const overdueMs = OVERDUE_THRESHOLD_DAYS * 24 * 60 * 60 * 1000;
  return now.getTime() - dueDate.getTime() > overdueMs;
}
```

**Annotations:**

- **Pure helpers live in a `helpers.ts` file** within the service folder. Pure means: no I/O, no external dependencies, deterministic output for given input.
- **Constants are module-private** unless explicitly exported.
- **Time-dependent functions accept an optional `now: Date` parameter** for testability. Tests inject a fixed time; production code uses the default.
- **The reason for the time threshold (24 hours / 7 days) is in a comment**, not just the constant name. Future readers want to know the policy decision, not just the magic number.

---

### 3.7 `src/repositories/invoice.repository.ts` (modified — show only the added method and its context)

```typescript
import { prisma } from "@/lib/prisma";

import type { Invoice } from "@prisma/client";

export const invoiceRepository = {
  async findById(id: string): Promise<Invoice | null> {
    return prisma.invoice.findUnique({ where: { id } });
  },

  async findOverdueForReminders(input: {
    olderThan: Date;
    notRemindedSince: Date;
  }): Promise<Invoice[]> {
    return prisma.invoice.findMany({
      where: {
        status: "overdue",
        dueDate: { lt: input.olderThan },
        OR: [
          { lastReminderSentAt: null },
          { lastReminderSentAt: { lt: input.notRemindedSince } },
        ],
      },
    });
  },

  async updateLastReminderSentAt(input: {
    id: string;
    lastReminderSentAt: Date;
  }): Promise<Invoice> {
    return prisma.invoice.update({
      where: { id: input.id },
      data: { lastReminderSentAt: input.lastReminderSentAt },
    });
  },
};
```

**Annotations:**

- **Repositories are objects with methods**, exported as a single value. This makes them easy to mock at the boundary if needed (though the team's testing convention is to not mock the database — see `conventions/testing-conventions.md` section 6).
- **Methods accept input objects** for the same reason services do: readability and refactoring resilience.
- **The repository does database I/O only.** It does not enforce tenant boundaries (that is the service's job), does not log, does not throw custom errors.
- **Returns Prisma's native types.** Translation to domain types, if needed, happens at the service layer.
- **The `findOverdueForReminders` query is structured to be index-efficient**: the schema's `(tenantId, lastReminderSentAt)` index is used in conjunction with the worker filtering by tenant separately. (In a real codebase, you might consider including `tenantId` in this method's input and the query — choose based on how the worker dispatches work across tenants.)

---

### 3.8 `src/services/email/send-reminder-email.ts` (new)

```typescript
import { Resend } from "resend";

import { logger } from "@/lib/logger";

import type { Invoice } from "@prisma/client";

const resend = new Resend(process.env.RESEND_API_KEY);

export async function sendReminderEmail(input: {
  invoice: Invoice;
  customerName: string;
}): Promise<{ messageId: string }> {
  const response = await resend.emails.send({
    from: "billing@example.com",
    to: input.invoice.customerEmail,
    subject: `Reminder: invoice ${input.invoice.id} is overdue`,
    react: ReminderEmailTemplate({
      customerName: input.customerName,
      amount: input.invoice.amount,
      dueDate: input.invoice.dueDate,
    }),
  });

  if (response.error) {
    logger.error(
      {
        invoiceId: input.invoice.id,
        tenantId: input.invoice.tenantId,
        err: response.error,
      },
      "reminder email send failed",
    );
    throw new Error(`Failed to send reminder email: ${response.error.message}`);
  }

  return { messageId: response.data!.id };
}

// The React template is imported from the email templates folder.
// Shown here as a reference; the template itself is in
// src/emails/reminder-email-template.tsx and is MLR-approved
// (listed in do-not-modify.md).
declare function ReminderEmailTemplate(props: {
  customerName: string;
  amount: number;
  dueDate: Date;
}): React.ReactElement;
```

**Annotations:**

- **External service integrations live in their own service module**, isolated from business logic.
- **The function takes the invoice as input rather than fetching it**, so the calling service controls what is passed in. This keeps the email service focused and stateless.
- **The Resend client is initialized once at module level**, not per call.
- **Failures are logged with structured context** (`invoiceId`, `tenantId`) before being re-thrown. The throw lets the calling service decide what to do.
- **The `messageId` is returned** so the caller can record it in the audit log if needed.
- **Email content (the React template) lives separately** in `src/emails/` and is MLR-approved. The service references it but does not modify it. See `compliance/do-not-modify.md` section 2.

---

### 3.9 `src/services/reminders/trigger-manual-reminder.ts` (new)

```typescript
import {
  InvoiceNotFoundError,
  TenantMismatchError,
  ReminderAlreadySentError,
  InvoiceNotEligibleForReminderError,
} from "@/lib/errors";
import { logger } from "@/lib/logger";
import { invoiceRepository } from "@/repositories/invoice.repository";
import { customerRepository } from "@/repositories/customer.repository";
import { sendReminderEmail } from "@/services/email/send-reminder-email";

import { wasRecentlySent } from "./helpers";

import type {
  TriggerManualReminderInput,
  TriggerManualReminderResult,
} from "./types";

/**
 * Sends a reminder email for an overdue invoice, triggered manually by
 * an admin from the UI.
 *
 * Tenant isolation: enforced inside this function. The caller passes
 * the admin's tenantId; the function verifies the invoice belongs to
 * the same tenant before acting. See backend-conventions.md section 5.
 *
 * Idempotency: a reminder sent within the last 24 hours blocks a new
 * send, returning the existing `lastReminderSentAt` rather than
 * triggering another email.
 */
export async function triggerManualReminder(
  input: TriggerManualReminderInput,
): Promise<TriggerManualReminderResult> {
  const invoice = await invoiceRepository.findById(input.invoiceId);

  if (!invoice) {
    throw new InvoiceNotFoundError(input.invoiceId);
  }

  if (invoice.tenantId !== input.tenantId) {
    logger.warn(
      {
        actorId: input.actorId,
        actorTenantId: input.tenantId,
        resourceId: invoice.id,
        action: "reminder.manual_trigger_denied",
        outcome: "denied",
        failureReason: "tenant_mismatch",
      },
      "manual reminder denied due to tenant mismatch",
    );
    throw new TenantMismatchError();
  }

  if (invoice.status !== "overdue") {
    throw new InvoiceNotEligibleForReminderError(invoice.id, invoice.status);
  }

  if (invoice.lastReminderSentAt && wasRecentlySent(invoice.lastReminderSentAt)) {
    throw new ReminderAlreadySentError(invoice.id);
  }

  const customer = await customerRepository.findById(invoice.customerId);
  if (!customer) {
    throw new Error(
      `Invoice ${invoice.id} references missing customer ${invoice.customerId}`,
    );
  }

  await sendReminderEmail({
    invoice,
    customerName: customer.displayName,
  });

  const updated = await invoiceRepository.updateLastReminderSentAt({
    id: invoice.id,
    lastReminderSentAt: new Date(),
  });

  logger.info(
    {
      actorId: input.actorId,
      tenantId: invoice.tenantId,
      resourceId: invoice.id,
      action: "reminder.manually_sent",
      outcome: "success",
    },
    "manual reminder sent",
  );

  return { lastReminderSentAt: updated.lastReminderSentAt! };
}
```

**Annotations:**

- **The function signature** uses the typed input object pattern.
- **Tenant isolation happens in the service**, not in the route. The route already verified the caller is authenticated and is an admin; the service verifies the *resource* is in the caller's tenant. See `conventions/backend-conventions.md` section 5.
- **A tenant mismatch logs a structured warning** with the actor's tenant and the resource ID, but does *not* log the resource's actual tenant. The asymmetry prevents logs from being a cross-tenant data leak.
- **Failure modes are thrown errors of specific types.** The route maps them to HTTP statuses.
- **The happy-path log uses `level: info`** and includes a stable `action` identifier (`reminder.manually_sent`). The action identifier is what audit reports and analytics queries group by.
- **The order of checks matters.** Not-found → tenant mismatch → not eligible → already sent. This order prioritises the most security-relevant check (tenant) before the business-logic checks.
- **The customer lookup is defensive.** A missing customer for an existing invoice is a data integrity bug; the service throws a generic error which the route maps to 500.
- **The `!` after `updated.lastReminderSentAt` is justified** because `updateLastReminderSentAt` just set the value. The team's convention (see `conventions/js-conventions.md` section 2.3) is to avoid `!`, but the alternative (a redundant null check) is worse here. A linter comment explains it.

---

### 3.10 `src/services/reminders/send-overdue-reminders.ts` (new)

```typescript
import { logger } from "@/lib/logger";
import { invoiceRepository } from "@/repositories/invoice.repository";
import { customerRepository } from "@/repositories/customer.repository";
import { sendReminderEmail } from "@/services/email/send-reminder-email";

import { isOverdueForReminder } from "./helpers";

import type { SendOverdueRemindersResult } from "./types";

const OVERDUE_THRESHOLD_DAYS = 7;
const DEDUP_WINDOW_HOURS = 24;

/**
 * Scans all overdue invoices across all tenants and sends reminders
 * for those that have not been reminded in the current dedup window.
 *
 * Called by the daily background worker. Returns counts for monitoring.
 */
export async function sendOverdueReminders(): Promise<SendOverdueRemindersResult> {
  const now = new Date();
  const olderThan = new Date(now.getTime() - OVERDUE_THRESHOLD_DAYS * 24 * 60 * 60 * 1000);
  const notRemindedSince = new Date(now.getTime() - DEDUP_WINDOW_HOURS * 60 * 60 * 1000);

  const candidates = await invoiceRepository.findOverdueForReminders({
    olderThan,
    notRemindedSince,
  });

  const result: SendOverdueRemindersResult = {
    scanned: candidates.length,
    sent: 0,
    skippedDueToWindow: 0,
    failed: 0,
  };

  for (const invoice of candidates) {
    // Belt-and-braces: the query already filtered, but check again
    // in case the row was updated between query and processing.
    if (!isOverdueForReminder(invoice.dueDate, now)) {
      result.skippedDueToWindow += 1;
      continue;
    }

    try {
      const customer = await customerRepository.findById(invoice.customerId);
      if (!customer) {
        logger.warn(
          { invoiceId: invoice.id, tenantId: invoice.tenantId },
          "skipping reminder: customer not found",
        );
        result.failed += 1;
        continue;
      }

      await sendReminderEmail({ invoice, customerName: customer.displayName });
      await invoiceRepository.updateLastReminderSentAt({
        id: invoice.id,
        lastReminderSentAt: now,
      });

      logger.info(
        {
          actorId: "system",
          tenantId: invoice.tenantId,
          resourceId: invoice.id,
          action: "reminder.automatically_sent",
          outcome: "success",
        },
        "automatic reminder sent",
      );
      result.sent += 1;
    } catch (error) {
      logger.error(
        {
          invoiceId: invoice.id,
          tenantId: invoice.tenantId,
          err: error,
        },
        "automatic reminder failed for invoice",
      );
      result.failed += 1;
    }
  }

  return result;
}
```

**Annotations:**

- **The function is sequential, not parallel.** Reminders are sent one at a time. Parallelising would risk hammering the email provider and increase the cost of any single failure. The trade-off is throughput, which is acceptable for a daily scan.
- **Each invoice is wrapped in its own try/catch.** One failed send does not stop the rest of the batch.
- **The structured log entry uses `actorId: "system"`** for jobs, distinguishing automatic from manual reminders. The `action` identifier (`reminder.automatically_sent` vs. `reminder.manually_sent`) is different.
- **A defensive re-check** (`isOverdueForReminder`) protects against rows being modified between the query and processing.
- **The function returns counts** rather than throwing on partial failure. The worker logs the result; partial failure is a normal operating mode.
- **The function does not handle tenant scoping inside.** It iterates all overdue invoices regardless of tenant because the job runs as a system-wide scan. If your team prefers per-tenant scans, the function would take a `tenantId` parameter and the worker would dispatch one job per tenant.

---

### 3.11 `src/services/reminders/index.ts` (new — barrel file)

```typescript
export { triggerManualReminder } from "./trigger-manual-reminder";
export { sendOverdueReminders } from "./send-overdue-reminders";
export type {
  TriggerManualReminderInput,
  TriggerManualReminderResult,
  SendOverdueRemindersResult,
} from "./types";
```

**Annotations:**

- **Barrel files are allowed for service folders** because the folder represents a coherent public API.
- **The barrel exports only the public surface.** Helpers, repository internals, and types not used by consumers are not re-exported.
- **Type-only exports use the `export type` syntax.** This works with `verbatimModuleSyntax: true` in the tsconfig.

---

### 3.12 `src/app/api/admin/invoices/[id]/remind/route.ts` (new)

```typescript
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

import { requireAdminInTenant } from "@/lib/auth";
import { logger } from "@/lib/logger";
import {
  InvoiceNotFoundError,
  TenantMismatchError,
  ReminderAlreadySentError,
  InvoiceNotEligibleForReminderError,
} from "@/lib/errors";
import { triggerManualReminder } from "@/services/reminders";

const ParamsSchema = z.object({
  id: z.string().uuid(),
});

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  let parsedParams;
  try {
    parsedParams = ParamsSchema.parse(params);
  } catch {
    return NextResponse.json({ error: "invoice_not_found" }, { status: 404 });
  }

  const session = await requireAdminInTenant(request);
  if (!session) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }

  try {
    const result = await triggerManualReminder({
      invoiceId: parsedParams.id,
      tenantId: session.tenantId,
      actorId: session.userId,
    });

    return NextResponse.json({
      success: true as const,
      lastReminderSentAt: result.lastReminderSentAt.toISOString(),
    });
  } catch (error) {
    if (error instanceof TenantMismatchError) {
      // Return 404 rather than 403 to avoid revealing the invoice exists in another tenant.
      return NextResponse.json({ error: "invoice_not_found" }, { status: 404 });
    }
    if (error instanceof InvoiceNotFoundError) {
      return NextResponse.json({ error: "invoice_not_found" }, { status: 404 });
    }
    if (error instanceof InvoiceNotEligibleForReminderError) {
      return NextResponse.json({ error: "invoice_not_eligible" }, { status: 409 });
    }
    if (error instanceof ReminderAlreadySentError) {
      return NextResponse.json(
        { error: "reminder_already_sent_in_window" },
        { status: 409 },
      );
    }

    logger.error(
      { err: error, invoiceId: parsedParams.id },
      "manual reminder failed with unexpected error",
    );
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
}
```

**Annotations:**

- **The route is thin.** It parses params, verifies auth, calls one service, and maps the result. No business logic.
- **`requireAdminInTenant` is the auth helper.** It returns the session if the caller is authenticated and has the admin role, or `null` otherwise.
- **Tenant mismatch returns 404, not 403.** This is the team's chosen convention to avoid revealing that a given invoice exists in another tenant. The internal log records the truth; the user-facing response does not. (See `conventions/backend-conventions.md` section 8.2.)
- **Each known error type maps to a specific status and stable error identifier.** The identifiers come from `reminder.schema.ts` and are what the frontend maps via `getUserFacingMessage`.
- **The catch-all logs the unexpected error and returns a generic 500.** Stack traces and error details do not leave the server.
- **The `as const` after `true`** narrows the type to satisfy `TriggerManualReminderResponseSchema`.

---

### 3.13 `src/workers/overdue-reminders.worker.ts` (new)

```typescript
import { Queue, Worker } from "bullmq";

import { logger } from "@/lib/logger";
import { redisConnection } from "@/lib/redis";
import { sendOverdueReminders } from "@/services/reminders";

const QUEUE_NAME = "overdue-reminders";

export const overdueRemindersQueue = new Queue(QUEUE_NAME, {
  connection: redisConnection,
});

export const overdueRemindersWorker = new Worker(
  QUEUE_NAME,
  async (job) => {
    logger.info({ jobId: job.id, jobName: job.name }, "overdue reminders job starting");
    const result = await sendOverdueReminders();
    logger.info({ jobId: job.id, result }, "overdue reminders job complete");
    return result;
  },
  {
    connection: redisConnection,
    concurrency: 1,
  },
);

/**
 * Schedule the daily scan. Idempotent — calling repeatedly is safe;
 * BullMQ deduplicates by repeat-key.
 */
export async function scheduleOverdueRemindersDaily() {
  await overdueRemindersQueue.add(
    "daily-scan",
    {},
    {
      repeat: {
        pattern: "0 9 * * *", // 09:00 UTC every day
      },
      removeOnComplete: { age: 7 * 24 * 60 * 60, count: 100 },
      removeOnFail: { age: 30 * 24 * 60 * 60 },
    },
  );
}
```

**Annotations:**

- **The queue and worker are in the same file** as the scheduling helper. For more complex job systems, splitting them is fine; for a single-job worker like this, co-location is clearer.
- **Concurrency is `1`** because this job is a tenant-wide scan. Running it concurrently risks race conditions on the deduplication check.
- **The repeat key (`daily-scan`)** ensures BullMQ deduplicates if `scheduleOverdueRemindersDaily` is called more than once (e.g., on every server boot).
- **`removeOnComplete` and `removeOnFail`** prevent the job log from growing unbounded.
- **The worker just invokes the service.** It does not contain business logic.

---

## 4. What this example demonstrates

The Backend Builder should pick up these patterns from this example:

| Pattern | Where shown |
|---|---|
| Three-layer architecture (route → service → repository) | All of section 3 |
| Tenant isolation at the service layer | 3.9 |
| Idempotency via a column + a service check | 3.6, 3.9 |
| Custom error classes mapped to HTTP statuses | 3.3, 3.12 |
| Tenant mismatch returning 404 to avoid information leak | 3.12 |
| Structured logging with `actorId`, `tenantId`, `resourceId`, `action`, `outcome` | 3.9, 3.10 |
| Zod schemas shared between backend and frontend | 3.4 |
| Pure helpers separated from I/O code | 3.6 |
| Time-dependent helpers accepting an injectable `now` for testability | 3.6 |
| Background job invoking a service with concurrency 1 for safety | 3.10, 3.13 |
| Append-only migrations with named indexes | 3.1, 3.2 |
| Money stored as integer cents | 3.1 |
| Barrel files for coherent service folders | 3.11 |
| External service integration isolated in its own module | 3.8 |
| Routes parsing params, verifying auth, calling exactly one service, mapping the result | 3.12 |

---

## 5. What this example deliberately omits

These patterns exist in the team's broader codebase but are not shown here to keep the example focused:

- **Transactions across multiple repositories.** This feature only writes one row at a time. For multi-row writes, the team uses `prisma.$transaction` with the same patterns shown here. External calls (emails, third-party APIs) happen outside the transaction.
- **Optimistic locking.** The deduplication check is sufficient for this feature; concurrent manual triggers in the same window collide on the unique-ish state via the timestamp check. For features where two clients can race on the same row, the team uses `updatedAt` as a version key.
- **Caching.** This feature does not cache. For features that cache, the team uses Redis with stale-while-revalidate; the cache layer wraps the repository, not the service.
- **Internationalization of email content.** This example uses a single-language template. The team's i18n approach lives in `src/emails/` and is referenced from MLR-approved templates.
- **Audit log writes (separate from application logs).** This example logs to the application log (Pino). The team also maintains a separate audit log for regulated actions; see `compliance/regulated-environment-rules.md` section 4. The pattern is similar but uses a different writer module that is listed in `do-not-modify.md`.
- **Rate limiting on the admin endpoint.** Production-grade rate limiting is handled at the platform edge (Vercel rate limit rules), not in the route. If application-level rate limiting were needed, it would wrap the route handler.

If a feature needs any of the above, the Spec Writer must surface it in section 7 of the brief, and the Backend Builder may need patterns from other example feature files (or the broader codebase) in addition to this one.

---

## 6. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

- **This file is a snapshot of "what good looks like" today.** As the team's conventions evolve, this file must evolve with them. A stale example produces stale code.
- **If the Backend Builder consistently misses a pattern**, the pattern probably is not shown clearly enough in this file. Add a more explicit example.
- **If the Backend Builder consistently produces a pattern you do not want**, the pattern is probably not flagged in this file. Add a counter-example or a "what this deliberately omits" entry.
- **Resist the urge to make this example more complex.** Adding three more services, two more routes, and a webhook receiver would make the file comprehensive but unreadable. A single coherent feature is the right size.
- **Refresh this file after every major convention change.** When `conventions/backend-conventions.md` changes, walk this file to confirm it still matches.