# Backend Conventions

> **Location:** `js-saas-factory-knowledge/conventions/backend-conventions.md`
>
> **Purpose:** Rules specific to backend code — API layer, services, database access, jobs, errors, logging, tenant isolation, auth.
>
> **Audience:** Researcher, Spec Writer, Backend Builder, Validate.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

This file is the canonical reference for backend code. The Backend Builder mirrors what it sees here when writing new code; the Validator flags deviations during Gate 3.

The single most important section is **section 5 — tenant isolation**. Backend bugs in regulated-adjacent work are most often tenant boundary failures. Treat that section as the highest-stakes content in this file.

---

## 1. Layering

The backend has three layers. Each layer has a single responsibility and is allowed to call only the layer directly below it.

```
┌──────────────────────────────────────────┐
│  API routes / request handlers            │  ← request shape, auth, validation, response
├──────────────────────────────────────────┤
│  Services                                 │  ← business logic, orchestration
├──────────────────────────────────────────┤
│  Repositories / data access modules       │  ← database I/O only
└──────────────────────────────────────────┘
```

### 1.1 What routes are allowed to do

- Parse and validate the request body, query, and params with a Zod schema
- Verify the caller is authenticated
- Verify the caller has the required role for this endpoint
- Call exactly one service function
- Map service results to HTTP responses
- Set response status codes and headers

### 1.2 What routes are NOT allowed to do

- Contain business logic of any kind
- Call the database or ORM directly
- Loop, branch on data, transform results beyond the response mapping
- Read environment variables (services do that)
- Catch errors and decide what to log (services and the global error handler do that)

### 1.3 What services own

- All business logic for the feature
- Orchestration across multiple repositories or external calls
- Tenant boundary enforcement (see section 5)
- Authorization checks beyond role (resource-level permissions)
- Calling external services (email, third-party APIs)
- Producing structured log events for important state changes

### 1.4 What repositories own

- Database queries (selecting, inserting, updating, deleting)
- Transactions, where the transaction is scoped to a single repository call
- ORM-specific concerns (Prisma includes, raw queries)
- Type-safe mapping between database rows and domain objects

Repositories never contain business logic. They are CRUD plus query shaping, and nothing else.

---

## 2. API route structure

A typical route file looks like this:

```typescript
// src/app/api/admin/invoices/[id]/remind/route.ts

import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

import { requireAdminInTenant } from "@/lib/auth";
import { logger } from "@/lib/logger";
import { triggerManualReminder } from "@/services/reminders";
import { TenantMismatchError, InvoiceNotFoundError } from "@/lib/errors";

const ParamsSchema = z.object({
  id: z.string().uuid(),
});

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  const parsedParams = ParamsSchema.parse(params);

  const session = await requireAdminInTenant(request);

  try {
    const result = await triggerManualReminder({
      invoiceId: parsedParams.id,
      tenantId: session.tenantId,
      actorId: session.userId,
    });

    return NextResponse.json({
      success: true,
      lastReminderSentAt: result.lastReminderSentAt,
    });
  } catch (error) {
    if (error instanceof TenantMismatchError) {
      return NextResponse.json({ error: "tenant_mismatch" }, { status: 403 });
    }
    if (error instanceof InvoiceNotFoundError) {
      return NextResponse.json({ error: "invoice_not_found" }, { status: 404 });
    }

    logger.error({ err: error, invoiceId: parsedParams.id }, "manual reminder failed");
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
}
```

**Notable rules from this example:**

- The Zod schema is defined inline if it's only used here, or imported from `*.schema.ts` if it's shared with the frontend
- Auth happens before service call; the service receives the validated tenant context
- The service is called exactly once
- Known errors are mapped to specific status codes; unknown errors get a generic 500 with logging

---

## 3. Request validation

Every request body, query, and params object is validated by a Zod schema at the route boundary. There are no exceptions to this rule.

**Shared schemas live in `*.schema.ts` files** when they're used by both the backend (for validation) and the frontend (for form validation):

```typescript
// src/schemas/reminder.schema.ts

import { z } from "zod";

export const TriggerManualReminderRequestSchema = z.object({
  // Empty body; included for shape consistency.
});

export const TriggerManualReminderResponseSchema = z.object({
  success: z.literal(true),
  lastReminderSentAt: z.string().datetime(),
});

export type TriggerManualReminderResponse = z.infer<
  typeof TriggerManualReminderResponseSchema
>;
```

**Validation behavior:**

- Invalid request body → 400 with a generic error message (do not echo the raw input)
- Invalid query/params → 400
- The error response shape is consistent: `{ error: string, details?: unknown }`

---

## 4. Service structure

Services are pure functions that take their dependencies and inputs explicitly. They do not import the database directly; they receive a repository or pass through a repository call.

```typescript
// src/services/reminders/trigger-manual-reminder.ts

import { logger } from "@/lib/logger";
import { sendReminderEmail } from "@/services/email";
import { invoiceRepository } from "@/repositories/invoice";
import {
  TenantMismatchError,
  InvoiceNotFoundError,
  ReminderAlreadySentError,
} from "@/lib/errors";

type TriggerManualReminderInput = {
  invoiceId: string;
  tenantId: string;
  actorId: string;
};

type TriggerManualReminderResult = {
  lastReminderSentAt: Date;
};

export async function triggerManualReminder(
  input: TriggerManualReminderInput,
): Promise<TriggerManualReminderResult> {
  const invoice = await invoiceRepository.findById(input.invoiceId);

  if (!invoice) {
    throw new InvoiceNotFoundError(input.invoiceId);
  }

  // Tenant isolation: enforced at the service layer, not just the route.
  if (invoice.tenantId !== input.tenantId) {
    logger.warn(
      { invoiceId: input.invoiceId, actorTenantId: input.tenantId },
      "tenant mismatch on manual reminder attempt",
    );
    throw new TenantMismatchError();
  }

  // Idempotency: prevent duplicate sends within the same window.
  if (invoice.lastReminderSentAt && wasRecentlySent(invoice.lastReminderSentAt)) {
    throw new ReminderAlreadySentError(input.invoiceId);
  }

  await sendReminderEmail(invoice);

  const updated = await invoiceRepository.updateLastReminderSentAt({
    id: invoice.id,
    lastReminderSentAt: new Date(),
  });

  logger.info(
    {
      invoiceId: invoice.id,
      tenantId: invoice.tenantId,
      actorId: input.actorId,
      action: "manual_reminder_sent",
    },
    "manual reminder sent",
  );

  return { lastReminderSentAt: updated.lastReminderSentAt };
}
```

**Notable rules from this example:**

- The function signature is explicit: typed input, typed output
- The tenant check happens in the service, not relying on the route
- Errors are thrown with specific custom error types
- Important state changes produce structured log events with an `action` field

---

## 5. Tenant isolation

**This section is the highest-stakes content in this file.** Tenant isolation failures are how cross-tenant data leaks happen.

### 5.1 The rule

**Every service function that operates on tenant-scoped data must verify that the data belongs to the caller's tenant before acting on it.** This check happens in the service layer, not just the route.

### 5.2 Why "not just the route"

A route-level check works only when the service is called from a route. Services are also called from:

- Background jobs (BullMQ workers)
- CLI scripts and admin tools
- Tests
- Other services (where the calling service may have a different tenant context)

If tenant checks live only in routes, a service called from a worker can bypass them entirely. Service-level checks always run.

### 5.3 The pattern

Every tenant-scoped service function takes a `tenantId` parameter. The function fetches the resource, compares the resource's tenant to the input tenant, and throws `TenantMismatchError` if they differ:

```typescript
async function getInvoice(input: { id: string; tenantId: string }) {
  const invoice = await invoiceRepository.findById(input.id);
  if (!invoice) throw new InvoiceNotFoundError(input.id);
  if (invoice.tenantId !== input.tenantId) throw new TenantMismatchError();
  return invoice;
}
```

For bulk queries, scope the query at the database level:

```typescript
async function listInvoices(input: { tenantId: string; status?: string }) {
  return invoiceRepository.findMany({
    tenantId: input.tenantId,
    status: input.status,
  });
}
```

### 5.4 What to log on a tenant mismatch

A tenant mismatch is suspicious. Log it at WARN level with the actor, the target resource, and the actor's tenant. Do not log the target resource's actual tenant — that itself could leak information if logs are accessed across tenants.

```typescript
logger.warn(
  { actorId, actorTenantId, resourceId },
  "tenant mismatch attempt",
);
```

### 5.5 What never happens in tenant-scoped code

- Querying without a tenant filter and then checking after — too easy to forget the post-check
- Trusting `tenantId` from the request body — it must come from the authenticated session
- Returning a "not found" status when the actual issue is a tenant mismatch — the user will think the resource doesn't exist, which is the right user-facing message, but the log must record the truth

---

## 6. Database access (Prisma)

### 6.1 Query patterns

- Use Prisma's typed query builder for everything; avoid raw SQL except for queries that the builder can't express
- All queries scoped to a tenant include `tenantId` in the `where` clause at the repository level
- Use `select` to fetch only the fields needed; avoid pulling the whole row when you'll use three columns
- Use `include` for relations only when the caller will use the relation; otherwise fetch separately

### 6.2 Transactions

- Wrap any operation that modifies more than one row in a transaction
- Keep transactions short; long transactions block the database
- A transaction must not call external services (email, third-party APIs) — those happen outside the transaction

```typescript
// Good
await prisma.$transaction(async (tx) => {
  const invoice = await tx.invoice.update({ where: { id }, data: { status: "paid" } });
  await tx.payment.create({ data: { invoiceId: id, amount } });
});

await sendPaymentConfirmation(invoice); // external call outside the transaction

// Avoid
await prisma.$transaction(async (tx) => {
  await tx.invoice.update(/* ... */);
  await sendPaymentConfirmation(/* ... */); // external call inside transaction
});
```

### 6.3 Migration policy

- Migrations are append-only — see `stack/deployment-notes.md` section 6
- Migration filenames must be descriptive: `20260525143000_add_last_reminder_sent_at.sql`
- Destructive migrations (drop column, drop table) require a corresponding backfill or data preservation plan

---

## 7. Background jobs (BullMQ)

Use a background job when:

- The work takes longer than 1 second
- The work can be retried safely if it fails
- The caller doesn't need to wait for the result
- The work is on a schedule (daily, hourly)

Do NOT use a background job when:

- The caller needs the result immediately
- The work is part of an atomic transaction (jobs are not part of database transactions)
- The work is one-off (use an admin script)

### 7.1 Job structure

```typescript
// src/workers/send-overdue-reminders.worker.ts

import { Worker } from "bullmq";
import { logger } from "@/lib/logger";
import { sendOverdueReminders } from "@/services/reminders";
import { redisConnection } from "@/lib/redis";

export const sendOverdueRemindersWorker = new Worker(
  "send-overdue-reminders",
  async (job) => {
    logger.info({ jobId: job.id }, "starting overdue reminders job");
    const result = await sendOverdueReminders();
    logger.info({ jobId: job.id, sent: result.sent }, "overdue reminders job complete");
    return result;
  },
  {
    connection: redisConnection,
    concurrency: 1,
  },
);
```

### 7.2 Retry policy

- Default retry: 3 attempts with exponential backoff
- Idempotency: every job must be safe to run more than once
- Failed jobs after retries are moved to a dead-letter queue and surface in monitoring

### 7.3 Naming

Job queue names use kebab-case and describe the action: `send-overdue-reminders`, `process-stripe-webhook`, `recompute-invoice-totals`.

---

## 8. Error handling

### 8.1 Custom error classes

Define a custom error class for each known failure mode. Each class extends `Error` and sets `name` to the class name:

```typescript
// src/lib/errors.ts

export class TenantMismatchError extends Error {
  constructor(message = "Tenant boundary violation") {
    super(message);
    this.name = "TenantMismatchError";
  }
}

export class InvoiceNotFoundError extends Error {
  constructor(invoiceId: string) {
    super(`Invoice not found: ${invoiceId}`);
    this.name = "InvoiceNotFoundError";
  }
}

export class ReminderAlreadySentError extends Error {
  constructor(invoiceId: string) {
    super(`Reminder already sent recently for invoice ${invoiceId}`);
    this.name = "ReminderAlreadySentError";
  }
}
```

### 8.2 Error-to-status mapping

Route handlers map known errors to HTTP responses:

| Error type | Status | User-facing message |
|---|---|---|
| `TenantMismatchError` | 403 | `"tenant_mismatch"` (or 404 if you don't want to reveal that the resource exists) |
| `NotFoundError` (resource doesn't exist) | 404 | `"not_found"` |
| `ValidationError` (Zod failure) | 400 | `"invalid_input"` |
| `UnauthorizedError` (not authenticated) | 401 | `"unauthenticated"` |
| `ForbiddenError` (authenticated but lacks role) | 403 | `"forbidden"` |
| `ConflictError` (idempotency violation, duplicate) | 409 | `"conflict"` |
| Any other thrown error | 500 | `"internal_error"` |

The Validator should flag any route that returns a raw exception, a stack trace, or detailed internal information in the response body.

---

## 9. Logging (Pino)

### 9.1 Structure

Every log line is structured JSON with these fields where applicable:

- `level` — error / warn / info / debug
- `tenantId` — the tenant context for the operation
- `actorId` — the user performing the action
- `action` — a stable identifier for the operation (`manual_reminder_sent`, `invoice_created`)
- `resourceId` — the primary resource the action touched
- `err` — the error object if logging an error

```typescript
logger.info(
  { tenantId, actorId, action: "manual_reminder_sent", resourceId: invoice.id },
  "manual reminder sent",
);
```

### 9.2 Log levels

| Level | When to use |
|---|---|
| `error` | An operation failed in a way that needs investigation |
| `warn` | An unexpected condition that didn't fail but is worth noting (tenant mismatch attempts, rate limit hits) |
| `info` | Important state changes (record created, job started/completed) |
| `debug` | Detail useful during development; not enabled in production |

Avoid `console.log` entirely; ESLint blocks it.

### 9.3 What never gets logged

- Raw request bodies that may contain user input
- PHI of any kind
- Secrets (API keys, tokens, connection strings, passwords)
- Full stack traces of expected errors (only `error` cause matters; stack belongs in error tracking)
- Personal data in URLs or query strings

The Validator should flag any `logger.info(req.body, ...)` pattern as **CRITICAL**.

---

## 10. Auth and authorization

### 10.1 Authentication

- Auth.js (NextAuth) handles authentication
- Sessions are JWT-based or database-backed depending on the project; whichever is chosen is consistent across the codebase
- Every protected route calls a helper (`requireAuth`, `requireAdmin`, `requireAdminInTenant`) before doing anything else

### 10.2 Authorization

- **Role checks** happen at the route level (this admin endpoint requires the admin role)
- **Resource-level checks** happen at the service level (this admin can act on this resource because the resource belongs to their tenant)
- Mixing the two is a common bug — separate them clearly

### 10.3 The session shape

Every authenticated request has access to a session containing at minimum:

- `userId` — the authenticated user
- `tenantId` — the user's current tenant context
- `roles` — the user's roles in this tenant

`tenantId` is sourced from the session, never from the request body. The Validator should flag any pattern that reads `tenantId` from request input as **CRITICAL**.

---

## 11. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

- If Builders keep placing business logic in routes or queries in services, section 1 (layering) needs sharper examples.
- If the Validator keeps flagging tenant isolation gaps, section 5 needs a concrete example for the specific bug pattern that's recurring.
- If logs keep coming back without `tenantId` or `actorId`, section 9.1 needs to be more explicit about the required fields.
- This file should stay under three pages of dense content. Detail beyond that belongs in the example backend feature file.