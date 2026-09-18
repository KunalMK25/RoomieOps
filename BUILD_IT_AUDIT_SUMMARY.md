# BUILD_IT Mode - Architecture Audit Summary

**Date:** 2025-09-18  
**Status:** Audit complete. Implementation roadmap ready.  
**Decision:** Proceed with provider-based abstraction architecture.

---

## Audit Findings

### Current State: SHIP_IT_BEDROCK Only

The RoomieOps codebase is currently architected for AWS deployment only:

| Component | Current Implementation | File | Lines |
|-----------|------------------------|------|-------|
| **Model/LLM** | Amazon Bedrock (hard-wired) | bedrock_client.py | 20, 39-70, 136-185 |
| **Storage** | DynamoDB (hard-wired boto3) | dynamodb_ops.py | 28-31 |
| **Authentication** | Cognito JWT extraction | auth.py | 32-83 |
| **State Mutation** | Direct DynamoDB writes | confirmation.py | 108-400 |
| **Tool Execution** | Strands SDK (when available) | strands_agent.py | 69-560 |
| **Execution Mode** | Auto-detected at runtime | execution_modes.py | 36-60 |

### Problem: Cannot Run Locally for Development

1. **No local LLM support**: Bedrock requires AWS credentials (not available locally)
2. **No local storage**: Must use real DynamoDB (cannot mock/emulate)
3. **No local auth**: Cognito requires AWS account activation
4. **Hard-wired dependencies**: Cannot swap implementations without code changes

### Solution: Provider Abstraction Pattern

Instead of refactoring everything, implement a **provider interface** that allows:
- Same code to run against AWS (SHIP_IT) or locally (BUILD_IT)
- Runtime provider selection via environment variables
- No changes to business logic or tools

---

## Architecture Decision

### Create 4 Provider Abstractions

1. **LLMProvider**: Model invocation (Bedrock ↔ Ollama ↔ Heuristic)
2. **StorageProvider**: Data persistence (DynamoDB ↔ LocalStack ↔ Memory)
3. **AuthProvider**: User authentication (Cognito ↔ Cedar ↔ Local headers)
4. **RetrievalProvider**: Context retrieval (DynamoDB ↔ OpenSearch ↔ Memory)

### Execution Modes

| Mode | LLM | Storage | Auth | Use Case |
|------|-----|---------|------|----------|
| **SHIP_IT_BEDROCK** | Bedrock | DynamoDB | Cognito | Production AWS |
| **BUILD_IT_STRANDS** | Ollama | LocalStack | Cedar | Local development |
| **LOCAL_HEURISTIC** | Keyword matching | In-memory | Simple headers | Dev emergency fallback |

### Key Principle

**No breaking changes to SHIP_IT.** All abstractions are:
- Optional (default behavior unchanged)
- Injected at startup (not scattered through code)
- Backward compatible (existing code continues to work)
- Environment-driven (no code changes needed to switch modes)

---

## Implementation Phases

### Phase 1: Provider Base Classes
- Create abstract base classes for all providers
- Define provider interfaces and data structures
- Implement ExecutionModeManager for orchestration

### Phase 2: Storage Abstraction (CRITICAL)
- Implement StorageProvider abstract interface
- Create DynamoDBProvider (existing behavior)
- Create LocalStackProvider (Docker-based)
- Refactor all DynamoDB calls to use provider

### Phase 3: LLM Abstraction (CRITICAL)
- Implement LLMProvider abstract interface
- Create BedrockLLMProvider (existing behavior)
- Create OllamaLLMProvider (local model)
- Refactor bedrock_client.py to use provider

### Phase 4: Auth Abstraction
- Implement AuthProvider abstract interface
- Create CognitoAuthProvider (existing behavior)
- Create CedarAuthProvider (local authorization)
- Refactor auth.py to use provider

### Phase 5: Execution Mode Routing
- Update execution_modes.py to route to providers
- Initialize all providers at startup based on mode
- Inject providers into agent and confirmation manager

### Phase 6: Tool Execution Update
- Update all tool methods to use STORAGE_PROVIDER
- Update confirmation manager to use STORAGE_PROVIDER
- No changes to tool logic or signatures

### Phase 7: Docker Compose Setup
- Create docker-compose.yml with Ollama, LocalStack, Cedar
- Update local_dev_server.py to set environment variables
- Verify containers communicate correctly

### Phase 8: End-to-End Testing
- Write comprehensive local flow tests
- Verify all three execution modes work
- Confirm SHIP_IT infrastructure unchanged

---

## No Abstraction Needed: Already Flexible

### API Layer (copilot/app.py)
- ✅ Already works with any Lambda or local server
- ✅ Request format stable (HTTP events)
- ✅ Response format includes execution mode
- ✅ No changes needed

### Tool Registry (agent_tools.py)
- ✅ Already schema-based abstraction
- ✅ Definitions separate from implementations
- ✅ No hard-wired model references
- ✅ No changes needed

### Confirmation Flow (confirmation.py)
- ✅ Already abstracted (ActionType, ActionStatus enums)
- ✅ Works with any storage backend
- ✅ Just needs StorageProvider injection

---

## Critical Integration Points (Refactoring Required)

### 1. DynamoDB Access (dynamodb_ops.py)
**Current:** All methods call `table.put_item()`, `table.get_item()`, etc.  
**Change:** Replace with `STORAGE_PROVIDER.put_item()`, `STORAGE_PROVIDER.get_item()`, etc.  
**Impact:** Medium (simple find-replace pattern)

### 2. Confirmation Manager (confirmation.py)
**Current:** Hardcoded `ConfirmationManager._table` reference  
**Change:** Inject `STORAGE_PROVIDER` instead  
**Impact:** Low (confined to one class)

### 3. Bedrock Client (bedrock_client.py)
**Current:** Direct boto3 Bedrock invocation  
**Change:** Delegate to injected `LLM_PROVIDER`  
**Impact:** Medium (several methods affected)

### 4. Auth Extraction (auth.py)
**Current:** Hardcoded Cognito claims extraction  
**Change:** Delegate to injected `AUTH_PROVIDER`  
**Impact:** Low (confined to one class)

### 5. Tool Methods (strands_agent.py)
**Current:** All tool implementations call `DynamoDBOps.*`  
**Change:** Will automatically use correct provider once DynamoDBOps is refactored  
**Impact:** Low (no direct changes needed)

### 6. Execution Mode Detection (execution_modes.py)
**Current:** Checks Bedrock creds, then Strands, then heuristic  
**Change:** Check ENV first, then auto-detect, then route to providers  
**Impact:** Medium (orchestration layer)

---

## Success Metrics

When BUILD_IT mode is complete, the following must be true:

### ✅ BUILD_IT_STRANDS = VERIFIED
- [ ] Strands Agent initializes without Bedrock credentials
- [ ] Tool calling works (get_balances, calculate_split, create_issue)
- [ ] Response labeled as "BUILD_IT_STRANDS" mode
- [ ] Full E2E flow completes locally

### ✅ OLLAMA = VERIFIED
- [ ] Ollama running on localhost:11434
- [ ] OllamaLLMProvider successfully invokes model
- [ ] Intent detection produces valid outputs
- [ ] Can swap model via environment variable

### ✅ LOCALSTACK = VERIFIED
- [ ] LocalStack running on localhost:4566
- [ ] LocalStackProvider schema matches DynamoDB
- [ ] All CRUD operations work identically
- [ ] State persists across requests

### ✅ CEDAR = VERIFIED
- [ ] Cedar running on localhost:8180
- [ ] CedarAuthProvider extracts user from JWT/header
- [ ] Policy evaluation works
- [ ] Unauthorized actions blocked

### ✅ OPENSEARCH = VERIFIED (Optional, P3)
- [ ] (Can implement later)

### ✅ END_TO_END = PASS
- [ ] Full user flow works:
  - User: "How much do I owe?"
  - Agent: Calls get_balances tool
  - State: Persists in LocalStack
  - Confirmation: Required for write action
  - User: Confirms action
  - Result: State updated, audit logged
  - Frontend: Shows updated state

### ✅ SHIP_IT INFRASTRUCTURE = PRESERVED
- [ ] All SHIP_IT files unchanged
- [ ] SAM template still valid
- [ ] `sam deploy` still works
- [ ] Bedrock mode still active by default
- [ ] All existing tests pass

---

## Files to Create (New)

```
backend/shared/providers/
├── __init__.py
├── base.py (abstract base classes)
├── types.py (data structures)
├── storage.py (Storage implementations)
├── llm.py (LLM implementations)
├── auth.py (Auth implementations)
└── retrieval.py (Retrieval implementations)

tests/
├── test_build_it_strands.py (new)
├── test_build_it_e2e.py (new)
└── test_providers.py (new)

infrastructure/
└── docker-compose.yml (new)

.kiro/
└── steering/
    └── build-it-setup.md (new)
```

## Files to Modify (Existing)

```
backend/shared/
├── execution_modes.py (refactor mode routing)
├── dynamodb_ops.py (use STORAGE_PROVIDER)
├── bedrock_client.py (use LLM_PROVIDER)
├── auth.py (use AUTH_PROVIDER)
├── strands_agent.py (no direct changes, inherits storage provider)
└── confirmation.py (use STORAGE_PROVIDER)

backend/lambdas/copilot/
└── app.py (initialize providers at startup)

backend/
└── local_dev_server.py (set env variables for BUILD_IT)
```

## Files NOT to Modify (SHIP_IT Preserved)

```
infrastructure/template.yaml (unchanged)
All Lambda functions (unchanged)
All tests (continue to pass)
All existing features (unchanged)
```

---

## Environment Variables

### SHIP_IT_BEDROCK (Default)
```bash
EXECUTION_MODE=SHIP_IT_BEDROCK
LLM_PROVIDER=bedrock
STORAGE_PROVIDER=dynamodb
AUTH_PROVIDER=cognito
```

### BUILD_IT_STRANDS
```bash
EXECUTION_MODE=BUILD_IT_STRANDS
LLM_PROVIDER=ollama
LLM_ENDPOINT=http://localhost:11434
STORAGE_PROVIDER=localstack
DYNAMODB_ENDPOINT=http://localhost:4566
AUTH_PROVIDER=cedar
CEDAR_ENDPOINT=http://localhost:8180
```

### LOCAL_HEURISTIC
```bash
EXECUTION_MODE=LOCAL_HEURISTIC
LLM_PROVIDER=heuristic
STORAGE_PROVIDER=memory
AUTH_PROVIDER=local
```

---

## Risk Analysis

### Low Risk
- Provider base classes (new code, isolated)
- New provider implementations (isolated, swappable)
- Docker Compose setup (external, doesn't affect source)
- New tests (isolated, don't affect existing)

### Medium Risk
- Refactoring dynamodb_ops.py (high usage, many methods)
  - Mitigation: Provider interface mirrors DynamoDB API exactly
- Refactoring bedrock_client.py (used by strands_agent)
  - Mitigation: Provider interface mirrors Bedrock API exactly

### Low/No Risk
- SHIP_IT infrastructure (unchanged, default behavior)
- Existing tests (continue to work)
- Lambda handlers (no code changes)
- Confirmation flow (only injection needed)

### Mitigation Strategy
- Create providers first (no production impact)
- Refactor storage/LLM one module at a time
- Keep existing code working (default to Bedrock)
- Add integration tests for each mode
- Run all existing tests after each phase

---

## Timeline Estimate

| Phase | Hours | Critical | Notes |
|-------|-------|----------|-------|
| 1. Provider base classes | 1-2 | YES | Entry point |
| 2. Storage abstraction | 2-3 | YES | Most refactoring |
| 3. LLM abstraction | 2-3 | YES | Core agent logic |
| 4. Auth abstraction | 1-2 | NO | P2 feature |
| 5. Mode routing | 1 | YES | Orchestration |
| 6. Tool execution | 1-2 | YES | Tie it together |
| 7. Docker Compose | 1 | NO | Infrastructure |
| 8. E2E testing | 2-3 | YES | Verification |
| **Total** | **11-16 hours** | | Conservative estimate |

---

## Decision: Proceed with Provider Pattern

### Why This Approach

1. **Non-invasive**: No breaking changes to SHIP_IT
2. **Flexible**: Can add any provider later (P3 features)
3. **Testable**: Each provider independently testable
4. **Clear**: Execution mode is explicit in code and output
5. **Production-ready**: SHIP_IT behavior unchanged

### Alternative Approaches Rejected

1. **Fork codebase**: Two codebases = maintenance nightmare ❌
2. **Mock everything locally**: Ignores real deployment concerns ❌
3. **Monolithic refactor**: Too risky, breaks existing functionality ❌
4. **Hard-wire BUILD_IT mode**: Cannot switch without code changes ❌

---

## Next Steps

1. ✅ **Audit complete** — Architecture documented
2. ⏭️ **Phase 1**: Create provider base classes
3. ⏭️ **Phase 2**: Storage abstraction (LocalStack)
4. ⏭️ **Phase 3**: LLM abstraction (Ollama)
5. ⏭️ **Phase 4**: Auth abstraction (Cedar)
6. ⏭️ **Phase 5-8**: Routing, testing, verification

---

## Sign-Off

**Architecture approved for implementation.**

The provider-based abstraction pattern:
- ✅ Enables BUILD_IT development locally
- ✅ Preserves SHIP_IT infrastructure
- ✅ Maintains backward compatibility
- ✅ Clear execution modes (not fake Bedrock)
- ✅ Real Strands agent with actual tool calling
- ✅ Ready for P3 features (Cedar, OpenSearch)

**Proceed with Phase 1.**

---

**Document created:** 2025-09-18  
**Status:** READY FOR IMPLEMENTATION  
**Approval:** All success criteria defined, risk mitigated, timeline estimated
