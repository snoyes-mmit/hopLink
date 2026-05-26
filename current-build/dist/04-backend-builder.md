# Project 4 — Backend Builder

> **Role in the chain:** Step 4 of 9. Runs after the Spec Writer (post-Gate 2).
> **Human approval gate:** No
> **Output saved as:** Individual code files + `04-backend-summary.md` in the per-feature folder

---

## Purpose

The Backend Builder implements the backend half of an approved technical brief: API routes, services, database access, background jobs, schemas, and the unit tests that cover its own code. Its output is code the user reviews, saves, and runs locally.

This role exists to do focused implementation work without the cognitive load of also designing the feature, choosing the stack, or thinking about the UI. The brief has settled all of those decisions. The Backend Builder's only job is to honor the brief, match existing patterns, and produce code that runs.

The Backend Builder never touches frontend files, never invents endpoints not in the brief, never adds dependencies without justification, and never proceeds without an approved spec.

---

## Inputs

The Backend Builder expects to receive:

- The approved technical brief (`03-spec.md`)
- The Researcher's findings (`01-research.md`)
- Optionally, existing backend files the builder should mirror in pattern
- Any clarification the user wants to add before code is written

It reads from its knowledge base on every run:

- `general-conventions.md`
- `js-conventions.md`
- `backend-conventions.md`
- `testing-conventions.md`
- `regulated-environment-rules.md`
- `do-not-modify.md`
- `target-stack-spec.md`
- `example-backend-feature.md`
- `example-test-suite.md`

---

## Outputs

A series of code artifacts, one per file, plus a final summary. Each file is produced as a complete, copy-paste-ready artifact in the side panel. You save each one into your working folder at the path the Builder specifies. The final summary is saved as `04-backend-summary.md` and becomes a critical input for the Frontend Builder (it documents the API contract).

Expect the following kinds of output per feature, depending on the brief:

- Database migration or schema change
- Service modules (where business logic lives)
- API route handlers (thin layer that calls into services)
- Background job handlers (if the brief involves async work)
- Zod schemas for input/output validation
- TypeScript types shared with the frontend
- Unit tests for each service and route

---

## Knowledge base files to upload

Upload these into the Backend Builder Project's knowledge base:

| File | Purpose |
|---|---|
| `general-conventions.md` | Commits, branches, PRs, no-secrets, naming |
| `js-conventions.md` | Node version, package manager, tsconfig, ESLint, Prettier |
| `backend-conventions.md` | API layer rules, service layer, error handling, logging |
| `testing-conventions.md` | Test runner, structure, builders, naming |
| `regulated-environment-rules.md` | PHI, MLR, audit trails, do-not-log lists |
| `do-not-modify.md` | Approved templates, validated systems |
| `target-stack-spec.md` | The default stack for new apps |
| `example-backend-feature.md` | One real backend feature, fully shown |
| `example-test-suite.md` | One real test file, success/failure/edge case examples |

The example files are the most important items in this knowledge base. They are what the Builder will mirror in shape, layout, and style. Spend time on them — the Backend Builder's output quality is roughly equal to the quality of `example-backend-feature.md`.

---

## Custom instructions

Paste the block below into the Backend Builder Project's **Custom Instructions** field.

```
You write Node.js/TypeScript backend code for a SaaS engineering
team. Your output is code the user will review and paste into
their IDE.

When the user provides an approved technical brief:

1. Confirm scope.
   Restate the brief in 2-3 bullets. If anything is unclear or
   missing, ask one focused question before producing code. Do
   not guess at scope.

2. Identify patterns to follow.
   Reference example-backend-feature.md and name the patterns
   you'll mirror: file layout, layering (route → service →
   data), error handling, logging, test structure. State the
   patterns explicitly so the user can correct you before code
   is produced.

3. Produce code, file by file. For each file:
   - Full file path (anchored to the conventions in the
     knowledge base)
   - Full file content in a fenced code block tagged
     ```typescript
   - 1-2 sentence explanation of what the file does and why

4. Produce unit tests in the same file-by-file format.
   Cover success cases, validation failure, auth failure,
   tenant boundary, and the edge cases listed in the brief.
   Use the test data builders from example-test-suite.md
   rather than inline setup.

5. End with a summary saved as 04-backend-summary.md:
   - Files added / edited (backend only)
   - Patterns and helpers reused
   - Any new dependencies (and why they were necessary)
   - API contract: endpoints, methods, paths, request and
     response shapes (as TypeScript types or Zod schemas).
     This section is what the Frontend Builder will consume,
     so be precise.
   - Commands the user should run locally:
     pnpm install, pnpm typecheck, pnpm lint, pnpm test
   - Suggested additions to convention files, if any

Behaviour rules:
- Only produce backend code. No React, no Next.js client
  components, no client-side hooks.
- Match patterns in example-backend-feature.md exactly. Don't
  invent new conventions.
- Don't introduce new packages unless the brief required it.
  If a new package seems necessary mid-build, stop and ask.
- Don't refactor unrelated code. Stay inside the file paths
  named in section 8 of the brief.
- Never log raw request payloads. Never return raw exceptions
  to the client.
- Enforce tenant isolation in services, not just routes. Even
  if a route checks tenancy, the service must check it too.
- If the brief conflicts with do-not-modify.md, stop and
  report. Do not proceed.
- Produce every file as a complete artifact ready to download.
  Don't truncate or use "// ... rest of file" comments. The
  user is going to save these directly into their codebase, so
  partial files create silent breakage.
- If a unit test would require mocking infrastructure that
  example-test-suite.md does not mock, follow the example.
  Do not invent new mocking patterns.
- If the user has not provided an approved spec, refuse to
  write code and ask for the spec first.
```

---

## How to use this Project in the workflow

1. **Open the Backend Builder Project** in claude.ai.
2. **Start a new conversation.** Always start fresh.
3. **Paste the inputs** in this order:
   - The approved technical brief (`03-spec.md`)
   - The Researcher's findings (`01-research.md`)
   - Optionally, upload one or two existing backend feature files the Builder should pattern-match against
4. **Read the scope restatement and pattern identification** (sections 1 and 2 of the Builder's response). This is your last cheap chance to correct course before code is generated. If the restatement misses something or the patterns are wrong, say so before code starts streaming.
5. **Receive code as artifacts.** Claude Projects will produce each file as a separate artifact in the side panel. Save each one to the file path the Builder specifies, inside your working folder.
6. **Save the summary** as `04-backend-summary.md` in the feature folder (e.g. `features/2026-05-25-invoice-reminders/04-backend-summary.md`). This file is critical — the Frontend Builder needs it to know the API contract.
7. **Run the local commands** the Builder specifies: `pnpm install && pnpm typecheck && pnpm lint && pnpm test`. If anything fails, paste the failure back into the same conversation and ask for a fix. Do not move on to the Frontend Builder until the backend is green.
8. **Hand off to the Frontend Builder** by starting a new Frontend Builder conversation and pasting the approved spec, the Researcher's findings, and the backend summary.

---

## Why the backend summary matters so much

The backend summary is the most important non-code artifact this Project produces. It is the **API contract** the Frontend Builder will consume.

If the summary is vague ("added an endpoint for triggering reminders"), the Frontend Builder will invent the request and response shapes and almost certainly get them wrong. If the summary is precise (endpoint method and path, full request schema, full response schema, status codes, auth requirement), the Frontend Builder can build against it directly without inventing anything.

A good summary's API contract section looks like this:

```
POST /api/admin/invoices/:id/remind
Auth: requires admin role + same tenant as invoice
Request body: (none)
Response 200: { success: true, lastReminderSentAt: ISO8601 string }
Response 403: { error: "tenant_mismatch" | "not_admin" }
Response 404: { error: "invoice_not_found" }
Response 409: { error: "reminder_already_sent_in_window" }
```

Vague summaries are the single most common cause of frontend-backend mismatch in this chain. Tighten this section every time you find the Frontend Builder confused about the API.

---

## Handling large features: splitting the Builder across conversations

For small features, one Backend Builder conversation handles everything. For larger features (multiple new models, several endpoints, a new worker), expect to split the work across multiple conversations:

- **Conversation A:** Data layer (migration, schema, types, basic service)
- **Conversation B:** API routes and route-level tests
- **Conversation C:** Background jobs or async workflows, if any

Between conversations, pass a running summary so each new conversation knows what the previous one produced. The final summary saved as `04-backend-summary.md` should consolidate everything from all the conversations, not just the last one.

If you find yourself wanting four or more conversations to handle one backend, the feature is probably too large for one chain run. Go back to the Story Writer and split.

---

## Tuning notes

- If the Backend Builder keeps producing code that does not match your real codebase patterns, the issue is almost always `example-backend-feature.md`. Refresh it with a recent, real, well-written feature from your codebase. The Builder will mirror whatever example you show it.
- If the Builder keeps inventing new packages, the brief probably did not justify reuse strongly enough — but you can also add an explicit "do not add packages X, Y, Z without confirmation" line to the custom instructions.
- If unit tests come out shallow, `example-test-suite.md` is the lever. Add a strong example covering success, validation failure, auth failure, tenant boundary, and one edge case. The Builder will match its depth.
- If files come out truncated despite the "no truncation" rule, the feature scope is probably too large for one response. Split the conversation as described above.
- Watch for the Builder enforcing tenant isolation only at the route level. If it does, strengthen the "enforce in services, not just routes" rule with a concrete example in `example-backend-feature.md`.

---

## Compliance reminder

Backend code in regulated-adjacent work has higher consequences than frontend code: it is where PHI is handled, where audit trails are written, and where tenant boundaries are enforced. Two rules in the custom instructions deserve particular attention during your review:

1. **"Never log raw request payloads."** This is a hard line. Logs that include raw payloads will leak PHI into observability systems that were never designed to hold it. If a unit test seems to rely on raw-payload logging for assertions, the test is wrong — fix the test.
2. **"Enforce tenant isolation in services, not just routes."** Route-level checks fail when a service is invoked from a background job, a CLI, or another internal caller that bypasses the route layer. Service-level checks always run. This is one of those rules that costs nothing to follow and a lot to skip.

Before saving any backend code into your real codebase, confirm with your IT/security/compliance stakeholders that Claude Projects use is approved for the content being processed — especially if the code path touches PHI.