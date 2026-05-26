# Target Stack Specification

> **Location:** `stack-target-spec.md`
>
> **Purpose:** The single source of truth for what the factory is building with. Every Project in the chain reads this file to ensure consistency across features.
>
> **Audience:** Researcher, Spec Writer, Backend Builder, Frontend Builder, Test, Documentation, Package.
>
> **Last reviewed:** _<set date when first adopted, then update each formal review>_

---

## How to use this file

This file is the default stack for new features. When a feature uses a different tool or version than what's listed here, the Spec Writer must call out the deviation in section 7 of the brief ("Risks and open questions") with explicit justification.

Treat the contents as decisions, not suggestions. The whole point of having a default stack is that the chain doesn't have to guess — and a default that's regularly ignored isn't a default.

When the team wants to change a default, update this file first, then run a feature through the chain to confirm the change propagates correctly. Updating the file is the change.

---

## 1. Stack table

The table below lists every layer of the stack with the chosen tool, the target version, and a brief note on why the choice was made.

| Layer | Choice | Target version | Notes |
|---|---|---|---|
| **Runtime** | Node.js | 22 LTS | Active LTS through October 2027. Use 20 LTS only if a deployment platform requires it. |
| **Language** | TypeScript | 5.x, strict mode | Strict mode non-negotiable. `noUncheckedIndexedAccess` on. No plain JS in production code. |
| **Package manager** | pnpm | 9.x | Faster than npm/yarn, smaller `node_modules`, better monorepo support. |
| **Backend framework** | Fastify | 5.x | Lower overhead and better type inference than Express. Use Express only if existing team familiarity strongly outweighs the migration cost. |
| **Frontend framework** | Next.js App Router | 15.x (React 19) | Industry standard for SaaS UI. App Router only — Pages Router is not part of this stack. |
| **Database** | PostgreSQL | 16+ | Default relational store. SQLite for local dev is allowed but never for production. |
| **ORM / data access** | Prisma | 5.x | Schema-as-code, strong migrations, type-safe queries. Drizzle is the next-best alternative if Prisma's runtime overhead becomes a problem. |
| **Auth** | Auth.js (NextAuth) | 5.x | Open-source, framework-native. Clerk is the managed alternative if the team prefers to outsource auth. |
| **Validation** | Zod | 3.x | Used at every API boundary. Schemas are shared between backend (validation) and frontend (form validation). |
| **Unit / integration tests** | Vitest | 2.x | Fast, modern, works for both backend and frontend. Replaces Jest for new projects. |
| **End-to-end tests** | Playwright | 1.x | Standard choice. Chromium-first; cross-browser only when the feature genuinely needs it. |
| **Linter** | ESLint | 9.x (flat config) | With `@typescript-eslint/recommended-type-checked`. |
| **Formatter** | Prettier | 3.x | Default config; team-specific tweaks go in `conventions/general-conventions.md`. |
| **Background jobs** | BullMQ + Redis | 5.x / 7.x | Only when the app actually needs background work. Don't add Redis just to have it. |
| **Email** | Resend | Latest | Only when the app actually sends transactional email. Use the existing template system; do not introduce a second one. |
| **Logging** | Pino | 9.x | Structured JSON logs, fast. Pretty-print only in local development. |
| **HTTP client (server-side)** | `fetch` (built-in) | Node native | Use the runtime's built-in `fetch`. No `axios`, `got`, or `node-fetch` in new code. |
| **Date / time** | `Temporal` polyfill or `date-fns` | Latest stable | Day.js and Moment are not part of this stack. Prefer Temporal where the polyfill is stable; `date-fns` is the fallback. |
| **Environment variable loading** | Node native (`--env-file`) | Node 22 native | No `dotenv` package in production code; rely on the runtime's built-in env file support. |

---

## 2. Deployment target

Default: **Vercel** for the Next.js frontend, **a managed Postgres provider** (Neon, Supabase, or Railway Postgres) for the database, and **Upstash Redis** for BullMQ if background jobs are used.

This default is chosen for one reason: it minimises infrastructure work for a small team and lets the factory focus on shipping features rather than running platforms. It is not the right choice for every context — in particular, regulated environments often require self-hosted or vendor-approved infrastructure, and that decision is layered in `compliance/regulated-environment-rules.md` rather than overriding the default here.

If your deployment target differs, document it in `stack/deployment-notes.md` rather than editing this file. This file describes *what the app is built with*; deployment notes describe *where the app runs*.

**Deployment characteristics this stack assumes:**

- HTTPS-terminated at the platform edge (no in-app TLS handling)
- Environment variables provided by the platform's secrets management
- Database migrations run as part of the deployment pipeline, not at application start
- Background workers run in a separate process from the web server (not in-process)
- Structured logs collected by the platform and forwarded to a log aggregator

If any of these assumptions don't hold for your deployment target, the brief should call that out and the Builder should account for it.

---

## 3. Version pinning policy

**Major versions are pinned in `package.json` using exact ranges (`^` is acceptable for minor and patch).** Major version upgrades are deliberate decisions, not automatic ones.

**Cadence for review:** the stack is reviewed quarterly. Out-of-cycle review is triggered by:

- A security advisory affecting any listed component
- A new major version of Node.js LTS
- A new major version of Next.js, React, or TypeScript
- A consistent class of issues that points to a stack-level problem rather than a per-feature problem

**Who decides:** the team's tech lead, with input from anyone whose work is directly affected. Stack changes are not made unilaterally inside a feature branch.

**Upgrade process for a major version:**

1. Update this file with the new target version and the reason for the change.
2. Update `examples/example-backend-feature.md`, `examples/example-frontend-feature.md`, and `examples/example-test-suite.md` to match the new version.
3. Run a sample feature through the chain to confirm the change propagates correctly.
4. Communicate the change to the team.

Skipping any of those four steps is how stacks drift across a codebase.

---

## 4. Deviation rules

A feature may deviate from the default stack only when one of the following applies:

1. **An external system dictates the choice.** Examples: a webhook handler must use a specific signature library; an integration with a vendor SDK requires a specific HTTP client; a third-party platform supports only a particular auth provider.
2. **The default stack genuinely cannot do what the feature needs.** This is rare. Most "the default can't do this" claims are actually "the default is unfamiliar to me." Investigate before deviating.
3. **A spike or experiment is being run to evaluate a replacement.** Spikes are time-boxed, clearly labelled as experimental, and produce a decision (replace the default, or revert) rather than long-lived parallel infrastructure.

When a deviation is proposed:

- The Spec Writer must call it out in section 7 of the brief with the reason from the list above
- The justification must reference an external constraint or a concrete limitation of the default, not a personal preference
- The Validator must flag any unjustified deviation as **CRITICAL** during Gate 3 review

A pattern of unjustified deviations means the default stack itself needs updating — bring it to the next quarterly review rather than continuing to deviate.

---

## 5. Forbidden choices

The following tools are explicitly not part of this stack. They appear here so the chain doesn't propose them and so reviewers know to flag their use.

| Tool | Reason it's excluded |
|---|---|
| **Moment.js** | Deprecated by its own maintainers. Use Temporal or `date-fns`. |
| **Day.js** | Adequate, but date-fns has better tree-shaking and TypeScript support. Pick one date library; don't run two. |
| **Lodash** | Modern JavaScript covers most use cases natively. Pulling in lodash for one helper imports a large surface area. Use native methods or import single utilities (`lodash.debounce`) only where genuinely needed. |
| **jQuery** | No place in a React/Next.js stack. If found, it's a bug. |
| **Axios / got / node-fetch** | The native `fetch` is sufficient on Node 18+ and avoids a third-party dependency at the HTTP boundary. |
| **Sequelize / TypeORM** | Prisma is the chosen ORM. Pick one ORM per project. |
| **Express middleware in Fastify projects** | Fastify has its own plugin ecosystem. Mixing Express middleware in Fastify works but defeats Fastify's type and performance advantages. |
| **CommonJS in new code** | All new modules use ESM. Existing CommonJS files in dependencies are tolerated, but new code is ESM only. |
| **Default exports (except where required)** | Named exports are the rule. Default exports are allowed only where Next.js requires them (pages, layouts, route handlers, error boundaries). |
| **`any` and non-null assertions (`!`)** | Both indicate the type system has been bypassed. Use `unknown` and explicit narrowing instead. |
| **`console.log` in committed code** | Use the Pino logger for anything that should land in production logs. `console.log` is a debugging tool, not a logging tool. |
| **In-memory caches as primary deduplication** | If the app needs deduplication that survives restarts or scales across processes, use the database or Redis. In-memory state is process-local and lost on restart. |

This list grows over time as the team makes more decisions. Add an entry whenever a chain run produces something you don't want to see again.

---

## 6. Greenfield bootstrap commands

For reference, here is the command sequence to bootstrap a new project that matches this stack. Use these as a starting point in `stack/deployment-notes.md` rather than running them blindly from this file.

```bash
# Node version
node --version  # should be v22.x

# pnpm install (one-time)
npm install -g pnpm@latest

# Create a new Next.js project with TypeScript and App Router
pnpm create next-app@latest my-saas \
  --typescript \
  --eslint \
  --app \
  --src-dir \
  --use-pnpm

cd my-saas

# Add the rest of the stack
pnpm add prisma @prisma/client zod
pnpm add -D vitest @vitest/ui playwright @playwright/test prettier
pnpm add pino pino-pretty
pnpm add next-auth@beta

# Initialise Prisma
pnpm exec prisma init

# Initialise Playwright
pnpm exec playwright install --with-deps

# Add scripts to package.json (see package-manifest-template.md)
```

This sequence produces a project that matches the stack table above. The first feature through the chain should fill in the conventions, examples, and templates with concrete content.

---

## 7. What's deliberately not in this file

A few things you might expect to find here that belong elsewhere:

- **Specific deployment instructions** (how to deploy to Vercel, how to run migrations in production, how to manage secrets in production): `stack/deployment-notes.md`.
- **PHI handling, MLR review triggers, vendor approval status for regulated data**: `compliance/regulated-environment-rules.md`.
- **Validated systems and approved templates that must not be modified**: `compliance/do-not-modify.md`.
- **Naming, commit format, PR shape, secrets handling**: `conventions/general-conventions.md`.
- **TypeScript strictness rules, ESLint config, Prettier config**: `conventions/js-conventions.md`.
- **API layer rules, service patterns, tenant isolation enforcement**: `conventions/backend-conventions.md`.
- **Component structure, state management, accessibility**: `conventions/frontend-conventions.md`.
- **Test runner setup, test data builders, naming**: `conventions/testing-conventions.md`.

If any of those topics has crept into this file during an edit, move it to its proper home. This file describes *what the app is built with*, not *how the team writes code*.

---

## 8. Change log

Maintain a short list of changes to this file so future readers can see how the stack has evolved.

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

If the chain keeps producing code that doesn't match this stack — wrong Node version assumptions, packages you've forbidden, deployment commands that don't apply — the issue is usually one of two things:

1. **The file is out of date.** Stack drift happens silently. If you upgraded Next.js six months ago and never updated this file, the chain is still building against the older version. Run a quarterly review and update.
2. **The file is being skipped.** Confirm this file is uploaded to every Project's knowledge base. A common failure mode is uploading the conventions but forgetting the stack spec, which leaves the chain guessing.

The single best test of whether this file is accurate is the bootstrap command sequence in section 6. If a fresh project built from those commands doesn't match what you actually ship, the file is wrong.