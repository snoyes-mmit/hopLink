# Package Manifest Template

> **Location:** `js-saas-factory-knowledge/workflow/package-manifest-template.md`
>
> **Purpose:** The shape of the file manifest, version scheme, archive naming, build script behavior, and inclusion/exclusion rules for distributable packages. The Package Project mirrors this template on every run.
>
> **Audience:** Package.
>
> **Last reviewed:** _<set date when first adopted>_

---

## How to use this file

The Package Project reads this file at the start of every conversation. The conventions here are what the Package Project produces; they keep packages consistent across features so reviewers (and CI, and clients) know what to expect.

The Package Project does *not* produce the `.zip` itself — claude.ai cannot package multi-file output. It produces the *recipe*: a file manifest, a build script, assembly instructions, and a release checklist that the user runs locally to produce the archive. This file defines the shape of the recipe.

This file pairs with:

- `09-package.md` (the role file)
- `stack/target-stack-spec.md` (for the Node version and engines)
- `stack/deployment-notes.md` (for the build process and secrets policy)

---

## 1. FILE_MANIFEST.md

### 1.1 Purpose

The manifest lists every file that goes into the package, mapping each artifact the Package Project receives to its target location in the assembled project. It is the checklist the user follows when assembling the archive locally.

### 1.2 Required structure

```markdown
# File Manifest — <Project Name> v<version>

Generated: <YYYY-MM-DD>

## Backend source

| Source artifact | Target path | Purpose |
|---|---|---|
| backend-builder-artifact-1 | `src/services/reminders/trigger-manual-reminder.ts` | Manual reminder service |
| backend-builder-artifact-2 | `src/services/reminders/send-overdue-reminders.ts` | Scheduled reminder service |
| ... | ... | ... |

## Frontend source

| Source artifact | Target path | Purpose |
|---|---|---|
| frontend-builder-artifact-1 | `src/app/(admin)/invoices/_components/SendReminderButton.tsx` | Manual trigger button |
| ... | ... | ... |

## Tests

| Source artifact | Target path | Purpose |
|---|---|---|
| test-artifact-1 | `src/services/reminders/trigger-manual-reminder.test.ts` | Service unit/integration tests |
| ... | ... | ... |

## Documentation

| Source artifact | Target path | Purpose |
|---|---|---|
| doc-readme | `README.md` | Project root README |
| doc-api | `docs/api.md` | API reference |
| doc-user-guide | `docs/user-guide.md` | User guide |
| doc-architecture | `docs/architecture.md` | Architecture overview |
| doc-changelog | `CHANGELOG.md` | (Append entry to existing file or create new) |

## Configuration

| Source artifact | Target path | Purpose |
|---|---|---|
| package-json | `package.json` | Node project manifest |
| env-example | `.env.example` | Environment template |
| gitignore | `.gitignore` | Git exclusions |

## Build scripts

| Source artifact | Target path | Purpose |
|---|---|---|
| build-sh | `build-package.sh` | macOS/Linux build script |
| build-ps1 | `build-package.ps1` | Windows build script |

## Total files

<count> files total. Verify each one is saved per the table above
before running `build-package.sh`.
```

### 1.3 What good looks like

- **Every artifact the chain produced is listed.** Missing entries mean missing files in the package, which means broken installs.
- **Target paths are exact.** No "approximately here" or "somewhere under src/".
- **Files are grouped by category** so the user can verify each group is complete before moving on.
- **The total file count** is a final sanity check.

### 1.4 What NOT to include in the manifest

- Files from the `features/` audit trail — those are internal evidence, not part of the distributable
- `.env` files — only `.env.example` is included
- `node_modules/` — installed during the build, not bundled
- `.git/` — clean checkout only
- `.next/` cache directories — produced during build

These exclusions are enforced in the build script (section 5 below); the manifest reinforces the rule.

---

## 2. package.json

### 2.1 Required fields

```json
{
  "name": "<project-name>",
  "version": "<semantic-version>",
  "description": "<one-paragraph description matching the README>",
  "license": "<SPDX-id-or-UNLICENSED>",
  "private": true,
  "engines": {
    "node": ">=22.0.0 <23.0.0",
    "pnpm": ">=9.0.0"
  },
  "packageManager": "pnpm@9.x.x",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "typecheck": "tsc --noEmit",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check ."
  },
  "dependencies": {
    "<derived from what the produced code actually imports>"
  },
  "devDependencies": {
    "<derived from what the produced code actually imports>"
  }
}
```

### 2.2 Rules for the dependency lists

- **Pull dependencies from what the code actually imports.** Do not include generic defaults the code doesn't use.
- **Pin major versions with caret** (`^15.0.0` for Next.js 15). The lockfile pins minor and patch.
- **Match the stack spec.** If `target-stack-spec.md` says Node 22, `engines.node` says `>=22.0.0 <23.0.0`.
- **`private: true` is the default.** Public packages need explicit registry configuration that is not part of the standard template.

### 2.3 What never appears in package.json

- Real secrets, tokens, or credentials
- Personal email addresses (use the team email or omit the `author` field)
- `scripts` that contain hard-coded paths to a specific machine
- Custom registries unless the team has explicitly chosen one

---

## 3. .env.example

### 3.1 Required structure

```bash
# ===== Database =====
DATABASE_URL="postgresql://user:password@host:5432/database"

# ===== Authentication =====
# Generate with: openssl rand -base64 32
AUTH_SECRET=""
# Production URL, e.g. https://app.example.com
AUTH_URL="http://localhost:3000"

# ===== Email (Resend) =====
# Optional in dev; required in production
RESEND_API_KEY=""

# ===== Background jobs (Redis) =====
# Only required if the app uses BullMQ
REDIS_URL="redis://localhost:6379"

# ===== Third-party integrations =====
# (Add per-integration variables here as features are added)
```

### 3.2 Rules

- **Group by category** with `# ===== Category =====` headers
- **Every variable has a placeholder value.** Use empty strings (`""`) when the value must be provided; use safe defaults (`http://localhost:3000`) where one is appropriate for local dev
- **Every variable has a one-line comment** explaining what it is or how to generate it
- **Placeholders never look like real values.** Don't use `sk_test_1234567890abcdef` — that could be mistaken for a real test key. Use empty strings or obviously-fake markers like `"changeme"`
- **The file lists every `process.env.*` the code uses.** If the code reads it, this file lists it. The Validator will check this correspondence

### 3.3 What never appears in `.env.example`

- Real API keys, tokens, passwords (the file is committed; real values would leak)
- URLs containing credentials (`postgres://user:realpassword@host/db`)
- Variables the code does not use (keep this file in sync as variables are removed)

---

## 4. .gitignore

### 4.1 Required baseline

```gitignore
# Dependencies
node_modules/
.pnpm-store/

# Build output
.next/
out/
dist/
build/

# Local environment
.env
.env.local
.env.*.local

# Testing
coverage/
playwright-report/
test-results/

# Editor / OS
.DS_Store
*.swp
.idea/
.vscode/*
!.vscode/settings.json
!.vscode/extensions.json
!.vscode/launch.json

# Logs
*.log
npm-debug.log*
pnpm-debug.log*

# Cache
.cache/
.eslintcache
.turbo/

# TypeScript
*.tsbuildinfo
next-env.d.ts

# Prisma (generated files only)
node_modules/.prisma
```

### 4.2 Rules

- **Never gitignore migration files.** `prisma/migrations/` must be committed; only the generated client (`node_modules/.prisma`) is ignored
- **Never gitignore `.env.example`** — it must be committed
- **Always gitignore `.env`, `.env.local`, and platform-specific env files**
- **Custom additions are allowed** but documented inline

---

## 5. build-package.sh and build-package.ps1

### 5.1 Behavioral requirements

The two scripts must do the same thing on their respective platforms:

1. **Verify Node version** matches `engines.node` in `package.json`. Exit non-zero if it doesn't.
2. **Install dependencies** with `pnpm install --frozen-lockfile`. The frozen flag prevents accidental lockfile drift.
3. **Run typecheck** with `pnpm typecheck`.
4. **Run linter** with `pnpm lint`.
5. **Run tests** with `pnpm test`.
6. **Build the production bundle** with `pnpm build`.
7. **Create the versioned archive** in `./dist/` (created if it doesn't exist).
8. **Print success or failure messages** at each step. The user must be able to see at a glance which step failed.

Each step exits non-zero on failure, with the script propagating the exit code.

### 5.2 Exclusion rules for the archive

The archive **must exclude**:

- `node_modules/` — installed fresh on the deployment platform
- `.next/cache/` — not needed at runtime
- `.git/` — version control history
- `.env`, `.env.local`, any `.env.*.local` — secrets
- `features/` — internal audit trail, never distributed
- Test fixture directories if `--production` flag is set (e.g., `test/`, `e2e/`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`)

The archive **must include**:

- `src/` — source code
- `prisma/` — schema and migrations
- `public/` — static assets
- `.next/` (the built output, minus cache)
- `package.json`, `pnpm-lock.yaml`
- `README.md`, `docs/`, `CHANGELOG.md`
- `.env.example`
- `.gitignore` (some deployment targets want it; safe to include)

### 5.3 Archive naming

The archive is named:

```
<project-name>-v<version>-<YYYYMMDD>.zip
```

Example: `invoice-billing-saas-v1.4.0-20260615.zip`

- `project-name` is the `name` from `package.json`
- `version` is the `version` from `package.json`
- `YYYYMMDD` is the build date in UTC

The naming convention makes it possible to know what a `.zip` contains just from its filename.

### 5.4 Idempotency

The script is idempotent: running it twice in a row should produce the same result (same archive, no errors from leftover state). This means:

- The script removes any previous build output for the same version before building
- It does not assume the absence of previous state
- It does not corrupt or leak state if interrupted partway through

### 5.5 Sample bash script structure (illustrative)

```bash
#!/usr/bin/env bash
set -e  # exit on first error

PROJECT_NAME=$(node -p "require('./package.json').name")
VERSION=$(node -p "require('./package.json').version")
BUILD_DATE=$(date -u +%Y%m%d)
ARCHIVE_NAME="${PROJECT_NAME}-v${VERSION}-${BUILD_DATE}.zip"

PRODUCTION_FLAG=""
if [[ "$1" == "--production" ]]; then
  PRODUCTION_FLAG="--production"
fi

echo "▶ Verifying Node version..."
node -e "if (process.versions.node.split('.')[0] !== '22') process.exit(1)" \
  || { echo "✗ Node 22 required"; exit 1; }
echo "✓ Node version OK"

echo "▶ Installing dependencies..."
pnpm install --frozen-lockfile
echo "✓ Dependencies installed"

echo "▶ Running typecheck..."
pnpm typecheck
echo "✓ Typecheck passed"

# ... (lint, test, build steps follow the same pattern) ...

echo "▶ Creating archive..."
mkdir -p dist
# (zip command with exclusions per section 5.2)
echo "✓ Archive created: dist/${ARCHIVE_NAME}"

echo ""
echo "Package ready: dist/${ARCHIVE_NAME}"
```

The PowerShell variant mirrors this structure with PowerShell idioms (`$ErrorActionPreference = "Stop"`, `if/else` syntax, `Compress-Archive`).

---

## 6. ASSEMBLY_INSTRUCTIONS.md

### 6.1 Required structure

```markdown
# Assembly Instructions — <Project Name> v<version>

These instructions walk you through assembling the package into a
runnable project folder, then building the distributable archive.

## Prerequisites

- Node.js 22 LTS installed
- pnpm 9.x installed
- A clean directory to assemble the project in

## Step 1 — Create the project folder

```bash
mkdir <project-name>
cd <project-name>
```

## Step 2 — Copy each file from the manifest

Refer to `FILE_MANIFEST.md`. For each row in the table, save the
corresponding artifact to the target path inside your project folder.

Most artifacts are individual files in the Package Project's
side panel. Save them with their exact target filenames.

Verify the directory structure matches the manifest before continuing.

## Step 3 — Configure environment variables

```bash
cp .env.example .env.local
```

Then edit `.env.local` with real values for your environment. See
`.env.example` for what each variable does.

## Step 4 — Make the build script executable (macOS/Linux only)

```bash
chmod +x build-package.sh
```

## Step 5 — Run the build script

**macOS/Linux:**
```bash
./build-package.sh --production
```

**Windows (PowerShell):**
```powershell
.\build-package.ps1 -Production
```

The script verifies Node, installs dependencies, runs typecheck, lint,
and tests, builds the production bundle, and creates a versioned `.zip`
in `./dist/`.

## Step 6 — Verify the archive

```bash
ls -la dist/
```

You should see a file named `<project-name>-v<version>-<YYYYMMDD>.zip`.

## Troubleshooting

### "Node 22 required" error

Your Node version doesn't match. Use `nvm` or `fnm` to switch:

```bash
nvm install 22
nvm use 22
```

### "Frozen lockfile" error

The `pnpm-lock.yaml` is out of sync with `package.json`. Run
`pnpm install` (without `--frozen-lockfile`) and check that the
lockfile changes are intentional before committing.

### Tests fail

Confirm the database is running and migrations are applied. If a
specific test fails repeatedly, see the test output for the file and
test name; consult the relevant convention or example file.

### Port 3000 already in use

A previous dev server may still be running. Either kill it
(`lsof -ti:3000 | xargs kill` on macOS/Linux) or set
`PORT=3001 pnpm dev`.

### `.env.local` not loading

Confirm the file is named exactly `.env.local` (not `.env`), and
that `next dev` was restarted after creating it.
```

### 6.2 What good looks like

- **Steps are atomic.** One action per step.
- **Each step verifies the previous one before assuming success.**
- **Troubleshooting covers the actual failures users hit.** Not generic problems; the specific errors that come up.

---

## 7. PACKAGE_CHECKLIST.md

### 7.1 Required structure

A short checklist for the user to verify before distributing the package:

```markdown
# Package Release Checklist — <Project Name> v<version>

Before distributing this package, confirm every item below.

## Files

- [ ] All files present per `FILE_MANIFEST.md`
- [ ] No files from the `features/` audit trail are in the archive
- [ ] No `.env` files (with real values) are in the archive
- [ ] `.env.example` is present and matches the variables the code uses

## Build

- [ ] `build-package.sh` (or `.ps1`) runs cleanly on a fresh checkout
- [ ] All steps pass: Node check, install, typecheck, lint, test, build
- [ ] The `.zip` is in `./dist/` with the expected filename

## Tests

- [ ] `pnpm test` passes locally
- [ ] `pnpm test:e2e` passes locally (if e2e tests exist)
- [ ] `pnpm typecheck` passes
- [ ] `pnpm lint` passes

## Validation

- [ ] All CRITICAL findings from the latest `07-validation.md` are resolved
- [ ] All IMPORTANT findings from the latest `07-validation.md` are resolved
- [ ] All COMPLIANCE FLAGS from the latest `07-validation.md` have been verified with the appropriate stakeholder

## Documentation

- [ ] `README.md` is present at the project root
- [ ] `docs/api.md`, `docs/user-guide.md`, `docs/architecture.md` are present
- [ ] `CHANGELOG.md` includes the entry for this feature/release

## Versioning

- [ ] `package.json` version reflects the change (major / minor / patch as appropriate)
- [ ] Archive filename matches `<project-name>-v<version>-<YYYYMMDD>.zip`

## Secrets

- [ ] No real secrets in `package.json`
- [ ] No real secrets in `.env.example`
- [ ] No real secrets in source code (search for likely patterns)
- [ ] Production secrets are configured in the deployment platform, not in the archive

## Distribution

- [ ] A copy of the final `.zip` is saved alongside the audit trail (`features/<feature-folder>/09-package/`)
- [ ] The recipient or deployment target is approved for the content of this package
- [ ] Distribution method matches team policy (release platform, secure channel, etc.)
```

### 7.2 What good looks like

- **Every item is a yes/no check.** No "consider whether…" language.
- **The list is short enough to actually be used.** A 30-item checklist gets skipped; this one is around 20 items grouped logically.
- **Distribution is the last category** because everything else must be confirmed before the package leaves the building.

---

## 8. Version scheme

The team uses [Semantic Versioning](https://semver.org/) (semver):

| Bump | When |
|---|---|
| **Major** (X.0.0) | Breaking changes that require changes to downstream consumers — API contract changes, removed endpoints, changed response shapes |
| **Minor** (0.X.0) | New features that don't break existing usage — new endpoints, new optional fields, new UI features |
| **Patch** (0.0.X) | Bug fixes that don't change behavior intentionally |

Initial version: `0.1.0`. Bump to `1.0.0` when the first stable, production-ready release ships.

**Pre-release versions** use a hyphenated suffix: `1.4.0-rc.1`, `2.0.0-beta.2`. The build script accepts these and includes them in the archive filename.

The Package Project picks a reasonable default based on the feature's brief, but the version is yours to confirm. Gate 4 explicitly asks: "Does the version number make sense?"

---

## 9. Tuning notes

- **If packages keep failing to build on a fresh checkout**, walk the `build-package.sh` script against a clean clone and update section 5 accordingly.
- **If `.env.example` keeps missing variables the code actually uses**, the Backend/Frontend Builder summaries are probably not listing them. Strengthen the summary templates upstream.
- **If the manifest keeps missing files**, the Package Project's inputs were probably incomplete. Confirm every chain artifact is uploaded before the Package Project runs.
- **If the archive keeps including files it shouldn't**, the exclusion list in section 5.2 needs to be sharper.

---

## 10. Change log

| Date | Change | Reason | Decided by |
|---|---|---|---|
| _YYYY-MM-DD_ | Initial adoption | Bootstrapping the factory | _name / role_ |