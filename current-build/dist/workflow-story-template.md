# Story Template

> **Location:** `js-saas-factory-knowledge/workflow/story-template.md`
>
> **Purpose:** The required shape of a user story plus strong-vs-weak examples for each section. The Story Writer Project mirrors this shape on every run.
>
> **Audience:** Story Writer.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

The Story Writer Project reads this file at the start of every conversation. The template here is what the Story Writer produces; the strong-vs-weak examples teach the difference between a story that drives clean downstream work and one that creates ambiguity for the Spec Writer.

A good story is the foundation of every successful chain run. Time spent on the story is repaid many times over downstream.

---

## 1. The required shape

Every story has these six sections, in this exact order. The Story Writer must produce all six; missing sections are not acceptable.

1. **User story** — the one-sentence statement
2. **Acceptance criteria** — testable statements
3. **Edge cases worth thinking about** — boundaries, retries, permissions, accessibility, timezone, empty states
4. **Compliance considerations** — PHI, MLR, audit trails, accessibility, or an explicit "none identified"
5. **Out of scope** — what this story explicitly does NOT cover
6. **Open questions** — only if genuinely unclear; never invent answers

A complete story fits on roughly one page (or the equivalent in screen space).

---

## 2. Section-by-section guidance with examples

### 2.1 User story

**The shape:** `"As a <role>, I want <behaviour>, so that <outcome>."`

The three parts:

- **Role** — the specific user type (`account admin`, `billing manager`, `unauthenticated visitor`). Avoid vague roles like `user`.
- **Behaviour** — what they want to do. Plain language, no implementation detail.
- **Outcome** — why they want to do it. The business or user value.

**Strong example:**

> *As an account admin, I want overdue invoice reminders to be sent automatically, so that customers are reminded without manual follow-up.*

**Weak example:**

> *As a user, I want a button to send reminders, so that things work.*

**Why the second is weak:** "user" is too vague (admin? viewer? customer?); "a button to send reminders" is implementation detail dressed as behaviour; "so that things work" provides no business reason. The Spec Writer cannot infer the design from this story.

---

### 2.2 Acceptance criteria

**The shape:** testable statements in plain language. Each criterion must be something a test can verify directly — not something requiring human judgment.

**Strong example:**

> 1. A reminder is sent when an invoice is unpaid for more than 7 days.
> 2. No reminder is sent for paid or cancelled invoices.
> 3. Duplicate reminders are not sent within a 24-hour window for the same invoice.
> 4. Failed email send attempts do not mark the reminder as sent.
> 5. Admins can see the timestamp of the last reminder for each invoice.
> 6. Admins can manually trigger a reminder for any specific invoice.

**Weak example:**

> 1. Reminders work correctly.
> 2. The system handles failures gracefully.
> 3. The UI is intuitive for admins.

**Why the second is weak:** "Work correctly" cannot be tested. "Handles failures gracefully" is vague — what behaviour proves graceful handling? "Intuitive" is a human-judgement matter, not a testable criterion. A test author reading these has nothing concrete to verify.

**The single most useful test of a criterion:** can you imagine a `describe`/`it` block whose name is the criterion, and whose body is a clear test? If not, rewrite the criterion.

---

### 2.3 Edge cases worth thinking about

**The shape:** boundary conditions, retries, multi-tenant concerns, permissions, accessibility, timezone, empty states. List the case, not the solution — the Spec Writer decides how each one is handled.

**Strong example:**

> - **Boundary at exactly 7 days:** does an invoice 7 days overdue trigger a reminder, or only at 7 days + 1 second?
> - **Timezone:** if the system runs in UTC but the customer is in a different timezone, what "day" is used for the 7-day calculation?
> - **Tenant boundary:** admins from Tenant A must not be able to trigger reminders for Tenant B's invoices, even by guessing IDs.
> - **Retries:** if the email service fails transiently, should the reminder be retried automatically, and if so, how often?
> - **Empty state:** what does the admin UI show when there are no overdue invoices?
> - **Concurrent triggers:** if two admins click "Send reminder" within the same second, do both succeed or only one?
> - **Email bounce:** what happens if the customer's email address bounces? Does the reminder count as sent?

**Weak example:**

> - There may be edge cases.
> - Errors should be handled.
> - Performance might matter.

**Why the second is weak:** none of these are edge cases — they're meta-statements about the existence of edge cases. The Spec Writer cannot resolve "errors should be handled" because the story has not named which errors.

**A rule of thumb for completeness:** for a backend-touching feature, the edge cases section almost always includes at least timezone, multi-tenant, retry behaviour, and empty state. If any of those is absent, ask whether the Story Writer should have considered it.

---

### 2.4 Compliance considerations

**The shape:** anything that might touch PHI, MLR review, audit trails, accessibility (WCAG 2.2 AA), or other regulated concerns. If nothing applies, write "No compliance considerations identified for this story" — the section must always appear.

**Strong example:**

> - **Audit trail:** every reminder send (automatic or manual) must produce an audit log entry recording the actor, the invoice, the customer, the timestamp, and the outcome. Failed sends must also be logged.
> - **PHI:** customer name and email address appear in the reminder email. The reminder content itself does not contain clinical PHI, but the customer record is treated as PHI per `regulated-environment-rules.md` section 1.
> - **MLR:** the reminder email template is MLR-approved; the chain must not modify it (see `do-not-modify.md` section 2).
> - **Accessibility:** the admin UI for triggering reminders must be keyboard-accessible and announce status changes (reminder sent / failed) to assistive technology.

**Strong example for a low-stakes feature:**

> No compliance considerations identified for this story. The change is to internal tooling not visible to regulated audiences; no PHI is involved; no audit-relevant action is taken.

**Weak example:**

> Compliance applies as usual.

**Why the second is weak:** it provides no signal about which compliance rules apply. The Spec Writer cannot reflect "compliance applies as usual" in section 7 of the brief. Silence is not acceptable, but vagueness is barely better.

**A rule of thumb:** if you write "no compliance considerations identified," briefly say *why* (no PHI, no MLR touch, no audit-relevant action, no validated systems). The "why" is what tells reviewers you actually checked.

---

### 2.5 Out of scope

**The shape:** specific things this story does NOT cover. The Spec Writer treats out-of-scope items as forbidden territory; the Builders do not implement them.

**Strong example:**

> - SMS reminders are out of scope; this story is for email reminders only.
> - Customer-side preferences (the customer cannot opt out of reminders via this feature) are out of scope; opt-out is a separate story.
> - Reminders in languages other than English are out of scope for the first version; internationalization is a separate story.
> - Reminder content customization (per-tenant templates) is out of scope; all reminders use the existing MLR-approved template.

**Weak example:**

> - Out of scope: anything not described above.

**Why the second is weak:** it's the default. Saying "anything not described above is out of scope" is the same as saying nothing. The value of this section is in naming the *adjacent* features someone might assume are included but are not. Without explicit out-of-scope items, the Builders may pattern-match a similar feature and include behaviour the user does not want.

**A rule of thumb:** the strongest out-of-scope items are the ones a reasonable person might have expected to be in scope. Listing them prevents misunderstanding.

---

### 2.6 Open questions

**The shape:** things that are genuinely unclear from the input. Never invent answers. List the question for the user to resolve before Gate 1 approval.

**Strong example:**

> - **Reminder content for partially-paid invoices:** if a customer pays part of an overdue invoice, does the reminder still go out for the remaining balance? The story assumes full overdue status; clarify before proceeding.
> - **Weekend/holiday handling:** should reminders pause on weekends and public holidays, or send every day regardless? The story is silent; defaulting to "every day" but flagging for confirmation.
> - **MLR re-approval:** the existing reminder template is approved for invoices over 30 days overdue. This feature triggers at 7 days. Does this require MLR re-review? Recommending verification with the MLR coordinator before Gate 1 approval.

**Strong example (when there are no open questions):**

> No open questions.

**Weak example:**

> - Some things might need clarification.

**Why the second is weak:** it's a placeholder, not a question. If something needs clarification, name it specifically. If nothing does, say "no open questions" explicitly.

**A rule of thumb:** open questions are not a sign of a bad story — they're a sign that the Story Writer noticed an ambiguity instead of papering over it. A story with three thoughtful open questions is usually better than one that pretends every rule is settled.

---

## 3. A complete sample story

The following is a complete story for the invoice reminders feature, written to demonstrate the template in action. The Story Writer should produce stories of roughly this depth and length.

```markdown
## User story

As an account admin, I want overdue invoice reminders to be sent
automatically, so that customers are reminded without manual follow-up.

## Acceptance criteria

1. A reminder is sent when an invoice is unpaid for more than 7 days.
2. No reminder is sent for paid or cancelled invoices.
3. Duplicate reminders are not sent within a 24-hour window for the
   same invoice.
4. Failed email send attempts do not mark the reminder as sent.
5. Admins can see the timestamp of the last reminder for each invoice
   in the admin UI.
6. Admins can manually trigger a reminder for any specific overdue
   invoice from the admin UI.

## Edge cases worth thinking about

- **Boundary at exactly 7 days:** does an invoice 7 days overdue
  trigger a reminder, or only at 7 days + 1 second?
- **Timezone:** if the system runs in UTC but the customer is in a
  different timezone, what "day" is used for the 7-day calculation?
- **Tenant boundary:** admins from Tenant A must not be able to
  trigger reminders for Tenant B's invoices, even by guessing IDs.
- **Retries:** if the email service fails transiently, should the
  reminder be retried automatically, and if so, how often?
- **Empty state:** what does the admin UI show when there are no
  overdue invoices?
- **Concurrent triggers:** if two admins click "Send reminder"
  within the same second, do both succeed or only one?
- **Email bounce:** what happens if the customer's email address
  bounces? Does the reminder count as sent?

## Compliance considerations

- **Audit trail:** every reminder send (automatic or manual) must
  produce an audit log entry recording the actor, the invoice, the
  customer, the timestamp, and the outcome. Failed sends must also
  be logged.
- **PHI:** customer name and email address appear in the reminder
  email. The reminder content itself does not contain clinical PHI,
  but the customer record is treated as PHI per
  `regulated-environment-rules.md` section 1.
- **MLR:** the reminder email template is MLR-approved; the chain
  must not modify it (see `do-not-modify.md` section 2).
- **Accessibility:** the admin UI for triggering reminders must be
  keyboard-accessible and announce status changes (reminder sent /
  failed) to assistive technology.

## Out of scope

- SMS reminders are out of scope; this story is for email reminders
  only.
- Customer-side preferences (the customer cannot opt out of reminders
  via this feature) are out of scope; opt-out is a separate story.
- Reminders in languages other than English are out of scope for the
  first version; internationalization is a separate story.
- Reminder content customization (per-tenant templates) is out of
  scope; all reminders use the existing MLR-approved template.

## Open questions

- **Reminder content for partially-paid invoices:** if a customer pays
  part of an overdue invoice, does the reminder still go out for the
  remaining balance? The story assumes full overdue status; clarify
  before proceeding.
- **Weekend/holiday handling:** should reminders pause on weekends and
  public holidays, or send every day regardless? The story is silent;
  defaulting to "every day" but flagging for confirmation.
- **MLR re-approval:** the existing reminder template is approved for
  invoices over 30 days overdue. This feature triggers at 7 days. Does
  this require MLR re-review? Recommending verification with the MLR
  coordinator before Gate 1 approval.
```

---

## 4. Anti-patterns

Patterns the Story Writer should avoid. The Validator and Gate 1 reviewer should flag these on sight.

### 4.1 Technical design dressed as a story

> ❌ *"As an admin, I want a `POST /api/admin/invoices/:id/remind` endpoint that calls the `sendOverdueReminder` service..."*

A story describes user intent, not API endpoints. If the story names files, function names, libraries, or HTTP methods, it has crossed into the Spec Writer's territory. Strip the technical detail.

### 4.2 Invented business rules

The Story Writer must not fill in unstated rules. If the user says "send reminders for overdue invoices" and does not specify the threshold, the Story Writer:

- Does NOT pick "7 days" because it sounds reasonable
- DOES list "what is the overdue threshold?" as an open question

Inventing rules at the story stage creates downstream rework when the real rule is different.

### 4.3 Untestable acceptance criteria

> ❌ *"The system performs well under load."*
> ❌ *"The user experience feels modern."*
> ❌ *"Errors are handled appropriately."*

Each of these requires human judgement, not a test. If a criterion depends on subjective interpretation, it does not belong in acceptance criteria. Either rewrite it as something testable, move it to edge cases as a topic to think about, or move it out of scope.

### 4.4 Silent compliance section

> ❌ *(no compliance section, or just "compliance applies as usual")*

The Compliance Considerations section must always appear with concrete content or an explicit "No compliance considerations identified, because…" statement. Silence is treated as a skipped check.

### 4.5 Out-of-scope as a catchall

> ❌ *"Anything not in the acceptance criteria is out of scope."*

This adds nothing. The value of out-of-scope is in naming the *adjacent* features a reader might assume are included. A catchall sentence is no protection against misunderstanding.

### 4.6 Stories that are actually multiple stories

If a story tries to cover two distinct user needs, the chain produces a tangled brief and tangled code. Split the story.

A signal: if the user story sentence has "and" in it ("As an admin, I want X and Y..."), it is probably two stories. Sometimes legitimately one; sometimes two pretending to be one.

---

## 5. Tuning notes

- **If stories keep being approved at Gate 1 but failing downstream**, the most likely cause is acceptance criteria that turned out to be untestable. Sharpen section 2.2's examples.
- **If stories keep coming back too short and vague**, the example in section 3 should be even more concrete.
- **If stories keep including technical design**, section 4.1's anti-pattern needs sharper examples — show specific phrasing to avoid.
- **If the Story Writer keeps inventing rules**, section 4.2 needs reinforcement. The rule is non-negotiable; the Story Writer should *always* ask rather than guess.
- **If reviewers keep skipping the Compliance Considerations section**, the "always appears" rule needs to be louder in the role file (`02-story-writer.md`) as well as here.

---

## 6. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |