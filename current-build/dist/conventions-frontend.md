# Frontend Conventions

> **Location:** `js-saas-factory-knowledge/conventions/frontend-conventions.md`
>
> **Purpose:** Rules specific to frontend code — components, pages, hooks, state, styling, accessibility, routing, error handling on the client.
>
> **Audience:** Researcher, Spec Writer, Frontend Builder, Validate.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

This file is the canonical reference for frontend code. The Frontend Builder mirrors what it sees here; the Validator flags deviations during Gate 3.

The most important section for any team is **section 6 — accessibility**. Frontend conventions without accessibility expectations produce inaccessible UIs by default, and inaccessible UIs are bugs whether or not they're called out as such.

---

## 1. Server Components vs. Client Components

Next.js 15 App Router defaults to Server Components. The team's rule:

**Default to Server Components. Use Client Components only when interactivity requires it.**

Use a Client Component (`"use client"` directive) when the component needs any of:

- React hooks (`useState`, `useEffect`, `useReducer`, custom hooks that use them)
- Browser-only APIs (`window`, `document`, `localStorage`)
- Event handlers (`onClick`, `onChange`, `onSubmit`)
- React Context that propagates client state

Use a Server Component for everything else: data fetching, layout, static markup, anything that can run on the server.

**Don't pull a component into the client just because its child is a client component.** Compose: a Server Component can render a Client Component, and pass it server-fetched data as props. This keeps the JavaScript bundle smaller.

```tsx
// Good — server fetches, client interacts
// app/(admin)/invoices/page.tsx (Server Component)
export default async function InvoicesPage() {
  const invoices = await fetchInvoices();
  return <InvoiceList invoices={invoices} />;
}

// app/(admin)/invoices/_components/InvoiceList.tsx (Server Component)
export function InvoiceList({ invoices }: { invoices: Invoice[] }) {
  return (
    <table>
      {invoices.map((inv) => (
        <InvoiceRow key={inv.id} invoice={inv} />
      ))}
    </table>
  );
}

// app/(admin)/invoices/_components/InvoiceRow.tsx (Client Component)
"use client";
export function InvoiceRow({ invoice }: { invoice: Invoice }) {
  return (
    <tr>
      <td>{invoice.id}</td>
      <td>
        <SendReminderButton invoiceId={invoice.id} />
      </td>
    </tr>
  );
}
```

---

## 2. Component structure

### 2.1 File layout

| Item | Convention |
|---|---|
| Component file | `PascalCase.tsx`, one component per file |
| Component test | Same name, `.test.tsx` suffix, co-located |
| Component-specific types | At the top of the component file, or in a `*.types.ts` sibling |
| Component-specific styles | Tailwind classes in the component file; no separate CSS file unless using CSS Modules |

### 2.2 Component organization

A typical component file:

```tsx
// app/(admin)/invoices/_components/SendReminderButton.tsx

"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { triggerManualReminder } from "@/lib/api/reminders";

type SendReminderButtonProps = {
  invoiceId: string;
  onSent?: (lastReminderSentAt: string) => void;
};

export function SendReminderButton({ invoiceId, onSent }: SendReminderButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  async function handleClick() {
    setIsLoading(true);
    try {
      const result = await triggerManualReminder(invoiceId);
      onSent?.(result.lastReminderSentAt);
      toast({ title: "Reminder sent", variant: "success" });
    } catch (error) {
      toast({
        title: "Could not send reminder",
        description: getUserFacingMessage(error),
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
    >
      {isLoading ? "Sending..." : "Send reminder"}
    </Button>
  );
}
```

**Notable rules:**

- Props type defined at the top, named `<ComponentName>Props`
- One exported component per file, named
- `useState`, then handler functions, then JSX
- Accessibility attributes (`aria-busy`) included in the button
- User-facing error message comes from a mapping function, not from the raw error

### 2.3 Presentational vs. container

The split is informal but useful:

- **Presentational components** take props, render markup, fire callbacks. No data fetching, no state management beyond UI state.
- **Container components** (pages, route segments, top-level feature components) fetch data, manage state, and pass props down.

Don't enforce a strict split with naming conventions; use the distinction as a guide.

---

## 3. State management

The team uses a layered approach:

| State type | Tool | Use when |
|---|---|---|
| Server state | React Query (TanStack Query) | Data fetched from the backend, cached, may need refetching or mutation |
| Local UI state | `useState`, `useReducer` | State that lives in one component (toggles, form values, loading flags) |
| URL state | Next.js search params and routing | Filters, pagination, sort order — anything that should be shareable via URL |
| Cross-component client state | React Context (sparingly) | Theme, authenticated user, feature flags — things many components read |

**Rules:**

- **Don't put server state in `useState`.** Use React Query for caching, invalidation, and refetching.
- **Don't put URL-shareable state in `useState`.** If a user should be able to refresh and see the same view, the state belongs in the URL.
- **Don't reach for Context unless many components need the value.** Prop-drilling through two or three levels is fine; Context is for genuinely cross-cutting state.
- **Don't bring in Redux, Zustand, or Jotai without a specific reason.** The defaults above cover most needs.

### 3.1 React Query patterns

```tsx
// Fetching
const { data, isLoading, error } = useQuery({
  queryKey: ["invoices", { status: "overdue" }],
  queryFn: () => fetchInvoices({ status: "overdue" }),
});

// Mutating
const queryClient = useQueryClient();
const mutation = useMutation({
  mutationFn: triggerManualReminder,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["invoices"] });
  },
});
```

Query keys are arrays starting with a stable string identifier, then any filter/parameter objects. This makes invalidation predictable.

---

## 4. Data fetching

### 4.1 Server-side fetching (Server Components)

Fetch directly from the database via repository or service modules, not via the project's own API:

```tsx
// Good — directly call into services
export default async function InvoicesPage() {
  const session = await getServerSession();
  const invoices = await listInvoices({ tenantId: session.tenantId });
  return <InvoiceList invoices={invoices} />;
}

// Avoid — fetching from your own API in a Server Component
export default async function InvoicesPage() {
  const res = await fetch(`${process.env.API_URL}/invoices`);
  const invoices = await res.json();
  return <InvoiceList invoices={invoices} />;
}
```

The exception is when the API call enforces logic that the service alone doesn't (e.g., rate limiting handled at the route).

### 4.2 Client-side fetching (Client Components)

Use React Query. Every client-side fetch goes through a function that handles the request shape, sets the right headers, and parses the response:

```typescript
// lib/api/reminders.ts
export async function triggerManualReminder(invoiceId: string) {
  const response = await fetch(`/api/admin/invoices/${invoiceId}/remind`, {
    method: "POST",
  });
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return TriggerManualReminderResponseSchema.parse(await response.json());
}
```

Notice the Zod schema validates the response — the same schema the backend uses for its response shape. This catches contract drift at runtime.

---

## 5. Forms

### 5.1 Library

Use **React Hook Form** for form state management. Use **Zod** for validation, with schemas shared with the backend where possible.

### 5.2 Pattern

```tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { CreateReminderRequestSchema, type CreateReminderRequest } from "@/schemas/reminder.schema";

export function CreateReminderForm({ onSubmit }: { onSubmit: (values: CreateReminderRequest) => Promise<void> }) {
  const form = useForm<CreateReminderRequest>({
    resolver: zodResolver(CreateReminderRequestSchema),
    defaultValues: {
      message: "",
    },
  });

  async function handleSubmit(values: CreateReminderRequest) {
    try {
      await onSubmit(values);
    } catch (error) {
      form.setError("root", { message: getUserFacingMessage(error) });
    }
  }

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} aria-label="Send custom reminder">
      <label htmlFor="message">
        Message
      </label>
      <textarea
        id="message"
        {...form.register("message")}
        aria-invalid={!!form.formState.errors.message}
        aria-describedby={form.formState.errors.message ? "message-error" : undefined}
      />
      {form.formState.errors.message && (
        <p id="message-error" role="alert">
          {form.formState.errors.message.message}
        </p>
      )}

      {form.formState.errors.root && (
        <p role="alert">{form.formState.errors.root.message}</p>
      )}

      <Button type="submit" disabled={form.formState.isSubmitting}>
        Send
      </Button>
    </form>
  );
}
```

**Notable rules:**

- Every form input has a `<label>` with a matching `htmlFor`
- Validation errors are connected to inputs via `aria-describedby` and announced with `role="alert"`
- The form itself has an `aria-label` if its purpose isn't clear from context
- Submit button is disabled during submission to prevent double-submit
- Errors thrown from the submit handler are displayed at the form root

---

## 6. Accessibility

**Target: WCAG 2.2 AA across all UI.** Not a stretch goal; the baseline.

### 6.1 Required practices

- Every interactive element is reachable by keyboard
- Every interactive element has a visible focus indicator (don't remove the default outline without replacing it)
- Every form input has a label (visible or via `aria-label`)
- Color is never the only signal (use icons or text alongside red/green status)
- Contrast ratios meet WCAG 2.2 AA (4.5:1 for body text, 3:1 for large text and UI components)
- Page has a logical heading hierarchy (one `<h1>`, then `<h2>` and below, no skipping levels for styling)
- Images have `alt` text (descriptive for content images, empty `alt=""` for decorative)

### 6.2 Keyboard navigation

- `Tab` moves between interactive elements
- `Enter` / `Space` activates buttons and form controls
- `Escape` closes modals, dropdowns, popovers
- Arrow keys move within menus, lists, and date pickers (use a library that handles this — don't reinvent it)
- Focus is trapped within open modals (focus cannot Tab outside)
- Focus returns to the trigger element when a modal closes

### 6.3 Focus management

- When a modal opens, focus moves to the first interactive element inside
- When a modal closes, focus returns to the element that triggered it
- When form validation fails, focus moves to the first invalid field
- Skip links exist for repetitive navigation ("Skip to main content")

### 6.4 ARIA usage

The rule: **no ARIA is better than wrong ARIA.** Use semantic HTML first; reach for ARIA only when HTML can't express the meaning.

- Buttons are `<button>`, not `<div onClick>`
- Links are `<a>`, not `<button>` with a redirect
- Lists are `<ul>` or `<ol>`, not divs
- `aria-label` only when the visible label is missing
- `aria-describedby` for error messages and help text
- `aria-live="polite"` for status announcements (e.g., "5 reminders sent")
- `aria-busy="true"` on elements that are loading

### 6.5 Forbidden patterns

- `<div onClick>` and `<span onClick>` for interactions — use buttons
- Removing focus indicators without replacing them
- Tooltips as the only way to label an icon button (icon buttons must have an accessible name)
- Auto-focusing on page load (annoys screen reader users)
- Form fields without labels
- Modals without focus management
- Color as the only signal of state

### 6.6 Testing accessibility

- Use Testing Library queries that mirror assistive technology (`getByRole`, `getByLabelText`) over implementation-detail queries (`getByTestId`)
- Use `axe-core` (via `@axe-core/playwright` for e2e, `jest-axe` for unit/integration) in tests
- Manually test keyboard navigation for any new interactive component
- Manually test with a screen reader for any complex UI (VoiceOver on macOS, NVDA on Windows)

---

## 7. Styling

### 7.1 Tailwind CSS

The team uses Tailwind for styling. Rules:

- Use Tailwind utilities for almost everything
- Use Tailwind's design tokens (spacing scale, color palette, font sizes) rather than arbitrary values
- Group classes consistently: layout → spacing → typography → color → effects (a Prettier plugin enforces this)
- For repeated patterns, extract a component, not a Tailwind preset class

### 7.2 When to use CSS Modules

Reach for CSS Modules only when:

- You need a complex selector Tailwind can't express (`:has`, animations)
- You're integrating a third-party library that expects specific classes
- You're animating with `@keyframes`

### 7.3 Design tokens

Design tokens live in `tailwind.config.ts`. Don't hardcode colors, spacing, or font sizes in component files. If a token doesn't exist for what you need, propose adding it to the config rather than overriding it inline.

### 7.4 Responsive design

- Mobile-first: write base styles for mobile, add `sm:`, `md:`, `lg:` prefixes for larger viewports
- Test all new UI at three sizes: 375px, 768px, 1280px
- Avoid horizontal scroll on mobile

### 7.5 Dark mode

If the app supports dark mode, every new component supports it via Tailwind's `dark:` variants. Use the design system's color tokens rather than hardcoded values.

---

## 8. Routing (Next.js App Router)

### 8.1 Folder structure

```
app/
├── (auth)/               # Route group: shared layout for login/signup
│   ├── login/
│   └── signup/
├── (admin)/              # Route group: admin-only routes with shared layout
│   ├── layout.tsx        # Layout that enforces admin auth
│   ├── invoices/
│   │   ├── page.tsx
│   │   ├── _components/  # Private folder: not routable
│   │   └── [id]/
│   │       └── page.tsx
│   └── settings/
├── api/                  # API route handlers (backend)
└── page.tsx              # Public home page
```

**Conventions:**

- **Route groups** `(name)` for shared layouts without affecting URLs
- **Private folders** `_name` for component files that aren't routable
- **Dynamic segments** `[name]` for variable URL parts
- One `page.tsx` per route, the entry point

### 8.2 Layouts

- Use layouts for shared UI (navigation, headers) and shared auth gating
- Don't put data fetching in layouts unless every child page needs the data
- A layout that gates access (e.g., admin layout) verifies the session and redirects if missing

### 8.3 Loading and error UI

- `loading.tsx` next to a route shows during async data fetching for that route
- `error.tsx` catches errors thrown during render and shows a recovery UI
- `not-found.tsx` shows when `notFound()` is called

Use these consistently. Every route that fetches data has a `loading.tsx`; every route that can fail has an `error.tsx`.

### 8.4 Parallel and intercepted routes

Reach for parallel routes (`@slot`) and intercepted routes (`(.)`) only when the use case genuinely needs them. They are powerful but increase the complexity of the routing model. Most features don't need them.

---

## 9. Error handling on the client

### 9.1 Never display raw API errors to end users

API error responses contain identifiers like `"tenant_mismatch"` or `"invoice_not_found"`. These are not user-facing messages. Map them through a function:

```typescript
// lib/error-messages.ts
const ERROR_MESSAGES: Record<string, string> = {
  tenant_mismatch: "You don't have permission to act on this invoice.",
  invoice_not_found: "The invoice could not be found.",
  reminder_already_sent_in_window: "A reminder was already sent recently. Please wait before sending another.",
};

export function getUserFacingMessage(error: unknown): string {
  if (error instanceof ApiError && error.code in ERROR_MESSAGES) {
    return ERROR_MESSAGES[error.code];
  }
  return "Something went wrong. Please try again.";
}
```

### 9.2 The generic fallback

Any unknown error returns the generic message. Never display:

- The error's raw message
- A stack trace
- The error's internal code or technical details

These belong in error tracking (Sentry, error monitoring service), not in the UI.

### 9.3 Error boundaries

Every page has an `error.tsx` boundary. Critical flows (checkout, settings, anything with unsaved data) may have additional boundaries scoped to a component subtree so a single failure doesn't lose the user's work.

---

## 10. Component testing

What to test, what not to test — the headline rules. The depth of testing belongs in `testing-conventions.md`.

### 10.1 What to test

- Visible states (loading, error, empty, success)
- User interactions (clicks, form submissions, keyboard navigation)
- Accessibility queries (the component is reachable via `getByRole`, `getByLabelText`)
- Error handling (the component handles a thrown error from a prop callback)

### 10.2 What not to test

- Implementation details (internal state names, the specific structure of JSX)
- Framework code (Next.js routing, React Query caching)
- Third-party library internals (you're not testing React Hook Form's validation engine)

### 10.3 Tools

- Vitest + Testing Library for unit and component tests
- Playwright for end-to-end tests across the full app
- `jest-axe` or `@axe-core/playwright` for automated accessibility checks

---

## 11. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

- If components keep coming back with accessibility issues, section 6 needs concrete examples for the specific failure pattern (e.g., a modal without focus management — show the right pattern).
- If forms keep coming back without proper labels or error association, section 5's example is the lever.
- If components keep doing data fetching the wrong way, sections 1 and 4 need sharper examples — particularly the Server Component vs. Client Component decision.
- This file should stay under three pages of dense content. Detail beyond that belongs in the example frontend feature file.