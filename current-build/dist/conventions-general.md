# General Conventions

> **Location:** `js-saas-factory-knowledge/conventions/general-conventions.md`
>
> **Purpose:** Cross-cutting rules that apply to every part of the codebase, regardless of layer. The standards everything else assumes.
>
> **Audience:** Every Project in the chain.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

This file contains rules. Each rule is one or two sentences with a concrete example. If you find yourself writing a paragraph to justify a rule, the justification belongs in onboarding docs — not here.

The Validator reads this file at Gate 3 and will flag deviations. Keep the rules concrete enough that a deviation is unambiguous.

---

## 1. File and folder naming

| Item | Convention | Example |
|---|---|---|
| Source files (non-React) | `kebab-case.ts` | `send-overdue-reminder.ts` |
| React components | `PascalCase.tsx` | `InvoiceReminderButton.tsx` |
| Test files | Same name as the file they test, with `.test.ts` or `.test.tsx` | `send-overdue-reminder.test.ts` |
| Folders | `kebab-case` | `services/invoice-reminders/` |
| Constants files | `kebab-case.ts` | `error-codes.ts` |
| Type-only files | `kebab-case.types.ts` | `invoice.types.ts` |
| Zod schema files | `kebab-case.schema.ts` | `create-reminder.schema.ts` |
| Configuration files | Tool-specific defaults (`.eslintrc.json`, `prisma/schema.prisma`) | n/a |

**Plural vs. singular for folder names:** plural for collections of related items (`services/`, `components/`, `hooks/`), singular for single-purpose folders (`prisma/`, `public/`). When in doubt, plural.

**Index files:** allowed for re-exporting from a folder; required when external consumers should import from the folder root. Forbidden for re-exporting unrelated items just to reduce import lines.

---

## 2. Import order

Imports are grouped, with one blank line between groups, in this order:

1. External packages (`react`, `zod`, `@prisma/client`)
2. Internal absolute imports (paths starting with `@/`)
3. Relative imports (paths starting with `.` or `..`)
4. Type-only imports (separated from value imports using `import type`)

ESLint's `import/order` rule enforces this; the linter is the source of truth, not human memory.

```typescript
// Good
import { useState } from "react";
import { z } from "zod";

import { logger } from "@/lib/logger";
import { sendEmail } from "@/services/email";

import { formatReminder } from "./format-reminder";

import type { Invoice } from "@/types/invoice";
```

---

## 3. Commit message format

Commits follow **Conventional Commits**: `<type>(<scope>): <description>`.

| Type | When to use |
|---|---|
| `feat` | A new feature visible to users |
| `fix` | A bug fix |
| `refactor` | Code change with no behavior change |
| `test` | Adding or correcting tests |
| `docs` | Documentation only |
| `chore` | Tooling, configuration, dependencies |
| `perf` | Performance improvement |

**Scope** is optional but recommended; use the area of the codebase (`reminders`, `auth`, `db`).

**Description** is imperative, lowercase, no period: `feat(reminders): add manual trigger endpoint`, not `Added a manual trigger endpoint.`.

**Body** (optional) explains *why*, not *what*. The diff shows the *what*.

**Breaking changes** are marked with `!` after the type and a `BREAKING CHANGE:` footer.

---

## 4. Branch naming

| Branch type | Pattern | Example |
|---|---|---|
| Feature | `feature/<short-description>` | `feature/invoice-reminders` |
| Bug fix | `fix/<short-description>` | `fix/reminder-tenant-check` |
| Hotfix | `hotfix/<short-description>` | `hotfix/auth-callback-url` |
| Chore | `chore/<short-description>` | `chore/upgrade-prisma` |
| Spike / experiment | `spike/<short-description>` | `spike/biome-evaluation` |

Use the same short description across the branch name, the per-feature folder name, and the PR title where possible. Consistency makes the audit trail easier to follow.

---

## 5. Pull request shape

**Title:** matches the commit message format for the most representative commit in the PR.

**Description template:**

```markdown
## What
One-paragraph summary of what changed.

## Why
The business or technical reason. Link to the user story file:
`features/<YYYY-MM-DD-name>/02-story.md`.

## How
The approach taken. Link to the spec file:
`features/<YYYY-MM-DD-name>/03-spec.md`.

## Testing
What was tested and how. Link to the test report:
`features/<YYYY-MM-DD-name>/06-test-report.md`.

## Validator findings
Critical/important findings that were resolved. Link to:
`features/<YYYY-MM-DD-name>/07-validation.md`.

## Risks
Anything reviewers should be cautious about.
```

**Size expectations:** one feature = one PR. A PR that touches more than one feature's worth of code is too large; split it. PRs over 500 lines (excluding tests and generated code) get extra scrutiny.

**Draft vs. ready:** open as draft while the chain is running; mark ready for review only after Gate 3 validation comes back clean.

---

## 6. Secrets handling

**What counts as a secret:** API keys, database connection strings, OAuth client secrets, signing keys, webhook secrets, encryption keys, third-party tokens, anything labelled "secret" by its provider.

**Where secrets live:**

- Local development: `.env.local` (git-ignored)
- Production: the deployment platform's secrets manager
- Shared with teammates: the team's password manager or secrets-sharing tool

**What is forbidden:**

- Committed `.env` files with real values (`.env.example` with placeholders only)
- Hard-coded secrets anywhere in source code, including comments
- Secrets in logs (see `backend-conventions.md` for what gets logged)
- Secrets in client-side bundles (anything in `process.env` that doesn't start with `NEXT_PUBLIC_` should never reach the client)
- Sharing secrets via email, Slack, or chat history

The pre-commit hook should block commits that contain anything matching common secret patterns. The Validator should flag any committed secret as **CRITICAL**.

---

## 7. Comments

**When comments are required:**

- Explaining *why* code does something non-obvious (the *what* is in the code itself)
- TODO markers with a ticket reference and the writer's initials: `// TODO(QU-123): handle the rate-limit case`
- Public API documentation using JSDoc/TSDoc for exported functions, types, and modules
- Workarounds for known bugs in dependencies, with a link to the upstream issue
- Anything that would surprise a future reader

**When comments are discouraged:**

- Restating what the code says (`// increment counter` above `counter++`)
- Commented-out code (delete it; git history preserves it)
- Stale comments that no longer match the code (delete or update — never leave)
- Author tags (`// Created by X on Y`) — git blame handles this

**A good comment:**

```typescript
// We dedupe on lastReminderSentAt rather than a separate sent_reminders table
// because the same reminder window can be triggered multiple times by retries
// and we need atomic check-and-set semantics. The unique index on
// (invoice_id, reminder_window_start) enforces this at the DB level.
```

**A bad comment:**

```typescript
// Send the email
await sendEmail(invoice);
```

---

## 8. The no-go list

Patterns the team has explicitly chosen not to use. These appear here so the chain doesn't propose them and so reviewers know to flag them.

| Pattern | Reason |
|---|---|
| `any` type | Indicates the type system has been bypassed. Use `unknown` and narrow explicitly. |
| Non-null assertions (`!`) | Same reason. If you know the value is non-null, prove it with a guard. |
| Default exports (except where required) | Named exports are the rule. Default exports are allowed only where Next.js requires them. |
| `console.log` in committed code | Use the Pino logger. `console.log` is a debugging tool, not a logging tool. |
| Commented-out code | Delete it. Git history preserves it. |
| `// @ts-ignore` and `// @ts-expect-error` without an explanation | If you must suppress a type error, comment immediately above with the reason. |
| Force-pushing to shared branches | Force-push is allowed only on your own feature branches. Never on `main` or release branches. |
| Direct commits to `main` | All changes go through PR review. |
| Magic numbers and strings | Extract to a named constant. The exception is genuinely-obvious values like `0`, `1`, `""`. |
| Long imports of single utilities (`import { camelCase, kebabCase, ... } from 'lodash'`) | Either use native methods or import single utilities (`lodash.camelCase`). |
| Mutating function arguments | Treat arguments as read-only. Return a new value instead. |
| Synchronous file I/O in request handlers | Use the async versions. Synchronous I/O blocks the event loop. |

This list grows as the team makes more decisions. Add entries whenever a chain run produces something you don't want to see again.

---

## 9. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

- If the chain keeps producing code in shapes you don't like, the rules here may be too vague. Add a specific example to the offending rule.
- If reviewers keep catching the same kind of issue, that issue belongs in the no-go list.
- Don't let this file sprawl past two pages. Rules that are too detailed for here belong in `js-conventions.md`, `backend-conventions.md`, or `frontend-conventions.md`.