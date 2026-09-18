# BUILD_IT Mode Architecture Plan

**Goal:** Enable RoomieOps to run locally with Strands + Ollama while preserving SHIP_IT infrastructure (Lambda + Bedrock).

**Status:** Architecture audit complete. Ready for implementation.

---

## Execution Modes

### SHIP_IT_BEDROCK (Current)
- **Model:** Amazon Bedrock (claude-sonnet-4-5-20250929-v1:0)
- **Storage:** DynamoDB
- **Auth:** Cognito User Pool
- **Infrastructure:** AWS Lambda, API Gateway, S3, Step Functions
- **Deployment:** `sam deploy`
- **Environment:** `EXECUTION_MODE=SHIP_IT_BEDROCK`

### BUILD_IT_STRANDS (New)
- **Model:** Ollama local (mistral, llama2, or similar)
- **Storage:** LocalStack (local DynamoDB emulation)
- **Auth:** Cedar (local authorization)
- **Infrastructure:** Docker Compose, LocalStack, Cedar
- **Deployment:** `docker-compose up`
- **Environment:** `EXECUTION_MODE=BUILD_IT_STRANDS`

### LOCAL_HEURISTIC (Fallback)
- **Model:** Keyword-based intent detection
- **Storage:** In-memory or LocalStack
- **Auth:** Simple header-based (dev only)
- **Infrastructure:** Local, no dependencies
- **Environment:** `EXECUTION_MODE=LOCAL_HEURISTIC`

---

## Provider Abstraction Architecture

### Layer 1: Provider Base Classes

```
ProviderInterface (abstract)
├── LLMProvider
│   ├── detect_intent(message, context) → intent_dict
│   ├── generate_explanation(action, result) → text
│   └── invoke_agent(context) → response_dict
├── StorageProvider
│   ├── get_item(pk, sk) → dict
│   ├── put_item(item) → None
│   ├── query(pk, sk_prefix) → list[dict]
│   └── scan(filters) → list[dict]
├── AuthProvider
│   ├── extract_user(event) → AuthenticatedUser
│   └── verify_permission(user, action, resource) → bool
└── RetrievalProvider
    ├── search(query, household_id) → list[doc]
    └── index_document(doc, household_id) → None
```

### Layer 2: Concrete Implementations

#### SHIP_IT_BEDROCK
```
BedrockLLMProvider → bedrock_client.invoke_model()
DynamoDBProvider → boto3 DynamoDB resource
CognitoAuthProvider → JWT claims extraction
```

#### BUILD_IT_STRANDS
```
OllamaLLMProvider → http://localhost:11434 (Ollama API)
LocalStackProvider → http://localhost:4566 (LocalStack)
CedarAuthProvider → http://localhost:8180 (Cedar PDP)
InMemoryRetrievalProvider → Dict cache
```

#### LOCAL_HEURISTIC
```
HeuristicLLMProvider → keyword matching (bedrock_client.py fallback)
InMemoryProvider → Dict cache
LocalAuthProvider → x-user-id header
```

### Layer 3: ExecutionModeManager (Orchestrator)

```python
class ExecutionModeManager:
    @staticmethod
    def determine_mode() -> ExecutionMode:
        """Check ENV, then auto-detect."""
        
    @staticmethod
    def get_providers(mode: ExecutionMode) -> ProviderSet:
        """Return provider set for mode."""
        # Returns: (llm, storage, auth, retrieval)
```

---

## Implementation Roadmap

### Phase 1: Provider Base Classes (1-2 hours)
**Files to create:**
- `backend/shared/providers/__init__.py` — Package definition
- `backend/shared/providers/base.py` — Abstract base classes
- `backend/shared/providers/types.py` — Data structures

**What happens:**
- Define abstract interfaces for LLMProvider, StorageProvider, AuthProvider, RetrievalProvider
- Define ProviderSet dataclass to hold all four
- Define execution mode routing logic

### Phase 2: Storage Abstraction (2-3 hours)
**Files to create:**
- `backend/shared/providers/storage.py` — Abstract + implementations
  - `StorageProvider` (abstract)
  - `DynamoDBProvider` (SHIP_IT)
  - `LocalStackProvider` (BUILD_IT)
  - `InMemoryProvider` (testing)

**Files to modify:**
- `backend/shared/dynamodb_ops.py` — Replace all `table.` calls with `STORAGE_PROVIDER.`
- `backend/shared/confirmation.py` — Inject provider instead of direct table reference
- `backend/lambdas/copilot/app.py` — Initialize provider at startup

**What happens:**
- DynamoDB ops become provider-agnostic
- LocalStack can emulate DynamoDB for local dev
- Same code runs against real DynamoDB (AWS) and local (LocalStack)

### Phase 3: LLM Abstraction (2-3 hours)
**Files to create:**
- `backend/shared/providers/llm.py` — Abstract + implementations
  - `LLMProvider` (abstract)
  - `BedrockLLMProvider` (SHIP_IT)
  - `OllamaLLMProvider` (BUILD_IT)
  - `HeuristicLLMProvider` (fallback)

**Files to modify:**
- `backend/shared/bedrock_client.py` — Refactor to use injected provider
- `backend/shared/strands_agent.py` — Use provider for intent detection

**What happens:**
- Bedrock calls go through provider interface
- Can swap Ollama without code changes
- Heuristic fallback always available

### Phase 4: Auth Abstraction (1-2 hours)
**Files to create:**
- `backend/shared/providers/auth.py` — Abstract + implementations
  - `AuthProvider` (abstract)
  - `CognitoAuthProvider` (SHIP_IT)
  - `CedarAuthProvider` (BUILD_IT)
  - `LocalAuthProvider` (dev)

**Files to modify:**
- `backend/shared/auth.py` — Use provider for user extraction
- `backend/lambdas/copilot/app.py` — Initialize provider

**What happens:**
- Auth extraction works with any backend
- Cedar can validate permissions (P2 feature)
- Local dev auth doesn't require Cognito

### Phase 5: Execution Mode Routing (1 hour)
**Files to modify:**
- `backend/shared/execution_modes.py` — Add mode determination + provider routing
- `backend/shared/strands_agent.py` — Use determined mode + providers
- `backend/lambdas/copilot/app.py` — Initialize providers at startup

**What happens:**
- Check ENV `EXECUTION_MODE` first
- Fall back to auto-detection (Bedrock > Strands > Heuristic)
- Inject all providers based on mode
- Code is now mode-agnostic

### Phase 6: Tool Execution (1-2 hours)
**Files to modify:**
- `backend/shared/strands_agent.py` — All tool methods use STORAGE_PROVIDER
- `backend/shared/confirmation.py` — _execute_action uses STORAGE_PROVIDER

**What happens:**
- Tools work the same regardless of mode
- State mutations go through provider
- No tool changes needed for BUILD_IT

### Phase 7: Local Server Integration (1 hour)
**Files to modify:**
- `backend/local_dev_server.py` — Already exists, set ENV variables
- Add docker-compose.yml configuration

**What happens:**
- `docker-compose up` starts: Ollama, LocalStack, Cedar, local server
- Flask server routes requests to handlers
- Handlers use injected providers
- Works identically to Lambda + API Gateway

### Phase 8: End-to-End Testing (2-3 hours)
**Files to create:**
- `tests/test_build_it_e2e.py` — Full local flow test
  - User request → Strands agent → tool execution → state mutation → confirmation → audit
  - Test multiple tools and scenarios
  - Verify BUILD_IT_STRANDS execution mode label

**What happens:**
- Confirm Strands actually executes locally
- Confirm state persists in LocalStack
- Confirm Cedar authorization works
- Confirm mode is correctly reported

---

## Docker Compose for BUILD_IT

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_MODELS=/root/.ollama/models

  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
      - "4571:4571"
    environment:
      - SERVICES=dynamodb,s3,lambda
      - AWS_DEFAULT_REGION=us-east-1
      - AWS_ACCESS_KEY_ID=test
      - AWS_SECRET_ACCESS_KEY=test
      - DYNAMODB_SHARE_DB=1
    volumes:
      - localstack_data:/tmp/localstack
      - /var/run/docker.sock:/var/run/docker.sock

  cedar:
    image: cedar:latest  # Build from policy-as-code repo
    ports:
      - "8180:8180"
    environment:
      - CEDAR_POLICIES_DIR=/policies
    volumes:
      - ./cedar_policies:/policies

  roomieops-dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - EXECUTION_MODE=BUILD_IT_STRANDS
      - LLM_PROVIDER=ollama
      - LLM_ENDPOINT=http://ollama:11434
      - STORAGE_PROVIDER=localstack
      - DYNAMODB_ENDPOINT=http://localstack:4566
      - AUTH_PROVIDER=cedar
      - CEDAR_ENDPOINT=http://cedar:8180
      - PYTHON_ENV=development
    depends_on:
      - ollama
      - localstack
      - cedar
    volumes:
      - ./backend:/app/backend
      - ./tests:/app/tests
    command: python backend/local_dev_server.py

volumes:
  ollama_data:
  localstack_data:
```

---

## Environment Variables

### SHIP_IT_BEDROCK
```bash
EXECUTION_MODE=SHIP_IT_BEDROCK
LLM_PROVIDER=bedrock
STORAGE_PROVIDER=dynamodb
AUTH_PROVIDER=cognito
AWS_REGION=us-east-1
DYNAMODB_TABLE=roomieops-household-state
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0
```

### BUILD_IT_STRANDS
```bash
EXECUTION_MODE=BUILD_IT_STRANDS
LLM_PROVIDER=ollama
LLM_ENDPOINT=http://localhost:11434
LLM_MODEL=mistral
STORAGE_PROVIDER=localstack
DYNAMODB_ENDPOINT=http://localhost:4566
AUTH_PROVIDER=cedar
CEDAR_ENDPOINT=http://localhost:8180
PYTHON_ENV=development
```

### LOCAL_HEURISTIC
```bash
EXECUTION_MODE=LOCAL_HEURISTIC
LLM_PROVIDER=heuristic
STORAGE_PROVIDER=memory
AUTH_PROVIDER=local
```

---

## File Structure After Implementation

```
backend/
├── shared/
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py (abstract classes)
│   │   ├── types.py (data structures)
│   │   ├── storage.py (Storage provider implementations)
│   │   ├── llm.py (LLM provider implementations)
│   │   ├── auth.py (Auth provider implementations)
│   │   └── retrieval.py (Retrieval provider implementations)
│   ├── execution_modes.py (refactored with provider routing)
│   ├── dynamodb_ops.py (refactored to use STORAGE_PROVIDER)
│   ├── bedrock_client.py (refactored to use LLM_PROVIDER)
│   ├── auth.py (refactored to use AUTH_PROVIDER)
│   ├── strands_agent.py (tools use STORAGE_PROVIDER)
│   ├── confirmation.py (uses STORAGE_PROVIDER)
│   └── ... (other files unchanged)
├── lambdas/
│   ├── copilot/
│   │   └── app.py (initialize providers at startup)
│   └── ... (other lambdas unchanged)
├── local_dev_server.py (set ENV vars for providers)
└── docker-compose.yml (new)

tests/
├── test_build_it_e2e.py (new)
├── test_build_it_strands.py (new)
├── ... (existing tests)
```

---

## No Breaking Changes to SHIP_IT

- Default environment: EXECUTION_MODE not set → auto-detect → Bedrock (existing behavior)
- SAM template unchanged
- Lambda handlers unchanged
- All existing tests pass
- Deployment via `sam deploy` unchanged
- No credentials, configs, or infrastructure affected

---

## Testing Strategy

### Unit Tests (Per Provider)
```python
# tests/test_providers.py
def test_dynamodb_provider():
    provider = DynamoDBProvider()
    item = provider.put_item({"pk": "...", "sk": "...", "data": {...}})
    retrieved = provider.get_item("...", "...")
    assert retrieved == item

def test_localstack_provider():
    provider = LocalStackProvider(endpoint="http://localhost:4566")
    # Same test as above - interface is identical
    
def test_ollama_provider():
    provider = OllamaLLMProvider(endpoint="http://localhost:11434")
    intent = provider.detect_intent("I paid for groceries", {...})
    assert intent["intent"] == "create_expense"
```

### Integration Tests (Mode-Specific)
```python
# tests/test_build_it_strands.py
def test_build_it_e2e():
    os.environ["EXECUTION_MODE"] = "BUILD_IT_STRANDS"
    
    # Full user flow
    agent = RoomieOpsAgent(context)
    result = agent.process_user_request("I paid ₹1200 for groceries. Split equally.")
    
    assert result["status"] == "success"
    assert result["execution_mode"] == "BUILD_IT_STRANDS"
    assert result["requires_confirmation"] == True
    assert result["action_id"] is not None
```

### Backward Compatibility Tests
```python
# tests/test_ship_it_bedrock.py
def test_ship_it_bedrock_unchanged():
    # Bedrock mode should still work exactly as before
    # All existing tests continue to pass
```

---

## Success Criteria

✅ **BUILD_IT_STRANDS = VERIFIED** when:
- Strands Agent initializes locally
- Tool calling works (get_balances, calculate_split, create_issue, etc.)
- Execution mode correctly labeled as BUILD_IT_STRANDS
- E2E test: user request → agent → tools → state mutation → confirmation

✅ **OLLAMA = VERIFIED** when:
- Ollama running on localhost:11434
- OllamaLLMProvider connects and invokes model
- Intent detection produces valid responses
- Can swap models without code changes

✅ **LOCALSTACK = VERIFIED** when:
- LocalStack running on localhost:4566
- LocalStackProvider creates same table schema as DynamoDB
- All DynamoDB operations work identically
- State persists across requests

✅ **CEDAR = VERIFIED** when:
- Cedar running on localhost:8180
- CedarAuthProvider extracts user from JWT
- Policy evaluation returns permit/deny correctly
- Authorization checks block unauthorized actions

✅ **OPENSEARCH = VERIFIED** when:
- (P3 feature) Indices created and searched
- Context retrieval works
- Agent uses context for disambiguation

✅ **END_TO_END = PASS** when:
- Full RoomieOps flow works locally:
  1. User: "How much do I owe?"
  2. Agent calls get_balances tool
  3. Returns actual balance from LocalStack
  4. User: "I paid ₹1200 for groceries. Split equally."
  5. Agent proposes action, requests confirmation
  6. User confirms via API
  7. Agent executes tool, state mutation persists
  8. Audit log recorded
  9. Frontend updates with new state

✅ **SHIP_IT INFRASTRUCTURE = PRESERVED** when:
- All SHIP_IT files unchanged
- SAM template still valid
- Bedrock mode still works
- `sam deploy` still succeeds
- No AWS resources affected

---

## Not Included in BUILD_IT (P3 features)

- OpenSearch integration (can add later)
- Full Cedar authorization policies (basic auth only)
- EventBridge notifications (local alternative)
- Multi-region failover (single-region BUILD_IT)

---

## Next Steps

1. **Create provider base classes** (Phase 1)
2. **Implement storage abstraction** (Phase 2)
3. **Implement LLM abstraction** (Phase 3)
4. **Implement auth abstraction** (Phase 4)
5. **Wire execution mode routing** (Phase 5)
6. **Refactor tool execution** (Phase 6)
7. **Add docker-compose** (Phase 7)
8. **Run E2E tests** (Phase 8)

---

**Status:** Ready to implement. SHIP_IT infrastructure will remain untouched.
