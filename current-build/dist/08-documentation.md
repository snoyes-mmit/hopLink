# Project 8 — Documentation

> **Role in the chain:** Step 8 of 9. Runs after the Validate Project (post-Gate 3).
> **Human approval gate:** No
> **Output saved as:** Individual documentation files in the feature folder's `08-documentation/` subdirectory

---

## Purpose

The Documentation Project produces every document the package needs: README, API reference, user guide, architecture notes, and a changelog entry. Each one is written for a different audience and serves a different purpose, but they share a common source — the approved story, brief, builder summaries, and validator findings.

This role exists because documentation is often the last thing to happen and the first thing to be skipped. By placing it as a dedicated step after validation, the chain forces documentation to be a deliverable, not an afterthought. The story and brief have already settled what the feature does; the builder summaries have settled how it works; the validator has settled that it works correctly. All that remains is to record those decisions for the audiences who will need them.

The Documentation Project never invents behavior, never describes features that were not built, and never papers over gaps with marketing language.

---

## Inputs

The Documentation Project expects to receive:

- The approved user story (`02-story.md`)
- The approved technical brief (`03-spec.md`)
- The Backend Builder's summary (`04-backend-summary.md`) — for endpoints and types
- The Frontend Builder's summary (`05-frontend-summary.md`) — for routes and components
- The Test Project's coverage report (`06-test-report.md`) — for noting what is tested
- The final validator findings (`07-validation.md`) — for noting anything that affected the final shape

It reads from its knowledge base on every run:

- `general-conventions.md`
- `target-stack-spec.md`
- `documentation-template.md`
- `deployment-notes.md`

---

## Outputs

Five Markdown documents, each produced as a separate artifact in the side panel. You save each one into the feature folder's `08-documentation/` subdirectory, and they will be carried forward into the package by the Package Project.

The five documents are:

1. **`README.md`** — project root level. Stack, prerequisites, setup, run, test, build, folder structure.
2. **`docs/api.md`** — technical API reference, generated from the backend summary.
3. **`docs/user-guide.md`** — plain-language walkthrough for non-developers.
4. **`docs/architecture.md`** — design decisions, data flow, service boundaries, ongoing maintenance notes.
5. **`CHANGELOG.md`** — a single Keep-a-Changelog formatted entry for this feature.

---

## Knowledge base files to upload

Upload these into the Documentation Project's knowledge base:

| File | Purpose |
|---|---|
| `general-conventions.md` | Commits, branches, PRs, no-secrets, naming |
| `target-stack-spec.md` | The default stack for new apps |
| `documentation-template.md` | The shape and tone every doc must follow |
| `deployment-notes.md` | How apps are run locally and deployed |

This is one of the smallest knowledge bases in the factory. The Documentation Project does not need conventions for backend, frontend, or testing — those concerns are settled by the time documentation begins. It needs to know the stack (so prerequisites are accurate), the documentation template (so the shape is consistent), and the deployment story (so the README's "how to run" section is correct).

`documentation-template.md` is the key file. It defines the tone, the section ordering, and the level of detail for each document. Spend time on it. The Documentation Project will mirror what it sees.

---

## Custom instructions

Paste the block below into the Documentation Project's **Custom Instructions** field.

```
You write the documentation that ships with a JavaScript SaaS
feature or app. Your output is Markdown files the user will
save into the project's docs/ directory (and a README.md at
the project root).

Inputs:
- The approved user story
- The approved technical brief
- The Backend Builder's summary (endpoints, types)
- The Frontend Builder's summary (routes, components)
- The Test Project's coverage report
- The validator's findings (anything that affected the final
  shape)

If any of these inputs are missing, refuse to produce
documentation and ask for the missing input first.
Documentation written from partial inputs is documentation
that will mislead readers.

Produce these documents, each as its own artifact in the side
panel so the user can download them individually:

1. README.md (project root)
   - One-paragraph project description
   - Stack overview (pulled from target-stack-spec.md)
   - Prerequisites (Node version, pnpm, Postgres, etc.)
   - Setup commands (clone, install, env, migrate, seed)
   - How to run locally (dev command)
   - How to run tests (unit + e2e)
   - How to build for production
   - Folder structure (one-line per top-level folder)
   - Links to docs/ files
   - License placeholder

2. docs/api.md
   - Each endpoint documented with:
     * Method and path
     * Auth requirement (anonymous / authenticated /
       role-gated / tenant-scoped)
     * Request schema (TypeScript type or Zod schema)
     * Response schemas (success + each error case)
     * Status codes
     * Example request and response
   - Pull every endpoint from the Backend Builder's summary.
     Do not invent endpoints.

3. docs/user-guide.md
   - Plain-language walkthrough of how a non-developer uses
     the feature
   - Generated from the user story and frontend summary
   - Written for a non-developer audience (no jargon, no
     framework names, no technical detail)
   - Include screenshots or screenshot placeholders where
     the UI flow is non-obvious

4. docs/architecture.md
   - Short overview of how the feature is wired together
   - Data flow (request → service → data layer → response)
   - Service boundaries (which service owns what)
   - Key decisions (anything from the brief's "Risks" section
     that ongoing maintainers should know)
   - Trade-offs that were made and why
   - Anything from the validator's findings that resulted in
     a design choice worth recording

5. CHANGELOG.md entry
   - Follow Keep-a-Changelog format
   - Section: Added / Changed / Fixed / Removed as appropriate
   - One-line user-facing description plus a pointer to the
     story ID (e.g., the feature folder date or ticket)
   - This is a NEW entry to be appended to an existing
     CHANGELOG.md, not a replacement for the whole file

Behaviour rules:
- Use plain language for user-facing docs (README, user-guide).
  Avoid jargon. Avoid framework names where they do not help.
- Use precise technical language for api.md and architecture.md.
  Be specific about types, schemas, and contracts.
- Match the documentation-template.md structure exactly. Do not
  reorder sections, do not invent new sections, do not skip
  required sections.
- Never invent behavior that isn't in the spec, builder
  summaries, or validator findings. If something is unclear,
  leave a "TODO: confirm" marker rather than guessing.
- Never document tests as if they were features. The user
  guide describes what the user does, not what the tests cover.
- Produce every document as a complete artifact ready to
  download. No truncation, no "// rest of file" placeholders.
- Each document is its own artifact — do not concatenate them
  into one big response.
- If the validator's findings include items that affected the
  final implementation (e.g., a tenant check was added late in
  the chain), reflect those in architecture.md as decisions
  worth recording. Documentation should match the as-shipped
  state, not the originally-planned state.
- If the feature touches PHI, MLR-reviewed content, or
  anything in regulated-environment-rules.md, note this in
  architecture.md and recommend the user verify with the
  appropriate stakeholder before publishing the docs externally.
```

---

## How to use this Project in the workflow

1. **Open the Documentation Project** in claude.ai.
2. **Start a new conversation.** Always start fresh.
3. **Paste the inputs** in this order:
   - The approved user story (`02-story.md`)
   - The approved technical brief (`03-spec.md`)
   - The Backend Builder's summary (`04-backend-summary.md`)
   - The Frontend Builder's summary (`05-frontend-summary.md`)
   - The Test Project's coverage report (`06-test-report.md`)
   - The final validator findings (`07-validation.md`)
4. **Receive each document as a separate artifact** in the side panel. The Documentation Project should produce five artifacts: README, api.md, user-guide.md, architecture.md, CHANGELOG entry.
5. **Save each document** into the feature folder's `08-documentation/` subdirectory:
   ```
   features/2026-05-25-invoice-reminders/08-documentation/
   ├── README.md
   ├── docs/
   │   ├── api.md
   │   ├── user-guide.md
   │   └── architecture.md
   └── CHANGELOG-entry.md
   ```
6. **Review each document** before moving on. The five questions in the next section guide that review.
7. **Hand off to the Package Project** by starting a new Package conversation and uploading (or pasting) all five documents along with the rest of the chain's outputs.

---

## How to review documentation before approving

Documentation has no human approval gate in this chain, but skipping a review of the produced docs is a mistake. Five questions catch the most common issues:

1. **Does the README actually run?** If you followed the setup steps in a clean environment, would the app start? Missing environment variables, wrong Node version, or skipped migration steps are the most common breakages.
2. **Does the API doc match the backend summary exactly?** Endpoints, methods, schemas, and status codes should be identical. If the API doc disagrees with the summary, the doc is wrong — the summary is the source of truth.
3. **Can a non-developer follow the user guide?** Read it as if you were a customer success person who needs to support this feature. Jargon, framework names, and missing screenshots are common gaps.
4. **Does the architecture doc record decisions, not just describe code?** A good architecture doc tells the maintainer *why* something is the way it is, not just *what* it is. If the doc reads like a code summary, it is too shallow.
5. **Does the changelog entry tell the user what changed for them?** "Added invoice reminder service" describes the code. "Admins can now send invoice reminders manually or have them sent automatically after 7 days of non-payment" describes the user-visible change. The second is correct.

If any of the five answers is no, ask the Documentation Project for a revision in the same conversation rather than fixing the doc by hand. The chain's value is that the artifacts are consistent; hand-edits create drift.

---

## The audience-shifting problem

The Documentation Project's hardest challenge is that it writes for five different audiences in one conversation:

- **README** — for any developer who picks up the codebase
- **API doc** — for the developer integrating with or extending the API
- **User guide** — for the non-developer (admin, customer success, end user) who uses the feature
- **Architecture doc** — for the maintainer who will modify or debug the feature in six months
- **Changelog** — for any reader scanning release notes

Each audience needs a different voice, a different level of detail, and a different vocabulary. The most common failure is **voice contamination**: the user guide that uses framework names, the architecture doc that reads like a marketing brochure, the README that assumes you already know the project.

The custom instructions try to prevent this by giving each document explicit guidance on tone and audience, but the lever that actually works is `documentation-template.md`. The clearer your template is about who each document is for, the cleaner the Documentation Project's output will be.

When a document comes out in the wrong voice, name the audience explicitly in the revision request: *"The user guide is using framework names. Rewrite it for a customer success person who has never seen the codebase."*

---

## What goes in architecture.md vs. the brief

A common question: if the brief (`03-spec.md`) already documents the design, what is `architecture.md` for?

They serve different purposes:

- **The brief is a forward-looking artifact.** It says *"here is what we plan to build."* It is dated, frozen at Gate 2 approval, and never edited after.
- **The architecture doc is a backward-looking artifact.** It says *"here is what was actually built, and why."* It reflects the as-shipped state, including any changes that happened during the chain (e.g., a tenant check added after a validator finding).

In regulated-adjacent work, both matter for different reasons. The brief is part of the design evidence; the architecture doc is part of the ongoing system documentation. If they diverge, the architecture doc is correct for "what is" and the brief is correct for "what was planned" — and that divergence itself is often interesting (it shows how the design evolved).

Do not collapse them. Do not edit the brief to match the as-shipped state. The history of the design is part of the audit trail.

---

## Tuning notes

- The single biggest lever for documentation quality is `documentation-template.md`. It defines the tone, structure, and required sections for each of the five outputs. Tune this file as you find patterns in what the Documentation Project produces.
- If the README is consistently incomplete (missing setup steps, wrong commands, missing environment variables), `deployment-notes.md` is the lever. Make it explicit and concrete.
- If user guides keep coming out too technical, add a "Voice and audience" section to `documentation-template.md` with a strong example of plain-language writing. The Documentation Project will mirror what it sees.
- If architecture docs keep reading like code summaries instead of decision records, add an example of a good architecture doc to `documentation-template.md` showing the *"what / why / trade-offs"* shape.
- If changelog entries keep describing code instead of user-visible changes, sharpen the entry rule with a strong example: code-focused vs. user-focused side by side.
- If documentation references behavior that wasn't actually built, the issue is usually that the inputs (especially `05-frontend-summary.md`) were incomplete. The Documentation Project should not invent — but it will reach if the inputs are thin. Strengthen the upstream summaries.

---

## Compliance reminder

Documentation produced through the chain may be distributed to clients, used in MLR review, included in audit packs, or published on a developer portal. Three rules deserve specific attention in regulated-adjacent work:

1. **The user guide is a candidate for MLR review.** If your team's user-facing documentation goes through MLR (medical, legal, regulatory) review, treat `user-guide.md` as draft content, not final content. The chain produces it; the review process approves it. Note this clearly in the document header so downstream readers know it is not yet approved.

2. **The API doc is the integration contract.** Once published, downstream consumers (internal teams, external partners) will build against it. Errors in the API doc create real integration bugs. The custom instructions tell the Documentation Project to pull every endpoint from the Backend Builder's summary verbatim — confirm this is what happened before publishing.

3. **The architecture doc may surface design decisions that touch validated systems.** If `architecture.md` describes how the feature interacts with anything in `do-not-modify.md` or anything covered by `regulated-environment-rules.md`, do not publish the doc externally without compliance review. Internal use is fine; external distribution requires approval.

Before publishing documentation externally, confirm with your IT/security/compliance stakeholders that the content is approved for the audience that will receive it, and that no information in the docs (configuration details, infrastructure choices, internal patterns) crosses a line that should not be crossed.