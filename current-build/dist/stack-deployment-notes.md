# Deployment Notes

> **Location:** `js-saas-factory-knowledge/stack/deployment-notes.md`
>
> **Purpose:** How apps built with this factory are run locally and deployed to production. The Documentation Project pulls setup steps and prerequisites from this file; the Package Project pulls the build process and secrets policy.
>
> **Audience:** Documentation, Package.
>
> **Last reviewed:** _<set date when first adopted, then update each formal review>_

---

## How to use this file

This file is a working reference, not a public guide. It describes:

- How a developer sets up the project on a fresh machine and runs it locally
- How the project is built for production
- How and where the project is deployed
- How secrets are managed across environments

If the chain produces a README with setup steps that don't actually work, this file is where the fix lives. If the build script in `09-package/` fails on a fresh checkout, this file is where the diagnosis starts.

**Platform-specific note:** the default deployment target in this file is Vercel + managed Postgres + Upstash Redis, consistent with `target-stack-spec.md`. If your real target differs, edit the relevant sections — but keep the structure. The Documentation and Package Projects depend on the section shape, not the specific platform.

---

## 1. Local development setup

### 1.1 Prerequisites

Before cloning the project, a developer's machine must have:

| Tool | Version | Install method |
|---|---|---|
| Node.js | 22 LTS (use `nvm`, `fnm`, or `volta` for version management) | https://nodejs.org or your version manager |
| pnpm | 9.x | `npm install -g pnpm@latest` |
| Git | Any modern version | OS package manager |
| Docker Desktop _or_ a managed Postgres dev instance | Latest | Docker for local Postgres; or use a hosted dev DB |
| Redis (only if the project uses BullMQ) | 7.x | Via Docker, or Upstash for a hosted dev instance |

A `.nvmrc` file at the project root pins the Node version. Developers using `nvm` or `fnm` get the right version automatically by running `nvm use` or `fnm use` after cloning.

### 1.2 First-time setup (cold start, fresh machine)

```bash
# Clone
git clone <repository-url>
cd <project-folder>

# Confirm Node version (should match .nvmrc)
node --version

# Install dependencies
pnpm install

# Copy the environment template and fill it in
cp .env.example .env.local

# Start the database (local Docker option)
docker compose up -d db

# Run migrations
pnpm exec prisma migrate dev

# Seed development data (if a seed script exists)
pnpm exec prisma db seed

# Start the dev server
pnpm dev
```

The dev server runs at `http://localhost:3000` by default. The first run will be slower than subsequent runs because Next.js compiles routes on demand.

### 1.3 Environment variables for local development

`.env.local` is the local file. It is git-ignored and must never be committed. `.env.example` (committed, no real values) lists every variable the app requires, with placeholder values and one-line comments.

When a developer adds a new environment variable to the code, they must also add it to `.env.example` in the same commit. The Validator should flag any missing entry in `.env.example` during Gate 3 review.

A typical `.env.local` for the default stack contains:

```bash
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/appname_dev"

# Auth
AUTH_SECRET="generate-with-openssl-rand-base64-32"
AUTH_URL="http://localhost:3000"

# Optional: email (Resend)
RESEND_API_KEY="re_..."  # leave blank if not testing email locally

# Optional: background jobs (Redis)
REDIS_URL="redis://localhost:6379"

# Optional: third-party integrations
# STRIPE_SECRET_KEY=...
```

Group variables by category (database, auth, email, jobs, integrations). Use comments to explain non-obvious values.

### 1.4 Running the app components separately

For projects with background workers, the dev server alone does not run the worker process. Common dev commands:

```bash
pnpm dev          # web server (Next.js)
pnpm dev:worker   # BullMQ worker (only if the project has one)
pnpm dev:all      # both, via concurrently or similar
```

If `pnpm dev:worker` doesn't exist in `package.json`, the project doesn't have background jobs and this section doesn't apply.

---

## 2. Local development troubleshooting

These are the most common errors developers hit during local setup. The Package Project's `ASSEMBLY_INSTRUCTIONS.md` includes a shorter version of this list for end users; this longer version is the working reference.

| Error | Cause | Fix |
|---|---|---|
| `node: command not found` or `Unsupported engine` | Node version doesn't match the `.nvmrc` | Run `nvm use` (or `fnm use`); install the right Node version if missing |
| `pnpm: command not found` | pnpm not installed globally | `npm install -g pnpm@latest` |
| `Error: P1001: Can't reach database server` | Postgres isn't running, or `DATABASE_URL` is wrong | Start Postgres (`docker compose up -d db`); verify `DATABASE_URL` in `.env.local` |
| `Error: Environment variable not found: DATABASE_URL` | `.env.local` not created, or app started without env vars | `cp .env.example .env.local` and fill in real values |
| Port 3000 already in use | Another process is bound to the port | Kill the other process (`lsof -ti:3000 \| xargs kill`) or run with `PORT=3001 pnpm dev` |
| `prisma migrate dev` fails with "shadow database" error | Postgres user lacks `CREATEDB` permission | Use a Postgres user with the right permissions, or use a hosted dev DB that provides one |
| TypeScript errors after `pnpm install` that weren't there before | `node_modules` cache is stale | Delete `node_modules` and `pnpm-lock.yaml`'s lockfile state by running `pnpm install --force` |
| Hot reload not picking up changes | File watcher limit on Linux | Increase `fs.inotify.max_user_watches` (see Next.js docs) |
| `AUTH_SECRET` errors at startup | Auth secret not set or too short | Generate with `openssl rand -base64 32` and put it in `.env.local` |
| Worker process starts but doesn't pick up jobs | Redis not running, or `REDIS_URL` wrong | Start Redis; verify `REDIS_URL` |

If a new failure mode shows up repeatedly across team members, add it here. This table is the team's accumulated knowledge of how the local environment breaks.

---

## 3. Production build process

The production build is what gets bundled, deployed, and run in the live environment. It is produced by the build script in `09-package/build-package.sh` (or `.ps1`), which the Package Project generates.

### 3.1 Build sequence

The build script runs these steps in order. Each step must succeed before the next runs; the script exits non-zero on any failure.

1. **Verify Node version** matches `.nvmrc` / `engines.node` in `package.json`
2. **Install dependencies** with `pnpm install --frozen-lockfile` (fail if lockfile out of date)
3. **Run typecheck** with `pnpm typecheck`
4. **Run linter** with `pnpm lint`
5. **Run tests** with `pnpm test` (unit + integration; e2e tests run in a separate CI step)
6. **Build the production bundle** with `pnpm build`
7. **Create the versioned `.zip`** in `./dist/` excluding `node_modules`, `.next/cache`, `.git`, `.env*`, `features/`, and test files when `--production` is set

The build is deterministic in principle: the same source plus the same lockfile should produce the same bundle. In practice, timestamps and minor toolchain variations introduce small differences. Aim for build reproducibility, but don't treat byte-for-byte determinism as a hard requirement.

### 3.2 Build output

A successful build produces:

- `.next/` directory — Next.js production bundle (server-side and client-side assets)
- `dist/<project-name>-v<version>-<YYYYMMDD>.zip` — the distributable archive

The archive contains everything needed to run the app in production *except* `node_modules` (installed at the deployment platform) and `.env` (provided by the platform's secrets management).

### 3.3 Database migrations in the build

**Migrations are not run as part of the build.** The build produces a bundle that contains the migration files; the deployment pipeline runs them against the production database as a separate step. This separation is deliberate — a build failure shouldn't leave the database half-migrated, and a migration failure shouldn't block the build from being created.

The deployment pipeline runs `pnpm exec prisma migrate deploy` against the production database **after** the bundle is uploaded but **before** new traffic is routed to it. If the migration fails, the deployment is rolled back automatically.

---

## 4. Deployment target

**Default target (matches `target-stack-spec.md`):**

| Component | Platform | Notes |
|---|---|---|
| Web (Next.js) | Vercel | Auto-deploys on push to `main`; preview deploys per PR |
| Database | Neon, Supabase, or Railway Postgres | Pick one based on team preference; all three support branching for preview environments |
| Redis (jobs) | Upstash | Only if the project uses BullMQ |
| Email | Resend | Configured via API key in production env vars |
| File storage (if used) | Vercel Blob, AWS S3, or Cloudflare R2 | Specified per project if relevant |

**If your deployment target differs from these defaults, replace this section with concrete details for your actual platform.** The chain needs a real target to build against; "deploy however you like" produces unusable artifacts.

### 4.1 Deployment characteristics

Whatever platform is chosen, the stack assumes:

- **HTTPS terminates at the platform edge.** The Next.js app does not handle TLS directly.
- **Environment variables come from the platform's secrets manager.** The app reads them via `process.env`; the platform injects them at runtime. No secrets in the bundle.
- **Database migrations run in the deployment pipeline.** Not at application start. Migrations are a deployment step, not a runtime concern.
- **Workers run in a separate process from the web server.** The web process should be stateless; long-running jobs go to BullMQ.
- **Structured logs are collected by the platform.** The app emits JSON logs to stdout; the platform handles forwarding.

If any of these assumptions don't hold for your deployment target (for example, an on-prem environment where you handle TLS yourself), the brief should call that out and the Builder should account for it.

### 4.2 Deployment pipeline (default)

The default pipeline assumes Vercel for the web app and a separate CI service (GitHub Actions, GitLab CI, or similar) for the worker:

1. **PR opened** → CI runs typecheck, lint, unit/integration tests, e2e tests; Vercel produces a preview deploy
2. **PR merged to `main`** → CI runs the same checks; on success:
   - Vercel deploys the web app to production
   - CI runs `prisma migrate deploy` against the production database
   - CI deploys the worker process (if applicable) to its host platform
3. **Smoke checks run after deploy** — a small set of e2e tests against the production URL to confirm the deploy is healthy
4. **On smoke failure** → automatic rollback of the Vercel deploy; manual review of the migration

For projects without a worker, steps 2c is skipped. For projects without e2e smoke tests, step 3 is skipped (and you should consider adding them).

---

## 5. Secrets management

### 5.1 Local development

- Secrets live in `.env.local` (git-ignored)
- `.env.example` (committed, no real values) lists every required variable with placeholder values and comments
- Real secret values are shared via the team's password manager or secrets-sharing tool, **never** by email, Slack, or commit

### 5.2 Production

- Secrets live in the deployment platform's secrets manager (Vercel env vars, AWS Secrets Manager, etc.)
- Production secrets are different from development secrets and are never reused
- Access to production secrets is restricted to the people who need it; the team's secrets manager is the source of truth for who has access
- Rotation policy: secrets are rotated when a team member with access leaves, when a secret is suspected of being exposed, or on a regular cadence (every 6–12 months for long-lived secrets)

### 5.3 What never appears in the codebase

- Real API keys, tokens, passwords, connection strings
- `.env` files with real values
- Hard-coded credentials of any kind, even in comments

The Validator should flag any of these as **CRITICAL** during Gate 3 review. The pre-commit hook (covered in convention files) should block them from being committed.

### 5.4 What `.env.example` should and should not contain

**Should:**

- Every variable the app actually reads via `process.env`
- A safe placeholder value (`"your-api-key-here"`, `"changeme"`, an empty string for optional values)
- A short comment explaining what the variable is for
- Grouping by category (database, auth, email, jobs, integrations)

**Should not:**

- Real secrets, even temporarily
- Variables that have been removed from the code (keep this file in sync — the Validator checks this)
- Placeholders that look like real values (don't write `sk_test_1234567890abcdef` as a placeholder; it could be mistaken for a real key)

---

## 6. Database migration policy

Migrations are append-only. Once a migration is merged to `main`, it must never be edited — only superseded by a new migration. The `do-not-modify.md` file should list `prisma/migrations/` to enforce this.

### 6.1 Local development

```bash
# Create a new migration after editing schema.prisma
pnpm exec prisma migrate dev --name short-descriptive-name

# Reset the local DB and replay all migrations (development only, destroys data)
pnpm exec prisma migrate reset

# Apply pending migrations without prompting (for CI / non-interactive contexts)
pnpm exec prisma migrate deploy
```

### 6.2 Production

```bash
# Run during deployment, before new traffic is routed
pnpm exec prisma migrate deploy
```

Production migrations:

- Run as a deployment step, not at application start
- Are forward-only — no automatic rollback. If a migration fails, the deployment fails and is rolled back; the migration itself is fixed in a follow-up
- Run against the production database with credentials that are scoped to migration use only (not the application's runtime credentials)

### 6.3 Migration review

Migrations involving destructive changes (dropping columns, dropping tables, renaming columns without a backfill) require explicit review and a documented backfill plan. The Validator should flag any migration that includes a destructive operation without a corresponding backfill or data preservation strategy.

---

## 7. Environment parity

The closer development, preview, and production environments are to each other, the fewer "works on my machine" surprises the team hits.

| Concern | Development | Preview (per PR) | Production |
|---|---|---|---|
| Node version | Pinned via `.nvmrc` | Pinned via platform config | Pinned via platform config |
| Database | Local Postgres (Docker or hosted dev) | Preview DB (branched from prod schema, no prod data) | Production Postgres |
| Background jobs | Local Redis (Docker or Upstash dev) | Upstash preview instance | Upstash production instance |
| Email | Resend test mode, or disabled | Resend test mode | Resend production |
| Auth | Local Auth.js with test users | Preview Auth.js with test users | Production Auth.js |
| Logs | Pretty-printed to console | Platform log viewer | Platform log viewer + aggregator |

Differences worth being aware of:

- **Email in preview is sandboxed.** Don't write tests that depend on email actually being delivered to a real inbox in preview environments.
- **Background jobs run differently in dev.** Local Redis loses state on container restart; production Redis is durable. If a feature depends on job durability, test it against a persistent Redis instance, not the local Docker one.
- **Auth callbacks differ across environments.** OAuth providers need different callback URLs per environment. Misconfigured callbacks are one of the most common preview-environment bugs.

---

## 8. What's deliberately not in this file

A few things you might expect to find here that belong elsewhere:

- **The stack itself (Node version, framework, ORM)** — `stack/target-stack-spec.md`
- **PHI handling, vendor approval status, data residency rules** — `compliance/regulated-environment-rules.md`
- **Approved templates and validated systems** — `compliance/do-not-modify.md`
- **Naming conventions, commit format, secrets-handling rules in code** — `conventions/general-conventions.md`
- **Backend layering, tenant isolation, logging conventions** — `conventions/backend-conventions.md`
- **CI configuration (specific YAML for GitHub Actions, etc.)** — lives in the project's `.github/workflows/` or equivalent; this file references the pipeline shape, not the implementation

If any of those topics has crept into this file during an edit, move it to its proper home. This file describes *how the app is run and deployed*, not *how the team writes code* or *how regulated content is handled*.

---

## 9. Change log

Maintain a short list of changes so future readers can see how deployment has evolved.

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |

---

## Tuning notes

If the chain keeps producing READMEs with setup steps that don't actually work, or build scripts that fail on a fresh checkout, this file is the lever. Two common causes:

1. **The file describes an ideal state, not the real one.** Setup steps that look clean but skip a quirk of your real environment will produce a clean-looking README that breaks in practice. The fix is to actually run through the setup in a clean environment and update the file to match what actually happens.
2. **The file is out of date.** Stack upgrades or platform changes can invalidate sections quickly. After every quarterly stack review (per `target-stack-spec.md`), re-walk the setup steps and confirm they still work.

The simplest test of accuracy: a developer who has never seen the project should be able to clone it, follow section 1, and have a running dev server within 15 minutes. If they can't, the file is wrong.