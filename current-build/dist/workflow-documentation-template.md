# Documentation Template

> **Location:** `js-saas-factory-knowledge/workflow/documentation-template.md`
>
> **Purpose:** The shape, tone, and audience for each of the five documentation outputs the Documentation Project produces. Defines what good documentation looks like for this codebase.
>
> **Audience:** Documentation.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

The Documentation Project reads this file at the start of every conversation. It produces five distinct documents, each with a different audience, voice, and structure. This file defines all five.

The single hardest property of documentation work is **writing for five audiences in one conversation**. The Documentation Project must shift voice between technical reference and plain-language guide; the templates here keep that shift explicit.

This file pairs with:

- `08-documentation.md` (the role file)
- `examples/example-backend-feature.md` (source of API contract content)
- `examples/example-frontend-feature.md` (source of UI flow content)

---

## 1. The five documents

| File | Audience | Voice | Length |
|---|---|---|---|
| `README.md` | Any developer picking up the codebase | Technical, friendly | 1 page |
| `docs/api.md` | A developer integrating with or extending the API | Precise technical reference | Varies by surface area |
| `docs/user-guide.md` | A non-developer using the feature (admin, customer success) | Plain language, no jargon | Varies by feature complexity |
| `docs/architecture.md` | A maintainer modifying or debugging the feature in 6 months | Precise technical, decision-record style | 1–2 pages |
| `CHANGELOG.md` entry | Any reader of release notes | Action-oriented, user-facing | 1–3 lines |

Each document is produced as its own artifact in the Documentation Project's response, so the user can download them individually.

---

## 2. README.md

### 2.1 Audience and voice

Written for a developer who has just cloned the repository for the first time. Assumes they know JavaScript and TypeScript but does not assume they know this specific project.

**Voice:** technical but friendly. Uses second person ("Run `pnpm install`"). Avoids jargon-for-jargon's-sake.

### 2.2 Required structure

```markdown
# <Project Name>

One paragraph describing what the project is and what it does. Two
sentences minimum; four sentences maximum. A reader should know after
this paragraph whether the project is relevant to them.

## Stack

- Runtime: Node.js 22 LTS
- Language: TypeScript 5.x (strict)
- Framework: Next.js 15 (App Router)
- Database: PostgreSQL via Prisma
- ... (pulled verbatim from `target-stack-spec.md`)

## Prerequisites

- Node.js 22 LTS (use `nvm` or `fnm`)
- pnpm 9.x
- PostgreSQL 16+ (locally via Docker, or a managed dev instance)
- Redis 7.x (only if background jobs are used)

## Setup

```bash
# Clone the repository
git clone <repository-url>
cd <project-folder>

# Install dependencies
pnpm install

# Set up environment variables
cp .env.example .env.local
# Then edit .env.local with real values

# Start the database
docker compose up -d db

# Run migrations
pnpm exec prisma migrate dev

# Start the dev server
pnpm dev
```

The dev server runs at http://localhost:3000.

## Running tests

```bash
pnpm test              # unit + integration + acceptance
pnpm test:e2e          # end-to-end via Playwright
pnpm typecheck         # TypeScript check
pnpm lint              # ESLint
```

## Building for production

```bash
pnpm build
pnpm start
```

## Folder structure

```
src/
  app/               Next.js App Router pages and API routes
  components/        Shared UI components
  lib/               Cross-cutting utilities
  schemas/           Zod schemas shared between backend and frontend
  services/          Backend business logic
  repositories/      Database access
  workers/           Background jobs (BullMQ)
prisma/              Database schema and migrations
e2e/                 Playwright end-to-end tests
test/                Test infrastructure (builders, helpers)
docs/                Project documentation
```

## Documentation

- [API reference](./docs/api.md)
- [User guide](./docs/user-guide.md)
- [Architecture overview](./docs/architecture.md)

## License

<license placeholder>
```

### 2.3 What good looks like

- **The setup steps actually work.** Someone running them in a clean environment can get to a running dev server in 15 minutes.
- **Commands match `package.json`.** Don't invent command names; pull them from the actual scripts.
- **Folder structure is one line per top-level folder.** Not exhaustive — just enough orientation that a reader knows where to look next.

### 2.4 Common voice mistakes

- ❌ "Welcome to this exciting project!" — too marketing-flavored
- ❌ "Simply run `pnpm install`" — "simply" implies it's trivial; if it is, the reader will find out
- ❌ "This codebase uses cutting-edge React 19 features..." — readers don't need to know what's cutting-edge

The README is reference, not marketing. Match the tone of the Node.js or React documentation, not a launch announcement.

---

## 3. docs/api.md

### 3.1 Audience and voice

Written for a developer integrating with the API — either internally (a frontend developer who didn't write the backend) or externally (a partner system, an internal tool team).

**Voice:** precise, technical, terse. No filler words. Schemas are authoritative.

### 3.2 Required structure

```markdown
# API Reference

Base URL: `https://<your-deployment-url>`

All endpoints require authentication unless noted. Authentication uses
[describe the auth scheme — typically session cookies or bearer tokens].

## Errors

Errors return a JSON body with a stable `error` field:

```json
{ "error": "stable_identifier" }
```

Common error identifiers across endpoints:
- `unauthenticated` (401) — no valid session
- `forbidden` (403) — session lacks required permissions
- `invalid_input` (400) — request body or params failed validation
- `internal_error` (500) — unexpected server error

Endpoint-specific errors are documented per endpoint below.

## Endpoints

### POST /api/admin/invoices/:id/remind

Manually trigger an invoice reminder.

**Auth:** Admin role required in the invoice's tenant.

**Path parameters:**

| Parameter | Type | Notes |
|---|---|---|
| `id` | string (UUID) | Invoice ID |

**Request body:** none

**Success response (200):**

```json
{
  "success": true,
  "lastReminderSentAt": "2026-05-26T14:32:11.000Z"
}
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| 401 | `{ "error": "unauthenticated" }` | No valid session |
| 404 | `{ "error": "invoice_not_found" }` | Invoice does not exist, or exists in a different tenant |
| 409 | `{ "error": "invoice_not_eligible" }` | Invoice is not overdue (paid or cancelled) |
| 409 | `{ "error": "reminder_already_sent_in_window" }` | A reminder was sent in the last 24 hours |
| 500 | `{ "error": "internal_error" }` | Unexpected server error |

**Example:**

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Cookie: <session-cookie>" \
  https://example.com/api/admin/invoices/abc12345-.../remind
```
```

### 3.3 What good looks like

- **Every endpoint is documented identically.** Same headings, same column structure, same example format.
- **Schemas match the code exactly.** Pulled from the Backend Builder's summary verbatim. Never paraphrased.
- **Every status code that the route returns is listed.** Including the ones that "always apply" (401 for missing auth) — explicitness beats inheritance.
- **Examples use real-looking values, not lorem ipsum.** A UUID looks like a UUID; a timestamp looks like an ISO 8601 timestamp.

### 3.4 Common voice mistakes

- ❌ "This endpoint allows you to trigger a reminder for an invoice." — verbose; the heading already conveys the action
- ❌ "Returns the updated lastReminderSentAt." — the schema block is the source of truth; prose summaries get out of date
- ❌ "Please note that this requires an admin role." — drop "please note"; the **Auth** line is the place to say this

API docs are read by developers in a hurry. Every word should earn its place.

---

## 4. docs/user-guide.md

### 4.1 Audience and voice

Written for a non-developer using the feature. For the invoice reminders feature, this is an account admin — someone who manages billing for their tenant but is not a developer.

**Voice:** plain language. No framework names, no technical jargon, no implementation detail. Second person. Friendly but not chummy.

### 4.2 Required structure

```markdown
# Invoice reminders

This guide explains how invoice reminders work and how to use them
from the admin interface.

## What invoice reminders do

When an invoice is more than 7 days overdue, the system automatically
sends an email reminder to the customer. You can also send a reminder
manually for any specific overdue invoice.

Automatic reminders are sent once per day at 9:00 AM UTC. The system
will not send a duplicate reminder for the same invoice within 24
hours of the last one.

## Sending a reminder manually

1. Sign in to the admin interface.
2. Open the **Overdue invoices** page from the navigation menu.
3. Find the invoice you want to remind about.
4. Click **Send reminder** on that row.

You'll see a confirmation message at the top of the page. The
"Last reminder" column updates to show the timestamp.

If the reminder cannot be sent — for example, the invoice is already
paid, or a reminder was sent recently — you'll see an explanation
instead.

## Frequently asked questions

### Can a customer opt out of reminders?

Not currently. Opt-out is being considered for a future release.

### What does the customer see?

The customer receives an email reminding them of the overdue invoice
and the amount due. They can pay directly from a link in the email.

### What if the invoice is paid before the reminder goes out?

The system checks the invoice's status before sending. Paid and
cancelled invoices are never reminded, even if they were overdue
at some earlier point.

### Why is the "Send reminder" button greyed out for some invoices?

The button is unavailable when:
- The invoice is not overdue
- A reminder was sent in the last 24 hours
- The invoice has been paid or cancelled
```

### 4.3 What good looks like

- **Plain language throughout.** A customer success person can follow this guide without help.
- **The reader's perspective drives the structure.** The first thing the reader wants to know is "what does this feature do?" Not "what is its architecture?"
- **FAQ section answers questions the reader actually asks.** Real questions, not strawman questions invented to fill space.
- **Steps are numbered and atomic.** Each step is one action. No "click X and then do Y while also Z."

### 4.4 Common voice mistakes

- ❌ "This feature is implemented as a Next.js page that calls a Fastify..." — readers don't care about implementation
- ❌ "The system uses a BullMQ job to scan for overdue invoices..." — same problem
- ❌ "Simply click the Send reminder button" — drop "simply"
- ❌ "Note that this only works for admins" — drop "note that"; just say it
- ❌ "If you have any questions, please contact support" — generic boilerplate; the FAQ should cover real questions

Read the document aloud. If it sounds like a help article on a polished SaaS product, the voice is right. If it sounds like internal engineering documentation, the voice needs work.

---

## 5. docs/architecture.md

### 5.1 Audience and voice

Written for a maintainer who will modify or debug the feature in six months. Probably a developer, possibly one who didn't write the original code. They know the stack; they don't know this feature's history.

**Voice:** precise technical. Decision-record style — describe not just *what* the code does, but *why* it was designed that way and what trade-offs were made.

### 5.2 Required structure

```markdown
# Architecture: Invoice reminders

## Overview

The invoice reminders feature sends email notifications for overdue
invoices, either automatically via a scheduled background job or
manually via an admin action. The feature is composed of:

- A background worker that runs daily and dispatches reminders for all
  overdue invoices across all tenants
- An admin API endpoint that triggers a single reminder for a specific
  invoice
- An admin UI button that calls the endpoint and updates the row
  optimistically

## Data flow

### Automatic flow

```
[BullMQ scheduler] → [overdue-reminders worker]
  → [sendOverdueReminders service]
    → [invoice repository: findOverdueForReminders]
    → for each candidate:
        → [customer repository: findById]
        → [sendReminderEmail service → Resend]
        → [invoice repository: updateLastReminderSentAt]
        → [audit log]
```

### Manual flow

```
[Admin UI: Send reminder button]
  → POST /api/admin/invoices/:id/remind
    → [requireAdminInTenant]
    → [triggerManualReminder service]
      → [invoice lookup → tenant check → eligibility check → dedup check]
      → [sendReminderEmail service → Resend]
      → [invoice repository: updateLastReminderSentAt]
      → [audit log]
    → response 200 / error mapping
  → [Frontend: optimistic UI update]
```

## Key design decisions

### Tenant isolation in the service, not just the route

The `triggerManualReminder` service re-checks the tenant boundary
after fetching the invoice, even though the route already verified
the admin's session tenant. This is a deliberate redundancy: the
service is also callable from background jobs, CLI tools, and other
services, where the route-level check does not run. Centralising the
check in the service makes tenant isolation hold across all callers.

See `conventions/backend-conventions.md` section 5 for the team's
general approach.

### 404 instead of 403 for tenant mismatches

When an admin attempts an action on an invoice in a different tenant,
the API returns 404 (not 403). This avoids revealing that a given
invoice ID exists in another tenant. The internal audit log records
the tenant mismatch truthfully; the user-facing response does not.

### Deduplication via a column, not an external store

The 24-hour deduplication window is enforced by checking the invoice's
`lastReminderSentAt` column. An in-memory cache was considered and
rejected: it would not survive restarts and would not scale across
multiple worker processes. The column-based check is durable and
atomic.

### Sequential processing in the worker

The daily worker processes invoices one at a time, not in parallel.
This trades throughput for safety: parallel processing would risk
rate-limiting the email provider and would make per-invoice failure
harder to isolate. Daily reminder volumes are well within sequential
processing capacity.

## Trade-offs and known limitations

- **No timezone awareness:** the 7-day overdue calculation uses UTC.
  Tenants in distant timezones may see reminders at locally
  inconvenient times. A future enhancement could allow per-tenant
  scheduling.
- **No retry on transient email failures:** if the email service
  fails for an individual invoice, the worker moves on. The invoice
  will be re-attempted on the next daily run. A retry-with-backoff
  approach was considered and deferred.
- **No customer-side preferences:** customers cannot opt out of
  reminders via this feature. Opt-out is a separate planned story.

## Files

- `src/services/reminders/` — service-layer business logic
- `src/repositories/invoice.repository.ts` — invoice query methods
- `src/app/api/admin/invoices/[id]/remind/route.ts` — manual trigger
- `src/workers/overdue-reminders.worker.ts` — scheduled scan
- `src/app/(admin)/invoices/_components/SendReminderButton.tsx` — UI

## Related documentation

- [User guide](./user-guide.md)
- [API reference](./api.md)
- Original brief: `features/2026-05-25-invoice-reminders/03-spec.md`
- Final validation: `features/2026-05-25-invoice-reminders/07-validation.md`
```

### 5.3 What good looks like

- **The "Key design decisions" section is what makes architecture docs valuable.** A doc that only describes what the code does is redundant — the code already does that. A doc that describes *why* the code does what it does is genuinely useful in six months.
- **Trade-offs are named.** Every decision was made over some alternative. The doc records both the choice and the alternative that was rejected.
- **Known limitations are listed, not hidden.** The doc tells future maintainers what the feature does not do and what would need to change to address it.
- **The data flow diagrams use ASCII or simple text.** Real diagrams are nice, but they go out of date quickly. Text diagrams update along with the code.

### 5.4 Common voice mistakes

- ❌ Restating what the code says without explaining why. "The service checks the tenant ID" — that's in the code. Why is the check redundant with the route? That's the doc's job.
- ❌ Marketing the design. "This is an elegant, scalable, modern architecture" — drop it.
- ❌ Glossing over trade-offs. Every interesting design decision involved a choice. Name the choice.

---

## 6. CHANGELOG.md entry

### 6.1 Audience and voice

Written for any reader of release notes — developers reviewing the changelog before deploying, support staff explaining what's new, sometimes external users reading a public changelog.

**Voice:** action-oriented, user-facing. Says what changed for the user, not what changed in the code.

### 6.2 Required structure

Follows [Keep a Changelog](https://keepachangelog.com/) format. A new entry for the current unreleased version, or a new version section if cutting a release.

```markdown
## [Unreleased]

### Added
- Invoice reminders: admins can now send manual email reminders for
  overdue invoices from the admin UI, and the system automatically
  sends a reminder for any invoice that has been unpaid for more
  than 7 days. (feature: 2026-05-25-invoice-reminders)
```

For multiple changes in a release, group by category:

```markdown
## [1.4.0] — 2026-06-15

### Added
- Invoice reminders for overdue invoices (manual and automatic).
- Customer email change confirmation flow.

### Changed
- The admin invoices page now shows the last reminder timestamp
  for each invoice.

### Fixed
- Auth redirect now preserves the original destination URL when
  the user signs in.
```

### 6.3 What good looks like

- **Each entry is one or two lines.** A reader scanning the changelog should grasp each change in seconds.
- **Action-oriented language.** "Admins can now…" not "Added a reminder feature."
- **User-facing perspective.** Describe what changed from the user's point of view, not the developer's.
- **A pointer to the feature folder.** Lets a reader find the full story, spec, and validation if they want detail.
- **Categories are correct.** Added (new), Changed (modified), Fixed (bug fix), Removed (deprecated), Deprecated (will be removed), Security (security fix).

### 6.4 Strong vs. weak examples

**Strong:**

> Added: Admins can now send manual email reminders for overdue invoices from the admin UI, and the system automatically sends a reminder for any invoice that has been unpaid for more than 7 days.

**Weak:**

> Added invoice reminder service with manual trigger endpoint and scheduled worker.

**Why the second is weak:** it describes the *code*, not the user-visible change. A reader of release notes doesn't care that there's a "service" or a "worker"; they care that reminders now exist.

---

## 7. Cross-document rules

### 7.1 No voice contamination

Each document has a target voice. Do not let one voice leak into another:

- The README should not read like marketing
- The API doc should not include user-guide friendliness
- The user guide should not mention framework names
- The architecture doc should not paper over trade-offs
- The changelog should not describe code

When a draft document has the wrong voice, ask the Documentation Project to rewrite it with the target audience explicitly named: "Rewrite this user guide for a customer success person who has never seen the codebase."

### 7.2 Never invent behavior

If the Documentation Project doesn't know whether a behavior exists, it must leave a "TODO: confirm" marker — never guess. The chain runs after the code is written; the docs should describe what is, not what might be.

### 7.3 Match the as-shipped state, not the as-planned state

If the validator surfaced findings that changed the implementation (a tenant check added after Gate 3, a response shape adjusted), the docs reflect the final state. The architecture doc may briefly note that a late change happened if it's interesting for maintainers ("the service-layer tenant check was added in response to a Gate 3 finding"), but the API doc and user guide describe the current behavior only.

### 7.4 Pull from the right source

- API doc: pull endpoints, methods, schemas, status codes verbatim from `04-backend-summary.md`
- User guide: pull user-facing behavior from the user story (`02-story.md`) and the frontend summary (`05-frontend-summary.md`)
- Architecture doc: pull design decisions from the brief (`03-spec.md`) and from the validation (`07-validation.md`)
- README: pull stack details from `target-stack-spec.md` and setup steps from `deployment-notes.md`

Never paraphrase across sources. If a fact appears in the source, copy it precisely.

---

## 8. Tuning notes

- **If user guides keep slipping into technical jargon**, section 4.4's anti-patterns need sharper examples. The lever is to name the audience more explicitly in the role file.
- **If architecture docs keep reading like code summaries**, section 5.3 needs a stronger example of what a decision record looks like vs. a code description.
- **If changelog entries keep describing code instead of user changes**, section 6.4's strong-vs-weak example is the lever.
- **If the API doc keeps drifting from the actual schemas**, the issue is usually that the Documentation Project is paraphrasing rather than copying. Tighten the "pull verbatim" rule in section 7.4.
- **If the README's setup steps don't actually work**, `stack/deployment-notes.md` is the lever — the README pulls from it.

---

## 9. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |