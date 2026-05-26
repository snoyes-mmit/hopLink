# Regulated Environment Rules

> **Location:** `js-saas-factory-knowledge/compliance/regulated-environment-rules.md`
>
> **Purpose:** The rules the factory must follow because of the team's regulated-adjacent context — PHI handling, MLR review triggers, audit trail expectations, accessibility requirements, do-not-log lists, vendor approval considerations.
>
> **Audience:** Researcher, Story Writer, Spec Writer, Backend Builder, Frontend Builder, Validate.
>
> **Last reviewed:** _<set date when first adopted, then update after every formal review>_

---

## ⚠ Important framing — read this first

**This file is a working document, not a formal compliance attestation.**

The rules in this file are the team's working understanding of how the factory must operate to stay within the regulatory commitments the organisation has made. They are not legal advice, not regulatory guidance, and not a substitute for review by qualified compliance, legal, security, or quality stakeholders.

**Before adopting any section of this file:**

1. Confirm the contents with your organisation's compliance, MLR, security, and legal stakeholders as appropriate.
2. Verify the specific definitions and categories against your real regulatory exposure (HIPAA, GDPR, GxP, internal policies, client contracts, etc.).
3. Document who reviewed each section and when in the change log at the bottom.

**This file evolves. Treat every section as a starting structure that your team completes with real, verified information.** Sections marked _⚠ Stakeholder verification required_ must be filled in with your team — the placeholders are illustrative only.

---

## How to use this file

Every Project in the chain that could touch sensitive material reads this file at the start of each conversation. The rules are concrete enough that:

- The Researcher can flag a feature idea that touches PHI before any code is written
- The Spec Writer can call out compliance considerations in section 7 of the brief
- The Builders can avoid known anti-patterns (logging raw payloads, storing PHI in non-PHI columns)
- The Validator can flag specific compliance violations during Gate 3

If a rule in this file is vague, the chain produces vague flags. Concrete rules — with explicit examples of what crosses each line — produce useful findings.

---

## 1. What counts as PHI (Protected Health Information)

> ⚠ _Stakeholder verification required. The categories below are illustrative starting points based on common interpretations. Confirm with your compliance team before treating them as authoritative for your context._

### 1.1 Categories the team treats as PHI

| Category | Examples |
|---|---|
| Direct identifiers | Patient name, date of birth, address, phone number, email, MRN, SSN |
| Indirect identifiers in combination | Postal code + date of admission + sex (the HIPAA 18-identifier list applies) |
| Clinical data | Diagnoses, medications, lab results, procedure codes, clinical notes |
| Provider information tied to a patient | Treating physician name in the context of a specific patient |
| Insurance information | Plan ID, member ID, claims data |
| Device identifiers | Pacemaker serial numbers, wearable device IDs tied to an individual |
| Biometric identifiers | Fingerprints, voice prints, photos of a person's face |

### 1.2 The uncertainty rule

**If a piece of data could be PHI and you are not sure, treat it as PHI until a stakeholder confirms otherwise.**

The cost of treating non-PHI as PHI is mild inconvenience. The cost of treating PHI as non-PHI is a notifiable breach. The asymmetry tells you which side to err on.

When the chain encounters genuinely ambiguous data, the Spec Writer must list it as an open question and the team must resolve it before the brief is approved.

### 1.3 What is NOT PHI (but might look like it)

> ⚠ _Stakeholder verification required._

- De-identified data that meets the Safe Harbor or Expert Determination standards (see HIPAA §164.514)
- Aggregate counts and statistics that cannot be re-identified
- Information about the team's own employees (employment records are separate from PHI)
- Test data that does not represent a real person (see section 8 below)

The Validator should flag any production-data-in-test-environment pattern as **CRITICAL**.

---

## 2. PHI handling rules

### 2.1 Storage

| Rule | Reasoning |
|---|---|
| PHI columns are named with a `_phi` suffix (e.g., `patient_name_phi`, `dob_phi`) | Visual flag in code review; tooling can scan for it |
| PHI columns are excluded from default SELECT projections | Reduce accidental exposure in logs, error messages, debugging |
| Tables containing PHI are listed in `do-not-modify.md` if they require audit-controlled migrations | Migration changes to PHI tables get extra review |
| PHI is encrypted at rest (database-level encryption, not application-level unless required) | Standard practice; assume your hosting provider supports this |
| PHI is encrypted in transit (HTTPS everywhere, no HTTP fallback) | TLS terminates at the platform edge per `stack/deployment-notes.md` |
| PHI is never stored in browser localStorage, sessionStorage, or cookies (except authenticated session tokens) | Client-side storage is not a secure store |

### 2.2 Logging

PHI **must not** appear in:

- Application logs (Pino, console, anywhere)
- Error tracking systems (Sentry, etc.)
- Request/response logs at the platform edge
- Debug output during development
- Test fixtures committed to the repo
- Stack traces returned to clients

The Pino logger configuration must include redaction patterns for known PHI fields. The Validator should flag any `logger.info(req.body, ...)` pattern as **CRITICAL** during Gate 3.

```typescript
// Example Pino config with PHI redaction
import pino from "pino";

export const logger = pino({
  redact: {
    paths: [
      "*.patientName",
      "*.dob",
      "*.ssn",
      "*.mrn",
      "*.email",
      "*.phone",
      "*.address",
      "req.body.*_phi",
      "res.body.*_phi",
    ],
    censor: "[REDACTED]",
  },
});
```

### 2.3 Display

| Rule | Reasoning |
|---|---|
| PHI is never displayed in URLs, including query parameters | URLs appear in browser history, server logs, analytics |
| PHI is never displayed in browser tab titles or document titles | Visible in screen recordings, screenshots |
| PHI in screen captures or screenshots requires the same controls as PHI in the database | The pixel is the data |
| Pages displaying PHI must not be cached by browser or CDN | `Cache-Control: no-store` headers required |
| Forms accepting PHI must not autocomplete PHI fields | `autocomplete="off"` on sensitive inputs |

### 2.4 Transmission to third parties

> ⚠ _Stakeholder verification required. The approved-vendor list below is illustrative._

PHI can only be transmitted to third-party services that have:

- A signed Business Associate Agreement (BAA) with the organisation, where required
- Been reviewed and approved by the team's vendor approval process
- Documented data handling that meets the organisation's standards

| Service | Approved for PHI? | Notes |
|---|---|---|
| Resend (transactional email) | _<verify>_ | Email content can contain PHI only if approved |
| Vercel (hosting) | _<verify>_ | Logs and edge data may transit; verify retention |
| Neon / Supabase / Railway Postgres | _<verify>_ | Database hosting must meet residency requirements |
| Upstash Redis | _<verify>_ | Job payloads must not contain PHI |
| Sentry / error tracking | _<verify>_ | Redaction must be configured |
| Stripe | _<verify>_ | Payment data is regulated separately under PCI |
| Veeva / FormTrak | _<verify>_ | Likely the canonical system of record; defer to its handling |

**No new third-party service is added to the stack without an entry in this table.** The Spec Writer must flag any proposed new vendor in section 7 of the brief.

---

## 3. MLR review triggers

> ⚠ _Stakeholder verification required. This section depends entirely on your organisation's MLR process and is illustrative only._

### 3.1 What changes require MLR (Medical, Legal, Regulatory) review

MLR review is triggered when a change:

- Modifies user-facing copy that addresses a regulated audience (healthcare professionals, patients, payers)
- Makes a claim about a product, treatment, or outcome
- Changes anything that affects fair-balance presentation (e.g., presentation of risks vs. benefits)
- Modifies approved templates (see also `do-not-modify.md`)
- Adds new user-facing content in a context that has been approved as a complete unit

### 3.2 What changes typically do NOT require MLR review

- Internal-only tooling that doesn't surface content to a regulated audience
- Bug fixes that don't change displayed content
- Performance improvements with no UX change
- Backend refactors with no behavioral change
- Test code

### 3.3 The "if uncertain" rule

If you cannot tell whether a change requires MLR review, the Story Writer must list it as an open question. The team's MLR coordinator (named in section 7 of this file) makes the determination before Gate 1 approval.

### 3.4 The MLR review process

> ⚠ _Stakeholder verification required. Describe your organisation's actual MLR process here. Topics to cover:_
>
> - _Who requests MLR review_
> - _What artifacts the review requires (the draft content, the context, the audience description)_
> - _Typical turnaround time_
> - _How approval is documented_
> - _What changes after approval require re-review_
> - _How approved content is preserved (this is what connects to `do-not-modify.md`)_

---

## 4. Audit trail requirements

### 4.1 What must produce an audit log entry

The following actions must always generate an audit log entry, regardless of whether they succeed or fail:

| Action category | Examples |
|---|---|
| Authentication events | Login, logout, failed login, password reset, MFA challenge |
| Authorization changes | Role granted, role revoked, permission granted, permission revoked |
| Access to PHI | Viewing a patient record, exporting patient data, downloading reports containing PHI |
| Modifications to PHI | Creating, updating, deleting any PHI record |
| Modifications to validated content | Any change to an item listed in `do-not-modify.md` (which should never happen via the chain — see that file) |
| Configuration changes | Feature flag toggles, environment variable changes, vendor connections |
| Administrative actions | Tenant created, user invited, billing changes, data export |
| Cross-tenant boundary attempts | Any caller attempting an action against a resource in a different tenant (even when blocked) |

### 4.2 Required audit log fields

Every audit log entry includes at minimum:

- `timestamp` — UTC ISO 8601, including milliseconds
- `actorId` — the user or system component performing the action (or `"anonymous"` for unauthenticated)
- `actorType` — `"user"`, `"system"`, `"job"`, `"api"`
- `tenantId` — the tenant context the action ran in
- `action` — a stable identifier (`invoice.viewed`, `reminder.manually_triggered`, `auth.login_succeeded`)
- `resourceType` — the kind of resource acted on
- `resourceId` — the specific resource
- `outcome` — `"success"`, `"failure"`, `"denied"`
- `failureReason` — if outcome is `failure` or `denied`, the reason (e.g., `"tenant_mismatch"`, `"not_authenticated"`)
- `metadata` — additional context as a structured object (never raw payloads, never PHI)

### 4.3 Storage and retention

> ⚠ _Stakeholder verification required. The numbers below are illustrative; confirm against your organisation's actual retention policy._

- Audit logs are stored in a write-only, append-only store (not the application database)
- Audit logs are not editable from the application
- Retention period: _<verify with stakeholders — often 6 to 7 years for regulated industries>_
- Audit log access is itself audited

### 4.4 What never appears in audit logs

The audit log records *that* an action happened, not the content of the action. PHI does not appear in audit logs.

- ✅ "User X viewed patient record Y at timestamp Z"
- ❌ "User X viewed patient record showing diagnosis D and prescription P"

### 4.5 The audit-of-the-audit rule

Code that writes to the audit log is one of the items in `do-not-modify.md`. Modifying audit-write code is itself an audit-relevant action and requires explicit security review.

---

## 5. Accessibility requirements

Accessibility is part of the regulated environment because:

- Many regulated audiences (healthcare professionals, patients) include users of assistive technology
- The Americans with Disabilities Act (ADA) and Section 508 apply to many products
- Accessibility failures in regulated contexts can affect informed consent and clinical decision-making

### 5.1 The target

**WCAG 2.2 Level AA, across all UI.** Not a stretch goal; the baseline.

The detailed practices live in `conventions/frontend-conventions.md` section 6. This file's role is to make the requirement non-negotiable from a compliance perspective.

### 5.2 Specific compatibility expectations

| Assistive technology | Expected to work | Tested? |
|---|---|---|
| Keyboard navigation only | Yes, fully | Required per feature |
| VoiceOver (macOS, iOS) | Yes | Spot-check on critical flows |
| NVDA (Windows) | Yes | Spot-check on critical flows |
| JAWS (Windows) | Yes | _<verify if relevant to your audience>_ |
| Screen magnification | Yes (text reflows at 200% zoom) | Spot-check |
| High-contrast mode (Windows) | Yes | Spot-check |
| Voice control | Yes | _<verify if relevant>_ |

### 5.3 What cannot be deferred

- Forms collecting PHI must be fully accessible — they are part of the consent and data-capture surface
- Critical alerts (e.g., drug interaction warnings, severity indicators) must reach users of assistive technology with the right semantic weight
- Required-field indicators must not rely on color alone
- Error messages must be associated with their inputs via ARIA, not just visual proximity

### 5.4 Documentation of accessibility decisions

The Frontend Builder's summary (`05-frontend-summary.md`) includes an "Accessibility decisions made" section. The Validator should flag any feature whose summary's accessibility section is empty or trivially short.

---

## 6. Data retention and deletion

> ⚠ _Stakeholder verification required. Retention periods are organisation-specific._

### 6.1 What is retained, for how long

| Data category | Default retention | Notes |
|---|---|---|
| PHI in the production database | _<verify>_ | Often the duration of the patient/customer relationship plus a regulated tail |
| Audit logs | _<verify>_ — often 6–7 years | See section 4.3 |
| Application logs (non-audit) | _<verify>_ — typically 30–90 days | Forwarded to log aggregator; raw logs purged sooner |
| Database backups | _<verify>_ — often 30 days online, longer offline | Backups containing PHI need the same protections |
| Email transactional records | _<verify>_ | Resend retention varies; verify against organisation policy |
| Error tracking events | _<verify>_ — typically 30–90 days | Must have PHI redaction |
| Browser analytics | _<verify>_ | Many analytics tools should not be used in regulated contexts |

### 6.2 Deletion mechanics

When a record is deleted:

- The record is removed from active tables
- The record is removed from indexes
- Backups continue to contain the record until the backup is rotated out — this is normal but worth noting
- Audit log entries about the record are preserved (they record *that* the action happened)
- Associated cached data is invalidated

The Validator should flag any feature that adds soft-delete behavior on PHI without explicit consideration of whether the data should be hard-deleted instead.

### 6.3 The right to deletion (data subject requests)

> ⚠ _Stakeholder verification required. Topics to cover:_
>
> - _How a deletion request is received_
> - _Who authorizes deletion_
> - _What systems must be searched and updated_
> - _How completion is documented_
> - _Timeline expectations (GDPR allows 30 days)_

---

## 7. Vendor and tooling approval

See section 2.4 above for the approved-vendor table. Additional rules:

### 7.1 Adding a new vendor

A new third-party service is added to the stack only after:

1. A stakeholder-approved evaluation has been completed (functional fit, security review, contract review)
2. Required agreements are in place (BAA if PHI is involved, DPA for GDPR coverage)
3. An entry is added to section 2.4's table
4. Any required updates are made to `stack/target-stack-spec.md`, `stack/deployment-notes.md`, and this file

The Spec Writer must flag any proposed new vendor in section 7 of the brief.

### 7.2 Approved categories of data per vendor

> ⚠ _Stakeholder verification required._

For each approved vendor, the team should document specifically which categories of data the vendor is approved to process. A vendor approved for "transactional notifications" may not be approved for "clinical communications" even though both are emails.

### 7.3 Escalation paths

| Concern | Who to ask |
|---|---|
| Is this data PHI? | _<role/name — compliance lead>_ |
| Does this change require MLR review? | _<role/name — MLR coordinator>_ |
| Is this vendor approved for this kind of data? | _<role/name — security lead>_ |
| Can we extend the retention period for X? | _<role/name — data protection officer>_ |
| Does this affect our regulatory commitments? | _<role/name — compliance lead>_ |
| Should this go through external legal review? | _<role/name — legal counsel>_ |

These names should be real people in real roles. Stale escalation paths (a role currently held by someone who left) are worse than no path at all.

---

## 8. Test data and development environments

### 8.1 The rule

**Real PHI never appears in development or test environments.**

This means:

- Test fixtures committed to the repo contain only synthetic data
- Local development databases are seeded with synthetic data
- Preview environments use synthetic or anonymised data
- Production data is never copied to lower environments for debugging

### 8.2 Synthetic data sources

> ⚠ _Stakeholder verification required for any tools used._

Acceptable patterns for generating test data:

- Faker libraries (`@faker-js/faker`) for general personal information
- Hand-crafted fixtures with obviously-fake names ("Patient One", "Test Patient A")
- Domain-specific synthetic data generators

What is forbidden:

- Copying production data, even with names changed
- Using real patient names from publicly-available sources (the data may still be regulated by some standards)
- Photos of real people

### 8.3 When debugging requires real data

There are legitimate cases (a production bug that only reproduces with real data) where engineers need access to data that touches PHI. The process for these:

> ⚠ _Stakeholder verification required. Describe your organisation's process for emergency production access._

Typical elements:

- Documented request with reason
- Time-limited access
- Audit logged
- Read-only where possible
- Access revoked at the end of the work

The chain itself never accesses production data. If a feature requires production-data validation, that validation happens in a separate, audited process — not in the factory.

---

## 9. Incident reporting

> ⚠ _Stakeholder verification required. This section depends on your organisation's incident response process._

### 9.1 What counts as a compliance incident

- Suspected or confirmed PHI breach
- Unauthorized access to PHI
- Cross-tenant data leak (even if caught by tenant isolation)
- Unintended publication of regulated content (skipped MLR review, modified do-not-modify item)
- Logs containing PHI discovered in any environment
- Lost or stolen device with access to PHI

### 9.2 Reporting timeline

> ⚠ _Stakeholder verification required. Regulatory regimes have specific timelines (HIPAA's Breach Notification Rule, GDPR's 72-hour rule). Document yours._

### 9.3 What the chain does when an incident is suspected during a feature build

If the Validator or any other Project surfaces a finding that suggests an incident has already occurred (not just a risk going forward), the chain stops and the issue is escalated immediately to the team's incident response lead. The chain does not propose code fixes for active incidents — incident response is a separate process.

---

## 10. Specific Veeva / FormTrak / regulated-tooling considerations

> ⚠ _Stakeholder verification required. Tailor this section to your real integrations and the specific regulatory implications._

If the factory builds features that integrate with Veeva, FormTrak, or similar regulated systems:

- The integrated system is treated as the system of record for content it manages
- Approved Veeva content templates appear in `do-not-modify.md`
- Changes to fields, forms, or templates that have been MLR-approved in Veeva require re-approval before they can be modified
- Integration code that reads from or writes to Veeva is subject to the audit trail requirements in section 4
- Any new Veeva integration requires explicit security and compliance review before development begins

The general principle: **the factory builds the integration, not the regulated content itself.** Content lives in its system of record and the factory respects that boundary.

---

## 11. Change log

Every change to this file is documented here, including who reviewed it.

| Date | Section(s) changed | Change | Reviewed by | Reason |
|---|---|---|---|---|
| _YYYY-MM-DD_ | All | Initial structure | _name / role_ | Bootstrapping the factory |
| _YYYY-MM-DD_ | 1, 2, 7 | Verified PHI categories and vendor list | _compliance lead name_ | First formal compliance review |
| _YYYY-MM-DD_ | 4 | Updated audit retention period | _data protection officer_ | Aligned with annual policy review |

Maintain this log carefully. In audit contexts, the *history* of compliance decisions is part of the evidence that the team operates compliantly.

---

## 12. Review cadence

This file is reviewed:

- **At least quarterly**, jointly with the team's compliance, MLR, and security stakeholders
- **Out of cycle** when any of the following occurs:
  - A new regulation or guideline affects the organisation
  - A vendor changes data handling terms
  - An incident or near-miss reveals a gap in the rules
  - A new feature category is introduced (e.g., the team starts building features that touch a new data category)
  - The organisation's compliance posture changes (new audit scope, new BAA, new client contract terms)

The review is documented in the change log above. If the file has not been reviewed in over a quarter, the team is operating on stale rules — flag this at the next standup.

---

## Tuning notes

- If the Validator keeps producing empty COMPLIANCE FLAGS sections on features that should have flags, this file's rules are too abstract. Make them more concrete and specific.
- If the chain keeps proposing patterns that violate the rules (logging PHI, using unapproved vendors), the relevant convention file may need a cross-reference to this file's specific rule.
- If stakeholder reviews keep finding the same kinds of gaps, capture them as rules here so the chain catches them before review.
- This file's value is proportional to its specificity. Vague rules produce vague flags; specific rules produce useful flags. When in doubt, add a concrete example to the rule.

---

## Final reminder

**This file is a working document, not a formal compliance attestation.** Authoritative compliance guidance comes from your team's compliance, legal, security, and quality stakeholders. When this file and a stakeholder's guidance disagree, the stakeholder is right and this file is updated to match.

The factory produces engineering artifacts. Compliance certification remains a human responsibility, supported by the evidence the chain has produced.