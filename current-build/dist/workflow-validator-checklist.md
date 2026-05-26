# Validator Checklist

> **Location:** `js-saas-factory-knowledge/workflow/validator-checklist.md`
>
> **Purpose:** The explicit list of items every validation pass must check, with severity guidance and concrete examples for each level. The Validate Project mirrors this checklist on every run.
>
> **Audience:** Validate.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

The Validate Project reads this file at the start of every validation pass. The checks here are non-negotiable; the Validator works through each category and produces findings grouped by severity.

The single most important property of this file is that **severity is calibrated by example, not by description**. The category list tells the Validator *what* to check; the severity examples tell it *how seriously* to classify each finding. Calibration drift is the most common Validator failure — finding too many criticals (the team loses trust) or too few (real issues slip through).

This file pairs with:

- `07-validate.md` (the role file)
- All convention files (the rules being checked against)
- `compliance/regulated-environment-rules.md` and `compliance/do-not-modify.md` (compliance and protected items)

---

## 1. The check categories

Every validation pass works through all eight categories. Findings in any category can land in any severity bucket; the categories define *what* to check, not *how severe* a finding is.

### 1.1 Acceptance criteria coverage

Every criterion in the user story has a corresponding implementation in the code and a corresponding test in the test files.

**Cross-reference:**

- `02-story.md` → acceptance criteria
- Backend code → behavior matching each criterion
- Test files → at least one test per criterion

**Common findings:**

- A criterion that exists in the story but has no implementation
- A criterion that has implementation but no test
- A criterion that has a test but the test doesn't actually verify the criterion

---

### 1.2 Failure path coverage

Every failure path called out in section 6 of the brief has a corresponding test.

**Cross-reference:**

- `03-spec.md` → tests required section
- Test files → tests for each failure case

**Standard failure paths the Validator always checks for (whether or not the brief named them):**

- Authentication failure (401)
- Authorization / role failure (403 or 401, per team convention)
- Tenant boundary violation
- Validation failure (invalid input → 400)
- Resource not found (404)
- Conflict / idempotency (409)
- External service failure (the email service throws; the database throws)

**Common findings:**

- Only happy-path tests
- Tests for auth failure but not tenant boundary
- Tests for tenant boundary but no verification that side effects were NOT taken

---

### 1.3 Security and tenant safety

Authentication, authorization, tenant isolation, secrets, and exception handling at the API boundary.

**Specific checks:**

- Every protected route calls the right auth helper (`requireAuth`, `requireAdminInTenant`, etc.)
- Tenant isolation is enforced **at the service layer**, not only at the route (see `conventions/backend-conventions.md` section 5)
- `tenantId` is sourced from the authenticated session, never from request body
- No secrets appear in `package.json`, `.env.example`, source code, or logs
- No raw exceptions are returned to the client (stack traces, internal messages)
- No raw request payloads are logged (see `compliance/regulated-environment-rules.md` section 2.2)
- PHI-touching code paths don't log PHI, don't return PHI in error responses, don't put PHI in URLs

**Common findings:**

- Tenant check only at the route level (service called from a job/CLI would bypass it)
- `tenantId` read from request body instead of session
- Generic 500 returns the raw error message
- A new env var was added but `.env.example` wasn't updated

---

### 1.4 Pattern conformance

Code matches the conventions and the example feature files.

**Cross-reference:**

- `conventions/general-conventions.md`
- `conventions/js-conventions.md`
- `conventions/backend-conventions.md`
- `conventions/frontend-conventions.md`
- `conventions/testing-conventions.md`
- `examples/example-backend-feature.md`
- `examples/example-frontend-feature.md`
- `examples/example-test-suite.md`

**Specific checks:**

- File names follow the conventions (kebab-case for non-React, PascalCase for React components)
- Layering respected (routes thin, services own business logic, repositories own DB I/O only)
- Custom error classes defined for each known failure mode
- Structured logging with the required fields (`actorId`, `tenantId`, `resourceId`, `action`, `outcome`)
- TypeScript: no `any`, no `!` (non-null assertion), no `as` casts without `satisfies`
- Zod schemas at every API boundary
- Tests use builders, not inline setup
- Component tests use `getByRole` / `getByLabelText`, not `getByTestId`
- Server vs. Client Component split is correct (interactivity → client; static → server)

**Common findings:**

- Business logic in a route handler
- Repository function that filters by tenant (should be service's job)
- `any` used instead of `unknown` with narrowing
- Component test uses `getByTestId` instead of role-based queries

---

### 1.5 Scope conformance

No changes outside the agreed scope.

**Cross-reference:**

- `03-spec.md` → "Files that will change or be created" section
- The actual files modified in the PR

**Common findings:**

- Files modified that are not in the spec's file list
- A "small refactor" of unrelated code that the chain produced incidentally
- A new dependency added that wasn't justified in the brief
- Generated files committed when they should be gitignored

---

### 1.6 Compliance

PHI handling, audit trails, do-not-modify items, accessibility, vendor approval.

**Cross-reference:**

- `compliance/regulated-environment-rules.md`
- `compliance/do-not-modify.md`

**Specific checks:**

- No PHI in logs (anywhere — application logs, error tracking, audit logs)
- Audit log entries produced for the actions section 4 of `regulated-environment-rules.md` lists as audit-required
- No modifications to anything in `do-not-modify.md`
- Accessibility meets WCAG 2.2 AA per `conventions/frontend-conventions.md` section 6
- No new vendor introduced without approval (per `regulated-environment-rules.md` section 2.4)
- Test fixtures contain only synthetic data, never real PHI

**Common findings:**

- A code path that logs a raw request body (PHI risk)
- An admin action that does not produce an audit log entry
- A modal that traps focus but doesn't release it on close (accessibility)
- A new third-party service added without entry in the vendor approval table

---

### 1.7 Code quality

Idiomatic TypeScript, no duplication, clean diffs.

**Specific checks:**

- TypeScript types are real (no `any`, no stubbed `unknown` where a real type is possible)
- Zod schemas validate inputs at every API boundary
- No duplicate logic where a helper exists
- No dead code (commented-out blocks, unused imports, unused parameters)
- No `console.log` (ESLint should catch this; the Validator confirms)
- Reasonable PR size (a vertical slice, not a sprawling refactor)

**Common findings:**

- Two services with near-identical query logic (should share a repository function)
- An unused import left from a refactor
- A function that takes a `Date | string` because the author wasn't sure which the caller would pass

---

### 1.8 Documentation completeness

Documentation produced by the Documentation Project actually matches the as-shipped code.

**Cross-reference:**

- Documentation files in `08-documentation/`
- The actual code

**Specific checks:**

- The API doc lists every endpoint actually shipped
- The API doc's schemas match the Zod schemas in `src/schemas/`
- The README's setup steps produce a runnable project in a clean environment
- The user guide describes the feature as it actually works, not as originally planned
- The architecture doc reflects late changes (e.g., a tenant check added after a validator finding in an earlier pass)

**Common findings:**

- An endpoint exists in code but is missing from `api.md`
- The user guide describes a button label that was changed during the build
- The README's `pnpm install` step misses a new dependency

---

## 2. Severity classification

The four buckets — CRITICAL, IMPORTANT, MINOR, COMPLIANCE FLAGS — mean specific things. Use them correctly.

### 2.1 CRITICAL — must fix before merge

A merge with an open CRITICAL ships a known defect, security issue, or compliance violation. The team does not knowingly ship CRITICAL findings.

**Examples (calibrated for "critical"):**

- ✅ **Tenant boundary not enforced in service layer.** Route checks tenant; service does not. A background job or CLI calling the service would bypass the check. Cross-tenant data exposure risk. *(File: `src/services/reminders/trigger-manual-reminder.ts:14`)*
- ✅ **Raw request body logged.** `logger.info(req.body, ...)` in the route handler. The body may contain PHI. *(File: `src/app/api/.../route.ts:22`)*
- ✅ **Missing acceptance criterion.** Story acceptance criterion 3 ("duplicate reminders are not sent within 24 hours") has no corresponding code. The dedup check is absent.
- ✅ **`do-not-modify` item modified.** The reminder email template (`src/templates/email/reminder-email-template.tsx`) was changed. This is MLR-approved content and requires re-review.
- ✅ **Secret committed.** A real API key appears in `.env.example` (placeholder values only — real keys belong in the secrets manager).
- ✅ **Migration is destructive without a backfill plan.** Migration drops a column that contains existing data; no backfill or data preservation strategy in the brief.

**Counter-examples (NOT critical):**

- ❌ A typo in a log message — that is MINOR.
- ❌ A function that could be more concise — that is MINOR (and often opinion).
- ❌ A test that uses `getByTestId` when `getByRole` would have worked — that is IMPORTANT.
- ❌ An endpoint missing from `api.md` — that is IMPORTANT, not CRITICAL.

**Calibration rule:** if a senior engineer reading this finding would say "stop the merge," it's CRITICAL. If they'd say "fix this before next sprint," it's IMPORTANT. If they'd shrug, it's MINOR.

---

### 2.2 IMPORTANT — should fix before merge

Real quality problems that don't block merge in a pinch but should be fixed. If merged with an IMPORTANT open, it becomes a ticket that gets fixed immediately.

**Examples (calibrated for "important"):**

- ✅ **Missing test for a failure path.** The brief required a test for "email service failure leaves invoice unchanged"; no such test exists. The code does handle it correctly, but it's untested.
- ✅ **Pattern divergence from convention.** The new service uses `console.error` instead of the Pino logger. The behavior is similar; the convention isn't followed.
- ✅ **Accessibility issue with workaround available.** The Send button has a tooltip but no `aria-label`; users with screen readers hear "button" with no context. Fixable in 2 lines.
- ✅ **API doc missing an endpoint.** The endpoint works correctly but isn't documented; downstream consumers will be surprised.
- ✅ **Suboptimal query.** A query that does N+1 lookups instead of a single `findMany`. Will be slow at scale but works correctly for now.
- ✅ **New dependency without justification.** Brief did not call out the new package; the team's convention requires justification.

**Counter-examples (NOT important):**

- ❌ Tenant boundary bypassed — CRITICAL, not IMPORTANT.
- ❌ A variable name that could be clearer — MINOR.
- ❌ A pattern that diverges from convention but is clearly intentional and well-formed — MINOR or no finding at all (see section 3 below).

---

### 2.3 MINOR — nice to have

Small improvements that don't block merge and that reasonable people might disagree about. Safe to merge without fixing; safe to ignore if the team disagrees. Marked `(opinion)` if subjective.

**Examples (calibrated for "minor"):**

- ✅ **Helper could be extracted.** Two functions share three lines of similar logic. Extracting a shared helper would be cleaner but the duplication is small. *(opinion)*
- ✅ **Variable name could be clearer.** `result` could be `manualReminderResult` for clarity. *(opinion)*
- ✅ **Comment would help.** The non-obvious idempotency calculation in `wasRecentlySent` could use a one-line comment explaining the window. *(non-opinion — comments are encouraged by the conventions)*
- ✅ **Slightly inconsistent formatting.** A long parameter list is broken across lines differently than other examples in the codebase. *(Prettier should catch this; if it doesn't, it's MINOR.)*

**The `(opinion)` marker:** use it when reasonable people might disagree. A finding marked `(opinion)` is something the team can ignore without consequence.

---

### 2.4 COMPLIANCE FLAGS — verify with stakeholder

Different from the other three because **it does not classify severity at all**. It says: *"I noticed something that might matter under your compliance rules, and I am not the right judge of whether it does."*

Compliance flags get resolved by talking to the right person — IT, security, MLR review, legal — not by changing code unilaterally.

**Examples (calibrated for "flag, don't decide"):**

- ✅ **PHI may be in scope of a new code path.** The new `customerName` parameter to `sendReminderEmail` ultimately comes from a customer record. The compliance lead should confirm whether the existing PHI handling rules apply to this path.
- ✅ **MLR may require re-approval.** This feature triggers the existing reminder template at the 7-day threshold; the template was originally approved at 30 days. The MLR coordinator should verify whether re-review is required.
- ✅ **Audit trail boundary unclear.** The new service produces a structured log entry, but the team's audit trail rules in `regulated-environment-rules.md` section 4 distinguish between application logs and audit logs. Verify with security whether this action is audit-required.
- ✅ **New vendor not in the approval table.** The team's vendor table doesn't list the new service used by this feature. Recommend security lead confirms before merge.
- ✅ **Cross-tenant data in logs.** The tenant mismatch warning includes both the actor's tenant and the resource ID. Verify with compliance that the log format does not constitute a cross-tenant data leak in your retention setup.

**The "even if uncertain" rule:** the COMPLIANCE FLAGS section must always appear. If nothing applies, write "No compliance flags identified." Silence on compliance is treated as a skipped check.

**The Validator does NOT decide compliance.** It flags. Resolution requires a stakeholder.

---

## 3. What NOT to flag

Patterns that may look unusual but are deliberate, well-formed, or otherwise acceptable. Flagging these as findings creates noise that erodes the team's trust in the Validator.

### 3.1 New patterns that are intentional and well-formed

If the implementation uses a pattern not seen elsewhere in the codebase but the pattern looks intentional, well-formed, and consistent with the conventions — do not flag it as a finding. Codebases evolve; new patterns are how that evolution happens.

**The test:** would a senior engineer say "this is wrong" or "this is new but okay"? If the latter, do not flag.

### 3.2 Deviations from the brief that the user clearly intended

If the brief said "use X" and the code uses Y, but Y was clearly the intent (e.g., the user confirmed mid-build that Y was better), do not flag.

The exception: if the brief was approved at Gate 2 with X, and the change to Y wasn't documented anywhere, that's a scope finding — flag it.

### 3.3 Implementation details the brief left unspecified

If the brief said "use Zod for validation" but didn't specify how to structure the schema files, and the Builder chose a reasonable structure, do not flag the structure choice.

The exception: if the structure conflicts with a convention file, flag the convention conflict.

### 3.4 Stylistic preferences

If the code is correct, conformant, and well-tested but a particular variable name or function structure could be slightly nicer — that's MINOR with `(opinion)`. Do not promote stylistic preferences to IMPORTANT.

### 3.5 Findings that duplicate the linter

If ESLint catches a violation, do not duplicate it as a finding. The linter ran; the finding is already on the PR.

---

## 4. The findings report format

Every validation pass produces findings in this exact shape. The Validate role file (`07-validate.md`) defines the format; this section reinforces it.

```markdown
## CRITICAL (must fix before merge)
- <finding, with file path and line number where possible>
- <or "No critical findings.">

## IMPORTANT (should fix before merge)
- <finding>
- <or "No important findings.">

## MINOR (nice to have)
- <finding, marked "(opinion)" if subjective>
- <or "No minor findings.">

## COMPLIANCE FLAGS (verify with stakeholder)
- <anything that may touch PHI, MLR, audit trails, validated systems,
  accessibility, or do-not-modify — even if uncertain>
- <or "No compliance flags identified.">

## NEXT-STEP RECOMMENDATION
- <which role acts next, in what order>
```

**The four "no finding" lines are mandatory.** Silence is not allowed. "No critical findings" is the positive record that critical was checked. A missing line is indistinguishable from a skipped check.

---

## 5. Examples of complete findings reports

### 5.1 Clean report (no issues found)

```markdown
## CRITICAL (must fix before merge)
- No critical findings.

## IMPORTANT (should fix before merge)
- No important findings.

## MINOR (nice to have)
- The constant `OVERDUE_THRESHOLD_DAYS` is defined in two files
  (`helpers.ts` and `send-overdue-reminders.ts`) with the same value.
  Extracting to a single source would prevent drift if the value
  changes. *(opinion)* *(File: `src/services/reminders/helpers.ts:2`
  and `src/services/reminders/send-overdue-reminders.ts:8`)*

## COMPLIANCE FLAGS (verify with stakeholder)
- **MLR re-approval:** the existing reminder email template is approved
  for invoices over 30 days overdue; this feature triggers at 7 days.
  The brief flagged this as an open question at Gate 2; recommend the
  MLR coordinator confirms re-review is not required before merge.

## NEXT-STEP RECOMMENDATION
- Address the compliance flag with the MLR coordinator. Once confirmed,
  the PR is ready to merge. The minor finding is optional and can be
  deferred if the team prefers.
```

### 5.2 Report requiring rework

```markdown
## CRITICAL (must fix before merge)
- **Tenant boundary not enforced in service layer.** The route handler
  verifies the admin's session tenant matches, but the
  `triggerManualReminder` service does not re-check after fetching the
  invoice. A future caller from a background job or CLI would bypass
  the check entirely. Recommend Backend Builder add the check at the
  start of the service, after the not-found check.
  *(File: `src/services/reminders/trigger-manual-reminder.ts:14`)*

- **Test missing for tenant boundary failure path.** Acceptance
  criterion 3 (story `02-story.md`) requires tenant isolation; the
  test suite has no test for the cross-tenant case. Recommend Test
  Project add the test once the CRITICAL fix is in place.

## IMPORTANT (should fix before merge)
- **Endpoint missing from `api.md`.** `POST /api/admin/invoices/:id/remind`
  is implemented but absent from the API documentation. Recommend
  Documentation Project regenerate `api.md` from the corrected
  `04-backend-summary.md`.

- **Accessibility: button has no unique accessible name.** Multiple
  "Send reminder" buttons on the page; all share the same accessible
  name. Recommend Frontend Builder add `aria-label` with the invoice
  ID per `examples/example-frontend-feature.md` section 3.9.
  *(File: `src/app/(admin)/invoices/_components/SendReminderButton.tsx:24`)*

## MINOR (nice to have)
- **Function could be extracted.** The 24-hour window calculation is
  duplicated inline in both the service and the helpers file. Extracting
  to a single source would prevent drift. *(opinion)*

## COMPLIANCE FLAGS (verify with stakeholder)
- No compliance flags identified.

## NEXT-STEP RECOMMENDATION
- Backend Builder to add tenant check in
  `src/services/reminders/trigger-manual-reminder.ts:14`.
- Frontend Builder to add `aria-label` per the example.
- Test Project to add the cross-tenant test after the backend fix.
- Documentation Project to regenerate `api.md` last.
- Re-run validation. Save as `07-validation-v2.md`.
```

---

## 6. Tuning notes

- **If the Validator keeps over-classifying findings as CRITICAL**, sharpen the severity examples in section 2 — particularly the "counter-examples" lines that say what each level is NOT.
- **If the Validator keeps producing empty COMPLIANCE FLAGS sections on features that should have flags**, the issue is usually that `regulated-environment-rules.md` is too abstract. Make the rules there more concrete and specific.
- **If the Validator keeps proposing fixes inside findings**, reinforce the rule in `07-validate.md` that the Validator finds, does not fix. The recommendation section routes findings to the right role; it does not describe how to fix anything.
- **If findings are missing file paths and line numbers**, reinforce that requirement. Vague findings produce vague recommendations.
- **If the same kind of finding shows up across many features**, the upstream lever is usually a convention file or example file — not this checklist.

---

## 7. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |