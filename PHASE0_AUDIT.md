# Phase 0: Repository Audit Report

**Date:** September 18, 2026  
**Purpose:** Pre-implementation audit to classify current code and infrastructure  
**Status:** Identifies work needed before coding starts

---

## 1. Repository Structure

```
roomieops/
├── frontend/
│   ├── src/
│   │   ├── api/ — API client (rewritten for RoomieOps)
│   │   ├── screens/ — (empty, needs RoomieOps screens)
│   │   ├── types/ — RoomieOps entity types (created)
│   │   ├── App.tsx — (new RoomieOps app)
│   │   ├── App.css — (new styling)
│   │   ├── index.css — (generic globals)
│   │   └── main.tsx
│   ├── package.json — (updated to roomieops-frontend)
│   ├── index.html — (updated title)
│   └── build config — (intact: Vite, TypeScript, ESLint)
├── backend/
│   ├── lambdas/
│   │   ├── copilot/ — (NEW: placeholder)
│   │   ├── households/ — (NEW: placeholder)
│   │   ├── expenses/ — (NEW: placeholder)
│   │   ├── chores/ — (NEW: placeholder)
│   │   ├── payments/ — (NEW: placeholder)
│   │   ├── notifications/ — (NEW: placeholder)
│   │   ├── api-get-document/ — (SPASHTA: delete)
│   │   ├── api-presigned-url/ — (SPASHTA: delete)
│   │   ├── api-start-processing/ — (SPASHTA: delete)
│   │   ├── explanation/ — (SPASHTA: delete)
│   │   ├── extract/ — (SPASHTA: delete)
│   │   ├── match-situation/ — (SPASHTA: delete)
│   │   ├── risk-classify/ — (SPASHTA: delete)
│   │   └── shared/ — (REUSABLE: Bedrock client, utils)
│   ├── shared/
│   │   ├── bedrock.py — (REUSABLE: generic Bedrock wrapper)
│   │   ├── utils.py — (REUSABLE: Lambda utilities)
│   │   └── requirements.txt
│   ├── stepfunctions/
│   │   └── definition.yaml — (REUSABLE: placeholder structure)
│   ├── local_dev_server.py — (UPDATED: RoomieOps)
│   ├── local_server.py — (UPDATED: RoomieOps)
│   └── requirements-dev.txt
├── infrastructure/
│   ├── template.yaml — (ADAPTED: RoomieOps DynamoDB schema, S3, Lambda)
│   └── statemachine/ — (placeholder for workflows)
├── docker-compose.yml — (UPDATED: RoomieOps container names)
├── .env.example — (UPDATED: RoomieOps variables)
├── ROOMIEOPS_BUILD_SPEC.md — (AUTHORITATIVE)
├── KIRO_MASTER_PROMPT.md — (EXECUTION GUIDE)
└── README.md — (outdated, needs updates)
```

---

## 2. Frontend Status

### READY
- ✅ React 18 + TypeScript + Vite setup (intact, working)
- ✅ ESLint + TypeScript compilation
- ✅ API client structure (rewritten for RoomieOps endpoints)
- ✅ Type system (12 RoomieOps entity types defined)
- ✅ Minimal App.tsx with navigation structure

### NEEDS COMPLETION
- ❌ Screens: Dashboard, Copilot, Money, Chores, Maintenance, Shopping, Household, Notifications
- ❌ State management: (to be determined: Context API, Redux, Zustand, etc.)
- ❌ Error handling and loading states
- ❌ Confirmation flow for consequential actions (P1)
- ❌ Authentication integration (Cognito sign-in/up/out)

### BLOCKERS
- Frontend cannot work until backend APIs are defined and wired

---

## 3. Backend Status

### REUSABLE
- ✅ `backend/shared/bedrock.py` — Generic Bedrock client (no Spashta logic)
- ✅ `backend/shared/utils.py` — Lambda utilities (response formatting, auth extraction)
- ✅ Lambda structure pattern (handler, requirements.txt per function)
- ✅ Local dev servers (updated to RoomieOps branding)

### PLACEHOLDER HANDLERS (RoomieOps P0-tier)
- ⚠️ `backend/lambdas/copilot/` — AI agent orchestration (empty, needs Bedrock wiring)
- ⚠️ `backend/lambdas/households/` — Household operations (empty, needs implementation)
- ⚠️ `backend/lambdas/expenses/` — Expense tracking (empty, needs financial engine)
- ⚠️ `backend/lambdas/chores/` — Chore management (empty, needs rotation logic)
- ⚠️ `backend/lambdas/payments/` — Payment recording (empty, needs balance logic)
- ⚠️ `backend/lambdas/notifications/` — Notifications (empty, needs EventBridge integration)

### SPASHTA CODE TO DELETE
- ❌ `backend/lambdas/api-get-document/` — Spashta document retrieval
- ❌ `backend/lambdas/api-presigned-url/` — Spashta S3 upload
- ❌ `backend/lambdas/api-start-processing/` — Spashta pipeline start
- ❌ `backend/lambdas/explanation/` — Spashta explanation generation
- ❌ `backend/lambdas/extract/` — Spashta clause extraction
- ❌ `backend/lambdas/match-situation/` — Spashta situation matching
- ❌ `backend/lambdas/risk-classify/` — Spashta risk classification

### MISSING CORE COMPONENTS
- ❌ Deterministic financial engine (split calculation, balance reconciliation)
- ❌ DynamoDB access layer (household, member, expense, chore, balance, audit)
- ❌ Step Functions pipeline (validate → calculate → write → audit)
- ❌ Bedrock agent orchestrator (intent, tool selection, explanation)
- ❌ EventBridge workflows (reminders, notifications)
- ❌ Strands agent support (Build It path, P2)

---

## 4. Infrastructure Status

### SAM TEMPLATE (infrastructure/template.yaml)

**ADAPTED FOR ROOMIEOPS:**
- ✅ DynamoDB table: `roomieops-household-state` (pk/sk composite key schema)
- ✅ S3 bucket: `roomieops-documents-*`
- ✅ Cognito: RoomieOps user pool and client
- ✅ API Gateway: `RoomieOpsApi`
- ✅ IAM execution role with DynamoDB, S3, Bedrock permissions
- ✅ Step Functions: `EventWorkflowStateMachine` (placeholder)

**CURRENT STATE:**
- Template references deleted Spashta Lambda handlers
- Lambda function definitions need to be rewritten for RoomieOps handlers
- Step Functions definition is a placeholder
- All resource naming is RoomieOps-correct

### STEP FUNCTIONS (backend/stepfunctions/definition.yaml)
- Currently: placeholder "HandleEvent" state
- Needs: P0 workflow pipeline (validate → calculate → write → audit)

### ENVIRONMENT VARIABLES
- ✅ `.env.example` updated with RoomieOps variables
- Variables needed: `BEDROCK_MODEL_ID`, `DYNAMODB_TABLE_NAME`, `S3_BUCKET_NAME`, `COGNITO_*`, `API_GATEWAY_URL`

---

## 5. Configuration Status

### DOCKER COMPOSE
- ✅ Updated for RoomieOps (container names: `roomieops-localstack`, `roomieops-dynamodb`, `roomieops-s3`)
- ✅ Services: LocalStack, DynamoDB local, MinIO S3 local
- Ready for local development

### GIT STATUS
- ✅ Remote: https://github.com/KunalMK25/RoomieOps.git
- ✅ Branch: main (clean working tree)
- ✅ Commits: 3 recent (transformation + updates)

---

## 6. Remaining Spashta References

### IN SOURCE CODE
- ❌ 7 Lambda handler directories (extract, match-situation, risk-classify, explanation, api-* handlers)
- These must be deleted before proceeding

### IN CONFIGURATION
- ✅ No Spashta references in templates, config, or environment variables

### VERIFICATION
```bash
# Search command to verify cleanup:
grep -r "spashta\|Spashta\|SPASHTA\|academic\|attendance\|clause\|regulation" \
  backend/lambdas/api-* backend/lambdas/extract backend/lambdas/match-situation \
  backend/lambdas/risk-classify backend/lambdas/explanation \
  --include="*.py" 2>/dev/null | wc -l
```

Expected result after cleanup: **0 matches in RoomieOps handlers**

---

## 7. Missing P0 Components (Per Build Spec §11, §40)

### Day 1 (Repository Audit → Foundation)
- [ ] Clean up Spashta Lambda directories
- [ ] Deterministic split engine (unit-tested)
- [ ] Balance calculation engine
- [ ] DynamoDB access layer (CRUD for household, member, expense, balance, audit)
- [ ] Cognito integration (sign-in/out flow)
- [ ] API Gateway routes (POST /households, POST /expenses, GET /balances, etc.)

### Day 2 (Agent Integration)
- [ ] Bedrock agent orchestrator (`copilot` Lambda)
- [ ] Tool registry and execution
- [ ] Chore CRUD + simple round-robin rotation
- [ ] Single-intent command handling
- [ ] End-to-end testing against seed data

### Critical Path
The **deterministic financial engine** is the load-bearing piece. Must be:
- Unit-tested independently (before agent integration)
- Verified against evaluation benchmark (§35 in spec)
- Locked in before adding any Bedrock/AI layer

---

## 8. Classification Summary

| Category | Count | Status |
|----------|-------|--------|
| Reusable Infrastructure | 5 files | Ready |
| Adapted Infrastructure | 8 files | Ready |
| RoomieOps Placeholders | 6 handlers | Empty, need implementation |
| Spashta Code to Delete | 7 handlers | Must remove |
| Missing Core Logic | ~15 features | Needs implementation |

---

## 9. Immediate Actions Required

### Phase 1 (Cleanup) — Before Coding Starts
1. Delete 7 Spashta Lambda directories
2. Verify no Spashta references remain in source code
3. Confirm SAM template builds successfully
4. Test Docker Compose startup

### Phase 2 (Foundation) — Day 1 Implementation
1. Implement deterministic split engine (unit tests)
2. Create DynamoDB access layer
3. Wire Cognito authentication
4. Create API Gateway routes
5. Implement balance calculation

### Phase 3 (Integration) — Day 2 Implementation
1. Build copilot Lambda with Bedrock
2. Implement chore CRUD + rotation
3. Add tool registry
4. End-to-end testing

---

## 10. Evaluation Benchmark Reference

Per §35, seed household "Room 302":
- Members: 4 (predictable state)
- Known expenses: Set amounts (for split verification)
- Expected balances: Pre-calculated
- Chore rotation: Verifiable sequence

All implementation must pass against this fixed benchmark before moving to next phase.

---

## Next Steps

1. **NOW:** Clean up Spashta code (delete 7 handler directories)
2. **THEN:** Confirm build and infrastructure readiness
3. **FINALLY:** Begin Phase 1 implementation (deterministic engine)

Do not start writing business logic until Spashta code is fully removed.
