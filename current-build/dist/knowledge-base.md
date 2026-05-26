# Knowledge Base Inventory — JavaScript SaaS Factory

> **What this file is:** A complete inventory of every file in the factory's shared knowledge base, with structure, purpose, audience, and required sections for each. Use this as the map for building out `js-saas-factory-knowledge/`.
>
> **What this file is not:** Actual content. The role files define behaviour; the knowledge base files define context, and the context comes from your team and your codebase. This document tells you *what* to write in each file — you and your team write the *what*.
>
> **Greenfield context:** This inventory assumes you are starting clean, with no pre-existing conventions to extract from. The sections include guidance on sensible default choices, but every team has its own taste — treat the suggestions as starting points, not prescriptions.

---

## How to use this inventory

For each file, you'll find:

- **Purpose** — one or two sentences on what the file is for
- **Audience** — which Projects in the chain read this file
- **Required sections** — the structural skeleton the file should follow
- **What good looks like** — guidance on the level of detail and the kinds of content that work well
- **Greenfield defaults** — suggested starting choices when you have no existing conventions to draw from
- **Tuning trigger** — the kind of factory output that should prompt you to update the file

Work through the files in the recommended writing order at the end of this document. Some files depend on others, and writing them in the wrong order means rewriting.

---

## Folder structure recap

```
js-saas-factory-knowledge/
├── conventions/
│   ├── general-conventions.md
│   ├── js-conventions.md
│   ├── backend-conventions.md
│   ├── frontend-conventions.md
│   └── testing-conventions.md
├── compliance/
│   ├── regulated-environment-rules.md
│   └── do-not-modify.md
├── examples/
│   ├── example-backend-feature.md
│   ├── example-frontend-feature.md
│   └── example-test-suite.md
├── workflow/
│   ├── story-template.md
│   ├── spec-template.md
│   ├── validator-checklist.md
│   ├── documentation-template.md
│   └── package-manifest-template.md
└── stack/
    ├── target-stack-spec.md
    └── deployment-notes.md
```

Fifteen files total.

---

# `stack/` — The team's tool and version choices

Write these first. Every other file references the stack, so settling it once removes ambiguity everywhere else.

## `stack/target-stack-spec.md`

**Purpose:** The single source of truth for what the factory is building with. Every Project reads this file to ensure consistency across features.

**Audience:** Researcher, Spec Writer, Backend Builder, Frontend Builder, Test, Documentation, Package.

**Required sections:**

1. **Stack table** — a table listing each layer (runtime, language, package manager, backend framework, frontend framework, ORM, database, auth, validation, test runner, e2e, linter/formatter, jobs, email, logging) with the chosen tool and a brief note on why.
2. **Version pinning policy** — when to upgrade major versions, who decides, and how often the stack is reviewed.
3. **Deviation rules** — when a feature is allowed to use a tool outside the default stack (almost never), and how that deviation must be documented in the brief.
4. **Forbidden choices** — tools or libraries the team has explicitly chosen not to use, with one-line reasons.

**What good looks like:** A page or two, mostly table. The deviation rules section should be specific enough that the Spec Writer knows when to flag a new dependency as a concern in section 7 of a brief.

**Greenfield defaults for SaaS in 2026:**

| Layer | Sensible default | Notes |
|---|---|---|
| Runtime | Node.js 22 LTS | Or 20 LTS for longer support window |
| Language | TypeScript 5.x strict mode | Strongly recommended over plain JS for SaaS work |
| Package manager | pnpm | Faster, smaller, better monorepo support |
| Backend framework | Fastify | Or Express if team familiarity matters more |
| Frontend framework | Next.js App Router (React 19) | Industry standard |
| Database / ORM | Prisma + PostgreSQL | Schema-as-code, strong migrations |
| Auth | Auth.js (NextAuth) | Or Clerk if you want managed |
| Validation | Zod | Pairs well with TS, used backend and frontend |
| Test runner | Vitest | Fast, modern, both backend and frontend |
| E2E tests | Playwright | Standard |
| Linter / formatter | ESLint + Prettier | Or Biome for single-tool setup |
| Background jobs | BullMQ + Redis | Only if needed |
| Email | Resend | Only if app sends email |
| Logging | Pino | Structured, fast |

You can change any of these per project, but having a default means Claude doesn't have to guess.

**Tuning trigger:** If Builders keep producing code in versions or styles that don't match what you actually want to ship, the stack spec is the lever. Update here once and the change propagates everywhere.

---

## `stack/deployment-notes.md`

**Purpose:** How apps are run locally (so the README is correct) and how they are deployed (so the architecture doc and package manifest reflect reality).

**Audience:** Documentation, Package.

**Required sections:**

1. **Local development setup** — clone, install, env file, database setup, migrations, seed data, dev command.
2. **Local development troubleshooting** — common errors and fixes (wrong Node version, port conflicts, database not running, missing env vars).
3. **Production build process** — build command, output location, what gets bundled and what doesn't.
4. **Deployment target** — where the app runs in production (Vercel, Railway, Fly, AWS, on-prem), and the deployment mechanism.
5. **Secrets management** — how production secrets are stored and rotated, and what `.env.example` should and should not contain.
6. **Database migration policy** — how migrations are run in production, who runs them, and rollback expectations.

**What good looks like:** A focused page. The Documentation Project will pull setup steps and prerequisites from this file; the Package Project will pull the build process and the secrets policy. If either keeps producing inaccurate output, this file is the lever.

**Greenfield defaults:** Pick a deployment target you can realistically host with (Vercel for Next.js is the easiest greenfield path), document it concretely, and update when the target changes. Avoid generic "deploy however you like" notes — the chain produces concrete artifacts and needs concrete deployment context.

**Tuning trigger:** If the README's setup steps don't actually work in a clean environment, this file is incomplete. If the build script in `09-package/` produces a bundle the deployment platform can't run, this file is wrong.

---

# `conventions/` — How the team writes code

Write these after the stack. They reference stack choices but define the *how*, not the *what*.

## `conventions/general-conventions.md`

**Purpose:** Rules that apply to every part of the codebase, regardless of layer. The cross-cutting standards everything else assumes.

**Audience:** Every Project in the chain.

**Required sections:**

1. **File and folder naming** — kebab-case vs. camelCase vs. PascalCase, plurals vs. singulars, where index files are required and where they're banned.
2. **Import order** — external packages, then internal absolute imports, then relative imports, with blank lines between groups.
3. **Commit message format** — conventional commits, gitmoji, or freeform; what each commit should describe.
4. **Branch naming** — pattern for feature branches, bugfix branches, hotfixes.
5. **PR shape** — title format, description template, size expectations, draft vs. ready, link to related artifacts.
6. **Secrets handling** — what counts as a secret, where secrets live (env vars, secret manager), and what is forbidden (committed `.env`, hard-coded keys, secrets in logs).
7. **Comments** — when comments are required, when they're discouraged, what a good comment looks like.
8. **No-go list** — patterns the team has explicitly chosen not to use (e.g., `any` types, default exports, console.log in committed code).

**What good looks like:** A short page. Each rule should be one or two sentences with a concrete example. Avoid prose explanations of *why* — keep this file rules-focused. The reasoning belongs in onboarding docs, not here.

**Greenfield defaults:** Conventional commits, kebab-case files for non-React, PascalCase for React components, no default exports except where Next.js requires them (pages, layouts), absolute imports via tsconfig paths.

**Tuning trigger:** If multiple chain runs produce code in inconsistent shapes (some kebab-case, some camelCase, some default exports, some named), this file is too vague.

---

## `conventions/js-conventions.md`

**Purpose:** JavaScript and TypeScript specific rules — language features, configuration, tooling settings.

**Audience:** Researcher, Spec Writer, Backend Builder, Frontend Builder, Test, Validate, Documentation, Package.

**Required sections:**

1. **TypeScript config** — strict mode on/off, `noUncheckedIndexedAccess`, target ES version, module resolution, paths configuration.
2. **Type style** — types vs. interfaces, where each is preferred, use of `any` (banned), use of `unknown` (encouraged at boundaries), generics naming convention.
3. **Error handling** — thrown errors vs. result types, custom error classes, error message conventions.
4. **Async style** — async/await vs. promise chains, when to use Promise.all vs. sequential, top-level await.
5. **Module organization** — barrel files (allowed or banned), index files, deep imports vs. surface imports.
6. **ESLint config** — chosen ruleset (e.g., `@typescript-eslint/recommended-type-checked`), notable rules turned on or off, custom rules.
7. **Prettier config** — print width, semicolons, quote style, trailing commas, arrow parens.
8. **Forbidden patterns** — `any`, non-null assertions (`!`), implicit any, callback-style APIs in new code.

**What good looks like:** A page or two. Concrete rules with one-line examples or counter-examples. Pin to specific versions of the tools where the version affects behaviour.

**Greenfield defaults:** TypeScript strict mode on, `noUncheckedIndexedAccess` on, no `any`, named exports only, types over interfaces except for declaration merging, custom error classes for known failure modes, async/await throughout.

**Tuning trigger:** If Builders keep producing code that lints clean but doesn't match your taste, the gap is between the linter rules and the unwritten style rules. Capture the unwritten rules here.

---

## `conventions/backend-conventions.md`

**Purpose:** Rules specific to backend code — API layer, services, database access, jobs.

**Audience:** Researcher, Spec Writer, Backend Builder, Validate.

**Required sections:**

1. **Layering** — where business logic lives (services), what API routes are allowed to do (validation, auth, calling services), what services are allowed to do (business logic, calling repositories), what repositories or data access modules are allowed to do (database I/O only).
2. **API route structure** — request validation pattern (Zod schemas), response shape, error response format, status code conventions.
3. **Service structure** — pure vs. stateful services, dependency injection or imports, transaction handling.
4. **Database access** — ORM patterns, query organization, transaction patterns, tenant scoping at the query level.
5. **Background jobs** — when to use a job vs. inline, retry policy, idempotency requirements, job naming.
6. **Error handling** — custom error classes, error-to-status-code mapping, what gets logged vs. what gets returned.
7. **Logging** — what to log, what never to log (PHI, secrets, raw payloads), structured logging fields, log levels.
8. **Tenant isolation** — how tenant scoping is enforced (in services, not just routes), where the tenant ID comes from, what to do if it's missing.
9. **Auth and authorization** — how routes are gated, how role checks work, where authorization logic lives.

**What good looks like:** Two pages. Each section should be concrete enough that a Builder reading it can produce matching code. The tenant isolation and logging sections deserve extra detail in regulated-adjacent contexts.

**Greenfield defaults:** Routes thin (Zod validation, auth, call service, return response); services own business logic; repositories own queries; never log raw payloads; tenant ID required everywhere and enforced in service layer; custom error classes for known failures, generic 500 for unknown.

**Tuning trigger:** If the Backend Builder keeps placing business logic in routes or queries in services, this file is too vague about layering. If the Validator keeps flagging tenant isolation gaps, the section on tenant isolation needs sharpening.

---

## `conventions/frontend-conventions.md`

**Purpose:** Rules specific to frontend code — components, pages, hooks, state, styling, accessibility.

**Audience:** Researcher, Spec Writer, Frontend Builder, Validate.

**Required sections:**

1. **Component structure** — presentational vs. container, file co-location pattern (component, styles, tests), folder organization.
2. **State management** — server state (React Query, SWR, or framework-native), client state (useState, Zustand, context), URL state, when to use each.
3. **Data fetching** — pattern for fetching, mutation handling, optimistic updates, loading and error states.
4. **Forms** — form library if any, validation pattern (Zod schema shared with backend), error display, accessibility.
5. **Styling** — chosen approach (Tailwind, CSS modules, styled-components), how design tokens are used, when raw CSS is allowed.
6. **Accessibility** — WCAG 2.2 AA expectations, keyboard navigation requirements, focus management on modals and dialogs, ARIA usage guidance, contrast requirements.
7. **Routing** — Next.js App Router conventions, where layouts live, when to use parallel routes vs. nested routes, loading and error UI placement.
8. **Component testing** — what to test (visible states, user interactions, accessibility queries), what not to test (implementation details, internal state).
9. **Error handling on the client** — never display raw API errors, map known error codes to user-facing language, generic message for unknown errors.

**What good looks like:** Two pages. The accessibility section deserves particular attention — frontend conventions without accessibility expectations produce inaccessible UIs by default.

**Greenfield defaults:** Server Components by default in Next.js App Router; Client Components only when interactivity is required; Tailwind for styling; Zod schemas for form validation (mirrored from backend); React Hook Form for form handling; WCAG 2.2 AA as the target; keyboard navigation tested in every component; Testing Library for component tests with accessibility queries (`getByRole`, `getByLabelText`) preferred over `getByTestId`.

**Tuning trigger:** If components keep coming out with accessibility issues (missing labels, keyboard traps, missing focus management), the accessibility section is too abstract. Make it concrete with patterns and counter-patterns.

---

## `conventions/testing-conventions.md`

**Purpose:** Rules for how tests are written, named, and organized.

**Audience:** Researcher, Spec Writer, Backend Builder, Frontend Builder, Test, Validate.

**Required sections:**

1. **Test runner and tooling** — Vitest for unit/integration, Playwright for e2e, test environment setup.
2. **Test file organization** — co-located with code (`*.test.ts` next to `*.ts`) or separate `tests/` directory, naming conventions.
3. **Test naming** — descriptive names that read as sentences (`"admin from tenant A cannot trigger reminder for tenant B invoice"`), not opaque IDs (`"test_403"`).
4. **Test structure** — `describe` blocks for grouping, `it` or `test` for assertions, arrange-act-assert structure, one logical assertion per test.
5. **Test data builders** — required pattern, where builders live, naming convention (e.g., `buildInvoice()`, `buildUser({ overrides })`).
6. **Mocking policy** — when mocking is allowed (external services, time), when it's forbidden (the database, the framework, the code under test).
7. **Test independence** — each test sets up its own state and cleans up, no shared state between tests, no reliance on execution order.
8. **What to test** — public behavior, acceptance criteria, failure paths, edge cases.
9. **What not to test** — implementation details, framework code, third-party library internals.
10. **Test commands** — `pnpm test`, `pnpm test:e2e`, `pnpm test:watch`, what each does.

**What good looks like:** A page and a half. The test data builders section is the highest-leverage — inline test setup is the single biggest cause of flaky, hard-to-read tests.

**Greenfield defaults:** Vitest + Playwright; co-located test files; descriptive test names; test data builders in `test/builders/`; mock external services and time only; one logical assertion per test; tests independent and order-agnostic.

**Tuning trigger:** If tests keep coming out shallow (happy path only) or flaky (passes when run alone, fails when run with others), this file needs sharpening — particularly the "what to test" and "test independence" sections.

---

# `compliance/` — What the team must and must not do

Write these after the conventions. They are the smallest files in the knowledge base but carry the most consequence per word.

## `compliance/regulated-environment-rules.md`

**Purpose:** The rules that apply because of the regulated-adjacent context. PHI handling, MLR review, audit trails, accessibility requirements, do-not-log lists.

**Audience:** Researcher, Story Writer, Spec Writer, Backend Builder, Frontend Builder, Validate.

**Required sections:**

1. **What counts as PHI in this environment** — concrete categories (patient name, DOB, MRN, diagnosis codes, prescription data, etc.) plus the rule that "if uncertain, treat as PHI."
2. **PHI handling rules** — never log raw payloads containing PHI, never include PHI in error messages returned to the client, never store PHI in columns not marked as PHI-safe, never include PHI in URLs.
3. **MLR review triggers** — what kinds of changes require MLR review (user-facing copy in regulated audiences, claims about products, anything that touches approved messaging) and how the review is requested.
4. **Audit trail requirements** — which actions must produce an audit log entry, what fields the entry must include (actor, action, target, timestamp, tenant), where audit logs live and how they're protected.
5. **Accessibility requirements** — WCAG 2.2 AA as the target, specific assistive technology compatibility expectations (screen readers, keyboard-only navigation), what cannot be deferred.
6. **Data retention** — how long different categories of data are kept, what triggers deletion, how deletion is performed.
7. **Vendor and tooling approval** — which third-party services are approved for which kinds of data, who approves new vendors, what the approval process looks like.
8. **Escalation paths** — when in doubt about a compliance rule, who to ask. Names or roles (compliance lead, MLR coordinator, security lead), not just "your manager."

**What good looks like:** A page or two. **Every rule should be specific enough that the Validator can flag a concrete violation against it.** Vague rules ("be careful with PHI") produce no compliance flags; concrete rules ("PHI columns must be named with the `_phi` suffix and excluded from the default SELECT projection") produce useful flags.

**⚠ Greenfield warning:** This is the file where greenfield defaults are most dangerous. The contents must reflect your actual regulatory environment, your team's actual compliance commitments, and the actual approval status of the vendors you use. **Draft the structure from this template, then sit with your compliance stakeholders to fill in the contents.** Do not rely on generic defaults here.

**Tuning trigger:** Every compliance incident, near-miss, or audit finding should be reflected in this file as an updated rule. Compliance learning lives here.

---

## `compliance/do-not-modify.md`

**Purpose:** Specific files, templates, validated systems, or pieces of infrastructure that the chain must never modify. The hard-stop list.

**Audience:** Researcher, Spec Writer, Backend Builder, Frontend Builder, Validate.

**Required sections:**

1. **Validated systems** — specific service files, modules, or directories that have been validated under a formal process and cannot be modified without a new validation cycle.
2. **Approved templates** — specific email templates, document templates, UI templates that have been approved through MLR or equivalent review and cannot be changed without re-approval.
3. **Audit trail code** — anything that writes to audit logs. Modifying audit code is itself an audit-relevant action.
4. **Authentication and authorization core** — specific auth modules where changes require security review.
5. **Migration history** — already-merged migration files that must never be edited (migrations are append-only).
6. **Third-party integration adapters** — code that integrates with external systems where the contract is fixed (Veeva, FormTrak, Stripe webhooks).
7. **Generated files** — any file produced by a code generator that should be regenerated, not edited.

**Format for each entry:**

- The exact file path or path pattern (use globs where appropriate)
- One-line reason for the protection
- Who must approve a change (compliance, security, vendor, etc.)
- What the chain should do if a feature appears to require touching it (almost always: stop and escalate, do not propose a workaround)

**What good looks like:** A short, specific file. Each entry is a path or pattern with a reason and an escalation path. If the file is long, it probably needs to be reorganized by category.

**⚠ Greenfield warning:** This file starts empty in a true greenfield environment — you don't have validated systems or approved templates yet because you haven't built anything. The file becomes important the moment you ship your first validated feature or first approved template. **Create the file as an empty skeleton on day one** with the section headers, and add entries as they become real. An empty `do-not-modify.md` with structured section headers is more useful than no file, because it signals to the chain that the categories exist even if nothing currently belongs in them.

**Tuning trigger:** Every time something gets validated or approved through formal review, add an entry. Every time the chain touches something it should not have, add a stricter entry.

---

# `examples/` — Real features the chain should mirror

Write these after conventions and stack are settled. **These three files do the heaviest lifting in the entire knowledge base.** The Builders mirror what they see here.

## `examples/example-backend-feature.md`

**Purpose:** One complete, realistic backend feature shown end to end, annotated with the patterns the Backend Builder should mirror.

**Audience:** Spec Writer, Backend Builder.

**Required sections:**

1. **Feature description** — one paragraph on what this example feature does and why it's a good representative of the team's backend work.
2. **File layout** — the directory tree showing every file the feature includes (route, service, repository or data access, types, Zod schemas, tests, migration if applicable).
3. **For each file:**
   - Full file path
   - Full file contents in a fenced code block
   - **Annotations** — call out the specific patterns this file demonstrates (layering, error handling, tenant scoping, logging, validation, test data builders)
4. **What this example demonstrates** — a bullet list of the patterns the Backend Builder should pick up: where business logic lives, how the route delegates to the service, how the service enforces tenant isolation, how errors are mapped, how tests are structured.
5. **What this example deliberately omits** — patterns that exist in your codebase but aren't shown here, with pointers to where to find them.

**What good looks like:** A working, non-trivial feature. Not a Hello World. Something like "send a transactional email when an invoice is created" — enough surface area to demonstrate layering, validation, tenant scoping, logging, error handling, and testing without being so large that the example becomes its own knowledge problem.

**Greenfield defaults:** Pick one of three starter shapes:

- **A simple create-and-notify flow** (create resource → write to DB → enqueue background notification). Demonstrates route, service, repository, job, and tests.
- **A scheduled job with manual override** (background worker runs daily; admin endpoint can trigger manually). Demonstrates job patterns, manual triggers, tenant scoping in admin endpoints.
- **A webhook receiver with idempotency** (external service POSTs; we deduplicate, transform, store, respond). Demonstrates idempotency, validation of untrusted input, structured logging.

Pick whichever maps closest to your real domain. The invoice-reminders example from the source article maps well to the second shape and may be a useful starting point.

**Tuning trigger:** Refresh this file after every significant convention change. If the Backend Builder keeps producing code in shapes that don't match your current taste, the example is stale.

---

## `examples/example-frontend-feature.md`

**Purpose:** One complete, realistic frontend feature shown end to end, annotated with the patterns the Frontend Builder should mirror.

**Audience:** Spec Writer, Frontend Builder.

**Required sections:** Same shape as the backend example.

1. **Feature description**
2. **File layout** — directory tree showing pages, components, hooks, types, tests
3. **For each file:**
   - Full file path
   - Full file contents
   - Annotations on patterns demonstrated (component structure, state management, accessibility, loading and error states, form handling)
4. **What this example demonstrates** — server-state vs. client-state, where data fetching happens, how forms are validated, how loading and error states are rendered, how accessibility is built in.
5. **What this example deliberately omits**

**What good looks like:** A non-trivial UI with a real interaction model. Not a static page. Something like "an admin form that creates a resource and updates a list optimistically" — enough surface area to show data fetching, mutation, form validation, accessibility, and component composition.

**Greenfield defaults:** Pick one of three starter shapes:

- **A data table with filtering and a detail drawer** — demonstrates server-state caching, URL state for filters, accessible interactions.
- **A multi-step form with validation** — demonstrates form library, Zod validation, error display, focus management between steps.
- **An admin action with optimistic update** — demonstrates mutation, optimistic UI, error rollback, accessibility of feedback.

**Tuning trigger:** Same as backend — refresh after convention changes. If the Frontend Builder keeps producing UI that looks inconsistent with what you actually ship, the example is the lever.

---

## `examples/example-test-suite.md`

**Purpose:** One complete, realistic test file shown end to end, demonstrating the team's test patterns.

**Audience:** Backend Builder, Frontend Builder, Test.

**Required sections:**

1. **Feature being tested** — short description and pointer to the example backend or frontend feature this tests against.
2. **Test file path**
3. **Full test file contents** in a fenced code block.
4. **Annotations covering:**
   - How test data builders are imported and used
   - How `describe`/`it` blocks are structured
   - How tests are named (descriptive, sentence-shaped)
   - How setup and teardown are handled
   - How assertions are written
   - How mocking is applied (and where it's avoided)
5. **Coverage demonstrated** — explicit list of what kinds of test cases this file covers: success, validation failure, auth failure, tenant boundary, edge case, error path.
6. **What this example deliberately omits** — kinds of tests not shown (e.g., e2e tests in a separate file), with pointers.

**What good looks like:** A file with 8–15 tests covering a representative spread of cases. Each test should be short, independent, and named so a non-developer can follow it. The test data builder usage should be the dominant pattern — almost no inline setup objects.

**Greenfield defaults:** A test file for whatever feature you used in `example-backend-feature.md`, covering at minimum:

- One success case
- One validation failure case (invalid input)
- One auth failure case (unauthenticated)
- One tenant boundary case (cross-tenant access blocked)
- One not-found case
- One edge case (e.g., the boundary value, the empty state, the concurrent action)

The Test Project will mirror the depth and shape of what it sees here.

**Tuning trigger:** If tests come out shallow (only happy-path), this file is the lever. Add explicit failure-case tests to the example and the depth of generated tests will match.

---

# `workflow/` — Templates for chain artifacts

Write these after conventions, stack, and examples are settled. They define the shape of what each Project produces.

## `workflow/story-template.md`

**Purpose:** The required shape of a user story plus examples of strong vs. weak content for each section.

**Audience:** Story Writer.

**Required sections:**

1. **The six required sections** of a story (user story sentence, acceptance criteria, edge cases, compliance considerations, out of scope, open questions) — listed in order with a one-line description of each.
2. **Strong vs. weak examples for each section** — one example of a well-written section and one example of a poorly-written section, with a note on why.
3. **Anti-patterns** — common ways stories drift into technical design, invent business rules, or skip compliance considerations.
4. **Sample complete story** — one full story for a realistic feature, end to end, to use as a reference.

**What good looks like:** A page and a half. The strong-vs-weak comparisons are the highest-leverage content — they teach by contrast better than rules teach by description.

**Greenfield defaults:** Use the invoice-reminders example from the source article as the sample story. It hits all six sections concretely.

**Tuning trigger:** If stories keep being approved at Gate 1 but failing downstream because acceptance criteria turn out to be untestable or compliance considerations were missed, this file's example sections need sharpening.

---

## `workflow/spec-template.md`

**Purpose:** The required shape of a technical brief plus examples of strong vs. weak content for each section.

**Audience:** Spec Writer.

**Required sections:**

1. **The eight required sections** of a brief (stack used, data model changes, flow, API changes, frontend changes, tests required, risks and open questions, files that will change) — listed in order with descriptions.
2. **Strong vs. weak examples for each section.** Particularly important for the "Risks and open questions" section — the most common Spec Writer failure is producing a perfunctory section 7.
3. **Specific guidance on tenant isolation, timezone, and accessibility callouts** — what a strong callout looks like vs. a weak one ("not applicable, because X" beats silence).
4. **Sample complete brief** — one full brief, end to end.

**What good looks like:** Two pages. The example brief and the strong-vs-weak comparisons for section 7 are the most valuable parts.

**Greenfield defaults:** Use the same feature for the sample as the story template, so a reader can see story → spec progression.

**Tuning trigger:** If briefs keep being approved at Gate 2 but producing critical findings at Gate 3 (tenant isolation gaps, missing failure paths, unjustified new dependencies), this file's example sections need sharpening.

---

## `workflow/validator-checklist.md`

**Purpose:** The explicit list of items every validation pass must check, with severity guidance and examples of each severity level.

**Audience:** Validate.

**Required sections:**

1. **Checks grouped by category:**
   - Acceptance criteria coverage (every criterion in the story is implemented)
   - Failure path coverage (every failure path in the brief has test coverage)
   - Security (auth checks, tenant isolation in service layer, no secrets in logs, no raw exceptions to client)
   - Pattern conformance (matches conventions and example features)
   - Scope (no changes outside the brief's "files that will change" list)
   - Compliance (PHI handling, audit trails, do-not-modify items, accessibility)
   - Code quality (no `any`, real types, Zod validation at boundaries, no duplicate logic where a helper exists)
2. **Severity classification examples** — three or four concrete examples for each of CRITICAL, IMPORTANT, MINOR, COMPLIANCE FLAGS, showing what kinds of findings belong in each bucket.
3. **When to mark something "(opinion)"** — guidance on subjective findings.
4. **What NOT to flag** — patterns that may look unusual but are deliberate (e.g., a new pattern that's well-formed, a deviation from the brief that the user clearly intended).

**What good looks like:** Two pages, mostly checklist and examples. The severity examples are the most important — they're what prevents the Validator from over-classifying or under-classifying.

**Greenfield defaults:** Start with the checks listed in the role file (`07-validate.md`, custom instructions, "Always check" section). Expand with severity examples as your team's actual findings accumulate.

**Tuning trigger:** Every time a validation pass misses something a human reviewer catches, or over-flags something that's actually fine, this file is the lever.

---

## `workflow/documentation-template.md`

**Purpose:** The shape, tone, and audience for each of the five documentation outputs.

**Audience:** Documentation.

**Required sections:**

1. **For each of the five docs (README, api.md, user-guide.md, architecture.md, CHANGELOG entry):**
   - Required structural sections (in order)
   - Target audience (specific role, not "users")
   - Voice and tone guidance (technical vs. plain language, formal vs. informal)
   - Length expectations
   - Example excerpt showing the right voice for that document
2. **Cross-document rules** — no voice contamination (user guide must not use framework names), no inventing behavior, "TODO: confirm" markers for unclear items.
3. **Sample complete set** — one full set of five docs for a realistic feature.

**What good looks like:** Two pages plus the sample set. The voice and tone guidance is the most leveraged content — voice contamination across documents is the most common Documentation Project failure.

**Greenfield defaults:** README in developer-facing technical language; api.md in precise technical reference style; user-guide in plain language for a non-developer admin; architecture.md as a decision record (what / why / trade-offs); CHANGELOG entry in user-facing, action-oriented language.

**Tuning trigger:** If user guides keep slipping into technical jargon, or architecture docs keep reading like code summaries, this file's voice guidance needs sharpening.

---

## `workflow/package-manifest-template.md`

**Purpose:** The shape of the file manifest and the conventions for package metadata (versioning, dependency derivation, build script behavior).

**Audience:** Package.

**Required sections:**

1. **Manifest table shape** — exact columns and headers for `FILE_MANIFEST.md`, plus an example row.
2. **Version scheme** — when to bump major / minor / patch, how the version is set, where it lives in `package.json`.
3. **Archive naming** — exact filename pattern (e.g., `<project-name>-v<version>-<YYYYMMDD>.zip`).
4. **Build script expectations** — what the script must do (verify Node, install, typecheck, lint, test, build, zip), in what order, what to print on success vs. failure, exit codes.
5. **Inclusion and exclusion rules** — what goes into the production `.zip` and what is excluded (`node_modules`, `.next`, `.git`, `.env`, test files if `--production`, the feature audit trail).
6. **`.env.example` conventions** — placeholder value format, comment style, grouping pattern.
7. **`.gitignore` baseline** — what every project's `.gitignore` must contain at minimum.

**What good looks like:** A page and a half. The exclusion rules and the build script expectations are the highest-leverage content — most packaging failures are missing files or included secrets.

**Greenfield defaults:** Semantic versioning starting at 0.1.0; ISO date in archive names; build script exits non-zero on any failure; production builds exclude `node_modules`, `.next`, `.git`, `.env`, `features/`, and `*.test.ts` files; `.env.example` groups by category (database, auth, email, jobs); standard Node/Next.js `.gitignore`.

**Tuning trigger:** If packages keep failing to build cleanly on a fresh machine, or `.env.example` keeps missing variables the code actually uses, this file is the lever.

---

# Recommended writing order

Some files depend on others. Writing in the wrong order means rewriting. The cleanest sequence:

**Day one** — settle the stack.

1. `stack/target-stack-spec.md` — everything else assumes this
2. `stack/deployment-notes.md` — Documentation and Package need this

**Day one or two** — write the conventions.

3. `conventions/general-conventions.md` — cross-cutting rules
4. `conventions/js-conventions.md` — language and tooling
5. `conventions/backend-conventions.md` — backend layering and rules
6. `conventions/frontend-conventions.md` — frontend layering and rules
7. `conventions/testing-conventions.md` — test patterns

**Day two** — set up compliance scaffolding.

8. `compliance/regulated-environment-rules.md` — start the structure, fill in with stakeholders
9. `compliance/do-not-modify.md` — create the skeleton even if empty

**Day two or three** — build the examples. **This is where the most time should go.**

10. `examples/example-backend-feature.md`
11. `examples/example-frontend-feature.md`
12. `examples/example-test-suite.md`

**Day three** — write the workflow templates.

13. `workflow/story-template.md`
14. `workflow/spec-template.md`
15. `workflow/validator-checklist.md`
16. `workflow/documentation-template.md`
17. `workflow/package-manifest-template.md`

(Two of these — 13 and 14 — can be written by running a sample feature through the chain using your existing role files and capturing the output as the template. This is often faster than writing the templates from scratch.)

**A realistic effort estimate:** Conventions and stack files are a half-day each, sometimes faster. The three example files are a day combined — they require real code, real annotations, and real care. Workflow templates are an hour or two each. Compliance files require stakeholder time and may take a week of calendar time even if the writing itself is fast.

**Total greenfield setup:** Plan for one focused week of effort, or two to three weeks of calendar time once compliance reviews are factored in. After that, the knowledge base tunes itself feature by feature.

---

# Three things to keep in mind while building this out

1. **The examples carry most of the weight.** If you have only an hour to spend on the knowledge base today, spend it on `example-backend-feature.md`. The Builders mirror what they see there more than they mirror anything else.

2. **Compliance files do not get sensible defaults.** Every other file in this inventory has reasonable starting points for greenfield work. `regulated-environment-rules.md` and `do-not-modify.md` do not — their contents must reflect your actual regulatory environment and your actual approval status. Draft the structure, then book time with your compliance stakeholders to fill in the contents.

3. **The knowledge base is meant to evolve.** None of these files should be written once and frozen. After every feature the chain produces, ask yourself which file's content would have prevented the most surprising or annoying output. Update that file. Over five or six features, the knowledge base becomes specific to your team's actual taste, your real codebase, and your particular context — and the factory's output quality jumps accordingly.

---

# Reference index

| Folder | File | Size | Priority |
|---|---|---|---|
| `stack/` | `target-stack-spec.md` | 1–2 pages | Write first |
| `stack/` | `deployment-notes.md` | 1 page | Write second |
| `conventions/` | `general-conventions.md` | 1 page | Write early |
| `conventions/` | `js-conventions.md` | 1–2 pages | Write early |
| `conventions/` | `backend-conventions.md` | 2 pages | Write early |
| `conventions/` | `frontend-conventions.md` | 2 pages | Write early |
| `conventions/` | `testing-conventions.md` | 1.5 pages | Write early |
| `compliance/` | `regulated-environment-rules.md` | 1–2 pages | Stakeholder-dependent |
| `compliance/` | `do-not-modify.md` | Variable, starts small | Stakeholder-dependent |
| `examples/` | `example-backend-feature.md` | Long (full feature) | Highest-leverage |
| `examples/` | `example-frontend-feature.md` | Long (full feature) | Highest-leverage |
| `examples/` | `example-test-suite.md` | Long (full file) | Highest-leverage |
| `workflow/` | `story-template.md` | 1.5 pages | Write after examples |
| `workflow/` | `spec-template.md` | 2 pages | Write after examples |
| `workflow/` | `validator-checklist.md` | 2 pages | Write after conventions |
| `workflow/` | `documentation-template.md` | 2 pages | Write after examples |
| `workflow/` | `package-manifest-template.md` | 1.5 pages | Write after stack |

Fifteen files. One week of focused work. The factory's quality is set by what lives here.