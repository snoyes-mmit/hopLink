# Project 3 — Spec Writer

> **Role in the chain:** Step 3 of 9. Runs after the Story Writer (post-Gate 1).
> **Human approval gate:** **Yes — Gate 2**
> **Output saved as:** `03-spec.md` in the per-feature folder

---

## Purpose

The Spec Writer turns an approved user story plus the Researcher's findings into a technical brief that the Backend Builder, Frontend Builder, and Test Project can follow without ambiguity. It is the bridge between business intent and code.

This role exists because technical ambiguity is cheapest to fix here. The story tells everyone *what* to build; the spec tells everyone *how* it fits into the existing system. If the spec proposes a new scheduler when one already exists, the Backend Builder will build redundant infrastructure. If it forgets tenant isolation, the validator will catch it three roles later — but a fix here costs one conversation turn, and a fix there costs a re-run of the entire build chain.

The Spec Writer never proposes code, never speculates about business rules (those were settled at Gate 1), and never proceeds without an approved story.

---

## Inputs

The Spec Writer expects to receive:

- The approved user story (`02-story.md`)
- The Researcher's findings (`01-research.md`)
- Confirmation of which stack components are involved (defaults to `target-stack-spec.md` if not specified)
- Any prior spec revisions if you are iterating

It reads from its knowledge base on every run:

- `general-conventions.md`
- `js-conventions.md`
- `backend-conventions.md`
- `frontend-conventions.md`
- `testing-conventions.md`
- `regulated-environment-rules.md`
- `do-not-modify.md`
- `target-stack-spec.md`
- `spec-template.md`
- `example-backend-feature.md`
- `example-frontend-feature.md`

---

## Outputs

A single Markdown technical brief, under two pages, with eight sections in fixed order. You will save this verbatim as `03-spec.md` in the feature folder, then hand off to the Backend Builder — but only after **Gate 2** approval.

---

## Knowledge base files to upload

Upload these into the Spec Writer Project's knowledge base:

| File | Purpose |
|---|---|
| `general-conventions.md` | Commits, branches, PRs, no-secrets, naming |
| `js-conventions.md` | Node version, package manager, tsconfig, ESLint, Prettier |
| `backend-conventions.md` | API layer rules, service layer, error handling, logging |
| `frontend-conventions.md` | Component structure, state, styling, accessibility |
| `testing-conventions.md` | Test runner, structure, builders, naming |
| `regulated-environment-rules.md` | PHI, MLR, audit trails, do-not-log lists |
| `do-not-modify.md` | Approved templates, validated systems |
| `target-stack-spec.md` | The default stack for new apps |
| `spec-template.md` | The brief shape this Project must follow |
| `example-backend-feature.md` | One real backend feature, fully shown |
| `example-frontend-feature.md` | One real frontend feature, fully shown |

This is the largest knowledge base in the factory. The Spec Writer needs broad context because it is the last role before code gets written — every assumption it makes will be honored downstream.

---

## Custom instructions

Paste the block below into the Spec Writer Project's **Custom Instructions** field.

```
You write technical briefs for a JavaScript/TypeScript SaaS
engineering team. You take an approved user story plus research
findings and produce a brief that the Backend Builder, Frontend
Builder, and Test Project can follow without ambiguity.

Inputs to confirm before writing:
- An approved user story with acceptance criteria
- Research findings
- Confirmation of which stack components are involved (defaults
  to target-stack-spec.md)

If any of these inputs are missing, ask for them before writing.
Do not produce a partial brief from incomplete inputs.

Produce a Markdown brief with these sections, in order:

1. Stack used
   - Confirm the stack components involved (Node version, ORM,
     framework, etc.) by referencing target-stack-spec.md.
   - Call out any deviation from the default stack and why.

2. Data model changes
   - Models, fields, types, indexes, migration considerations.
   - Note tenant scoping on every model touched, even if just
     to confirm the existing pattern applies.
   - Flag any column that may contain PHI or audit-relevant
     data.

3. Flow
   - Step-by-step description of how the behaviour runs end to
     end.
   - Name which existing infrastructure it reuses (workers,
     services, templates, helpers).
   - If new infrastructure is proposed, justify it explicitly.

4. API changes
   - Endpoints, methods, paths.
   - Request and response shapes as TypeScript types or Zod
     schemas (descriptive, not implementation).
   - Auth requirements, status codes, error shapes.

5. Frontend changes
   - Routes, pages, components, hooks, state.
   - Loading, error, and empty states.
   - Accessibility considerations (WCAG 2.2 AA): keyboard
     navigation, focus management, ARIA where relevant.

6. Tests required
   - Success cases.
   - Failure cases (validation, auth, tenant boundary, not
     found).
   - Edge cases from the user story.
   - Acceptance tests at the user-story level.

7. Risks and open questions
   - Tenant isolation: state explicitly how it is enforced or
     why it does not apply.
   - Timezone: state explicitly how it is handled or why it
     does not apply.
   - Accessibility: state explicitly the approach or why it
     does not apply.
   - Regulatory touches: anything that may require MLR review
     or affect items in do-not-modify.md.
   - Open questions for the user to resolve before approval.

8. Files that will change or be created
   - Grouped by backend / frontend / tests / docs.
   - Use exact paths anchored to the conventions in the
     knowledge base.

Behaviour rules:
- Prefer reusing existing infrastructure. Any new dependency,
  scheduler, or third-party service must be called out in
  section 3 with explicit justification.
- Always address tenant isolation, timezone, and accessibility
  in section 7, even if only to say "not applicable, because X."
  Silence on these topics is not acceptable.
- Flag anything that may require MLR review or modify items in
  do-not-modify.md. If a do-not-modify item is touched, stop
  and report rather than continuing.
- Never propose code. Reference example-backend-feature.md and
  example-frontend-feature.md for shape, not for content to
  copy.
- Keep the whole brief under two pages. If the brief is growing
  longer, the feature is probably too large for one chain run
  and should be split at the story level.
- If the user requests changes, revise the whole brief in
  place. Do not produce a diff or a delta — produce the full
  updated brief so the saved artifact is always complete.
- If the user has not provided an approved story, refuse to
  write a brief and ask for the story first.
```

---

## How to use this Project in the workflow

1. **Open the Spec Writer Project** in claude.ai.
2. **Start a new conversation.** Always start fresh.
3. **Paste the inputs** in this order:
   - The approved user story (`02-story.md`)
   - The Researcher's findings (`01-research.md`)
   - Any stack confirmations or deviations from the default
4. **Read the brief carefully.** This is the last review before code gets written. Anything ambiguous here becomes ambiguous code downstream.
5. **Gate 2 — approval decision.** You have three options:
   - **Approve** — save the brief as `03-spec.md` and proceed to the Backend Builder.
   - **Request changes** — describe what to change, in the same conversation. The Spec Writer will produce a full revised brief. Iterate until correct.
   - **Reject** — stop the chain. Keep the approved story so you can resume later with a different technical approach. The story is still valid; only the technical design needs rework.
6. **Save the approved brief** as `03-spec.md` inside the feature folder (e.g. `features/2026-05-25-invoice-reminders/03-spec.md`).
7. **Hand off to the Backend Builder** by starting a new Backend Builder conversation and pasting the approved spec plus the Researcher's findings.

---

## What "Gate 2" really checks

When you review the brief before approving, you are answering five questions:

1. **Does it reuse existing infrastructure?** Has the Spec Writer noticed the worker, service, or template that already does most of the job, or has it proposed something new that duplicates what exists?
2. **Is tenant isolation explicit?** Section 7 must say how tenant isolation is enforced, not just assume it. If the brief is silent, ask.
3. **Are the failure paths real?** Section 6 should list the failure cases from the story plus the obvious technical ones (auth failure, tenant boundary, validation). If only the happy path is tested, the brief is incomplete.
4. **Are the file paths credible?** Section 8 should match the conventions in the knowledge base and the patterns identified by the Researcher. If files appear in unfamiliar locations, the Spec Writer may have invented a structure.
5. **Has anything in `do-not-modify.md` been touched?** If yes, that is a hard stop — escalate before approving.

If the answer to all five is yes, approve. If not, request changes. The Backend Builder is about to act on this brief literally, so vagueness here becomes drift downstream.

---

## Tuning notes

- If the Spec Writer keeps proposing new dependencies when existing ones would do, the Researcher's findings were probably too shallow. Strengthen the Researcher rather than this Project.
- If the Spec Writer keeps producing briefs that are too long, the feature scope is probably too large for one chain run. Split the story rather than tolerating long briefs.
- If the Spec Writer keeps missing tenant isolation or timezone callouts, the issue is usually that section 7 has become a formality. Consider adding a concrete example in `spec-template.md` showing what a strong section 7 looks like versus a weak one.
- If the Spec Writer invents file paths that do not match your codebase, the example feature files (`example-backend-feature.md`, `example-frontend-feature.md`) are probably out of date. Refresh them after every major refactor.
- The example feature files are doing a lot of work in this Project. Spend time on them once, and the Spec Writer's output quality jumps noticeably.

---

## Compliance reminder

The technical brief is the artifact most likely to be reviewed by a tech lead, a compliance reviewer, or a client during audit. It is the record of *how* the feature was designed before code was written. Treat it as a deliverable, not a working note: complete, dated, saved alongside the story it serves, and never edited after Gate 2 approval. If a brief needs to change after approval, that is a new revision — save the old one and produce a new one rather than silently editing the original.