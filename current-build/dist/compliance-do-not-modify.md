# Do Not Modify

> **Location:** `compliance-do-not-modify.md`
>
> **Purpose:** A registry of specific files, modules, templates, and systems that the chain must never modify without explicit out-of-band approval. The hard-stop list.
>
> **Audience:** Researcher, Spec Writer, Backend Builder, Frontend Builder, Validate.
>
> **Last reviewed:** _<set date when first adopted>_

---

## ⚠ Important framing — read this first

**This file is a registry, not a policy document.**

The policy reasons *why* something is protected live in `compliance/regulated-environment-rules.md`. This file lists *what* is protected, with the specific paths or patterns the chain must respect.

**Greenfield note:** in a true greenfield context, this file starts mostly empty. You don't have validated systems or approved templates yet because you haven't built anything. The file's value grows as the codebase grows — every time something gets formally validated, approved, or otherwise locked down, it gets an entry here. **An empty section is still useful: it signals to the chain that the category exists and to expect entries there in the future.**

**This file is read by every Project that could touch code.** When the chain encounters a path or pattern from this file, the behavior is consistent: **stop and escalate, do not propose a workaround**. The Validator should flag any chain output that modifies, renames, or deletes anything in this file as **CRITICAL**.

---

## How to use this file

### When adding an entry

1. Identify the specific path or path pattern (use globs where appropriate)
2. Write a one-line reason for the protection
3. Name the approver — the role or person who must approve any change
4. State what the chain should do if a feature appears to require touching the entry (almost always: stop and escalate)
5. Document the addition in the change log at the bottom

### When removing an entry

Removal is itself a sensitive action. An entry is removed only when:

- The protected item has been formally retired or replaced
- The protection is being intentionally lifted via a documented process
- The change is logged and approved by the same roles that would approve a modification

**Never quietly delete an entry.** The change log preserves the history.

### Entry format

Each entry uses this shape:

```
**Path or pattern:** `path/to/protected/thing`
**Reason:** One-line description of why it's protected
**Approver:** Role or named person who must approve changes
**On encounter:** What the chain does if a feature seems to require modification
```

---

## 1. Validated systems

Code, modules, or directories that have been validated under a formal process (GxP validation, security audit, regulatory submission). Modifying these resets the validation cycle.

> _Greenfield: this section starts empty. Add entries as systems are formally validated._

<!--
Example entries (remove once real entries exist):

**Path or pattern:** `src/services/clinical/__validated__/`
**Reason:** Validated under GxP for clinical data processing; subject to re-validation if modified
**Approver:** Quality lead + compliance lead
**On encounter:** Stop. Escalate to the quality lead. Do not propose a workaround that touches this code, even indirectly.

**Path or pattern:** `src/services/audit/write-audit-log.ts`
**Reason:** Audit log write path. Modifying this is itself an audit-relevant action.
**Approver:** Security lead
**On encounter:** Stop. Any change to audit-write code requires explicit security review before the chain proceeds.
-->

_No validated systems registered yet. When systems are validated, add them here._

---

## 2. Approved templates

Email templates, document templates, UI templates, and any other content artifacts that have been approved through MLR or an equivalent review process. Modifying these requires re-approval before they can be changed.

> _Greenfield: this section starts empty. Add entries as content is MLR-approved._

<!--
Example entries:

**Path or pattern:** `src/templates/email/overdue-reminder-hcp.mjml`
**Reason:** MLR-approved email content for healthcare professional audience. Approved 2026-03-15, ID MLR-2026-042.
**Approver:** MLR coordinator
**On encounter:** Stop. Content changes to this template require re-approval through the MLR process. Adjacent changes (subject line, sender name) may also require review — defer to the MLR coordinator.

**Path or pattern:** `src/templates/email/payment-receipt.mjml`
**Reason:** MLR-approved transactional template, claims-bearing copy
**Approver:** MLR coordinator
**On encounter:** Stop. Even apparently-cosmetic changes (color, spacing) may affect approval scope — escalate.
-->

_No approved templates registered yet. When templates are MLR-approved, add them here._

---

## 3. Audit trail code

Code that writes to, reads from, or otherwise manages the audit log. Modifications here are themselves audit-relevant and require explicit security review.

> _Greenfield: add the audit-write module to this section as soon as it is created, even before any specific validation._

<!--
Example entries:

**Path or pattern:** `src/services/audit/**`
**Reason:** All audit-trail code. Modifying audit logic could affect the integrity of the audit record.
**Approver:** Security lead
**On encounter:** Stop. Any modification to audit code requires explicit security review before development begins. The chain does not propose changes here.

**Path or pattern:** `prisma/migrations/*audit*`
**Reason:** Migrations that touch the audit log schema
**Approver:** Security lead + DBA
**On encounter:** Stop. Schema changes to audit tables require a documented migration plan that preserves prior data.
-->

_Add audit-trail code paths as they are created._

---

## 4. Authentication and authorization core

Modules where changes affect how the application identifies and authorizes users. Bugs here have broad blast radius and security implications.

> _Greenfield: add core auth modules to this section as soon as they are created. The Auth.js / NextAuth integration files are common candidates._

<!--
Example entries:

**Path or pattern:** `src/lib/auth/**`
**Reason:** Core authentication and session handling. Bugs here could allow unauthorized access.
**Approver:** Security lead
**On encounter:** Stop. Auth changes require explicit security review. Routine consumer-side changes (calling an auth helper from a new route) are fine; modifying the helpers themselves is not.

**Path or pattern:** `src/middleware.ts`
**Reason:** Application-wide auth and route protection middleware
**Approver:** Security lead + tech lead
**On encounter:** Stop. Middleware changes affect every request; coordinate review carefully.
-->

_Add auth core paths as they are created._

---

## 5. Migration history

Database migration files that have been merged to `main`. Migrations are append-only — once merged, they must never be edited, only superseded by new migrations.

> _Greenfield: this is a category that applies as soon as you have your first migration. Add the path pattern below from day one._

**Path or pattern:** `prisma/migrations/*/migration.sql`
**Reason:** Migrations are append-only. Editing a merged migration breaks the schema history and creates inconsistency between environments that have already run it.
**Approver:** No one — this rule is absolute
**On encounter:** Stop. If a previous migration was wrong, create a new migration that fixes the issue. Never edit a merged migration.

**Path or pattern:** `prisma/migrations/migration_lock.toml`
**Reason:** Records the database provider; changing this breaks all migration history
**Approver:** Tech lead + DBA
**On encounter:** Stop. Database provider changes are a major architectural shift.

---

## 6. Third-party integration adapters

Code that integrates with external systems where the integration contract is fixed by the external system (Veeva, FormTrak, Stripe webhooks, etc.). Modifying the contract side of these adapters can break production integrations or cause data corruption.

> _Greenfield: this section starts empty. Add entries as integrations are built, especially when the external system is regulated or critical._

<!--
Example entries:

**Path or pattern:** `src/integrations/veeva/`
**Reason:** Veeva integration adapter. Contract changes affect the regulated system of record.
**Approver:** Veeva integration owner + compliance lead
**On encounter:** Stop. Even adapter-side changes require coordination with the Veeva integration owner.

**Path or pattern:** `src/integrations/stripe/webhook-handler.ts`
**Reason:** Stripe webhook signature verification and idempotency handling
**Approver:** Tech lead
**On encounter:** Stop. Webhook signature handling bugs cause silent payment integration failures.

**Path or pattern:** `src/integrations/formtrak/`
**Reason:** FormTrak integration adapter
**Approver:** FormTrak integration owner + compliance lead
**On encounter:** Stop.
-->

_No third-party integration adapters registered yet. Add them as integrations are built._

---

## 7. Generated files

Files produced by code generators. These should be regenerated, not edited.

> _Greenfield: add generated-file patterns as soon as code generation is set up in the project._

<!--
Example entries:

**Path or pattern:** `src/generated/**`
**Reason:** Auto-generated by code generators (Prisma client, OpenAPI types, etc.)
**Approver:** N/A — regenerate, do not edit
**On encounter:** If the generated output is wrong, fix the generator config or the source schema and regenerate. Do not edit the generated files directly — the next regeneration will overwrite them.

**Path or pattern:** `node_modules/.prisma/`
**Reason:** Prisma client generated output
**Approver:** N/A
**On encounter:** Regenerate via `prisma generate`. Do not edit.
-->

_Add generated file paths as code generators are introduced._

---

## 8. Configuration files with security implications

Configuration files where changes can have broad security or compliance impact.

> _Greenfield: add these as the configuration files are created._

<!--
Example entries:

**Path or pattern:** `next.config.js` (or `.ts`)
**Reason:** Next.js configuration. Changes can affect Content Security Policy, headers, redirects, and build behavior.
**Approver:** Tech lead + security lead (for header / CSP changes)
**On encounter:** Routine config changes (adding a new image domain, environment-variable forwarding) are fine. Changes to headers, CSP, redirects, or build behavior require review.

**Path or pattern:** `.github/workflows/**` (or equivalent CI config)
**Reason:** CI/CD pipeline. Changes can affect what runs before code reaches production.
**Approver:** Tech lead
**On encounter:** Stop. Pipeline changes affect every future deploy.

**Path or pattern:** `prisma/schema.prisma`
**Reason:** Database schema source of truth
**Approver:** Tech lead + DBA
**On encounter:** Schema changes are common during feature work, but each one produces a migration that itself becomes append-only. Coordinate carefully.
-->

_Add configuration files as they become significant._

---

## 9. Compliance and policy files

This file and the related compliance files. Modifying these affects the rules the chain operates under.

**Path or pattern:** `js-saas-factory-knowledge/compliance/do-not-modify.md` (this file)
**Reason:** Self-reference. Modifying this file changes what the chain treats as protected.
**Approver:** Compliance lead + tech lead
**On encounter:** Updates to this file are normal and expected; the protection means changes are documented in the change log and reviewed.

**Path or pattern:** `js-saas-factory-knowledge/compliance/regulated-environment-rules.md`
**Reason:** The rules the chain must follow because of regulated-adjacent context
**Approver:** Compliance lead
**On encounter:** Same as above — changes are reviewed and logged, not blocked outright.

---

## 10. The "stop and escalate" pattern

When the chain encounters anything in this file, the standard response is **stop and escalate**, not "find a way around it." A few examples of what this looks like in practice:

### Example: Researcher

> _"The feature appears to require modifying the audit log writer (`src/services/audit/write-audit-log.ts`), which is listed in `do-not-modify.md`. I am stopping here. The security lead must approve any change to audit-write code before the chain proceeds. Recommendation: contact <security lead name> with the proposed change before any further work."_

### Example: Spec Writer

> _"The technical brief would require modifying `src/templates/email/overdue-reminder-hcp.mjml`, which is MLR-approved (MLR-2026-042). I cannot produce a brief that includes this modification. Options: (1) re-route the change through the MLR re-approval process and return when approved, or (2) use a different (non-approved) template for this feature."_

### Example: Validator

> _"CRITICAL: PR modifies `src/integrations/veeva/sync-record.ts`, which is listed in `do-not-modify.md` under section 6 (third-party integration adapters). This change requires Veeva integration owner approval before merge."_

The chain's job is to identify the protection and escalate. The chain's job is **not** to:

- Propose a workaround that touches the protected item indirectly
- Suggest a "small" change that "probably doesn't affect" the protection
- Skip the escalation because the change "looks safe"

If the chain encounters something protected and a workaround is genuinely needed, the workaround is itself a decision the named approver makes — not the chain.

---

## 11. Change log

Every entry added, modified, or removed from this file is documented here. **This log is itself part of the audit trail.**

| Date | Section(s) | Change | Approved by | Reason |
|---|---|---|---|---|
| _YYYY-MM-DD_ | All | Initial structure | _name / role_ | Bootstrapping the factory |
| _YYYY-MM-DD_ | 5 | Added `prisma/migrations/*/migration.sql` | Tech lead | First migration created; pattern locked in |
| _YYYY-MM-DD_ | 2 | Added overdue-reminder HCP template | MLR coordinator | Template approved as MLR-2026-042 |
| _YYYY-MM-DD_ | 1 | Removed `src/legacy/old-clinical-handler.ts` | Quality lead | Legacy code formally retired |

Removal entries are kept in this log permanently. Quietly deleting a registry entry is itself a violation; the log preserves the history.

---

## 12. Review cadence

This file is reviewed:

- **Monthly** by the tech lead, to identify items that should be added based on the past month's work
- **Quarterly** jointly with compliance, MLR, security, and quality stakeholders
- **Out of cycle** whenever:
  - A new system is formally validated
  - New content is MLR-approved
  - A new third-party integration is added
  - A protection is intentionally lifted (rare; document carefully)
  - An incident reveals that something should have been protected and was not

The cadence matters because forgetting to add an entry is a far more common failure than wrongly adding one. The chain treats unlisted items as fair game; if it should be protected and isn't here, the chain will modify it.

---

## Tuning notes

- If the chain repeatedly modifies something it shouldn't, the lever is to add an entry here, then update relevant convention files to mention the protection.
- If the chain repeatedly stops on things that are actually fine to modify, the entry may be too broad. Tighten the path pattern.
- If entries here are not being respected by Builders, the issue may be that they aren't reading this file — confirm `do-not-modify.md` is uploaded to every relevant Project's knowledge base.
- This file grows with the codebase. Empty sections are fine on day one. By the time the project has been in production for a year, every section should have real entries.

---

## Final reminder

**The protections in this file are not suggestions.** When the chain encounters a registered item, the rule is **stop and escalate**, regardless of how small the proposed change looks or how confident the chain feels that the change is safe.

The cost of stopping unnecessarily is one conversation with the named approver. The cost of modifying a protected item incorrectly can include broken validations, failed audits, lost approvals, compromised integrations, or regulatory action. The asymmetry is large; err toward stopping.