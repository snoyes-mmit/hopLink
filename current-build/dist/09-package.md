# Project 9 — Package

> **Role in the chain:** Step 9 of 9. Runs after the Documentation Project. Final step.
> **Human approval gate:** **Yes — Gate 4**
> **Output saved as:** Assembly artifacts in the per-feature folder's `09-package/` subdirectory

---

## Purpose

The Package Project produces everything needed to assemble the feature or app into a runnable, distributable archive on the user's local machine. It generates the file manifest, the build script, the assembly instructions, and the release checklist — but it does **not** produce the archive itself. That step happens locally, by running the build script the Project provides.

This role exists because claude.ai Projects cannot package a multi-file archive from a conversation. Artifacts are downloaded one at a time, which is fine for review but not for distribution. The Package Project's job is to make the gap between "I have all these artifacts" and "I have a single downloadable archive" as painless and traceable as possible.

The Package Project never produces the `.zip` itself, never modifies source files, and never proceeds without all prior outputs from the chain.

---

## Inputs

The Package Project expects to receive:

- All code files produced by the Backend Builder
- All code files produced by the Frontend Builder
- All test files produced by the Test Project
- All documentation files produced by the Documentation Project
- The approved user story (`02-story.md`) and technical brief (`03-spec.md`) for context
- The validator's final clean report (`07-validation.md` or its latest versioned successor)

It reads from its knowledge base on every run:

- `general-conventions.md`
- `js-conventions.md`
- `target-stack-spec.md`
- `deployment-notes.md`
- `package-manifest-template.md`

---

## Outputs

Eight files, each produced as a separate artifact in the side panel. You save each one into the feature folder's `09-package/` subdirectory.

1. **`FILE_MANIFEST.md`** — every file in the package and where it goes
2. **`package.json`** — complete, install-ready
3. **`.env.example`** — all required environment variables
4. **`.gitignore`** — Node/Next.js standard plus project-specific
5. **`README.md`** — packaging-specific (or merged with the Documentation Project's README)
6. **`build-package.sh`** AND **`build-package.ps1`** — cross-platform build scripts
7. **`ASSEMBLY_INSTRUCTIONS.md`** — step-by-step for the user
8. **`PACKAGE_CHECKLIST.md`** — release verification checklist

---

## Knowledge base files to upload

Upload these into the Package Project's knowledge base:

| File | Purpose |
|---|---|
| `general-conventions.md` | Commits, branches, PRs, no-secrets, naming |
| `js-conventions.md` | Node version, package manager, tsconfig, ESLint, Prettier |
| `target-stack-spec.md` | The default stack for new apps |
| `deployment-notes.md` | How apps are run locally and deployed |
| `package-manifest-template.md` | The shape of the file manifest and package metadata |

`deployment-notes.md` and `package-manifest-template.md` are doing the heaviest work here. The Package Project will mirror the build script patterns, the environment variable conventions, and the manifest shape from these files. Spend time on them once and the packaging output will be consistent across every feature you ship.

---

## Custom instructions

Paste the block below into the Package Project's **Custom Instructions** field.

```
You are the packaging step for a JavaScript SaaS factory. Your
job is to produce everything the user needs to assemble the
feature or app into a runnable, distributable .zip on their
own machine. You do NOT produce the .zip directly — claude.ai
Projects cannot zip multi-file outputs in this environment.

Inputs:
- All file artifacts produced by Backend Builder, Frontend
  Builder, Test, and Documentation
- The approved user story and brief (for context)
- The final clean validator report

If any required input is missing (e.g., no Documentation
outputs were produced, or the validator report shows
unresolved critical findings), list what's missing and
refuse to proceed. Treat this as a release step. Be
conservative — if something feels incomplete, flag it
rather than papering over.

Produce these outputs, each as its own artifact in the side
panel:

1. FILE_MANIFEST.md
   A table listing every file that goes into the package:
   | Source artifact | Target path in package | Purpose |
   So the user can verify nothing was missed when copying
   artifacts into the project folder. Include every file
   from every prior role — backend code, frontend code,
   tests, documentation. Do not omit files.

2. package.json
   Complete and ready to install. Include:
   - name, version, description, license
   - scripts: dev, build, start, test, typecheck, lint, format
   - dependencies and devDependencies derived from what was
     actually used in the produced code (not generic defaults)
   - engines.node specifying the Node version from
     target-stack-spec.md
   - Any package-specific scripts the deployment-notes.md
     mention

3. .env.example
   All required environment variables with placeholder values
   and one-line comments explaining each. Pull the variables
   from what the produced code actually uses, not from a
   generic list. Group related variables together (database,
   auth, email, etc.).

4. .gitignore
   Standard Node/Next.js .gitignore plus any project-specific
   exclusions (build outputs, local caches, IDE files,
   environment files).

5. README.md (root, packaging section only)
   If the Documentation Project already produced a README.md,
   note that here and reference it. If the user wants the two
   merged, produce the merged version with the Documentation
   Project's content as the primary content and the packaging
   section appended. Default to referencing rather than merging
   unless instructed otherwise.

6. build-package.sh AND build-package.ps1
   Cross-platform scripts that:
   - Verify Node version matches target-stack-spec.md
   - Install dependencies (pnpm install)
   - Run typecheck (pnpm typecheck)
   - Run linter (pnpm lint)
   - Run tests (pnpm test)
   - Build the production bundle (pnpm build)
   - Create a versioned .zip in ./dist/ excluding
     node_modules, .next, .git, .env, and tests if a
     --production flag is set
   - Print clear success or failure messages at each step
   - Exit non-zero on any failure so the user knows the
     package is not ready

7. ASSEMBLY_INSTRUCTIONS.md
   Step-by-step instructions for the user:
   a) Create the project folder
   b) Copy each artifact to the correct path (reference
      FILE_MANIFEST.md)
   c) Set up .env from .env.example
   d) Run build-package.sh (or .ps1 on Windows)
   e) Find the resulting .zip in ./dist/
   Include troubleshooting for common issues:
   - Wrong Node version
   - Missing environment variables
   - Port conflicts
   - Database not running
   - Permission issues on the build script

8. PACKAGE_CHECKLIST.md
   A short checklist for the user to verify before
   distributing the package:
   - All files present per FILE_MANIFEST.md
   - Tests pass (typecheck, lint, unit, e2e)
   - .env.example complete and accurate
   - Validator critical and important findings resolved
   - Documentation present and accurate
   - Version number bumped appropriately
   - No secrets committed (scan package.json, .env.example,
     and source files)
   - CHANGELOG.md updated with this feature's entry

Behaviour rules:
- Produce every file as a complete, copy-paste-ready artifact.
  No truncation, no placeholders, no "// ... rest of file"
  comments. The user will run these directly.
- The build script must be idempotent — running it twice
  should produce the same result, not double-build or fail
  on the second run.
- Default to zip name: <project-name>-v<version>-<YYYYMMDD>.zip
- Never include secrets in package.json, .env.example, or any
  committed file. .env.example contains placeholder values
  only.
- If any required input is missing, list what's missing and
  stop. Do not produce a partial package.
- If the validator's final report has unresolved critical
  findings, refuse to package and ask the user to resolve
  them first.
- Treat this as a release step. Be conservative. If something
  feels incomplete (e.g., no e2e tests when the brief said
  they were required), flag it under PACKAGE_CHECKLIST as
  "to verify" rather than silently marking it complete.
- Reference the prior chain artifacts in FILE_MANIFEST.md by
  their saved filenames (01-research.md through
  07-validation.md) so the audit trail is preserved in the
  package.
```

---

## How to use this Project in the workflow

1. **Open the Package Project** in claude.ai.
2. **Start a new conversation.** Always start fresh.
3. **Paste or upload the inputs.** This is the most input-heavy step in the chain:
   - All backend code files (or summaries pointing to them)
   - All frontend code files (or summaries pointing to them)
   - All test files (or the coverage report pointing to them)
   - All documentation files
   - The user story and brief for context
   - The final validator report (must be clean of criticals)
4. **Receive eight artifacts** in the side panel. Save each one to the feature folder's `09-package/` subdirectory:
   ```
   features/2026-05-25-invoice-reminders/09-package/
   ├── FILE_MANIFEST.md
   ├── package.json
   ├── .env.example
   ├── .gitignore
   ├── README.md
   ├── build-package.sh
   ├── build-package.ps1
   ├── ASSEMBLY_INSTRUCTIONS.md
   └── PACKAGE_CHECKLIST.md
   ```
5. **Follow ASSEMBLY_INSTRUCTIONS.md** to copy the code, test, and documentation artifacts into a fresh project folder on your machine, structured according to `FILE_MANIFEST.md`.
6. **Run the build script** (`./build-package.sh` on macOS/Linux or `.\build-package.ps1` on Windows). The script will verify Node, install dependencies, run typecheck and lint and tests, build the production bundle, and produce a versioned `.zip` in `./dist/`.
7. **Gate 4 — final review of the package.** Work through `PACKAGE_CHECKLIST.md` before distributing the archive. This is your last chance to catch anything before the package leaves your machine.
8. **Distribute the archive** according to your team's normal process — upload to your release platform, share with the client, deploy to staging, whatever applies.

---

## What "Gate 4" really checks

Gate 4 is the final review before distribution. It is different from Gates 1–3 in that the chain has already validated the work; Gate 4 is checking the *package*, not the *feature*. Five questions cover the most consequential checks:

1. **Does the build script actually run cleanly on your machine?** A clean local build is the minimum evidence that the package is well-formed. If the script fails on a fresh checkout, the package is not ready, regardless of what every other artifact says.
2. **Does `FILE_MANIFEST.md` list every file you saved from the chain?** Cross-check the manifest against the artifacts you have. A missing file in the manifest means a missing file in the package, which means a broken install for the recipient.
3. **Does `.env.example` cover every environment variable the code actually uses?** The Package Project pulls these from the produced code, but if the chain quietly added a variable mid-build, it may be missing. A grep through the source for `process.env.` confirms.
4. **Are there any secrets anywhere they should not be?** Check `package.json`, `.env.example`, and skim the source for any string that looks like a credential. The Package Project enforces "no secrets" but humans should still verify.
5. **Does the version number make sense?** A new feature is usually a minor bump; a bug fix is a patch bump; a breaking change is a major bump. The Package Project picks something reasonable, but the version is yours to set.

If the answer to all five is yes, approve and distribute. If not, fix in the appropriate place — usually the Package Project itself, but sometimes you need to loop back further if the issue reveals a gap in an earlier role.

---

## Why the Package Project does not produce the `.zip`

This is worth stating clearly because it is the most counter-intuitive thing about the chain.

Claude Projects produces files as artifacts in the side panel, one at a time. Each artifact is individually downloadable. There is no built-in "download all as zip" capability in the claude.ai Projects environment.

The Package Project could theoretically generate a script that the user pipes into a shell or runs in a separate environment to assemble the artifacts — but that path is fragile (it requires the user to copy long shell snippets without modification), opaque (the user has no visibility into what is being assembled), and breaks audit traceability (the assembly step happens outside the chain).

The manifest-plus-script approach is more reliable for the same reason a recipe is more reliable than a fully-cooked meal delivered through the mail: it lets the user verify each step, see what is being included, and intervene if something looks wrong. In regulated-adjacent work, that visibility matters.

If running a local build script feels heavier than you want, the open-source `claude-artifacts-downloader` Chrome extension can bundle all artifacts from a single conversation into a `.zip`. It is third-party — vet it before installing in a work environment, and do not rely on it for anything you need a documented audit trail for. For SaaS deliverables that may face client or compliance review, the manifest-plus-script approach is the more reliable, traceable option.

---

## What goes into `09-package/` vs. the actual project folder

A common source of confusion: the artifacts the Package Project produces are *meta-artifacts* — they describe how to assemble the project, but they are not the project itself. Two folder structures are at play:

**The audit trail (lives in your `features/` folder):**
```
features/2026-05-25-invoice-reminders/
├── 00-feature-idea.md
├── 01-research.md
├── ... (all chain artifacts) ...
├── 08-documentation/
└── 09-package/
    ├── FILE_MANIFEST.md
    ├── ASSEMBLY_INSTRUCTIONS.md
    ├── build-package.sh
    ├── package.json
    └── ... (the meta-artifacts) ...
```

**The actual buildable project (lives wherever you assemble it):**
```
invoice-reminders/
├── src/
│   ├── services/
│   ├── components/
│   └── ...
├── tests/
├── docs/
├── package.json
├── .env.example
├── build-package.sh
└── README.md
```

The Package Project's outputs live in `09-package/` as the *recipe*. You follow `ASSEMBLY_INSTRUCTIONS.md` to construct the actual project folder elsewhere on your machine — typically in a clean workspace dedicated to that feature. The `.zip` ends up in `./dist/` of the actual project folder, not in `09-package/`.

This separation matters because the audit trail (the `features/` folder) is preserved long after the actual project folder may have been deleted or merged into a larger codebase. The chain's record of how the feature came to be lives on.

---

## Tuning notes

- The biggest lever for packaging quality is `package-manifest-template.md`. It defines the manifest shape, the version scheme, and the script conventions. Tune this once and packaging gets dramatically more consistent.
- If `package.json` keeps coming out with generic dependencies that don't match the produced code, the issue is usually that the prior chain artifacts were summarized rather than fully included as inputs. Paste the actual code, not just summaries.
- If the build script keeps failing in different ways on different runs, it is not idempotent. Strengthen the "must be idempotent" rule and check that the script cleans up its own intermediate state.
- If `.env.example` keeps missing variables that the code actually uses, the issue is usually that the Backend Builder or Frontend Builder summaries did not list environment variables explicitly. Add an "Environment variables used" section to the summary templates upstream.
- If `ASSEMBLY_INSTRUCTIONS.md` keeps glossing over the file-copy step, sharpen the rule that every file from `FILE_MANIFEST.md` must have a clear source-to-target mapping. The user should be able to assemble the project without reading any other document.

---

## Compliance reminder

The package is the artifact that leaves your environment and reaches the client, the deployment platform, or the audit system. Four rules apply specifically to packaging in regulated-adjacent work:

1. **Never include the per-feature audit trail in the distributable archive.** The `features/2026-05-25-invoice-reminders/` folder is your internal audit trail. It contains the design decisions, the validator findings, the test reports, and the intermediate artifacts. None of that belongs in the `.zip` you send to a client. The build script's exclusion list should keep this folder out by default — confirm before distribution.

2. **Never include `.env` files in the archive — only `.env.example`.** The build script's `--production` flag excludes `.env`, but verify. A leaked `.env` containing real credentials is one of the most common ways production secrets reach unauthorized recipients.

3. **Verify the version number reflects the change.** In regulated-adjacent work, version numbers are often tied to validation status, MLR approval, and audit records. A package shipped with the wrong version number may be interpreted as a different release than it actually is. The Package Project picks a reasonable default; you confirm it matches your team's versioning conventions.

4. **Save the final `.zip` alongside the audit trail.** Once the package is built, save a copy in `features/2026-05-25-invoice-reminders/09-package/` (or in your team's release archive) so future audits can confirm exactly what was distributed. The chain produced the recipe; the archive is the result; both are evidence.

Before distributing any package externally, confirm with your IT/security/compliance stakeholders that:

- The content of the package is approved for the audience that will receive it
- The build process used (claude.ai Projects + local assembly) is approved for the kind of content being processed
- The audit trail is complete and stored according to your team's retention policy
- Any third-party tools used to assist with packaging (Chrome extensions, conversion utilities) have been vetted for the work environment

The Package Project produces a release-ready archive. It does not certify that the archive is approved for distribution. That certification remains a human responsibility, supported by the evidence the chain has produced at every step.