# Orchestrator — JavaScript SaaS Factory

> **What this file is:** The operating manual for running a feature through the nine-Project factory. One section per worker, each summarising what to do, what inputs to pass, what outputs to expect, and what to check before moving on.
>
> **What this file is not:** A Claude prompt. The factory is built on nine separate Claude Projects in claude.ai. This file is a human-facing reference you keep open while running the chain. It does not get pasted into a Project conversation.

---

## How to use this orchestrator

Keep this file open in another tab while you run a feature through the factory. At each step:

1. Scroll to the relevant Project's section below.
2. Open the matching Claude Project in claude.ai (Researcher, Story Writer, etc.).
3. Start a **new conversation** in that Project — never reuse a conversation from a prior feature.
4. Follow the section's checklist for inputs, outputs, and the handoff to the next step.
5. Save the output as the named artifact in the per-feature folder.
6. Move to the next section.

The chain runs sequentially. Do not skip steps. Do not parallelise builder work (backend then frontend, in that order).

---

## Before you start

### Per-feature folder

Create a folder for the feature inside `features/` at the project root. The naming convention is `YYYY-MM-DD-short-feature-name`. Example:

```
features/2026-05-25-invoice-reminders/
```

This folder will hold every artifact the chain produces. By the end of a successful run, it will contain ten or eleven items — one per chain step plus subdirectories for documentation and packaging. That folder *is* the audit trail.

### Shared knowledge bundle

Before running any feature, confirm the shared knowledge bundle is in place and current. The bundle lives outside the per-feature folder and is referenced by every Project's knowledge base:

```
js-saas-factory-knowledge/
├── conventions/
├── compliance/
├── examples/
├── workflow/
└── stack/
```

If any of those files have changed since your last feature run, re-upload them to the affected Projects' knowledge bases. Out-of-date conventions are the single most common source of drift across the factory.

### Compliance check

Before running a feature through the chain that touches PHI, MLR-reviewed content, validated systems, or anything in `do-not-modify.md`, confirm with your IT/security/compliance stakeholders that Claude Projects use is approved for that material and that the plan's data-retention settings are appropriate. This check is per-feature, not one-time.

### The four human approval gates

The chain has four points where you stop and decide whether to continue:

| Gate | After | What you decide |
|---|---|---|
| **Gate 1** | Story Writer | Is this the right problem, with testable criteria? |
| **Gate 2** | Spec Writer | Is the design safe, complete, and aligned with existing infrastructure? |
| **Gate 3** | Validate | Are critical and important findings resolved, and compliance flags addressed? |
| **Gate 4** | Package | Does the package actually build cleanly, with no secrets and a correct version? |

Everything else is automation. The four gates are where your judgement is required.

---

## Section 1 — Researcher

**Purpose:** Map relevant code, identify patterns, surface risks. Read-only.

**Open the Project:** *Researcher*

**Approval gate:** No

**Inputs to paste/upload:**

- The feature idea, in 1–3 sentences (write this fresh; do not borrow from a prior feature)
- Any existing code files relevant to the area being changed. If the codebase is too large to upload in full, upload only the directories most likely to be affected.
- If the work is greenfield (no existing codebase), say so explicitly. The Researcher will produce a proposed structure instead of a relevant-files list.

**What the Researcher produces:** A single Markdown response under 500 words, in seven fixed sections — relevant files, existing patterns, similar feature examples, risks, recommended plan, tests to update or add, open questions.

**Before saving, check:**

- Are the cited file paths real, or has the Researcher invented any?
- Has anything in `do-not-modify.md` been flagged? If yes, escalate before continuing.
- Are the "similar feature examples" actually similar, or is the Researcher reaching?

**Save the output as:** `01-research.md`

**Hand off to:** Story Writer (next section)

**Pass forward to the next Project:**

- The original feature idea (verbatim, the same 1–3 sentences)
- The contents of `01-research.md`

---

## Section 2 — Story Writer

**Purpose:** Turn the feature idea plus research findings into a clear, testable user story.

**Open the Project:** *Story Writer*

**Approval gate:** **Gate 1**

**Inputs to paste:**

- The original feature idea
- The full contents of `01-research.md`
- Any business rules or constraints you want enforced (write these explicitly — do not assume the Story Writer knows them)

**What the Story Writer produces:** One user story, under one page, in six fixed sections — user story sentence, acceptance criteria, edge cases, compliance considerations, out of scope, open questions.

**Gate 1 review — four questions:**

1. Is this the right problem? Has the story drifted into a different problem from what you actually want to solve?
2. Are the acceptance criteria testable? Can each be verified by a test, or are some too vague to confirm?
3. Are the business rules correct? If the Story Writer made assumptions about unstated rules, are they right?
4. Is anything missing? Edge cases, compliance touches, permissions, accessibility — has the story acknowledged them, even if only to put them out of scope?

**Three possible outcomes at Gate 1:**

- **Approve** → save and proceed.
- **Request changes** → reply with what to change in the same conversation. The Story Writer produces a full revised story. Iterate until correct.
- **Reject** → stop the chain. The feature needs reshaping before it can be storied at all. Save what was explored so you can return to it later.

**Save the approved output as:** `02-story.md`

**Hand off to:** Spec Writer (next section)

**Pass forward to the next Project:**

- The full contents of `01-research.md`
- The full contents of the approved `02-story.md`

---

## Section 3 — Spec Writer

**Purpose:** Turn the approved story plus research findings into an actionable technical brief.

**Open the Project:** *Spec Writer*

**Approval gate:** **Gate 2**

**Inputs to paste:**

- The full contents of `01-research.md`
- The full contents of the approved `02-story.md`
- Any stack confirmations or deviations from `target-stack-spec.md` (most features will use the default stack; only flag exceptions)

**What the Spec Writer produces:** A Markdown brief under two pages, in eight fixed sections — stack used, data model changes, flow, API changes, frontend changes, tests required, risks and open questions, files that will change or be created.

**Gate 2 review — five questions:**

1. Does it reuse existing infrastructure? Or has the Spec Writer proposed something new that duplicates what already exists?
2. Is tenant isolation explicit? Section 7 must say *how* isolation is enforced, not just imply it.
3. Are the failure paths real? Section 6 should list failure cases from the story plus the obvious technical ones (auth failure, tenant boundary, validation).
4. Are the file paths credible? Section 8 should match the conventions in the knowledge base and the patterns identified by the Researcher.
5. Has anything in `do-not-modify.md` been touched? If yes, that is a hard stop — escalate before approving.

**Three possible outcomes at Gate 2:**

- **Approve** → save and proceed.
- **Request changes** → reply with what to change. The Spec Writer produces a full revised brief. Iterate.
- **Reject** → stop the chain. Keep the approved story so you can resume later with a different technical approach.

**Save the approved output as:** `03-spec.md`

**Hand off to:** Backend Builder (next section)

**Pass forward to the next Project:**

- The full contents of `01-research.md`
- The full contents of `03-spec.md`
- Optionally, one or two existing backend feature files for pattern reference

---

## Section 4 — Backend Builder

**Purpose:** Produce backend code (services, API routes, jobs, schemas) and unit tests.

**Open the Project:** *Backend Builder*

**Approval gate:** No

**Inputs to paste:**

- The full contents of `03-spec.md`
- The full contents of `01-research.md`
- Optionally, upload one or two existing backend feature files the Builder should pattern-match against

**What the Backend Builder produces:**

1. A scope restatement (2–3 bullets) — read this before code streams
2. A pattern identification section — confirm patterns are correct before code streams
3. Code files, one per artifact in the side panel, each with full path and explanation
4. Unit tests, in the same per-artifact format
5. A summary including the API contract (this is critical — the Frontend Builder consumes it)

**Before code streams, check:**

- Does the scope restatement match the brief?
- Are the named patterns the ones your codebase actually uses?

**After code is produced:**

- Save each code file artifact to the path the Builder specifies, into your working folder
- Run locally: `pnpm install && pnpm typecheck && pnpm lint && pnpm test`
- If anything fails, paste the failure back into the same conversation and ask for a fix
- Do not move on until the backend is green

**Critical: confirm the API contract in the summary is complete.** Every endpoint must have HTTP method, exact path, auth requirement, request body shape, success response shape and status, each distinct error response shape and status. If any of these are vague, ask the Builder to tighten the summary before moving on. The Frontend Builder will guess if the contract is vague, and the guesses will be wrong.

**Save the summary as:** `04-backend-summary.md`

**Hand off to:** Frontend Builder (next section)

**Pass forward to the next Project:**

- The full contents of `01-research.md`
- The full contents of `03-spec.md`
- The full contents of `04-backend-summary.md` — **the most important input for the Frontend Builder**
- Optionally, one or two existing frontend feature files for pattern reference

---

## Section 5 — Frontend Builder

**Purpose:** Produce frontend code (components, pages, hooks, state) and component tests, consuming the API contract from the Backend Builder.

**Open the Project:** *Frontend Builder*

**Approval gate:** No

**Inputs to paste:**

- The full contents of `01-research.md`
- The full contents of `03-spec.md`
- The full contents of `04-backend-summary.md`
- Optionally, upload one or two existing frontend feature files

**What the Frontend Builder produces:**

1. A scope and API contract restatement — **read this carefully**. If the Builder has misread the API contract, every component built on it will be wrong.
2. A pattern identification section — confirm patterns match your codebase
3. Code files, one per artifact in the side panel
4. Component tests, in the same per-artifact format
5. A summary including routes added, components reused, accessibility decisions made, and new dependencies (if any)

**Before code streams, check:**

- Does the API contract restatement match `04-backend-summary.md` exactly?
- Are the named patterns the ones your frontend codebase actually uses?

**After code is produced:**

- Save each artifact to the path the Builder specifies
- Run locally: `pnpm install && pnpm typecheck && pnpm lint && pnpm test`
- **If a failure is a backend-frontend mismatch, do not patch on the frontend.** Go back to the Backend Builder, fix there, regenerate the backend summary, and re-feed it to a fresh Frontend Builder conversation. Frontend patches for backend bugs are the biggest source of drift in the chain.

**If the Frontend Builder surfaces an API mismatch** (the API works for the backend but is awkward for the UI), you have three options:

1. **Adjust the backend** — best when the mismatch reflects a real design issue.
2. **Adjust the frontend** — reasonable when the backend shape is dictated by an external system you do not control (a Stripe webhook payload, a Veeva API response).
3. **Adjust the brief** — if the mismatch reveals a deeper design problem, escalate to the Spec Writer.

You make the call. The Frontend Builder's job is to flag the mismatch, not to choose.

**Save the summary as:** `05-frontend-summary.md`

**Hand off to:** Test (next section)

**Pass forward to the next Project:**

- The full contents of the approved `02-story.md`
- The full contents of `03-spec.md`
- The full contents of `04-backend-summary.md`
- The full contents of `05-frontend-summary.md`

---

## Section 6 — Test

**Purpose:** Write acceptance tests against the approved story, plus produce a coverage report.

**Open the Project:** *Test*

**Approval gate:** No

**Inputs to paste:**

- The full contents of `02-story.md`
- The full contents of `03-spec.md`
- The full contents of `04-backend-summary.md`
- The full contents of `05-frontend-summary.md`

**What the Test Project produces:**

1. Test files, one per artifact in the side panel
2. A coverage report in a fixed structure:
   - **ACCEPTANCE CRITERIA COVERED** — each criterion mapped to the test(s) covering it
   - **ACCEPTANCE CRITERIA NOT COVERED** — each uncovered criterion with the reason ("All criteria covered" if none)
   - **EDGE CASES COVERED** — each edge case mapped to its test(s)
   - **EDGE CASES NOT COVERED** — uncovered edge cases with reasons
   - **LIKELY DEFECTS NOTICED WHILE WRITING TESTS** — defects routed back to the appropriate builder ("No likely defects noticed" if none)

**Run the tests locally.** When tests fail, classify the failure:

| Failure type | What to do |
|---|---|
| Test bug (the test is wrong) | Fix in the same Test conversation |
| Backend bug | Go back to Backend Builder, paste the failing test, ask for a fix |
| Frontend bug | Go back to Frontend Builder, paste the failing test, ask for a fix |
| Brief gap (the brief itself missed something) | Escalate to Spec Writer — this is rare but important |

Do not move on to Validate until tests pass.

**Save the coverage report as:** `06-test-report.md`

**Hand off to:** Validate (next section)

**Pass forward to the next Project:**

- The full contents of `02-story.md`
- The full contents of `03-spec.md`
- The full backend code (paste from the Backend Builder's artifacts, or upload the saved files)
- The full frontend code (same)
- The full contents of `06-test-report.md`
- Optionally, the backend and frontend summaries for cross-reference

---

## Section 7 — Validate

**Purpose:** Compare the implementation against the approved story and brief. Report gaps without fixing them.

**Open the Project:** *Validate*

**Approval gate:** **Gate 3**

**Inputs to paste:**

- The full contents of `02-story.md`
- The full contents of `03-spec.md`
- The full backend code
- The full frontend code
- The full contents of `06-test-report.md`

**What the Validate Project produces:** A Markdown findings report in five fixed sections:

1. **CRITICAL** — must fix before merge (with file paths and line numbers)
2. **IMPORTANT** — should fix before merge
3. **MINOR** — nice to have (marked "(opinion)" if subjective)
4. **COMPLIANCE FLAGS** — anything that may touch PHI, MLR, audit trails, validated systems, or accessibility — even when uncertain
5. **NEXT-STEP RECOMMENDATION** — which role should act on the findings, in what order

**Gate 3 review — five questions:**

1. Are the critical findings actually critical, or has the validator over-classified?
2. Are the important findings genuinely important, or are they stylistic preferences?
3. Are the compliance flags surfaced? (A silent compliance section on a feature that touches PHI is suspicious — re-run with explicit compliance context.)
4. Is the next-step recommendation actionable? "Backend Builder to add tenant check in route X" is actionable. "Several improvements needed" is not.
5. Has the validator stayed in its lane? It should never have produced code, fixes, or refactored examples.

**Three possible paths after Gate 3:**

- **No critical or important findings, compliance flags resolved** → approve and proceed to Documentation.
- **Critical or important findings exist** → loop back to the appropriate role (the recommendation tells you which), apply the fix, re-run the affected downstream roles (typically Test, then Validate again).
- **Compliance flags exist** → resolve with the appropriate stakeholder before proceeding, even if no critical findings exist. A compliance flag with no critical finding is still a stop.

**Re-validation:** When the chain loops back for fixes, save each new validation pass with an incrementing suffix — `07-validation-v2.md`, `07-validation-v3.md`, and so on. **Never overwrite earlier validation reports.** The progression from initial findings to clean validation is part of the audit trail.

**Save the final clean validation as:** `07-validation.md` (or the latest versioned file if multiple passes happened)

**Hand off to:** Documentation (next section)

**Pass forward to the next Project:**

- The full contents of `02-story.md`
- The full contents of `03-spec.md`
- The full contents of `04-backend-summary.md`
- The full contents of `05-frontend-summary.md`
- The full contents of `06-test-report.md`
- The full contents of the final `07-validation.md`

---

## Section 8 — Documentation

**Purpose:** Produce README, API reference, user guide, architecture notes, and a changelog entry.

**Open the Project:** *Documentation*

**Approval gate:** No

**Inputs to paste:**

- All six inputs listed in the previous section's "Pass forward" list

**What the Documentation Project produces:** Five Markdown documents, each as a separate artifact:

1. `README.md` — project root, stack, prerequisites, setup, run, test, build, folder structure
2. `docs/api.md` — technical API reference (pulled verbatim from `04-backend-summary.md`)
3. `docs/user-guide.md` — plain-language walkthrough for non-developers
4. `docs/architecture.md` — design decisions, data flow, key trade-offs, ongoing maintenance notes
5. `CHANGELOG.md` entry — Keep-a-Changelog format, one-line user-facing description

**Review the docs — five questions:**

1. Does the README actually run? If you followed the setup steps in a clean environment, would the app start?
2. Does the API doc match the backend summary exactly? Endpoints, methods, schemas, status codes.
3. Can a non-developer follow the user guide? Read it as if you were a customer success person.
4. Does the architecture doc record decisions, not just describe code? It should say *why*, not just *what*.
5. Does the changelog entry tell the user what changed for them, in user-facing language?

If any answer is no, ask for a revision in the same conversation. Do not hand-edit — that creates drift.

**Save each document into:** `08-documentation/` inside the feature folder:

```
features/2026-05-25-invoice-reminders/08-documentation/
├── README.md
├── docs/
│   ├── api.md
│   ├── user-guide.md
│   └── architecture.md
└── CHANGELOG-entry.md
```

**Compliance note:** If your team's user-facing documentation goes through MLR review, treat `user-guide.md` as draft content. The chain produces it; the review process approves it. Mark this clearly in the document header.

**Hand off to:** Package (next section)

**Pass forward to the next Project:**

- All code files produced by the Backend Builder
- All code files produced by the Frontend Builder
- All test files produced by the Test Project
- All five documentation files
- The contents of `02-story.md` and `03-spec.md` for context
- The final clean `07-validation.md`

---

## Section 9 — Package

**Purpose:** Produce the file manifest, build script, environment template, assembly instructions, and release checklist so the user can assemble the feature into a runnable, distributable archive locally.

**Open the Project:** *Package*

**Approval gate:** **Gate 4**

**Inputs to paste or upload:** This is the most input-heavy step. Provide every artifact the chain has produced — backend code, frontend code, tests, documentation, plus the story, brief, and final validation report for context.

**What the Package Project produces:** Eight artifacts, each as a separate file:

1. `FILE_MANIFEST.md` — every file in the package and where it goes
2. `package.json` — complete, install-ready, with dependencies derived from what the produced code actually uses
3. `.env.example` — all required environment variables with placeholder values
4. `.gitignore` — standard plus project-specific
5. `README.md` — packaging-specific (references the Documentation Project's README or merged with it)
6. `build-package.sh` AND `build-package.ps1` — cross-platform build scripts
7. `ASSEMBLY_INSTRUCTIONS.md` — step-by-step folder assembly with troubleshooting
8. `PACKAGE_CHECKLIST.md` — release verification checklist

**Important: The Package Project does NOT produce the `.zip` itself.** It produces the recipe. You run the build script locally to assemble the archive. This is deliberate — claude.ai Projects cannot package multi-file output, and the manifest-plus-script approach preserves audit traceability.

**Save all eight artifacts into:** `09-package/` inside the feature folder.

**Assembly steps (run locally):**

1. Follow `ASSEMBLY_INSTRUCTIONS.md` to copy every code, test, and documentation artifact into a fresh project folder on your machine (outside the `features/` folder).
2. Set up `.env` from `.env.example` with real values for your environment.
3. Run the build script: `./build-package.sh` on macOS/Linux or `.\build-package.ps1` on Windows.
4. Find the resulting `.zip` in `./dist/`.

**Gate 4 review — five questions:**

1. Does the build script actually run cleanly on your machine? A failed local build means the package is not ready, regardless of any other artifact.
2. Does `FILE_MANIFEST.md` list every file you saved from the chain? Missing file = broken install for the recipient.
3. Does `.env.example` cover every environment variable the code actually uses? A quick grep through the source for `process.env.` confirms.
4. Are there any secrets anywhere they should not be? Check `package.json`, `.env.example`, and skim source for credential-shaped strings.
5. Does the version number make sense? New feature = minor bump; bug fix = patch; breaking change = major.

**After Gate 4 approval:**

- Save a copy of the final `.zip` into `09-package/` alongside the recipe, or into your team's release archive
- Distribute the archive according to your team's normal process (release platform, client share, staging deployment)
- **Never include the `features/` audit trail in the distributable archive** — that is internal evidence and should never reach the client
- **Never include `.env` files — only `.env.example`** — the build script's `--production` flag excludes `.env`, but verify

---

## Per-feature folder, final state

After a successful chain run, the feature folder should look like this:

```
features/2026-05-25-invoice-reminders/
├── 00-feature-idea.md           # The original 1-3 sentence prompt
├── 01-research.md
├── 02-story.md
├── 03-spec.md
├── 04-backend-summary.md
├── 05-frontend-summary.md
├── 06-test-report.md
├── 07-validation.md             # Plus any -v2, -v3 if re-validation happened
├── 08-documentation/
│   ├── README.md
│   ├── docs/
│   │   ├── api.md
│   │   ├── user-guide.md
│   │   └── architecture.md
│   └── CHANGELOG-entry.md
└── 09-package/
    ├── FILE_MANIFEST.md
    ├── package.json
    ├── .env.example
    ├── .gitignore
    ├── README.md
    ├── build-package.sh
    ├── build-package.ps1
    ├── ASSEMBLY_INSTRUCTIONS.md
    └── PACKAGE_CHECKLIST.md
```

That folder is the audit trail. Every decision, every revision, every validation pass, every artifact — captured, dated, and saved.

---

## When the chain breaks

The chain will not always run cleanly on the first pass. Common breakages and how to recover:

| Symptom | Most likely cause | Where to fix |
|---|---|---|
| Researcher cites files that don't exist | Insufficient code uploaded; Researcher is guessing | Re-upload more context; restart the Researcher conversation |
| Story Writer keeps inventing business rules | Rules were never stated; Story Writer is filling gaps | Restart with rules stated explicitly in the input |
| Spec Writer proposes new infrastructure when something exists | Researcher findings were too shallow | Strengthen the Researcher (Section 1) before re-running Spec Writer |
| Backend Builder produces code in unfamiliar patterns | `example-backend-feature.md` is out of date | Update the example file; re-run Backend Builder |
| Frontend Builder invents API endpoints | Backend summary was vague | Tighten the API contract in `04-backend-summary.md`; restart Frontend Builder |
| Test Project misses acceptance criteria | Story criteria were not observable | Return to Story Writer; rewrite criteria as testable statements |
| Validator finds many critical issues | Builders ignored the brief, or brief was incomplete | Read the validator's recommendation; loop back to the named role |
| Documentation invents behaviour | Summaries from prior roles were thin | Strengthen the summary template upstream |
| Build script fails locally | `package.json` dependencies don't match the code | Restart the Package Project with the actual code files included |

Three meta-rules cover most of these:

1. **Fix problems upstream when you can.** If the Frontend Builder is confused, the issue is usually in the Backend Builder's summary. If the Backend Builder is producing odd patterns, the issue is usually the Spec Writer or the example files. The further upstream you fix, the less drift you have downstream.
2. **Restart conversations, don't patch them.** A polluted conversation is harder to recover than a fresh one with better inputs. The cost of restarting is one paste; the cost of patching a confused conversation is sometimes the rest of the day.
3. **Save your work as you go.** Every step's output goes into the per-feature folder immediately. If the chain breaks at step 7, you do not want to discover at step 9 that step 4's output was never saved.

---

## When to stop forcing the chain

The factory works well for most features. It does not work for everything. Stop and reach for a different tool when:

- **The feature spans more than one codebase.** The factory assumes one project per chain run. Multi-repo features need a different orchestration.
- **You're shipping more than three features per week through one chain.** At that point, the manual artifact handoff is the bottleneck. The upgrade path is Claude Code on top of Projects, not instead of it.
- **Multiple developers need to work on the same feature concurrently.** Projects don't coordinate; you'd need shared state which Projects only provides at the knowledge-base level.
- **The feature is exploratory, not buildable.** The chain assumes you know what you want to build. For "I don't know what this should be yet" work, use a normal claude.ai conversation, sketch, iterate, then come to the factory once you have a real feature idea.

The factory is a delivery mechanism. Use it for delivery. Use other tools for exploration, coordination, or scaling.

---

## Compliance — the orchestrator-level view

Compliance has been called out in each role file. From the orchestrator perspective, three reminders apply across the whole chain:

1. **The per-feature folder is the audit trail.** Treat it accordingly: dated, complete, saved alongside the feature, never overwritten. Old validation reports are not noise; they are evidence that the process caught and resolved issues.
2. **Claude Projects use must be approved for each kind of content.** PHI, MLR content, validated-system code, and client deliverables each carry their own approval considerations. Before processing any of those through the chain, confirm with IT/security/compliance.
3. **The chain produces deliverables; humans certify them.** The factory produces packages that look polished and ready. They are not yet approved. Gate 4 approval is a human responsibility, and external distribution requires the same approvals it would for any other release process.

---

## Tuning the factory over time

The factory tunes itself if you let it. Three habits make that happen:

1. **After each feature, ask one question.** Where did the chain surprise you? An unexpected output, a missed pattern, a slow handoff. Trace it back to its source — usually a knowledge base file or a role's custom instructions — and update.
2. **Update knowledge base files, not role files, when possible.** Role files define behaviour; knowledge base files define context. Context changes far more often than behaviour. If a Project keeps making the same mistake, the lever is usually a knowledge base update.
3. **Keep role files tight.** The temptation to add "and also do X" to every role's custom instructions is real and dangerous. Long custom instructions get filtered or partially applied. Resist adding rules unless they prevent a real, recurring problem.

Over five or six features, the factory becomes specific to your team's actual conventions, your real codebase, and your particular regulated-adjacent context. That specificity is the asset. The factory ships only as much as the conventions and examples in its knowledge base allow.

---

## Reference index

| # | Project | File | Output filename | Gate |
|---|---|---|---|---|
| 1 | Researcher | `01-researcher.md` | `01-research.md` | — |
| 2 | Story Writer | `02-story-writer.md` | `02-story.md` | **Gate 1** |
| 3 | Spec Writer | `03-spec-writer.md` | `03-spec.md` | **Gate 2** |
| 4 | Backend Builder | `04-backend-builder.md` | `04-backend-summary.md` + code files | — |
| 5 | Frontend Builder | `05-frontend-builder.md` | `05-frontend-summary.md` + code files | — |
| 6 | Test | `06-test.md` | `06-test-report.md` + test files | — |
| 7 | Validate | `07-validate.md` | `07-validation.md` | **Gate 3** |
| 8 | Documentation | `08-documentation.md` | Five docs in `08-documentation/` | — |
| 9 | Package | `09-package.md` | Eight files in `09-package/` | **Gate 4** |

The nine role files (`01-researcher.md` through `09-package.md`) sit alongside this orchestrator in the factory's reference set. Each role file is the *configuration* for one Project; this orchestrator is the *operating manual* that ties them together.

Keep them together. They are a set.