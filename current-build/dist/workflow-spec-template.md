# Spec Template

> **Location:** `js-saas-factory-knowledge/workflow/spec-template.md`
>
> **Purpose:** The required shape of a technical brief plus strong-vs-weak examples for each section. The Spec Writer Project mirrors this shape on every run.
>
> **Audience:** Spec Writer.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

The Spec Writer reads this file at the start of every conversation. The template here is what the Spec Writer produces; the strong-vs-weak examples teach the difference between a brief that the Builders can act on directly and one that creates ambiguity.

A good brief settles every technical decision before code is written. If the Builders are forced to make design choices, the brief has failed. Time spent at Gate 2 is repaid many times over downstream.

---

## 1. The required shape

Every brief has these eight sections, in this exact order. The Spec Writer must produce all eight; missing sections are not acceptable.

1. **Stack used** — the layers involved, with any deviations from `target-stack-spec.md` called out
2. **Data model changes** — models, fields, types, indexes, migrations
3. **Flow** — step-by-step description of the behaviour end to end
4. **API changes** — endpoints, schemas, status codes, auth requirements
5. **Frontend changes** — routes, pages, components, hooks, state, accessibility
6. **Tests required** — success, failure, edge cases, acceptance tests
7. **Risks and open questions** — tenant isolation, timezone, accessibility, regulatory touches, anything else
8. **Files that will change or be created** — grouped by backend / frontend / tests / docs

A complete brief fits on roughly two pages.

---

## 2. Section-by-section guidance with examples

### 2.1 Stack used

**The shape:** confirm which stack components are involved. Reference `target-stack-spec.md`. Call out any deviation with explicit justification.

**Strong example:**

> Stack components in use for this feature:
>
> - **Backend:** Node 22, TypeScript strict, Next.js 15 App Router (API routes), Prisma + PostgreSQL, Zod for validation
> - **Background jobs:** BullMQ + Upstash Redis (existing worker)
> - **Email:** Resend (existing integration, MLR-approved template)
> - **Frontend:** React 19, Next.js App Router, Tailwind, React Hook Form not needed (no form), `Intl` for currency/date formatting
> - **Tests:** Vitest for unit/integration, Testing Library + userEvent for components, Playwright for one e2e smoke test
>
> No deviations from `target-stack-spec.md`.

**Weak example:**

> Uses the standard stack.

**Why the second is weak:** the Builders cannot tell from "standard stack" whether the feature touches the worker, whether email is involved, or whether Playwright is needed. The brief should always enumerate the specific layers being touched, even when no deviation is proposed.

---

### 2.2 Data model changes

**The shape:** specific models, specific fields, types, nullability, indexes, migration considerations. Tenant scoping called out on every model touched.

**Strong example:**

> ### Invoice model
>
> Add one nullable column:
>
> | Column | Type | Nullable | Notes |
> |---|---|---|---|
> | `lastReminderSentAt` | `DateTime?` | yes | `null` means no reminder has ever been sent |
>
> Add one index to support the deduplication query:
>
> ```
> @@index([tenantId, lastReminderSentAt])
> ```
>
> The existing `(tenantId, status, dueDate)` index continues to serve the overdue-scan query.
>
> **Migration:** single forward-only migration adding the column and the index. Nullable column means no backfill is required. Migration name: `20260525143000_add_last_reminder_sent_at`.
>
> **Tenant scoping:** `Invoice` already has `tenantId`. No new tenant-scoped table is introduced.
>
> **PHI:** the new column is a timestamp, not PHI. The `Invoice` record as a whole is treated per `regulated-environment-rules.md` section 1 (customer email and customer name are present on the record).

**Weak example:**

> Add a column to the Invoice model to track reminder timestamps.

**Why the second is weak:** column name, type, nullability, index strategy, and migration considerations are all absent. The Builder has to invent them. If the Builder invents a non-nullable column with a default, the migration breaks production; if the Builder forgets the index, the query is slow.

**A rule of thumb:** the Builder should be able to write the schema change directly from this section, without making any choices.

---

### 2.3 Flow

**The shape:** step-by-step description of how the behaviour runs end to end. Which existing infrastructure it reuses. Any new infrastructure called out explicitly.

**Strong example:**

> **Automatic reminder flow (daily worker):**
>
> 1. A BullMQ scheduled job (`send-overdue-reminders`, runs daily at 09:00 UTC) invokes the `sendOverdueReminders` service.
> 2. The service queries all invoices where:
>    - `status = "overdue"`
>    - `dueDate` is more than 7 days in the past
>    - `lastReminderSentAt` is null OR more than 24 hours ago
> 3. For each candidate, the service fetches the customer record, calls the existing `sendReminderEmail` service (Resend integration), and updates `lastReminderSentAt` to the current time.
> 4. Each invoice is processed sequentially. Failures are caught per-invoice; one failed send does not stop the batch.
> 5. The service returns counts (scanned, sent, skipped, failed) for the worker to log.
>
> **Manual trigger flow (admin UI):**
>
> 1. An admin clicks "Send reminder" on an invoice row in the admin UI.
> 2. The frontend `POST`s to `/api/admin/invoices/:id/remind`.
> 3. The route handler verifies the session is an admin, then calls `triggerManualReminder({ invoiceId, tenantId, actorId })`.
> 4. The service verifies the invoice belongs to the admin's tenant, is overdue, and was not reminded in the last 24 hours.
> 5. If checks pass, it sends the email and updates `lastReminderSentAt`. Otherwise it throws a specific error class.
> 6. The route maps the error (or the success) to an HTTP response. The frontend updates the row's "Last reminder" column optimistically.
>
> **Existing infrastructure reused:**
>
> - The BullMQ worker process (no new worker added)
> - The Resend integration and the MLR-approved `reminder-email-template.tsx`
> - The `requireAdminInTenant` auth helper
> - The Pino logger with existing PHI redaction config
>
> **New infrastructure:** none.

**Weak example:**

> A job runs daily and sends reminders. Admins can also trigger manually.

**Why the second is weak:** the worker name, the schedule, the query criteria, the per-invoice sequencing, the error handling, the manual endpoint shape — all absent. The Builders are forced to invent the design.

**A rule of thumb:** if a Builder asks "what does this flow actually do, step by step?" while reading the brief, the Flow section is too thin.

---

### 2.4 API changes

**The shape:** every new or modified endpoint, with method, path, auth requirement, request schema, success response shape, each error response shape with its status code.

**Strong example:**

> ### `POST /api/admin/invoices/:id/remind`
>
> **Auth:** requires authenticated session with the `admin` role in the invoice's tenant.
>
> **Path params:**
>
> - `id` — invoice UUID
>
> **Request body:** none.
>
> **Success response (200):**
>
> ```typescript
> {
>   success: true;
>   lastReminderSentAt: string; // ISO 8601 datetime
> }
> ```
>
> **Error responses:**
>
> | Status | Body | When |
> |---|---|---|
> | 401 | `{ error: "unauthenticated" }` | No session |
> | 404 | `{ error: "invoice_not_found" }` | Invoice does not exist, OR exists in a different tenant (deliberate — does not reveal cross-tenant existence) |
> | 409 | `{ error: "invoice_not_eligible" }` | Invoice is paid or cancelled |
> | 409 | `{ error: "reminder_already_sent_in_window" }` | Reminder was sent in the last 24 hours |
> | 500 | `{ error: "internal_error" }` | Any other error |
>
> Shared Zod schemas for request/response live in `src/schemas/reminder.schema.ts` (new file).

**Weak example:**

> Add an endpoint for triggering manual reminders. Returns success or an error.

**Why the second is weak:** the Frontend Builder cannot build against "success or an error." The exact status codes, error identifiers, and response shapes are the contract the frontend depends on. Without them, the frontend invents shapes and the chain produces mismatched code.

**The shape of every error must be specified.** The frontend maps these identifiers to user-facing messages (see `examples/example-frontend-feature.md` section 3.1). Unspecified errors become "internal_error" / "Something went wrong" — fine for unexpected failures, never for known ones.

---

### 2.5 Frontend changes

**The shape:** routes affected, components added or modified, hooks, state, loading and error states, accessibility considerations.

**Strong example:**

> **Routes affected:** `/admin/invoices` (existing page, modified).
>
> **Components added:**
>
> - `_components/InvoiceRow.tsx` — new Client Component. Holds local state for the optimistic update of `lastReminderSentAt`. Receives the invoice as a prop and a callback to update.
> - `_components/SendReminderButton.tsx` — new Client Component. Calls the API via the `triggerManualReminder` wrapper, shows loading and error states, fires `onSent` callback on success.
> - `_components/LastReminderColumn.tsx` — new Server Component-compatible component. Renders `<time>` element with relative formatting, or "Never" when null.
>
> **Components modified:**
>
> - `_components/InvoiceTable.tsx` — add the "Last reminder" column and the "Send reminder" action column.
>
> **State:** local `useState` in `InvoiceRow` for the optimistic update of `lastReminderSentAt`. No React Query — the action is one-shot and the page is server-rendered.
>
> **Loading state:** the Send button shows "Sending..." and is disabled during the request. `aria-busy="true"` is set on the button.
>
> **Error state:** errors trigger a toast (existing design system component) with a mapped user-facing message. The button re-enables after error so the user can retry.
>
> **Accessibility decisions:**
>
> - Button `aria-label` includes the invoice ID (multiple buttons on the page; the accessible name distinguishes them)
> - The success/error toast announces to assistive technology via the existing toast component's `aria-live="polite"` region
> - `<time>` element with `dateTime` attribute on the "Last reminder" column
> - Keyboard navigation: Tab moves between rows' buttons; Enter activates
> - No focus management changes required (no modal involved)

**Weak example:**

> Add a button to the admin invoices page and a column showing the last reminder time. Handle loading and errors.

**Why the second is weak:** Server vs. Client Component split, state management approach, accessibility decisions, and how loading/error states are surfaced are all absent. The Frontend Builder will invent each one, and the result will mismatch the team's conventions.

---

### 2.6 Tests required

**The shape:** success cases, failure cases (with HTTP status / error identifier), edge cases from the story, acceptance tests at the user-story level.

**Strong example:**

> ### Backend unit/integration tests (`trigger-manual-reminder.test.ts`)
>
> - **Success:** admin and invoice share a tenant, invoice is overdue → reminder sent, `lastReminderSentAt` updated
> - **Tenant boundary:** admin in Tenant A, invoice in Tenant B → throws `TenantMismatchError`, email service NOT called
> - **Not found:** invoice ID does not exist → throws `InvoiceNotFoundError`
> - **Not eligible:** invoice is paid → throws `InvoiceNotEligibleForReminderError`
> - **Not eligible:** invoice is cancelled → same
> - **Idempotency:** reminder sent 1 hour ago → throws `ReminderAlreadySentError`, email service NOT called
> - **Idempotency edge:** reminder sent exactly 23h 59m 59s ago → in window, throws
> - **Idempotency edge:** reminder sent exactly 24h 0m ago → out of window, sends
> - **Failure rollback:** email service throws → invoice's `lastReminderSentAt` is NOT updated
>
> ### Helper tests (`helpers.test.ts`)
>
> - `wasRecentlySent`: null → false; 1h ago → true; 25h ago → false; boundary at 24h → false
> - `isOverdueForReminder`: 6 days → false; 8 days → true; exactly 7 days → false; future date → false
>
> ### Acceptance tests at API level (`route.test.ts`)
>
> One test per acceptance criterion from the story (6 criteria → 6+ tests), plus the standard failure-path tests (401, 404, 409, 500 mappings).
>
> ### Component tests (`SendReminderButton.test.tsx`)
>
> - Renders accessible button with invoice ID in `aria-label`
> - Click calls the API with the right invoice ID
> - Calls `onSent` with the new timestamp on success
> - Disables button and shows "Sending..." during request
> - Re-enables button on error
> - Does NOT call `onSent` on error
> - Keyboard accessible (Tab + Enter)
>
> ### E2E test (`e2e/invoice-reminders.spec.ts`)
>
> One smoke test: admin signs in, navigates to overdue invoices, clicks Send reminder, sees success toast, sees "Last reminder" column update.

**Weak example:**

> - Test success and failure cases
> - Test the UI

**Why the second is weak:** the Test Project cannot produce specific tests from this. The strong example gives the Test Project a concrete checklist; the weak example leaves the work undefined.

---

### 2.7 Risks and open questions

**The shape:** tenant isolation, timezone, accessibility, regulatory touches — each addressed explicitly, even if only to say "not applicable, because X." Open questions for Gate 2 to resolve.

**Strong example:**

> **Tenant isolation:**
> Enforced at the service layer (`triggerManualReminder` checks `invoice.tenantId === input.tenantId`). The route also receives the tenant from the authenticated session, never from the request body. The `sendOverdueReminders` worker is a system-wide scan with no tenant input — the iteration itself does not need a tenant check because each invoice carries its own `tenantId` and reminders are sent per-invoice.
>
> **Timezone:**
> The 7-day overdue calculation uses UTC consistently. The invoice's `dueDate` is stored as a UTC timestamp; the worker runs daily at 09:00 UTC. The customer-facing email content uses the customer's locale for date display (via `Intl.DateTimeFormat`), but the eligibility logic itself is UTC-based. This is a deliberate choice — invoice billing is in a single business timezone (UTC), not per-customer.
>
> **Accessibility:**
> The admin UI changes are limited to one button per row and one column. Both meet WCAG 2.2 AA per `conventions/frontend-conventions.md` section 6. The button has a unique accessible name; the column uses `<time>` with `dateTime`; the toast announces via `aria-live`.
>
> **Regulatory touches:**
> The reminder email template is MLR-approved and listed in `do-not-modify.md` section 2. This feature does not modify the template content; it only changes when the template is sent. No MLR re-review expected, but the open question (below) should confirm.
>
> **Audit trail:**
> Every send (automatic or manual) produces a structured log entry with `action: "reminder.manually_sent"` or `"reminder.automatically_sent"`. The audit log writer is treated separately and is listed in `do-not-modify.md` — this feature uses it via the existing helper.
>
> **Open questions for Gate 2:**
>
> - **MLR re-approval:** confirm with the MLR coordinator that triggering the existing template at the 7-day threshold (instead of the 30-day threshold the template was originally approved for) does not require re-review.
> - **Daily worker timing:** 09:00 UTC is convenient but may not be ideal for all tenants' customer audiences. Recommend confirming with the product team before implementation.

**Weak example:**

> - Some risks may apply.
> - Tenant isolation should be handled.

**Why the second is weak:** silence on tenant isolation, timezone, and accessibility is treated as a skipped check. Every brief must address these three explicitly — even if the answer is "not applicable, because X." Vague mention is barely better than silence.

**A rule of thumb:** if the Validator at Gate 3 cannot tell from this section how a specific risk was addressed, the section needs sharpening. Concreteness is the test.

---

### 2.8 Files that will change or be created

**The shape:** every file path, grouped by backend / frontend / tests / docs. The Builders use this list to know their scope.

**Strong example:**

> ### Backend (new)
>
> - `src/services/reminders/trigger-manual-reminder.ts`
> - `src/services/reminders/send-overdue-reminders.ts`
> - `src/services/reminders/helpers.ts`
> - `src/services/reminders/types.ts`
> - `src/services/reminders/index.ts` (barrel)
> - `src/services/email/send-reminder-email.ts`
> - `src/schemas/reminder.schema.ts`
> - `src/app/api/admin/invoices/[id]/remind/route.ts`
> - `src/workers/overdue-reminders.worker.ts`
> - `prisma/migrations/20260525143000_add_last_reminder_sent_at/migration.sql`
>
> ### Backend (modified)
>
> - `prisma/schema.prisma` — add `lastReminderSentAt` and the index
> - `src/lib/errors.ts` — add four error classes
> - `src/repositories/invoice.repository.ts` — add `findOverdueForReminders` and `updateLastReminderSentAt`
>
> ### Frontend (new)
>
> - `src/lib/api/reminders.ts`
> - `src/lib/error-messages.ts`
> - `src/app/(admin)/invoices/loading.tsx`
> - `src/app/(admin)/invoices/error.tsx`
> - `src/app/(admin)/invoices/_components/InvoiceRow.tsx`
> - `src/app/(admin)/invoices/_components/SendReminderButton.tsx`
> - `src/app/(admin)/invoices/_components/LastReminderColumn.tsx`
>
> ### Frontend (modified)
>
> - `src/app/(admin)/invoices/page.tsx`
> - `src/app/(admin)/invoices/_components/InvoiceTable.tsx`
>
> ### Tests (new)
>
> - `src/services/reminders/trigger-manual-reminder.test.ts`
> - `src/services/reminders/helpers.test.ts`
> - `src/app/api/admin/invoices/[id]/remind/route.test.ts`
> - `src/app/(admin)/invoices/_components/SendReminderButton.test.tsx`
> - `e2e/invoice-reminders.spec.ts`
> - `test/builders/invoice.builder.ts` (new builder if not already present)
>
> ### Docs (new)
>
> - Will be produced by the Documentation Project at step 8.

**Weak example:**

> Various backend and frontend files will be added or modified.

**Why the second is weak:** the Builders can't tell what is in scope and what isn't. Files listed here are in scope; files not listed are out of scope. The Validator uses this list to flag scope creep at Gate 3.

---

## 3. Anti-patterns

### 3.1 Code in the brief

> ❌ *"Add a new service function: `async function triggerManualReminder(input) { const invoice = await prisma.invoice...`"*

The brief is a brief, not an implementation. Specify the function name, its inputs, its outputs, what it does — but not the code. If the brief contains code, the Builder may either copy it (and miss patterns the example file would have provided) or get confused by the partial specification.

### 3.2 Silence on tenant / timezone / accessibility

Every brief must address these three explicitly in section 7, even if only to say "not applicable, because X." Silence is treated as a skipped check.

### 3.3 New dependencies without justification

If the brief introduces a new package, vendor, or piece of infrastructure, it must include the justification in section 3 (Flow) or section 7 (Risks). "Adds a new scheduler" without explaining why the existing BullMQ worker can't be used is unacceptable.

### 3.4 File paths that don't match conventions

If the brief proposes paths that conflict with `conventions/backend-conventions.md` or `conventions/frontend-conventions.md`, the Builders will follow the brief and produce inconsistent code. The Spec Writer should anchor every path to the conventions and to the example feature files.

### 3.5 Briefs longer than two pages

A brief that sprawls is usually the result of a story that was too large. The fix is upstream: split the story, not the brief. Two pages is a strong signal of the right scope.

### 3.6 Briefs that don't reference the examples

The example files (`examples/example-backend-feature.md`, `examples/example-frontend-feature.md`) are the source of truth for "what good code looks like in this codebase." A brief that doesn't reference them is reinventing patterns the team has already settled.

---

## 4. Tuning notes

- **If briefs keep producing critical findings at Gate 3** (tenant gaps, missing failure paths, scope creep), the lever is usually section 2.7's examples — section 7 of the brief is where these are caught upstream.
- **If briefs keep proposing new dependencies when existing ones would do**, the Researcher's findings are probably too shallow — but section 2.1 here can also be sharpened to push back on stack deviations more firmly.
- **If briefs keep coming back too long**, the underlying story was too large. Push back at the story level rather than tolerating long briefs.
- **If file paths in section 2.8 keep being wrong**, refresh the example feature files and confirm the conventions match the real codebase.
- **If briefs keep skipping the timezone discussion**, add a more concrete timezone example to section 2.7.

---

## 5. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |