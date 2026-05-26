# Project 7 — Validate

> **Role in the chain:** Step 7 of 9. Runs after the Test Project.
> **Human approval gate:** **Yes — Gate 3**
> **Output saved as:** `07-validation.md` in the per-feature folder

---

## Purpose

The Validate Project compares what was actually built against what the approved story and brief said should be built. It reports gaps — missing acceptance criteria, security issues, scope creep, pattern inconsistencies, compliance concerns — and never proposes fixes.

This role exists because every prior role in the chain has a built-in bias toward producing output. The Researcher wants to find patterns; the Story Writer wants to write a story; the Builders want to ship code; the Test Project wants to write tests. None of those roles are well-positioned to step back and ask *"does this whole thing actually match what we agreed to build?"* The Validate Project is the only role in the chain whose job is to find things, not to make things.

The Validate Project never edits files, never produces code, never suggests how to fix what it finds, and never reruns prior steps. It produces findings; you decide what to do with them.

---

## Inputs

The Validate Project expects to receive:

- The approved user story (`02-story.md`)
- The approved technical brief (`03-spec.md`)
- The full code that was produced (paste from both Builders)
- The Test Project's coverage report (`06-test-report.md`)
- Optionally, the Backend and Frontend builder summaries for cross-reference

It reads from its knowledge base on every run:

- `general-conventions.md`
- `js-conventions.md`
- `backend-conventions.md`
- `frontend-conventions.md`
- `testing-conventions.md`
- `regulated-environment-rules.md`
- `do-not-modify.md`
- `validator-checklist.md`

---

## Outputs

A single Markdown findings report with five sections in fixed order, saved as `07-validation.md` in the feature folder. The report drives **Gate 3** — the third and most important human approval point in the chain.

The five sections are:

1. **CRITICAL** — must fix before merge
2. **IMPORTANT** — should fix before merge
3. **MINOR** — nice to have (marked "(opinion)" if subjective)
4. **COMPLIANCE FLAGS** — anything that may touch PHI, MLR, audit trails, validated systems, or accessibility — even if uncertain
5. **NEXT-STEP RECOMMENDATION** — which role should act on the findings, in what order

---

## Knowledge base files to upload

Upload these into the Validate Project's knowledge base:

| File | Purpose |
|---|---|
| `general-conventions.md` | Commits, branches, PRs, no-secrets, naming |
| `js-conventions.md` | Node version, package manager, tsconfig, ESLint, Prettier |
| `backend-conventions.md` | API layer rules, service layer, error handling, logging |
| `frontend-conventions.md` | Component structure, state, styling, accessibility |
| `testing-conventions.md` | Test runner, structure, builders, naming |
| `regulated-environment-rules.md` | PHI, MLR, audit trails, do-not-log lists |
| `do-not-modify.md` | Approved templates, validated systems |
| `validator-checklist.md` | The explicit checklist this Project applies to every review |

This is the second-largest knowledge base in the factory (after the Spec Writer's). The Validate Project needs broad context because its job is to compare the implementation against every standard the codebase enforces. `validator-checklist.md` is the single most important file here — it is the explicit list of things every validation pass must check. Spend time on it.

---

## Custom instructions

Paste the block below into the Validate Project's **Custom Instructions** field.

```
You are a strict implementation reviewer. You compare the code
that was produced against the approved story and technical brief,
and report what is missing, wrong, or risky. You never propose
fixes — your job is to find things, not change them.

Inputs:
- The approved user story
- The approved technical brief
- The full code that was produced (paste from Backend Builder
  and Frontend Builder)
- The Test Project's report

If any of these inputs are missing, refuse to validate and ask
for the missing input first. A validation pass with incomplete
inputs is worse than no validation pass.

Produce findings in this exact format:

CRITICAL (must fix before merge)
- <finding, with file path and line number where possible>

IMPORTANT (should fix before merge)
- <finding>

MINOR (nice to have)
- <finding, marked "(opinion)" if subjective>

COMPLIANCE FLAGS (verify with stakeholder)
- <anything that may touch PHI, audit trail expectations, MLR,
  validated systems, accessibility, or do-not-modify.md — even
  if you're not sure>

NEXT-STEP RECOMMENDATION
- <e.g., "Backend Builder to add tenant check in route X, then
  Test to add the matching test, then re-run this validation">

Always check:
- Every acceptance criterion is implemented (cross-reference
  the user story against the produced code)
- Every failure path has test coverage (cross-reference the
  brief's "Tests required" section against the test report)
- Auth and tenant isolation present where required, AND
  enforced at the service layer not just the route layer
- No secrets, raw payloads, or full exceptions in logs or
  client-facing responses
- Patterns match conventions and example features
- No duplicate logic where a helper exists
- No changes outside agreed scope (files outside the brief's
  "Files that will change" list)
- Timezone, accessibility (WCAG 2.2 AA), and multi-tenant
  concerns from the brief are addressed
- TypeScript types are real and not stubbed with `any` or
  `unknown` where a real type is possible
- Zod schemas validate inputs at API boundaries
- Anything from do-not-modify.md has not been modified
- Anything from regulated-environment-rules.md has been
  honored

Behaviour rules:
- Never propose fixes. Just report. The recommendation section
  routes findings to the right role; it does not describe how
  to fix anything.
- Cite file paths and line numbers wherever possible. "Tenant
  check missing" is less useful than "Tenant check missing in
  services/reminders/send-overdue.ts line 42."
- Mark opinion-based findings clearly with "(opinion)" so they
  can be ignored if the team disagrees.
- If you find no critical or important issues, say so plainly:
  "No critical findings." "No important findings." Do not
  invent findings to look thorough.
- If the implementation uses a pattern you have never seen
  before but the pattern looks intentional and well-formed,
  do not flag it as a minor finding. New patterns are how
  codebases evolve.
- When uncertain about a compliance question, flag it for
  stakeholder verification. Do not guess "this is probably
  fine" — flag it.
- The COMPLIANCE FLAGS section must always appear. If nothing
  applies, write "No compliance flags identified." Silence on
  compliance is not acceptable.
- Do not re-run prior roles' work. You are reviewing, not
  building or testing. If a finding requires more
  investigation than reading the code allows, surface it as a
  finding and route it to the right role.
```

---

## How to use this Project in the workflow

1. **Open the Validate Project** in claude.ai.
2. **Start a new conversation.** Always start fresh.
3. **Paste the inputs** in this order:
   - The approved user story (`02-story.md`)
   - The approved technical brief (`03-spec.md`)
   - The Backend Builder's output (all code files plus `04-backend-summary.md`)
   - The Frontend Builder's output (all code files plus `05-frontend-summary.md`)
   - The Test Project's coverage report (`06-test-report.md`)
4. **Read the findings carefully.** Pay particular attention to the COMPLIANCE FLAGS section and the NEXT-STEP RECOMMENDATION.
5. **Save the findings** as `07-validation.md` in the feature folder.
6. **Gate 3 — approval decision.** This is the most consequential gate in the chain. You have three paths:
   - **No critical or important findings** → approve and proceed to Documentation.
   - **Critical or important findings exist** → loop back to the appropriate role (the recommendation tells you which one), apply the fix, re-run the relevant downstream roles (typically Test, then Validate again), and re-evaluate.
   - **Compliance flags exist** → resolve them with the appropriate stakeholder before proceeding, even if no critical findings exist. A compliance flag with no critical finding is still a stop.
7. **Re-validate after fixes.** Save the second validation as `07-validation-v2.md`, the third as `07-validation-v3.md`, and so on. The history matters — do not overwrite earlier validations.
8. **Hand off to the Documentation Project** only when the validation comes back clean of critical and important findings, and compliance flags have been resolved.

---

## What "Gate 3" really checks

Gate 3 is where the chain proves the feature is ready to ship. When you review the validation report before approving, you are answering five questions:

1. **Are the critical findings actually critical?** Sometimes the validator over-classifies. Read each critical finding and confirm it would genuinely block a merge in your team's standards.
2. **Are the important findings genuinely important?** Same exercise. Important findings should be things that would degrade quality, performance, security, or maintainability — not stylistic preferences.
3. **Are the compliance flags surfaced?** A clean validation report with no compliance flags on a feature that touches PHI is suspicious. If your gut says compliance should have applied and the report is silent, re-run with explicit compliance context.
4. **Is the next-step recommendation actionable?** "Backend Builder to add tenant check in route X" is actionable. "Several improvements needed" is not. If recommendations are vague, ask for specifics.
5. **Has the validator stayed in its lane?** The validator should never have produced code, fixes, or refactored examples. If it did, re-run with stronger instructions — fixing things from a validation conversation breaks the audit trail.

If the answer to all five is yes and there are no unresolved criticals or compliance flags, approve. If not, loop back to the appropriate role.

---

## Severity classifications explained

The validator's four severity buckets are not interchangeable. Each one means something specific, and using them correctly is what makes the report useful.

**CRITICAL** — *must fix before merge*. The feature does not meet its acceptance criteria, the code has a security or data-integrity issue, tenant isolation is broken, or a do-not-modify item has been touched. A merge with an open CRITICAL is a known defect shipping to production.

**IMPORTANT** — *should fix before merge*. The feature meets its criteria but has a real quality problem: a missing test for a failure path, a pattern that diverges from the codebase without justification, an accessibility issue, a logging issue. Could be merged in a pinch but should not be — and if it is, the IMPORTANT becomes a ticket that gets fixed immediately.

**MINOR** — *nice to have*. Small improvements: a cleaner variable name, a helper that could be extracted, a comment that would help future readers. Often marked "(opinion)" because reasonable people disagree. Safe to merge without fixing; safe to ignore if the team disagrees.

**COMPLIANCE FLAGS** — *verify with stakeholder*. Different from the other three because it does not classify severity at all. It says: *"I noticed something that might matter under your compliance rules, and I am not the right judge of whether it does."* Compliance flags get resolved by talking to the right person — IT, security, MLR review, legal — not by changing code unilaterally.

A common failure mode: validators that flag everything as critical because critical sounds important. If your validator does this, sharpen `validator-checklist.md` with concrete examples of each severity level. The example is what shapes future classifications.

---

## What happens after a non-clean validation

A non-clean validation is the most common outcome of the first validation pass on any non-trivial feature. Handling it well is what separates a working factory from a stalled one.

The recommendation in the validation report tells you which role to loop back to. Common patterns:

- **Backend Builder fix** → re-run Backend Builder with the failing finding, regenerate `04-backend-summary.md` if the API contract changed, re-run Test if the contract changed, re-run Validate.
- **Frontend Builder fix** → re-run Frontend Builder with the failing finding, re-run Test if a UI behavior changed, re-run Validate.
- **Test gap** → re-run Test Project with the missing coverage explicitly called out, re-run Validate.
- **Spec gap** → escalate to Spec Writer. This is rare but important: it means the brief itself was missing something, and the chain needs to re-validate the brief through Gate 2 before downstream work continues.
- **Multiple roles** → handle them in dependency order: spec → backend → frontend → test → validate. Do not parallelize fixes that depend on each other.

Save every validation pass with an incrementing suffix (`07-validation.md`, `07-validation-v2.md`, etc.). The history is the audit trail. Three validation passes on a complex feature is not a failure — it is exactly what the chain is designed to surface.

---

## Tuning notes

- The single biggest lever for validation quality is `validator-checklist.md`. It is the explicit list the Project applies to every review. If validations keep missing the same kind of issue, add it to the checklist. If validations keep over-flagging stylistic preferences, soften the checklist accordingly.
- If the validator keeps producing code or fixes despite the "never propose fixes" rule, sharpen the rule with a concrete example: "If you find a missing tenant check, write 'Tenant check missing in <file>:<line>, recommend Backend Builder to add.' Do NOT write the corrected code."
- If validations come back clean too easily on features that should have findings, the issue is usually that the validator is reading the brief too charitably. Strengthen the cross-reference rule: every acceptance criterion in the story must be matched to specific code in the implementation.
- If the COMPLIANCE FLAGS section keeps coming back empty on features that should have flags, the issue is usually that `regulated-environment-rules.md` is too abstract. Make it concrete: "If the code logs anything that might contain PHI, flag it. If the code stores anything in a column not marked as PHI-safe, flag it."
- If next-step recommendations are vague, the issue is usually that the validator is not citing file paths and line numbers. Strengthen that rule — specific findings produce specific recommendations.

---

## Compliance reminder

The Validate Project's report is the single most important document for compliance review of any feature. Three things matter:

1. **The COMPLIANCE FLAGS section must always appear, even when empty.** "No compliance flags identified" is the positive record that compliance was considered. A missing section reads exactly like a skipped check, and in audit contexts the two are treated the same.
2. **Compliance flags get resolved with stakeholders, not in code.** The validator's job is to surface concerns; it is not qualified to judge whether a particular pattern meets MLR requirements or HIPAA expectations. When a compliance flag fires, route it to the right person before continuing the chain.
3. **Every validation pass is saved, not overwritten.** If a feature needs three validation passes, you should have `07-validation.md`, `07-validation-v2.md`, and `07-validation-v3.md`. The progression from findings to clean-bill-of-health is the evidence that the process worked. Overwriting the early reports erases that evidence.

Before saving any validation report into a context that will be reviewed externally (a client deliverable, an internal audit pack), confirm with your IT/security/compliance stakeholders that Claude Projects use is approved for the material being processed, and that the findings have been reviewed by a qualified human in addition to whatever automated review the chain produced. The validator surfaces concerns; it does not certify compliance.