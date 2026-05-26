# JavaScript / TypeScript Conventions

> **Location:** `js-saas-factory-knowledge/conventions/js-conventions.md`
>
> **Purpose:** JavaScript and TypeScript specific rules — language features, configuration, tooling settings. The rules that don't fit in `general-conventions.md` because they're language-specific.
>
> **Audience:** Researcher, Spec Writer, Backend Builder, Frontend Builder, Test, Validate, Documentation, Package.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

This file defines how TypeScript is written and how the toolchain is configured. The conventions here apply to every JavaScript/TypeScript file in the codebase, regardless of whether it's backend, frontend, or test code.

When a topic could live here or in `general-conventions.md`, it lives here if it's language-specific (`any` is banned, types over interfaces) and there if it's cross-cutting (file naming, commit format).

---

## 1. TypeScript configuration

The project's `tsconfig.json` enforces these settings non-negotiably. The Validator should flag any drift from this baseline.

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true,
    "verbatimModuleSyntax": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "incremental": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

**Notable choices:**

- `strict: true` is non-negotiable. Disabling it is forbidden.
- `noUncheckedIndexedAccess: true` makes array access return `T | undefined`. This catches a class of runtime errors at compile time. It is a small productivity hit and a large safety win.
- `exactOptionalPropertyTypes: true` treats `{ x?: string }` and `{ x: string | undefined }` as different types. Use the right one for your meaning.
- `paths: { "@/*": ["./src/*"] }` is the absolute-import alias. Use it in all source code; relative imports are for in-folder references only.

If a new TypeScript major version changes the recommended flags, update this file as part of the stack review (see `target-stack-spec.md`).

---

## 2. Type style

### 2.1 Types over interfaces

Use `type` aliases for new type definitions:

```typescript
// Good
type Invoice = {
  id: string;
  amount: number;
  status: "pending" | "paid" | "overdue";
};

// Bad (without a specific reason)
interface Invoice {
  id: string;
  amount: number;
  status: "pending" | "paid" | "overdue";
}
```

**Use `interface` only when you need:**

- Declaration merging (extending a library's interface)
- Class implementations (`class X implements I`)
- An object that consumers will extend with their own properties

If neither applies, use `type`.

### 2.2 Naming

| Item | Convention | Example |
|---|---|---|
| Types | `PascalCase` | `Invoice`, `ReminderStatus` |
| Type parameters (generics) | `PascalCase`, descriptive when possible | `TItem`, `TResult`, `TError`, not `T1`/`T2` |
| Enums | `PascalCase` for the name, `SCREAMING_SNAKE_CASE` for members (when enums are used at all) | `ReminderStatus.SENT` |

**Prefer string literal unions over enums.** Enums add runtime overhead and have unusual semantics in TypeScript. String unions are simpler and type-check the same way:

```typescript
// Good
type ReminderStatus = "pending" | "sent" | "failed";

// Avoid (without a specific reason)
enum ReminderStatus {
  Pending = "pending",
  Sent = "sent",
  Failed = "failed",
}
```

### 2.3 Forbidden type patterns

| Pattern | Why it's banned | Use instead |
|---|---|---|
| `any` | Bypasses type checking entirely | `unknown` with narrowing |
| Non-null assertion (`!`) | Asserts without proving | A guard (`if (x)`) or a typed accessor |
| `as` casts | Same as `!` but for types | `satisfies` for literal validation; narrowing for runtime types |
| `// @ts-ignore` | Silently suppresses errors | `// @ts-expect-error` with a comment explaining why, or fix the type |
| `Function` and `Object` types | Too broad to be useful | A specific function signature or `Record<string, unknown>` |

The `satisfies` operator is the right tool for "I want to check that this object conforms to a type without losing the literal type":

```typescript
// Good
const config = {
  apiUrl: "https://api.example.com",
  timeout: 5000,
} satisfies AppConfig;
// `config.apiUrl` is still typed as the literal, not as `string`.

// Avoid
const config: AppConfig = {
  apiUrl: "https://api.example.com",
  timeout: 5000,
};
// Loses the literal type.
```

### 2.4 Working with `unknown`

When you receive data from outside the type system (JSON, env vars, third-party APIs without types), the type is `unknown`. Narrow with Zod or with a type predicate:

```typescript
// Good: narrow with Zod at the boundary
const InvoiceSchema = z.object({ id: z.string(), amount: z.number() });
const parsed = InvoiceSchema.parse(rawJson);
// `parsed` is typed.

// Good: type predicate
function isInvoice(x: unknown): x is Invoice {
  return typeof x === "object" && x !== null && "id" in x && "amount" in x;
}

// Bad
const invoice = rawJson as Invoice;
// No runtime check; trusts the source.
```

---

## 3. Error handling

### 3.1 Thrown errors with custom classes

Use thrown errors for known failure modes. Define custom error classes that extend `Error`:

```typescript
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
```

The route handler maps these to HTTP responses (see `backend-conventions.md`).

### 3.2 What never appears in error messages

- PHI of any kind
- Secrets (API keys, tokens, connection strings)
- Stack traces visible to end users
- Full request payloads
- Internal file paths

The user-facing error message is generic and safe. The internal log captures the detail.

### 3.3 Result types are an option, not the default

Result types (`{ ok: true, value: T } | { ok: false, error: E }`) are useful when:

- The failure case is part of the normal flow (not exceptional)
- The caller is expected to handle both outcomes explicitly
- You're writing a pure function with no side effects

For service-layer code with side effects, prefer thrown errors. Mixing both patterns in one codebase creates inconsistency; pick a default (thrown errors) and use the other only when it clearly fits.

---

## 4. Async style

### 4.1 Async / await throughout

Prefer `async/await` over `.then()` chains. The exception is when you specifically need the parallel behavior of `Promise.all`:

```typescript
// Good
const invoice = await getInvoice(id);
const customer = await getCustomer(invoice.customerId);

// Good (parallel)
const [invoice, customer] = await Promise.all([
  getInvoice(id),
  getCustomer(customerId),
]);

// Avoid
return getInvoice(id).then((invoice) => {
  return getCustomer(invoice.customerId).then((customer) => {
    return { invoice, customer };
  });
});
```

### 4.2 Top-level await

Top-level `await` is allowed in ESM modules. Use it for initialization that must complete before the module is usable.

### 4.3 Never use callback-style APIs in new code

Wrap any callback-style API in a promise at the boundary. If a library has both callback and promise versions, use the promise version.

```typescript
// Good
import { readFile } from "node:fs/promises";
const data = await readFile(path, "utf-8");

// Avoid
import { readFile } from "node:fs";
readFile(path, "utf-8", (err, data) => {
  /* ... */
});
```

---

## 5. Module organization

### 5.1 Named exports only

Use named exports for everything except where Next.js requires a default export (pages, layouts, route handlers, error boundaries, loading components, not-found components).

```typescript
// Good
export function sendReminder(invoice: Invoice) { /* ... */ }
export const REMINDER_WINDOW_DAYS = 7;
export type ReminderResult = { /* ... */ };

// Bad (without a Next.js-imposed reason)
export default function sendReminder(invoice: Invoice) { /* ... */ }
```

Named exports give consistent import names across the codebase. Default exports let consumers rename freely, which fragments the codebase's vocabulary.

### 5.2 One concept per file

A file exports one primary thing (a function, a class, a component, a type) and optionally its supporting types and constants. If a file grows multiple unrelated concerns, split it.

### 5.3 Barrel files

Index files that re-export from a folder are allowed when the folder represents a coherent public API. They're not a substitute for organizing your imports.

```typescript
// Good: services/reminders/index.ts
export { sendOverdueReminder } from "./send-overdue-reminder";
export { triggerManualReminder } from "./trigger-manual-reminder";
export type { ReminderResult } from "./types";

// Bad: a barrel that re-exports everything in the folder, including
// internal helpers consumers shouldn't reach for
```

### 5.4 Deep imports vs. surface imports

When a folder has a barrel index file, prefer importing from the folder root over reaching into specific files. This makes refactoring easier — internal files can move without breaking consumers.

```typescript
// Good
import { sendOverdueReminder } from "@/services/reminders";

// Avoid
import { sendOverdueReminder } from "@/services/reminders/send-overdue-reminder";
```

---

## 6. ESLint configuration

The project uses ESLint 9 with flat config. The baseline ruleset:

```typescript
// eslint.config.js
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import importPlugin from "eslint-plugin-import";

export default [
  js.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  importPlugin.flatConfigs.recommended,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-non-null-assertion": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }
      ],
      "import/order": [
        "error",
        {
          groups: ["external", "internal", "parent", "sibling"],
          "newlines-between": "always"
        }
      ],
      "no-console": ["error", { allow: ["warn", "error"] }]
    }
  }
];
```

**Rules turned on that are not in the default `recommended-type-checked`:**

- `no-explicit-any` — bans `any`
- `no-non-null-assertion` — bans `!`
- `consistent-type-imports` — requires `import type` for type-only imports
- `import/order` — enforces the import grouping rule
- `no-console` — only `console.warn` and `console.error` are allowed; `console.log` is banned (use the Pino logger)

If a rule needs to be disabled for a single line, use an inline comment with an explanation:

```typescript
// eslint-disable-next-line @typescript-eslint/no-non-null-assertion -- value is checked above
const next = items[0]!;
```

Inline disables without an explanation should be flagged by the Validator.

---

## 7. Prettier configuration

```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

Prettier is the source of truth for formatting. Don't argue with it; if you don't like a default, change the config rather than fighting it per-file.

---

## 8. Package.json scripts

Every project's `package.json` has at minimum these scripts:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "typecheck": "tsc --noEmit",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check ."
  }
}
```

The Package Project will derive variants of these based on the produced code, but every project should support these as the canonical commands. CI, the build script, and developer onboarding all assume them.

---

## 9. Common pitfalls

A list of patterns the chain occasionally produces that look reasonable but cause problems. Catching them at code review prevents them from spreading.

| Pitfall | Why it's a problem | Fix |
|---|---|---|
| `Date.now()` for ordering across processes | Clock skew between machines | Use a database-side timestamp or a monotonic ID |
| `Promise.all` with side effects that should be sequential | Races, unpredictable order | Use `for...of` with `await` |
| `JSON.stringify` for deep equality | Property order is not stable | Use a deep-equal helper or compare specific fields |
| Mutating function arguments | Surprises callers | Return a new object |
| Catching errors and ignoring them | Hides real failures | Either handle the error or let it propagate |
| `try/catch` without specific error matching | Catches more than intended | Narrow with `instanceof` checks |
| Awaiting in a loop when parallel would do | Slow | `Promise.all` for independent operations |

---

## 10. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

- If Builders keep producing code that compiles but doesn't match your taste, the gap is in the unwritten style rules. Capture them here as specific examples.
- If the linter is consistently warning about something that turns out to be a real bug, consider escalating the rule from warning to error.
- Don't let this file sprawl past three pages. Patterns specific to backend or frontend belong in their respective files.