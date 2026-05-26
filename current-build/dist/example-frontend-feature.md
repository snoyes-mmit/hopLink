# Example: Frontend Feature — Invoice Reminders Admin UI

> **Location:** `js-saas-factory-knowledge/examples/example-frontend-feature.md`
>
> **Purpose:** One complete, realistic frontend feature shown end to end, consuming the API contract from `example-backend-feature.md`. **This is the highest-leverage file in the knowledge base for frontend code.**
>
> **Audience:** Spec Writer, Frontend Builder.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

The Frontend Builder reads this file at the start of every conversation. It mirrors the patterns shown here — Server Component vs. Client Component splits, state management, data fetching, form handling, accessibility, error handling — when producing code for new features.

This file pairs with `example-backend-feature.md`. The two files describe the same feature from different sides: the backend produces an API contract; the frontend consumes it.

This file does not stand alone. It works alongside:

- `conventions/frontend-conventions.md` (the rules)
- `conventions/js-conventions.md` (the language rules)
- `conventions/testing-conventions.md` (test rules)
- `examples/example-test-suite.md` (test-side example for this same feature)

---

## 1. Feature description

The feature is the **admin UI for invoice reminders**: an admin can view a list of overdue invoices with a "Last reminder sent" column, manually trigger a reminder for any overdue invoice, and see the UI update optimistically with a success or error message.

This feature is a good representative of the team's frontend work because it exercises:

- **Server Component for the page-level layout and data fetching**
- **Client Component for the interactive row actions**
- **React Query for client-side mutation and cache invalidation**
- **Optimistic UI update on the mutation**
- **Form-free button-triggered action with confirmation patterns**
- **Loading, success, and error states** all visually distinct
- **Accessibility-by-default**: keyboard navigation, focus management, ARIA, status announcements
- **Mapping backend error identifiers to user-facing messages**
- **Component tests covering visible states and interactions**

If the chain can mirror this example well, it can build most production UI features.

---

## 2. File layout

The feature touches the following frontend files. Backend files are covered in `example-backend-feature.md`; test files are covered in `example-test-suite.md`.

```
src/
├── app/(admin)/invoices/
│   ├── page.tsx                                   (modified — Server Component)
│   ├── loading.tsx                                (new)
│   ├── error.tsx                                  (new)
│   └── _components/
│       ├── InvoiceTable.tsx                       (modified — Server Component)
│       ├── InvoiceRow.tsx                         (new — Client Component)
│       ├── SendReminderButton.tsx                 (new — Client Component)
│       └── LastReminderColumn.tsx                 (new — Server Component)
├── lib/
│   ├── api/
│   │   └── reminders.ts                           (new — fetch wrapper)
│   ├── error-messages.ts                          (new — error-to-user mapping)
│   └── format/
│       └── relative-time.ts                       (existing — no change)
└── components/ui/
    ├── button.tsx                                 (existing — design system)
    └── use-toast.tsx                              (existing — design system)
```

The `_components/` folder is a private folder (Next.js convention) — files inside are not routable. The `(admin)` route group provides the shared admin layout that enforces authentication.

---

## 3. The files, in order

### 3.1 `src/lib/error-messages.ts` (new)

```typescript
import { ReminderErrorResponse } from "@/schemas/reminder.schema";

/**
 * Maps stable backend error identifiers to user-facing messages.
 * The backend returns identifiers like "tenant_mismatch"; the frontend
 * displays "You don't have permission to act on this invoice."
 *
 * Never display the raw error identifier or the API response body to
 * end users. See frontend-conventions.md section 9.
 */
const REMINDER_ERROR_MESSAGES: Record<ReminderErrorResponse["error"], string> = {
  tenant_mismatch: "This invoice could not be found.",
  invoice_not_found: "This invoice could not be found.",
  reminder_already_sent_in_window:
    "A reminder was sent recently. Please wait at least 24 hours before sending another.",
  invoice_not_eligible:
    "This invoice is not eligible for a reminder (it may be paid or cancelled).",
  internal_error: "Something went wrong. Please try again.",
  unauthenticated: "Your session has expired. Please sign in again.",
  forbidden: "You don't have permission to do this.",
};

const GENERIC_FALLBACK = "Something went wrong. Please try again.";

export function getReminderErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code in REMINDER_ERROR_MESSAGES) {
    return REMINDER_ERROR_MESSAGES[error.code as ReminderErrorResponse["error"]];
  }
  return GENERIC_FALLBACK;
}

/**
 * Generic API error class produced by the fetch wrappers. The `.code`
 * property is the stable identifier from the backend; the message is
 * for developer logs only and is never shown to end users.
 */
export class ApiError extends Error {
  constructor(
    public readonly code: string,
    public readonly status: number,
    message?: string,
  ) {
    super(message ?? `API error ${status}: ${code}`);
    this.name = "ApiError";
  }
}
```

**Annotations:**

- **The error-to-message mapping is a `Record`** keyed by the backend's enum of error identifiers. TypeScript ensures the mapping is complete; missing keys would produce a compile error.
- **`tenant_mismatch` and `invoice_not_found` map to the same user-facing message.** This is deliberate. The backend returns 404 for both to avoid revealing cross-tenant resource existence (see `example-backend-feature.md` section 3.12); the frontend maintains that veil by showing the same message.
- **A generic fallback** is shown for unknown errors. The user-facing message is intentionally bland; detail belongs in error tracking, not the UI.
- **`ApiError` carries the stable `code`** from the backend. This is what `getReminderErrorMessage` switches on.

---

### 3.2 `src/lib/api/reminders.ts` (new)

```typescript
import {
  TriggerManualReminderResponseSchema,
  ReminderErrorResponseSchema,
  type TriggerManualReminderResponse,
} from "@/schemas/reminder.schema";

import { ApiError } from "@/lib/error-messages";

/**
 * Triggers a manual reminder for the given invoice.
 * Throws ApiError with a stable code on any backend error.
 * Throws a generic Error if the response cannot be parsed.
 */
export async function triggerManualReminder(
  invoiceId: string,
): Promise<TriggerManualReminderResponse> {
  const response = await fetch(`/api/admin/invoices/${invoiceId}/remind`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let parsed;
    try {
      parsed = ReminderErrorResponseSchema.parse(await response.json());
    } catch {
      throw new ApiError("internal_error", response.status);
    }
    throw new ApiError(parsed.error, response.status);
  }

  const body = await response.json();
  return TriggerManualReminderResponseSchema.parse(body);
}
```

**Annotations:**

- **Every API call goes through a typed wrapper** (one function per endpoint). Components never call `fetch` directly.
- **The response is validated with the shared Zod schema.** If the backend changes the shape, this throws at runtime, surfacing the bug immediately rather than failing silently somewhere downstream.
- **Errors are normalized into `ApiError`** with a stable code. Components downstream catch `ApiError` and map via `getReminderErrorMessage`.
- **Malformed error responses fall back to `internal_error`**, not crash. This handles cases like the API returning HTML (e.g., a 502 from a proxy).
- **The wrapper is pure: no React, no React Query, no UI concerns.** It is callable from anywhere.

---

### 3.3 `src/app/(admin)/invoices/page.tsx` (modified — Server Component)

```tsx
import { redirect } from "next/navigation";

import { getServerSession } from "@/lib/auth";
import { listOverdueInvoices } from "@/services/invoices";

import { InvoiceTable } from "./_components/InvoiceTable";

export const metadata = {
  title: "Overdue invoices",
};

export default async function OverdueInvoicesPage() {
  const session = await getServerSession();
  if (!session || !session.roles.includes("admin")) {
    redirect("/sign-in");
  }

  const invoices = await listOverdueInvoices({ tenantId: session.tenantId });

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold">Overdue invoices</h1>
      <InvoiceTable invoices={invoices} />
    </main>
  );
}
```

**Annotations:**

- **This is a Server Component** (no `"use client"`). It runs on the server, fetches data directly via the service layer (no internal API round-trip), and renders the result.
- **Auth happens in the page**, redirecting unauthenticated or non-admin users. The redirect is server-side, before any UI is sent to the browser.
- **The page calls into the service layer directly**, not via `fetch` against the project's own API. Server Components can do this because they execute server-side; calling your own API from here would be a double round-trip (see `conventions/frontend-conventions.md` section 4.1).
- **`metadata` sets the document title** via Next.js's metadata API, not via `useEffect` on a client.
- **Layout uses Tailwind classes** consistently. No custom CSS or styled-components.
- **The table component is imported from the private `_components/` folder.** This is the Next.js convention for non-routable component files.

---

### 3.4 `src/app/(admin)/invoices/loading.tsx` (new)

```tsx
export default function Loading() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8" aria-busy="true">
      <div className="mb-6 h-8 w-48 animate-pulse rounded bg-slate-200" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 animate-pulse rounded bg-slate-100" />
        ))}
      </div>
    </main>
  );
}
```

**Annotations:**

- **Loading UI is colocated with the route** via Next.js's `loading.tsx` convention.
- **`aria-busy="true"`** on the main container signals to assistive technology that content is loading.
- **The skeleton matches the layout of the loaded UI** — a heading, then a list of rows. This avoids layout shift when the real content arrives.
- **`Array.from({ length: 5 })` produces stable skeleton rows.** The `key={i}` index is acceptable here because the skeleton items are interchangeable.

---

### 3.5 `src/app/(admin)/invoices/error.tsx` (new)

```tsx
"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { logger } from "@/lib/logger";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logger.error({ err: error, digest: error.digest }, "invoices page error boundary");
  }, [error]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8" role="alert">
      <h1 className="mb-2 text-2xl font-semibold">Something went wrong</h1>
      <p className="mb-6 text-slate-600">
        We could not load the invoices list. Please try again. If the problem
        continues, contact support.
      </p>
      <Button onClick={() => reset()}>Try again</Button>
    </main>
  );
}
```

**Annotations:**

- **`error.tsx` is a Client Component** by Next.js convention — error boundaries need to manage React state.
- **The error is logged on mount** via the application logger. The `digest` field is Next.js's server-side correlation ID; it shows up in server logs for the same error.
- **The user-facing message is generic.** No `error.message`, no stack trace. The user is shown a recovery path (the "Try again" button), not technical details.
- **`role="alert"`** announces the error to assistive technology when the UI swaps in.
- **The user-facing message uses plain language**: "Something went wrong," not "An error was caught by the error boundary." Tone matters.

---

### 3.6 `src/app/(admin)/invoices/_components/InvoiceTable.tsx` (modified — Server Component)

```tsx
import { InvoiceRow } from "./InvoiceRow";

import type { Invoice } from "@/types/invoice";

export function InvoiceTable({ invoices }: { invoices: Invoice[] }) {
  if (invoices.length === 0) {
    return (
      <p className="rounded border border-slate-200 bg-slate-50 px-4 py-6 text-center text-slate-600">
        No overdue invoices. Nice.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200">
        <caption className="sr-only">Overdue invoices with reminder actions</caption>
        <thead className="bg-slate-50 text-left text-sm font-medium text-slate-600">
          <tr>
            <th scope="col" className="px-4 py-3">Invoice</th>
            <th scope="col" className="px-4 py-3">Customer</th>
            <th scope="col" className="px-4 py-3">Amount</th>
            <th scope="col" className="px-4 py-3">Due date</th>
            <th scope="col" className="px-4 py-3">Last reminder</th>
            <th scope="col" className="px-4 py-3">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white text-sm">
          {invoices.map((invoice) => (
            <InvoiceRow key={invoice.id} invoice={invoice} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

**Annotations:**

- **This is still a Server Component.** Rendering the table structure does not require interactivity; only individual rows do.
- **An empty state** is rendered when there are no invoices, not a blank section.
- **Semantic HTML**: real `<table>`, `<thead>`, `<tbody>`, `<th scope="col">`. Screen readers navigate tables based on these structures.
- **`<caption className="sr-only">`** provides a table description to screen readers without showing it visually.
- **The "Actions" column header has visible-but-hidden text** (`sr-only`) so screen readers announce the column even though the visual design omits the label.

---

### 3.7 `src/app/(admin)/invoices/_components/InvoiceRow.tsx` (new — Client Component)

```tsx
"use client";

import { useState } from "react";

import { SendReminderButton } from "./SendReminderButton";
import { LastReminderColumn } from "./LastReminderColumn";

import type { Invoice } from "@/types/invoice";

export function InvoiceRow({ invoice }: { invoice: Invoice }) {
  // Local state for optimistic update of the last-reminder timestamp.
  const [lastReminderSentAt, setLastReminderSentAt] = useState(
    invoice.lastReminderSentAt,
  );

  return (
    <tr>
      <td className="px-4 py-3 font-medium">{invoice.id.slice(0, 8)}</td>
      <td className="px-4 py-3">{invoice.customerName}</td>
      <td className="px-4 py-3">{formatCurrency(invoice.amount)}</td>
      <td className="px-4 py-3">{formatDate(invoice.dueDate)}</td>
      <td className="px-4 py-3">
        <LastReminderColumn lastReminderSentAt={lastReminderSentAt} />
      </td>
      <td className="px-4 py-3">
        <SendReminderButton
          invoiceId={invoice.id}
          onSent={setLastReminderSentAt}
        />
      </td>
    </tr>
  );
}

function formatCurrency(amountInCents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amountInCents / 100);
}

function formatDate(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(d);
}
```

**Annotations:**

- **`"use client"`** because the row holds local state for the optimistic update.
- **`useState` initialised from props** — the prop is the server-rendered baseline; local state lets the row update without refetching when the user triggers a reminder.
- **`onSent` is the callback** the button uses to bubble up the new timestamp. The button does not know about the row's state; the row owns the state and exposes a setter.
- **Currency uses `Intl.NumberFormat`**, dates use `Intl.DateTimeFormat`. These respect locale and produce accessible text by default.
- **The invoice ID is truncated for display** but the full ID is what flows through the API call. The display shortening does not change the data.

---

### 3.8 `src/app/(admin)/invoices/_components/LastReminderColumn.tsx` (new — Server Component)

```tsx
import { formatRelativeTime } from "@/lib/format/relative-time";

export function LastReminderColumn({
  lastReminderSentAt,
}: {
  lastReminderSentAt: string | null;
}) {
  if (lastReminderSentAt === null) {
    return <span className="text-slate-400">Never</span>;
  }

  return (
    <time dateTime={lastReminderSentAt} title={new Date(lastReminderSentAt).toLocaleString()}>
      {formatRelativeTime(new Date(lastReminderSentAt))}
    </time>
  );
}
```

**Annotations:**

- **This component renders inside a Client Component row** but is itself a Server Component-compatible component (no hooks, no event handlers). It works in both contexts.
- **The empty state ("Never") uses muted styling** to distinguish "no data" from "old data."
- **`<time>` with a `dateTime` attribute** is semantically correct and accessible. Screen readers can announce the precise time.
- **`title={...}` shows the absolute timestamp on hover** for sighted users who want the precise time without losing the relative display.
- **`formatRelativeTime`** is an existing helper that produces "2 hours ago," "yesterday," etc.

---

### 3.9 `src/app/(admin)/invoices/_components/SendReminderButton.tsx` (new — Client Component)

```tsx
"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { triggerManualReminder } from "@/lib/api/reminders";
import { getReminderErrorMessage } from "@/lib/error-messages";

type SendReminderButtonProps = {
  invoiceId: string;
  onSent: (lastReminderSentAt: string) => void;
};

export function SendReminderButton({ invoiceId, onSent }: SendReminderButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  async function handleClick() {
    setIsLoading(true);
    try {
      const result = await triggerManualReminder(invoiceId);
      onSent(result.lastReminderSentAt);
      toast({
        title: "Reminder sent",
        description: "The customer will receive an email shortly.",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Could not send reminder",
        description: getReminderErrorMessage(error),
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Button
      onClick={handleClick}
      disabled={isLoading}
      aria-busy={isLoading}
      aria-label={`Send reminder for invoice ${invoiceId.slice(0, 8)}`}
    >
      {isLoading ? "Sending..." : "Send reminder"}
    </Button>
  );
}
```

**Annotations:**

- **`"use client"`** because of the event handler, state, and hooks.
- **The button is disabled during the request** to prevent double-submits, and `aria-busy="true"` announces the busy state to assistive technology.
- **`aria-label` provides a unique accessible name** for the button. Multiple "Send reminder" buttons appear on the page (one per row); the accessible name distinguishes them by invoice ID.
- **The success and error paths both produce a toast.** The toast component is the team's design-system component for transient feedback; it announces messages to assistive technology via `aria-live`.
- **Error mapping uses `getReminderErrorMessage`.** No raw error or backend identifier reaches the user.
- **`onSent` is the optimistic update hook.** The button does not refetch the whole list; it tells the row to update its local state.
- **The success message wording is friendly and concrete** — "The customer will receive an email shortly" is more useful than "Operation successful."

---

## 4. What this example demonstrates

The Frontend Builder should pick up these patterns from this example:

| Pattern | Where shown |
|---|---|
| Server Components fetch data directly via services, not via internal API | 3.3 |
| Client Components only where interactivity requires it | 3.7, 3.9 |
| `loading.tsx` and `error.tsx` colocated with the route | 3.4, 3.5 |
| Empty states rendered as deliberate UI, not blank | 3.6 |
| Semantic HTML for tables, with `<caption>` and `scope` attributes | 3.6 |
| Optimistic UI updates via local state + callback | 3.7, 3.9 |
| API calls go through typed wrappers in `lib/api/` | 3.2 |
| Response validation with shared Zod schemas | 3.2 |
| Backend error identifiers mapped to user-facing messages | 3.1, 3.9 |
| `aria-busy` and `aria-label` for accessibility on action buttons | 3.9 |
| `<time>` element with `dateTime` for accessible timestamps | 3.8 |
| `Intl.NumberFormat` and `Intl.DateTimeFormat` for locale-aware formatting | 3.7 |
| Toast notifications for transient success and error feedback | 3.9 |
| Error boundaries log to the application logger; show generic UI | 3.5 |
| Tenant-mismatch and not-found return the same user-facing message | 3.1 |

---

## 5. What this example deliberately omits

These patterns exist in the team's broader codebase but are not shown here:

- **React Query for server state.** This example uses a simple optimistic update with `useState` because the action is one-shot and the page is server-rendered. For multi-step flows with caching, refetching, or shared state across components, the team uses React Query with array-based query keys. See `conventions/frontend-conventions.md` section 3.1.
- **Forms with React Hook Form and Zod.** This feature has no form (a button is not a form). For form patterns, see future feature examples or `conventions/frontend-conventions.md` section 5.
- **Pagination and infinite scroll.** The overdue invoices list is small in practice. For longer lists, the team uses URL-driven cursor pagination via search params.
- **URL-driven filters and sort.** Not needed here because the page shows one view. For multi-view dashboards, filters and sort live in the URL via Next.js's `useSearchParams`.
- **Confirmation dialogs.** Sending a reminder is a one-click action because it's idempotent and reversible (well, the email is not reversible, but the consequences are mild). For destructive actions, the team uses an accessible dialog component with focus management.
- **Internationalization of UI text.** This example uses English. The team's i18n approach is via `next-intl`; strings live in JSON files and components consume them via hooks. The pattern applies to user-facing UI text; backend error identifiers (which are never user-facing) remain in English.
- **Dark mode.** All Tailwind classes shown work in light mode only. The team's design tokens include dark variants; production components use them via `dark:` prefixes.

If a feature needs any of the above, the Spec Writer must surface it in section 7 of the brief, and the Frontend Builder may need patterns from other example feature files.

---

## 6. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

- **This file pairs with `example-backend-feature.md`.** If you update one, walk the other to confirm the API contract and helper names still match.
- **If the Frontend Builder consistently produces inaccessible UI**, add an explicit example of the right accessibility pattern for the missing concern.
- **If the Frontend Builder confuses Server and Client Components**, the lever is more explicit examples in section 3.3 / 3.7. Mark them clearly with `"use client"` and explain why each choice was made.
- **If components keep coming back with the wrong styling approach**, add a counter-example showing what to avoid (e.g., styled-components, inline styles, ad-hoc CSS).
- **Resist sprawl.** A single coherent feature is the right size for this file. Multi-feature dashboards belong in their own examples once the chain has shipped a few simpler features.