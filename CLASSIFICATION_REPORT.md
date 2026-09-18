# Spashta → RoomieOps Transformation Classification Report

**Generated:** September 18, 2026  
**Purpose:** Comprehensive file-by-file audit for transformation from Spashta to RoomieOps  
**Status:** READY FOR EXECUTION

---

## SECTION A: REUSABLE INFRASTRUCTURE (KEEP AS-IS)

Files that provide generic technical patterns suitable for RoomieOps without modification.

### Backend — Shared Libraries

| File | Classification | Reason | Action |
|------|----------------|--------|--------|
| `backend/shared/bedrock.py` | **KEEP AS-IS** | Generic Bedrock client wrapper; no Spashta-specific logic | Reuse for RoomieOps AI operations |
| `backend/shared/utils.py` | **KEEP AS-IS** | Generic Lambda utilities (response formatting, env handling, auth extraction) | Reuse for all RoomieOps Lambdas |
| `backend/shared/requirements.txt` | **KEEP AS-IS** | Python dependencies for shared libraries | Maintain for Lambda shared layer |

### AWS Infrastructure (SAM Template)

| File | Classification | Reason | Action |
|------|----------------|--------|--------|
| `infrastructure/template.yaml` | **KEEP BUT ADAPT** | SAM template structure is sound; Spashta resource names/logic must be replaced | See Section B |
| `infrastructure/statemachine/` | **KEEP BUT ADAPT** | Step Functions pattern is reusable; need RoomieOps-specific states | See Section B |

### Frontend Foundation

| File | Classification | Reason | Action |
|------|----------------|--------|--------|
| `frontend/package.json` | **KEEP BUT ADAPT** | React + Vite + TypeScript setup is reusable | Update name, description, dependencies |
| `frontend/vite.config.ts` | **KEEP AS-IS** | Generic Vite configuration | Reuse as-is |
| `frontend/tsconfig.json` | **KEEP AS-IS** | Standard TypeScript config | Reuse as-is |
| `frontend/tsconfig.node.json` | **KEEP AS-IS** | Vite TypeScript config | Reuse as-is |
| `frontend/.eslintrc.cjs` | **KEEP AS-IS** | ESLint configuration | Reuse as-is |
| `frontend/index.html` | **KEEP BUT ADAPT** | HTML structure reusable; update title, viewport, etc. | Minimal updates needed |
| `frontend/src/index.css` | **KEEP AS-IS** | Generic CSS reset/globals | Reuse or extend |
| `frontend/src/api/client.ts` | **KEEP BUT ADAPT** | API client pattern is reusable; update endpoints for RoomieOps | See Section B |

### Configuration & Environment

| File | Classification | Reason | Action |
|------|----------------|--------|--------|
| `.env.example` | **KEEP BUT ADAPT** | Environment variable pattern is sound; update variable names | See Section B |
| `.gitignore` | **KEEP AS-IS** | Generic .gitignore for Node/Python projects | Reuse as-is |
| `docker-compose.yml` | **KEEP AS-IS** | LocalStack setup for local development | Maintain for local testing |

### Local Development

| File | Classification | Reason | Action |
|------|----------------|--------|--------|
| `backend/local_dev_server.py` | **KEEP BUT ADAPT** | Local development server pattern; update for RoomieOps endpoints | See Section B |
| `backend/local_server.py` | **KEEP BUT ADAPT** | Same as above | See Section B |
| `backend/requirements-dev.txt` | **KEEP AS-IS** | Development dependencies | Maintain for testing |

### Testing Infrastructure

| File | Classification | Reason | Action |
|------|----------------|--------|--------|
| `tests/` directory | **KEEP BUT ADAPT** | Test structure and patterns are reusable; delete Spashta tests | Rewrite for RoomieOps |
| Pytest fixtures | **KEEP AS-IS** | Generic pytest patterns | Reuse for RoomieOps tests |

---

## SECTION B: INFRASTRUCTURE NEEDING ADAPTATION

Files that require refactoring, renaming, or restructuring to fit RoomieOps architecture.

### Backend — Lambda Directory Structure

| Current Path | Action | Reason |
|--------------|--------|--------|
| `backend/lambdas/api-get-document/` | **DELETE & REPLACE** | Spashta-specific API endpoint; replace with RoomieOps household/expense APIs |
| `backend/lambdas/api-presigned-url/` | **DELETE & REPLACE** | Spashta document-specific; replace with generic file upload handler if needed |
| `backend/lambdas/api-start-processing/` | **DELETE & REPLACE** | Spashta pipeline orchestration; replace with RoomieOps copilot handler |
| `backend/lambdas/extract/` | **DELETE & REPLACE** | Spashta clause extraction logic; replace with RoomieOps expense extraction |
| `backend/lambdas/explanation/` | **DELETE & REPLACE** | Spashta explanation generation; replace with RoomieOps copilot responses |
| `backend/lambdas/match-situation/` | **DELETE & REPLACE** | Spashta situation matching logic; not needed for RoomieOps |
| `backend/lambdas/risk-classify/` | **DELETE & REPLACE** | Spashta risk classification; not needed for RoomieOps |

**Replacement Strategy:**
- Create new Lambda structure organized by RoomieOps domain:
  - `backend/lambdas/copilot/` — AI agent handler
  - `backend/lambdas/households/` — household management
  - `backend/lambdas/expenses/` — expense operations
  - `backend/lambdas/payments/` — payment handling
  - `backend/lambdas/chores/` — chore management
  - `backend/lambdas/members/` — member management
  - `backend/lambdas/notifications/` — notification service
  - `backend/lambdas/documents/` — receipt/bill processing (if retained)

### SAM Template (`infrastructure/template.yaml`)

**Changes Required:**

| Component | Current | Action |
|-----------|---------|--------|
| **Description** | "Spashta - Source-grounded decision support..." | Update to RoomieOps description |
| **DynamoDB Table Name** | `spashta-documents` | Rename to `roomieops-household-state` |
| **S3 Bucket Name** | `spashta-documents-*` | Rename to `roomieops-documents-*` |
| **Cognito User Pool** | Generic; keep structure | Keep but update naming |
| **Lambda Functions** | 7 Spashta handlers | Replace with RoomieOps handlers |
| **Step Functions** | Spashta 4-stage pipeline | Update to RoomieOps workflows |
| **EventBridge Rules** | None present; may be added | Create for household events |
| **IAM Policies** | Generic; keep structure | Keep but update table/bucket references |
| **Tags** | `Application: Spashta` | Update to `Application: RoomieOps` |

### Step Functions State Machine

**Current:** `infrastructure/statemachine/definition.yaml` orchestrates 4-stage Spashta pipeline (Extract → Match → Classify → Explain)

**Action:** Rewrite for RoomieOps workflows such as:
- Expense creation from receipt
- Chore rotation rebalancing
- Absence workflow coordination
- Bill reminder automation

### Frontend API Client (`frontend/src/api/client.ts`)

**Changes Required:**
- Update base URL environment variable
- Replace Spashta endpoints with RoomieOps endpoints
- Update request/response types
- Keep HTTP method patterns and error handling

### Package.json Metadata

**Changes Required:**
- `"name"`: `"spashta-frontend"` → `"roomieops-frontend"`
- `"description"`: Update to RoomieOps tagline
- `"version"`: Keep or reset to `"0.1.0"`
- Dependencies: Keep React, TypeScript, Vite, ESLint

### Environment Variables (`.env.example`)

**Current Names → New Names:**

| Old | New | Reason |
|-----|-----|--------|
| `S3_BUCKET_NAME=spashta-documents-*` | `S3_BUCKET_NAME=roomieops-documents-*` | Resource naming |
| `DYNAMODB_TABLE_NAME=spashta-documents` | `DYNAMODB_TABLE_NAME=roomieops-household-state` | Entity naming |
| (keep) `AWS_REGION` | (keep) `AWS_REGION` | Unchanged |
| (keep) `BEDROCK_MODEL_ID` | (keep) `BEDROCK_MODEL_ID` | Unchanged |
| (keep) `COGNITO_*` | (keep) `COGNITO_*` | Unchanged |
| (keep) `API_GATEWAY_URL` | (keep) `API_GATEWAY_URL` | Unchanged |

---

## SECTION C: SPASHTA-SPECIFIC FILES TO DELETE

Files that are entirely Spashta product logic and must be removed entirely.

### Lambda Handlers (All)

```
backend/lambdas/extract/app.py
backend/lambdas/match-situation/app.py
backend/lambdas/risk-classify/app.py
backend/lambdas/explanation/app.py
backend/lambdas/api-get-document/app.py
backend/lambdas/api-presigned-url/app.py
backend/lambdas/api-start-processing/app.py
backend/lambdas/*/requirements.txt (all handler-specific dependencies)
```

**Reason:** All implement Spashta document extraction/reasoning pipeline; not reusable for RoomieOps.

### Frontend Screens (All Spashta-Specific)

```
frontend/src/screens/Upload.tsx          (document upload screen)
frontend/src/screens/Processing.tsx      (4-stage pipeline progress)
frontend/src/screens/Results.tsx         (risk tier + explanation display)
frontend/src/screens/Checklist.tsx       (readiness checklist)
frontend/src/screens/*.css               (all corresponding stylesheets)
```

**Reason:** All screens implement Spashta workflows; must be replaced with RoomieOps screens.

### Frontend Type Definitions (`frontend/src/types/index.ts`)

**Current Exports (DELETE):**
- `RiskTier`, `Confidence` enums (Spashta-specific)
- `Clause`, `Match`, `RiskResult`, `ExplanationResult` interfaces
- `ProcessedDocument` interface (Spashta schema)

**Keep:** Generic types like `Language` if useful; otherwise rewrite.

### Frontend App Component (`frontend/src/App.tsx`)

**Action:** **DELETE & REWRITE**

**Current Flow:** Upload → Processing → Results (Spashta pipeline)

**Future Flow:** Dashboard → Copilot → Household state views (RoomieOps)

### Frontend CSS Files

```
frontend/src/App.css
frontend/src/screens/Upload.css
frontend/src/screens/Processing.css
frontend/src/screens/Results.css
frontend/src/screens/Checklist.css
```

**Action:** Delete; rewrite for RoomieOps layout/branding.

### Frontend Mock API (`frontend/src/api/mock.ts`)

**Action:** **DELETE**

**Reason:** Mocks Spashta API responses; replace with real API calls for RoomieOps.

### Prompts Directory

```
prompts/
  ├── extract.txt                (Spashta clause extraction prompt)
  ├── match-situation.txt        (Spashta situation matching prompt)
  ├── classify-risk.txt          (Spashta risk classification prompt)
  └── explain-translate.txt      (Spashta explanation generation prompt)
```

**Action:** **DELETE**

**Reason:** Spashta-specific AI prompts; will be replaced with RoomieOps copilot prompts.

### Data Files

```
data/
  └── attendance-regulation.md   (Spashta demo document)
```

**Action:** **DELETE**

**Reason:** Spashta-specific test data; not applicable to RoomieOps.

### Documentation (All Spashta-Focused)

```
README.md                          (Spashta README — complete rewrite needed)
SPASHTA_BUILD_SPEC.md             (Spashta specification document)
IMPLEMENTATION_SUMMARY.md         (Spashta implementation summary)
COMPLETION_REPORT.md              (Spashta completion report)
SESSION_SUMMARY.md                (Spashta session notes)
docs/ARCHITECTURE.md              (Spashta architecture)
docs/DEVELOPMENT.md               (Spashta development guide)
docs/AWS_DEPLOYMENT.md            (Spashta deployment guide)
docs/TESTING.md                   (Spashta testing guide)
DEPLOYMENT_CHECKLIST.md           (Spashta deployment checklist)
LOCALHOST_DEPLOYMENT_STATUS.md    (Spashta local deployment notes)
LOCAL_DEV_SETUP.md                (Spashta local setup notes)
```

**Action:** **DELETE ALL**

**Reason:** All are Spashta-specific documentation; will be replaced with minimal RoomieOps docs.

### Local Storage / Artifacts

```
local_storage/                     (LocalStack artifacts)
infrastructure/samconfig.toml     (Spashta SAM deployment config)
backend/lambdas/__pycache__/      (Python cache)
frontend/dist/                    (Spashta build output)
frontend/node_modules/            (Node dependencies — can be reinstalled)
```

**Action:** **DELETE or IGNORE**

**Reason:** Temporary/generated files; safe to remove.

### Miscellaneous

```
.git/                             (Spashta commit history)
desktop.ini                       (Windows metadata)
```

**Action:** **DELETE .git** (reinitialize as fresh RoomieOps repo)  
**Action:** **DELETE desktop.ini** (Windows-specific junk file)

---

## SECTION D: POTENTIALLY REUSABLE — REQUIRES MANUAL INSPECTION

Files that might contain useful patterns but need careful review before reuse.

| File | Classification | Risk | Recommendation |
|------|----------------|------|-----------------|
| `tests/` (if any exist) | **INSPECT** | May contain Spashta-specific test logic | Review test patterns; delete Spashta tests; rewrite for RoomieOps |
| Infrastructure policies/roles in SAM | **INSPECT** | May be too tightly scoped to Spashta | Review IAM policies; adapt for RoomieOps resources |
| Step Functions definition | **INSPECT** | Pipeline structure may be reusable | Review orchestration pattern; adapt to RoomieOps workflows |

---

## SUMMARY TABLE

| Category | Keep As-Is | Adapt | Delete | Total |
|----------|-----------|-------|--------|-------|
| **Backend Code** | 3 | 8 | 7 | 18 |
| **Frontend Code** | 6 | 2 | 8 | 16 |
| **Config/Env** | 2 | 1 | 0 | 3 |
| **Infrastructure** | 1 | 2 | 1 | 4 |
| **Documentation** | 0 | 0 | 11 | 11 |
| **Artifacts/Temp** | 0 | 0 | 6 | 6 |
| **TOTALS** | **12** | **13** | **33** | **58** |

---

## NEXT STEPS (EXECUTION ORDER)

1. **Verify this classification** — confirm no critical files are misclassified
2. **Delete Spashta-specific product code** (Section C)
3. **Adapt infrastructure** (Section B)
4. **Restructure backend/lambdas** with placeholder RoomieOps handlers
5. **Restructure frontend** with minimal RoomieOps screens
6. **Update environment variables and configs**
7. **Search/replace all Spashta references** globally
8. **Verify git status** and prepare for fresh repository
9. **Final validation** — build, lint, syntax check
10. **Prepare for new GitHub repository**

---

## CLASSIFICATION SIGN-OFF

**Report Generated:** 2026-09-18  
**Auditor:** Kiro (Automated Classification)  
**Status:** READY FOR EXECUTION — Proceed with Tasks 3-10

