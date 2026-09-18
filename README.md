# RoomieOps — AI-Powered Shared-Living Operations Copilot

**Status:** Day 1 Phase 1 Complete ✓  
**Target:** MVP (P0) delivery by end of Day 2  
**Stack:** Python (Lambda), React + TypeScript (frontend), DynamoDB, Cognito, Bedrock, API Gateway, SAM

---

## Project Overview

RoomieOps is a household coordination copilot that unifies chores, expenses, maintenance, and shopping. Residents coordinate across all domains through natural language, while a **deterministic backend** (never the AI) performs financial arithmetic and state mutation.

**One household. One shared state. One copilot.**

---

## Day 1 Progress

### ✅ Completed

#### Repository Setup
- Deleted all Spashta legacy code (7 Lambda handlers, audit documents)
- Verified zero Spashta references in production code
- Prepared infrastructure and frontend for RoomieOps

#### Deterministic Finance Engine (§21)
- **Location:** `backend/shared/finance_engine.py`
- **P0 Methods:**
  - `split_equal()` — Equal expense split with remainder reconciliation
  - `split_exact()` — Exact amount specification per participant
  - `split_percentage()` — Percentage-based split
  - `calculate_balances()` — Net balance computation
  - `get_balance_explanation()` — Human-readable balance breakdown
- **Guarantees:**
  - All arithmetic in integer paise (no floats)
  - All allocations reconcile: `SUM(allocations) == total`
  - Remainder assigned deterministically (to first participant)
  - Independently unit-tested and verified

#### DynamoDB Access Layer (§16)
- **Location:** `backend/shared/dynamodb_ops.py`
- **Schema:** Composite pk/sk (HOUSEHOLD#<id>/MEMBER#, EXPENSE#, BALANCE#, CHORE#, AUDIT#)
- **P0 Operations:**
  - Household CRUD (create, get, list)
  - Member management (add, list)
  - Expense creation with split allocation
  - Balance recording and retrieval
  - Chore CRUD with round-robin rotation
  - Audit logging

#### API Gateway + Lambda Handlers (P0)
- **Households Handler** (`backend/lambdas/households/app.py`)
  - `POST /households` — Create household
  - `GET /households/{id}` — Get household metadata
  - `GET /households/{id}/members` — List members
  - `POST /households/{id}/members` — Add member
  - `GET /households/{id}/expenses` — List expenses
  - `GET /households/{id}/balances` — Get balances
  - `GET /households/{id}/chores` — List chores

- **Expenses Handler** (`backend/lambdas/expenses/app.py`)
  - `POST /households/{id}/expenses` — Create expense with auto-split calculation
  - `POST /households/{id}/expenses/calculate` — Calculate split without persisting

- **Chores Handler** (`backend/lambdas/chores/app.py`)
  - `POST /households/{id}/chores` — Create chore with rotation order
  - `POST /households/{id}/chores/{id}/complete` — Complete and rotate

#### Infrastructure (SAM Template)
- **Location:** `infrastructure/template.yaml`
- **Resources Wired:**
  - DynamoDB table (roomieops-household-state, pk/sk composite)
  - S3 bucket (document storage, P2)
  - Cognito User Pool (sign up/in/out)
  - API Gateway (REST API, Cognito authorization)
  - Lambda Execution Role (DynamoDB, S3, Bedrock, Step Functions IAM)
  - Step Functions State Machine (event pipeline, P0 shape)

#### Unit Tests
- **Location:** `tests/test_finance_engine.py`
- **Coverage:**
  - Equal split (with/without remainder)
  - Exact split (validation)
  - Percentage split (remainder reconciliation)
  - Balance calculation (single/multi-expense)
  - **Room 302 seed data** (evaluation benchmark per §35) ✓ **PASSING**

---

## Architecture Decisions (Per §7 / §21)

1. **Finance Engine Independence**
   - Deterministic arithmetic isolated from AI orchestration
   - All calculations unit-testable without AWS/Bedrock
   - Remainder reconciliation assigned deterministically (never random)

2. **DynamoDB Schema**
   - Household-scoped partitioning: all entities under `HOUSEHOLD#<id>`
   - Composite pk/sk for efficient querying and audit trails
   - No relational joins required (denormalization intentional)

3. **Lambda + API Gateway**
   - Domain-organized handlers (households, expenses, chores, copilot, etc.)
   - Each handler stateless, idempotent, scoped to single HTTP request
   - Shared layer for finance_engine and dynamodb_ops

4. **Step Functions (P0 Shape)**
   - Not yet wired (Day 2), but schema defined: Validate → Calculate → Write → Audit → Notify
   - Ensures "AI never does arithmetic" is enforced at runtime, not just policy

---

## Known P0 Items Still To Do

- [ ] Cognito integration in Lambda handlers (extract `sub` from token, scope queries)
- [ ] Step Functions pipeline (validate request → call finance engine → write DynamoDB)
- [ ] Bedrock agent wiring (single-intent copilot, tool selection, result explanation)
- [ ] Frontend scaffolding + API client refine (already drafted)
- [ ] End-to-end testing (create household → add members → create expenses → verify balances)

---

## Getting Started

### Local Development

```bash
# Prerequisites
# - Python 3.11+
# - Node.js 18+ (frontend)
# - AWS SAM CLI
# - LocalStack (Docker)

# Backend
cd backend
pip install -r requirements-dev.txt

# Run unit tests
python -m pytest tests/

# Run finance engine tests
python tests/test_finance_engine.py

# Frontend
cd frontend
npm install
npm run dev

# Local AWS services (LocalStack)
docker-compose up -d
sam build
sam local start-api
```

### Testing Finance Engine

```bash
cd backend/shared
python finance_engine.py  # Embedded self-test
```

### Building & Deploying

**Day 1:** Local development only (LocalStack/SAM local)

**Day 3:** First deployment to live AWS (after P0 validation passes §34/§35)

---

## Spec & Execution Plan

- **Authoritative Spec:** `ROOMIEOPS_BUILD_SPEC.md` (§1–49, locked)
- **Execution Rules:** `KIRO_MASTER_PROMPT.md`
- **Four-Day Plan:** §40 of spec
  - **Day 1** ← *You are here*: repo, finance engine (✓ done), DynamoDB layer, API scaffolding
  - **Day 2:** Chore CRUD + rotation, Bedrock single-intent agent, P0 complete
  - **Day 3:** Step Functions pipeline, flagship absence workflow, confirmation flow, UI polish
  - **Day 4:** EventBridge reminders, testing against evaluation benchmark, deployment, demo rehearsal

---

## Commits (Day 1)

```
chore: delete all Spashta Lambda handlers - clean RoomieOps codebase only
feat: implement Day 1 Phase 1 - deterministic finance engine, DynamoDB ops layer, household/expense/chore APIs
feat: wire P0 Lambda functions to API Gateway in SAM template
test: add comprehensive unit tests for finance engine including Room 302 seed data
```

---

## Verification Checklist

✅ Finance engine reconciles: sum(allocations) == total  
✅ Room 302 seed data passes evaluation benchmark  
✅ DynamoDB schema matches spec §16  
✅ API routes match spec §17 (P0 subset)  
✅ Lambda handlers follow deterministic pattern  
✅ SAM template builds and validates  
✅ Zero Spashta references in source code  

---

**Next:** Day 2 — Bedrock wiring + copilot single-intent commands + P0 completion
