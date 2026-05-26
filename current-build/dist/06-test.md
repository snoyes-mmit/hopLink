# Project 6 — Test

> **Role in the chain:** Step 6 of 9. Runs after the Backend Builder and Frontend Builder.
> **Human approval gate:** No
> **Output saved as:** Individual test files + `06-test-report.md` in the per-feature folder

---

## Purpose

The Test Project writes acceptance tests that exercise the approved user story directly, and produces a coverage report showing which acceptance criteria are tested, which are not, and any likely defects noticed along the way.

This role exists to close the loop between business intent (the story) and what the code actually does. Unit tests live next to the code they cover — the Backend Builder and Frontend Builder wrote those. Acceptance tests live here. They are how the chain proves the feature does what the story said it should, not just what the code happens to do.

The Test Project never modifies production code, never fixes defects it finds (it reports them), and never invents acceptance criteria the story did not include.

---

## Inputs

The Test Project expects to receive:

- The approved user story (`02-story.md`)
- The approved technical brief (`03-spec.md`)
- The Backend Builder's summary (`04-backend-summary.md`)
- The Frontend Builder's summary (`05-frontend-summary.md`)
- Any test infrastructure files (existing test data builders, fixtures) the Builder should mirror

It reads from its knowledge base on every run:

- `general-conventions.md`
- `js-conventions.md`
- `testing-conventions.md`
- `target-stack-spec.md`
- `example-test-suite.md`

---

## Outputs

A series of test file artifacts plus a structured coverage report. Each test file is produced as a complete, copy-paste-ready artifact in the side panel. The coverage report is saved as `06-test-report.md` in the feature folder and becomes a critical input for the Validate Project.

Expect the following kinds of output per feature, depending on the brief:

- Integration tests (Vitest) covering API endpoints with the database
- Component-level integration tests (Vitest + Testing Library) covering full user flows
- End-to-end tests (Playwright) covering browser-level acceptance criteria
- The coverage report

---

## Knowledge base files to upload

Upload these into the Test Project's knowledge base:

| File | Purpose |
|---|---|
| `general-conventions.md` | Commits, branches, PRs, no-secrets, naming |
| `js-conventions.md` | Node version, package manager, tsconfig, ESLint, Prettier |
| `testing-conventions.md` | Test runner, structure, builders, naming |
| `target-stack-spec.md` | The default stack for new apps |
| `example-test-suite.md` | One real test file, success/failure/edge case examples |

This is the smallest knowledge base after the Story Writer's. The Test Project does not need backend or frontend conventions — those concerns were settled before tests were written. It needs to know how *tests* are structured in your codebase, which is what `testing-conventions.md` and `example-test-suite.md` provide.

The example file is doing almost all the work here. Spend time on it: show success cases, validation failure cases, auth failure cases, tenant boundary cases, and at least one edge case. The Test Project will mirror what it sees.

---

## Custom instructions

Paste the block below into the Test Project's **Custom Instructions** field.

```
You write acceptance tests for features that have already been
built. Your output is test code ready to paste into the user's
IDE, plus a coverage report.

When the user provides:
- The approved user story (with acceptance criteria)
- The approved technical brief
- The Backend Builder's summary
- The Frontend Builder's summary

Produce acceptance tests that cover every acceptance criterion
in the user story, plus the edge cases the story listed.

For each test file:
- Full file path (anchored to testing-conventions.md)
- Full file content in a fenced code block tagged
  ```typescript
- A short note listing which acceptance criterion or edge case
  each test in the file covers

End with a coverage report saved as 06-test-report.md, in this
exact structure:

ACCEPTANCE CRITERIA COVERED
- Criterion 1: covered by <test name(s)>
- Criterion 2: covered by <test name(s)>
- ...

ACCEPTANCE CRITERIA NOT COVERED
- Criterion N: not covered because <reason>
- ...
(If all criteria are covered, write "All acceptance criteria
covered." Do not omit this section.)

EDGE CASES COVERED
- Edge case 1: covered by <test name(s)>
- ...

EDGE CASES NOT COVERED
- Edge case N: not covered because <reason>
- ...
(If all edge cases are covered, write "All edge cases covered.")

LIKELY DEFECTS NOTICED WHILE WRITING TESTS
- <description, with file path and line number where possible,
  and a pointer back to the relevant builder for resolution>
(If no likely defects were noticed, write "No likely defects
noticed." Do not omit this section.)

Behaviour rules:
- Only produce test files. Never modify production code, even
  if you spot defects.
- Use existing test data builders from example-test-suite.md.
  Do not inline test setup unless the example shows inline
  setup.
- Use Vitest for unit and integration tests; Playwright for
  end-to-end browser tests. Match the choice to what
  example-test-suite.md uses for similar coverage.
- Cover every acceptance criterion. If a criterion is
  genuinely untestable (no observable behaviour, no API
  surface, no UI surface), say so in the coverage report.
  Don't invent a workaround.
- Cover the edge cases listed in the story. If an edge case
  is untestable for the same reason, say so.
- If you notice a likely defect while writing a test (a test
  fails for a reason that points to a real bug, not a test
  problem), report it in the "Likely defects noticed" section.
  Do not patch the code. Point back to which builder should
  fix it.
- Produce every test file as a complete artifact. No
  truncation, no "// ... rest of file" placeholders.
- If any of the four inputs are missing, refuse to write tests
  and ask for the missing input first. Tests written against
  an incomplete picture will themselves be incomplete.
- Tests must be independent. Each test sets up its own state
  and cleans up after itself. Do not rely on test execution
  order.
```

---

## How to use this Project in the workflow

1. **Open the Test Project** in claude.ai.
2. **Start a new conversation.** Always start fresh.
3. **Paste the inputs** in this order:
   - The approved user story (`02-story.md`)
   - The approved technical brief (`03-spec.md`)
   - The Backend Builder's summary (`04-backend-summary.md`)
   - The Frontend Builder's summary (`05-frontend-summary.md`)
4. **Receive test files as artifacts.** Save each one to the file path the Test Project specifies.
5. **Save the coverage report** as `06-test-report.md` in the feature folder. The Validate Project will consume this directly.
6. **Run the tests locally.** Use the commands from `testing-conventions.md` (typically `pnpm test` for unit/integration and `pnpm test:e2e` for Playwright).
7. **Handle test failures by category.** When tests fail, the failure type determines the next step:
   - **Test bug** (the test itself is wrong): paste the failure back into the Test Project conversation and ask for a fix.
   - **Backend bug**: go back to the Backend Builder, paste the failing test and the error, ask for a fix. Regenerate the backend summary if the fix changes the API contract.
   - **Frontend bug**: go back to the Frontend Builder, paste the failing test and the error, ask for a fix.
   - **Brief gap** (the test reveals the brief missed something): escalate to the Spec Writer. This is rare but real.
8. **Re-run tests until clean.** Do not move on to the Validate Project until tests pass.
9. **Hand off to the Validate Project** by starting a new Validate conversation with the story, spec, all code produced, and the test report.

---

## The coverage report is the audit artifact

The coverage report is the most important non-code output of this Project. It is the answer to the question *"how do we know this feature does what we said it would?"* — and in regulated-adjacent work, that question gets asked.

A good coverage report has three properties:

1. **Every criterion is accounted for.** If a criterion is not tested, the report says so and explains why. Silence is not acceptable — an unlisted criterion is indistinguishable from a forgotten one.
2. **Test names are precise.** "Test that admin can send reminder" is less useful than "POST /api/admin/invoices/:id/remind returns 200 when admin and invoice share a tenant." The latter is searchable, traceable, and reviewable.
3. **Defects are routed, not fixed.** If the Test Project notices a likely defect, it reports it and names the builder responsible. Patching defects from a test-writing conversation creates code the chain did not produce through its normal flow, which breaks the audit trail.

Treat the coverage report as the artifact a compliance reviewer or a tech lead will read to confirm the feature is fit to ship. Write it accordingly.

---

## What counts as a "likely defect"

The Test Project will sometimes write a test that fails for an unexpected reason. Distinguishing test bugs from real defects is a judgment call, and the custom instructions tell the Test Project to err toward reporting rather than patching. A few patterns that almost always indicate real defects:

- The test calls a documented endpoint with valid inputs and gets a 500.
- The test confirms tenant isolation and finds a tenant boundary is missing.
- The test confirms a UI state described in the brief and finds the state is unreachable.
- The test confirms an error response shape from the backend summary and finds the actual response is different.
- The test confirms accessibility (keyboard navigation, focus management) and finds a focus trap or unreachable interactive element.

If the Test Project reports any of these, do not move on to the Validate Project until the relevant builder has fixed the issue. The validator's job is to find what *everyone else* missed; sending it known defects is wasted effort.

---

## When acceptance criteria are genuinely untestable

Some acceptance criteria look testable but cannot be verified through code. A few real examples:

- "The reminder email is visually consistent with our brand." Visual consistency is a human judgment; tests can confirm the right template was used, but not that it looks right.
- "Admins find the reminder feature intuitive." Usability is not a unit; it requires user testing.
- "Failures do not impact the overall billing system." This is an architectural property that is verified by design and observability, not by a single test.

When the Test Project encounters one of these, the custom instructions tell it to list the criterion under "ACCEPTANCE CRITERIA NOT COVERED" with the reason. This is correct behaviour — do not pressure the Test Project to invent a test for an untestable criterion. Instead, route the criterion to whatever process actually verifies it: design review, usability testing, observability dashboards, or human QA.

In regulated-adjacent work, having these untestable criteria called out explicitly in the coverage report is often more valuable than the tests themselves. It tells reviewers exactly which assurances rest on test evidence and which rest on other evidence.

---

## Tuning notes

- If the Test Project keeps producing tests that do not match your real test patterns, the issue is almost always `example-test-suite.md`. Refresh it with a recent, real, well-structured test file. Pay particular attention to the test data builders and the assertion style — these are what the Test Project will mirror most closely.
- If tests come out shallow (only happy-path coverage), strengthen `example-test-suite.md` to include explicit failure cases, auth boundary cases, and tenant boundary cases.
- If the coverage report keeps omitting the "Edge cases not covered" or "Likely defects noticed" sections, sharpen the rule that those sections must always appear. The custom instructions already say this; you may need to enforce it with a stronger example in `testing-conventions.md`.
- If the Test Project reports defects but also tries to patch them, the "never modify production code" rule needs to be tightened. Consider adding an explicit "do not produce non-test files" line to the custom instructions.
- If tests are flaky, the issue is usually test independence — one test is relying on state from another. The "tests must be independent" rule is in the custom instructions; reinforce it with an example in `example-test-suite.md`.

---

## Compliance reminder

In regulated-adjacent work, the test artifacts and the coverage report are often part of the evidence pack reviewed by compliance, QA, or clients. Treat them accordingly:

1. **Save the coverage report every time, even when everything passes.** A clean coverage report ("all acceptance criteria covered, no likely defects noticed") is the positive record that the feature met its specification. A missing report is indistinguishable from a skipped test pass.
2. **Do not edit the coverage report after Validate runs.** If the validator finds gaps, those gaps go into `07-validation.md`. The original `06-test-report.md` stays as the snapshot of what the Test Project saw — the audit trail is the sequence, not the latest version.
3. **Name tests so a non-developer reviewer can follow them.** "Admin from Company A cannot trigger reminder for invoice belonging to Company B" is meaningful to a compliance reviewer. "test_tenant_403" is not. The test names are part of the audit artifact.

Before saving test code into your real codebase, confirm with your IT/security/compliance stakeholders that Claude Projects use is approved for the content being processed — particularly if test fixtures contain PHI or other regulated data. Test fixtures should use synthetic data wherever possible.