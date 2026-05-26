# Project 5 — Frontend Builder

> **Role in the chain:** Step 5 of 9. Runs after the Backend Builder.
> **Human approval gate:** No
> **Output saved as:** Individual code files + `05-frontend-summary.md` in the per-feature folder

---

## Purpose

The Frontend Builder implements the frontend half of an approved technical brief: components, pages, hooks, client-side state, and the component tests that cover its own code. It consumes the API contract the Backend Builder has already produced. Its output is code the user reviews, saves, and runs locally.

This role exists for the same reason the Backend Builder does: focused implementation work without the cognitive load of designing the feature or choosing the stack. The brief tells the Frontend Builder what to build; the backend summary tells it what API to build against. Everything else is honoring those two contracts.

The Frontend Builder never touches backend files, never invents endpoints that are not in the backend summary, never adds dependencies without justification, and never proceeds without both an approved spec and a backend summary.

---

## Inputs

The Frontend Builder expects to receive:

- The approved technical brief (`03-spec.md`)
- The Backend Builder's summary (`04-backend-summary.md`) — this contains the API contract it will consume
- The Researcher's findings (`01-research.md`)
- Optionally, existing frontend files the builder should mirror in pattern
- Any clarification the user wants to add before code is written

It reads from its knowledge base on every run:

- `general-conventions.md`
- `js-conventions.md`
- `frontend-conventions.md`
- `testing-conventions.md`
- `regulated-environment-rules.md`
- `target-stack-spec.md`
- `example-frontend-feature.md`
- `example-test-suite.md`

---

## Outputs

A series of code artifacts, one per file, plus a final summary. Each file is produced as a complete, copy-paste-ready artifact in the side panel. You save each one into your working folder at the path the Builder specifies. The final summary is saved as `05-frontend-summary.md` and feeds into the Test and Documentation Projects.

Expect the following kinds of output per feature, depending on the brief:

- React components (presentational and container)
- Next.js pages or route handlers (client-side only)
- Custom hooks for data fetching, mutations, and state
- Form components with validation (Zod schemas mirroring the backend's)
- TypeScript types shared with the backend (imported, not re-declared)
- Component tests using the project's test runner

---

## Knowledge base files to upload

Upload these into the Frontend Builder Project's knowledge base:

| File | Purpose |
|---|---|
| `general-conventions.md` | Commits, branches, PRs, no-secrets, naming |
| `js-conventions.md` | Node version, package manager, tsconfig, ESLint, Prettier |
| `frontend-conventions.md` | Component structure, state, styling, accessibility |
| `testing-conventions.md` | Test runner, structure, builders, naming |
| `regulated-environment-rules.md` | PHI display rules, audit considerations |
| `target-stack-spec.md` | The default stack for new apps |
| `example-frontend-feature.md` | One real frontend feature, fully shown |
| `example-test-suite.md` | One real test file, success/failure/edge case examples |

Note that `do-not-modify.md` is absent from this Project's knowledge base. The Frontend Builder should rarely touch validated systems or approved templates — those concerns sit on the backend. If your frontend codebase contains do-not-modify items (validated UI templates, approved marketing layouts), add the file. Otherwise leave it out to keep the context tight.

The example files do the heaviest lifting here. The Frontend Builder will mirror `example-frontend-feature.md` in component structure, styling approach, hook patterns, and accessibility decisions. Spend time on it.

---

## Custom instructions

Paste the block below into the Frontend Builder Project's **Custom Instructions** field.

```
You write React/Next.js frontend code for a SaaS engineering
team. Your output is code the user will review and paste into
their IDE.

When the user provides an approved technical brief AND the
Backend Builder's summary (which tells you the API contract):

1. Confirm scope and the API contract.
   Restate what the backend produces (endpoints, methods, paths,
   request and response shapes) and what UI you'll build. If
   the backend summary is vague on any contract detail, ask
   one focused question before producing code. Do not guess
   request or response shapes.

2. Identify patterns to follow.
   Reference example-frontend-feature.md and name the patterns
   you'll mirror: component structure (presentational vs.
   container), state management approach, styling conventions,
   loading and error state handling, accessibility patterns.
   State the patterns explicitly so the user can correct you
   before code is produced.

3. Produce code, file by file. For each file:
   - Full file path (anchored to the conventions in the
     knowledge base)
   - Full file content in a fenced code block tagged
     ```typescript or ```tsx as appropriate
   - 1-2 sentence explanation of what the file does and why

4. Produce component tests in the same file-by-file format.
   Cover the visible states (loading, error, empty, success),
   user interactions (clicks, form submission, keyboard
   navigation), and the edge cases listed in the brief. Use
   the patterns from example-test-suite.md.

5. End with a summary saved as 05-frontend-summary.md:
   - Files added / edited (frontend only)
   - Patterns and components reused (existing design system
     components, hooks, providers)
   - Accessibility decisions made (keyboard navigation, focus
     management, ARIA, contrast)
   - Any new dependencies (and why they were necessary)
   - User-facing routes added or changed
   - Commands the user should run locally:
     pnpm install, pnpm typecheck, pnpm lint, pnpm test
   - Suggested additions to convention files, if any

Behaviour rules:
- Only produce frontend code. No services, API route handlers,
  workers, or migrations. If the brief seems to require a
  backend change, surface the gap rather than working around
  it.
- Consume the API exactly as the Backend Builder produced it.
  Do not invent endpoints, request shapes, or response shapes.
  If the shape is wrong for the UI, surface the mismatch as
  feedback so the Backend Builder can correct it — don't patch
  around it on the frontend.
- Match existing component patterns: styling, accessibility
  (WCAG 2.2 AA), keyboard navigation, focus management, loading
  and error states. If your codebase has a design system, use
  its components rather than building new primitives.
- Don't add new packages unless the brief required it. If a
  new package seems necessary mid-build, stop and ask.
- Don't refactor unrelated code. Stay inside the file paths
  named in section 8 of the brief.
- Never display raw error messages from the API to end users.
  Map known error codes to user-facing language; show a
  generic message for unknown errors.
- Produce every file as a complete artifact ready to download.
  Don't truncate or use "// ... rest of file" comments.
- If the user has not provided both an approved spec and a
  backend summary, refuse to write code and ask for both first.
- For any form that accepts user input, include client-side
  validation that mirrors the backend's Zod schema. The
  backend remains the source of truth, but the frontend should
  catch obvious errors before the round trip.
```

---

## How to use this Project in the workflow

1. **Open the Frontend Builder Project** in claude.ai.
2. **Start a new conversation.** Always start fresh.
3. **Paste the inputs** in this order:
   - The approved technical brief (`03-spec.md`)
   - The Backend Builder's summary (`04-backend-summary.md`) — this is the most important input
   - The Researcher's findings (`01-research.md`)
   - Optionally, upload one or two existing frontend feature files the Builder should pattern-match against
4. **Read the scope restatement and API contract restatement** (section 1 of the Builder's response). This is the critical checkpoint: if the Frontend Builder has misread the API contract, every component built on it will be wrong. Correct any misunderstandings before code streams.
5. **Read the pattern identification** (section 2). If the Builder is about to use a component pattern that does not match your codebase, say so now.
6. **Receive code as artifacts.** Save each one to the file path the Builder specifies.
7. **Save the summary** as `05-frontend-summary.md` in the feature folder. The Test and Documentation Projects will consume this.
8. **Run the local commands** the Builder specifies: `pnpm install && pnpm typecheck && pnpm lint && pnpm test`. If anything fails, paste the failure back into the same conversation and ask for a fix.
9. **If the failure is a backend-frontend mismatch**, do not patch on the frontend. Go back to the Backend Builder conversation, fix it there, regenerate the backend summary, and re-feed it to a fresh Frontend Builder conversation. Frontend patches for backend bugs are the single biggest source of drift in this chain.
10. **Hand off to the Test Project** by starting a new Test conversation with the story, spec, and both builder summaries.

---

## The API contract is the most important input

If the Backend Builder's summary has a vague API contract section, the Frontend Builder will fill in the gaps by guessing — and those guesses will mostly be wrong. Before you paste the backend summary into a Frontend Builder conversation, confirm it answers all of these for every endpoint:

- HTTP method and exact path (including path parameters)
- Auth requirement (anonymous, authenticated, role-gated, tenant-scoped)
- Request body shape (or "none")
- Success response shape and status code
- Each distinct error response shape and status code
- Any non-obvious headers required (e.g. idempotency keys)

If any of these are missing, fix the backend summary before opening the Frontend Builder conversation. This is one extra minute upstream that saves an hour of confused frontend code.

---

## When the Frontend Builder pushes back on the API

A well-functioning Frontend Builder will sometimes surface a mismatch: the API contract works for the backend, but the response shape makes the UI awkward. For example, the backend returns a flat list when the UI needs a grouped structure, or returns an internal status code that does not map cleanly to a user-facing message.

The custom instructions tell the Builder to surface this as feedback rather than patch around it on the frontend. When it does, you have three options:

1. **Adjust the backend** — go back to the Backend Builder, change the response shape, regenerate the summary, restart the Frontend Builder. Best when the mismatch reflects a real design issue.
2. **Adjust the frontend** — accept the awkward shape and do the grouping or mapping in a hook. Reasonable when the backend shape is dictated by an external system (a Stripe webhook payload, a Veeva API response) you do not control.
3. **Adjust the brief** — if the mismatch reveals a deeper design problem, escalate back to the Spec Writer.

The Frontend Builder's job is to flag the mismatch, not to choose between these options. You make the call.

---

## Handling large features: splitting the Builder across conversations

For larger frontend work (a full dashboard, a multi-step form, a new section of the app), expect to split the work across multiple conversations:

- **Conversation A:** Shared types, hooks, and any new design system primitives
- **Conversation B:** Page-level components and routing
- **Conversation C:** Detailed UI components and forms

Between conversations, pass a running summary so each new conversation knows what the previous one produced. The final `05-frontend-summary.md` should consolidate everything from all the conversations.

---

## Tuning notes

- If the Frontend Builder keeps inventing API endpoints, the Backend Builder's summary is too vague. Tighten the API contract section of `04-backend-summary.md`. The Frontend Builder is downstream of the problem; fix it upstream.
- If components come out in a style that does not match your codebase, refresh `example-frontend-feature.md` with a recent, well-written feature. Pay attention to component structure (presentational vs. container), state management (server-state vs. client-state), and styling.
- If accessibility is consistently weak, add a strong accessibility section to `frontend-conventions.md` with concrete examples: keyboard navigation patterns, focus management on modals, ARIA labels on icon-only buttons, contrast requirements. The Builder will match what it sees in the conventions.
- If component tests come out shallow, the lever is `example-test-suite.md`. Show the Builder a strong frontend test that covers visible states, user interactions, and accessibility queries.
- If the Builder keeps producing forms that do not validate client-side, strengthen the form validation rule with a concrete example in `example-frontend-feature.md` showing a form with Zod validation matching the backend schema.

---

## Compliance reminder

Frontend code has lower compliance stakes than backend code in most cases, but two areas deserve careful review in regulated-adjacent work:

1. **PHI display.** If any UI surface displays patient-identifying information, the surrounding context matters: who can see this screen, how long does the data stay on screen, is it captured in browser caches or screenshots, is it visible in the URL? The Frontend Builder will not automatically think about these — surface them in the brief and check the produced code against them.
2. **Audit trail visibility.** If the feature touches audit-relevant actions (sending a reminder, approving a document, changing a status), the UI should clearly show what happened and when. "Reminder sent successfully" is fine for a flash message; the audit detail belongs in the data, not the UI, but the UI should not obscure the audit-relevant action behind ambiguous language ("Updated" when "Reminder sent at 10:42 AM" would be clearer).

Beyond those: the same general rule applies. Before saving frontend code into your real codebase, confirm with your IT/security/compliance stakeholders that Claude Projects use is approved for the content being processed.