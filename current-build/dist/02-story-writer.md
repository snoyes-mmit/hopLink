# Project 2 — Story Writer

> **Role in the chain:** Step 2 of 9. Runs after the Researcher.
> **Human approval gate:** **Yes — Gate 1**
> **Output saved as:** `02-story.md` in the per-feature folder

---

## Purpose

The Story Writer turns a rough feature idea plus the Researcher's findings into one clear, testable user story. It is the first place in the chain where business intent becomes concrete and reviewable.

This role exists because business ambiguity is cheapest to fix here. A wrong assumption in the story becomes a wrong data model, which becomes a wrong API, which becomes a wrong UI. By the time anyone notices, the mistake has spread through the whole feature. The story is the contract everything downstream is built against — which is why this is the first human approval gate.

The Story Writer never writes technical design, never proposes implementations, and never invents business rules.

---

## Inputs

The Story Writer expects to receive:

- The original feature idea (1–3 sentences)
- The Researcher's findings (saved as `01-research.md` from Project 1)
- Any product or business rules you already know and want enforced
- Any prior story revisions if you are iterating

It reads from its knowledge base on every run:

- `general-conventions.md`
- `regulated-environment-rules.md`
- `story-template.md`

---

## Outputs

A single Markdown user story, under one page, with six sections in fixed order. You will save this verbatim as `02-story.md` in the feature folder, then paste it into the Spec Writer conversation as input — but only after **Gate 1** approval.

---

## Knowledge base files to upload

Upload these into the Story Writer Project's knowledge base:

| File | Purpose |
|---|---|
| `general-conventions.md` | Commits, branches, PRs, no-secrets, naming |
| `regulated-environment-rules.md` | PHI, MLR, audit trails, do-not-log lists |
| `story-template.md` | The story shape this Project must follow |

Notice how much smaller this knowledge base is than the Researcher's. The Story Writer does not need stack details, conventions, or do-not-modify lists — those concerns belong downstream. Keeping each Project's knowledge base narrow improves output quality.

---

## Custom instructions

Paste the block below into the Story Writer Project's **Custom Instructions** field.

```
You write user stories for a JavaScript SaaS engineering team
working in a regulated-industry-adjacent environment.

When the user gives you a feature idea (and usually findings from
the Researcher), produce one user story in this exact shape:

1. User story
   One sentence in the form:
   "As a <role>, I want <behaviour>, so that <outcome>."

2. Acceptance criteria
   Testable statements in plain language. Cover the happy path,
   failure paths, and any rules called out by the user.
   Each criterion must be observable — something a test could
   verify directly. Avoid criteria that depend on internal state
   no user or test can see.

3. Edge cases worth thinking about
   Boundaries, retries, multi-tenant concerns, permissions,
   accessibility, timezone, empty states, race conditions.
   List the case, not the solution. The Spec Writer decides how
   each one is handled.

4. Compliance considerations
   Anything that might touch PHI, MLR review, audit trails, or
   accessibility (WCAG 2.2 AA). If nothing applies, write
   "No compliance considerations identified for this story" so
   the user knows you checked.

5. Out of scope
   What this story explicitly does NOT cover. Be specific.
   "Notifications are out of scope" is better than "extras are
   out of scope."

6. Open questions
   Things that are genuinely unclear from the input. Never
   invent answers. If a rule is missing, list it as a question
   for the user to resolve before approval.

Behaviour rules:
- Use plain language. Avoid framework or product jargon.
- Never invent business rules. If a rule is missing, ask.
- Keep the story under one page.
- Do not write technical design — that's the Spec Writer's job.
  No data models, no API shapes, no component names, no library
  choices.
- If a regulatory or branding question arises, recommend the
  user verify with the appropriate stakeholder rather than
  resolving it yourself.
- If the Researcher's findings flagged anything in
  do-not-modify.md or any regulated-environment rule, surface
  it under "Compliance considerations" and recommend the user
  confirm before the story is approved.
- If the user requests changes, revise the whole story in
  place. Do not produce a diff or a delta — produce the full
  updated story so the saved artifact is always complete.
```

---

## How to use this Project in the workflow

1. **Open the Story Writer Project** in claude.ai.
2. **Start a new conversation.** Always start fresh — never reuse a conversation from a previous feature.
3. **Paste the inputs** in this order:
   - The original feature idea
   - The full contents of `01-research.md`
   - Any additional business rules or constraints you want enforced
4. **Read the story carefully.** This is the most important review point in the entire chain because every downstream role builds against this story.
5. **Gate 1 — approval decision.** You have three options:
   - **Approve** — save the story as `02-story.md` and proceed to the Spec Writer.
   - **Request changes** — describe what to change, in the same conversation. The Story Writer will produce a full revised story. Iterate until correct.
   - **Reject** — stop the chain. Save what was explored so far. The feature may need to be reshaped before it can be storied at all.
6. **Save the approved story** as `02-story.md` inside the feature folder (e.g. `features/2026-05-25-invoice-reminders/02-story.md`).
7. **Hand off to the Spec Writer** by starting a new Spec Writer conversation and pasting the approved story plus `01-research.md`.

---

## What "Gate 1" really checks

When you review the story before approving, you are answering four questions:

1. **Is this the right problem?** Does the story describe the user need you actually want to solve, or has it drifted into a related but different problem?
2. **Are the acceptance criteria testable?** Can each one be verified by a test, or are some criteria too vague to confirm?
3. **Are the business rules correct?** If the Story Writer made any assumption about an unstated rule, was the assumption right?
4. **Is anything missing?** Edge cases, compliance touches, permissions, accessibility — has the story acknowledged them, even if only to put them out of scope?

If the answer to all four is yes, approve. If not, request changes. The cost of a revision here is one conversation turn. The cost of catching it after the Backend Builder has run is an afternoon of rework.

---

## Tuning notes

- If the Story Writer keeps inventing business rules instead of asking, sharpen the "never invent business rules" rule and consider adding a concrete example of what an open question looks like to `story-template.md`.
- If stories keep coming back vague, the issue is usually that acceptance criteria are not observable. Add an example of a strong vs. weak criterion to `story-template.md`.
- If the Story Writer slips into technical language (mentioning Prisma, React, endpoints), strengthen the "no technical design" rule and remove any technical breadcrumbs that may have been included accidentally in the inputs.
- Resist adding stack details to this Project's knowledge base. The Story Writer should be deliberately stack-agnostic so the story stays focused on user value.

---

## Compliance reminder

Stories for regulated-adjacent work may end up in MLR review, client documentation, or audit packs. Write them as if a non-technical compliance reviewer will read them — because one might. The plain-language rule is not just a style preference; it is what makes the story usable downstream of engineering.