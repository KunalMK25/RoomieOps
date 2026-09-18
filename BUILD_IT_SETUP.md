# BUILD_IT_STRANDS Local Development Setup

This guide sets up RoomieOps for local BUILD_IT_STRANDS development without AWS credentials.

## Prerequisites

### Required
- Python 3.11+
- pip
- Docker & Docker Compose (for LocalStack)

### Optional (recommended for BUILD_IT_STRANDS path)
- Ollama (https://ollama.com) - for local LLM support
- A compatible local model (mistral, llama2, or neural-chat recommended)

## Step 1: Install Python Dependencies

```bash
cd backend
pip install -r requirements-dev.txt
pip install -r shared/requirements.txt
```

Verify key providers:
```bash
python -c "from strands import Agent; print('✓ Strands SDK available')"
python -c "import requests; print('✓ Requests available')"
```

## Step 2: Install Ollama (Optional but Recommended for BUILD_IT_STRANDS)

### macOS
```bash
brew install ollama
ollama pull mistral  # or llama2, neural-chat
```

### Linux
```bash
curl https://ollama.ai/install.sh | sh
ollama pull mistral
ollama serve  # Start Ollama server
```

### Windows
- Download from https://ollama.com and install
- Run `ollama pull mistral` in PowerShell
- Start server: `ollama serve`

Verify Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

## Step 3: Set Up LocalStack

### Start LocalStack (Docker required)

```bash
docker-compose -f docker-compose.yml up localstack
```

Verify LocalStack is running:
```bash
curl http://localhost:4566/health | python -m json.tool
```

## Step 4: Initialize Local Environment

### Configure Environment Variables

Create `.env.local` in `backend/`:

```bash
# Execution mode (explicit is safer)
EXECUTION_MODE=BUILD_IT_STRANDS

# LLM Configuration
LLM_MODEL=mistral
OLLAMA_ENDPOINT=http://localhost:11434

# Storage Configuration  
DYNAMODB_ENDPOINT=http://localhost:4566
DYNAMODB_TABLE=roomieops-household-state

# Cedar Authorization (Phase 6+)
CEDAR_ENDPOINT=http://localhost:8180

# Local Auth (BUILD_IT authentication)
AUTH_MODE=local
```

### Initialize Database Schema

```bash
python backend/scripts/init_localstack_db.py
```

This creates the DynamoDB table with the same schema as SHIP_IT.

## Step 5: Load Seed Data

```bash
python backend/scripts/seed_household.py
```

This creates:
- **Household:** Sunrise PG (Room 302)
- **Members:** Kunal, Priya, Rahul, Arjun
- **Initial state:** Some expenses, balances, chores

## Step 6: Start the Local API Server

```bash
python backend/local_dev_server.py
```

Or with explicit BUILD_IT mode:

```bash
EXECUTION_MODE=BUILD_IT_STRANDS python backend/local_dev_server.py
```

API will be available at `http://localhost:5000`

## Step 7: Connect Frontend

From `frontend/`:

```bash
VITE_API_URL=http://localhost:5000 npm run dev
```

Frontend will be available at `http://localhost:5173`

## Verification

### Check Execution Mode

```bash
curl http://localhost:5000/status
```

Response should show:
```json
{
  "execution_mode": "BUILD_IT_STRANDS",
  "ollama_available": true,
  "localstack_available": true,
  "cedar_available": false  // Phase 6+
}
```

### Test a Simple Agent Request

```bash
curl -X POST http://localhost:5000/households/sunrise-pg/copilot \
  -H "Content-Type: application/json" \
  -H "x-user-id: kunal" \
  -d '{"message": "How much do I owe?"}'
```

Expected response:
```json
{
  "execution_mode": "BUILD_IT_STRANDS",
  "status": "success",
  "intent": "view_balance",
  "response": "You owe ₹..."
}
```

## Troubleshooting

### Ollama not available
- Make sure Ollama server is running: `ollama serve`
- Check endpoint: `curl http://localhost:11434/api/tags`
- Falls back to LOCAL_HEURISTIC if unavailable

### LocalStack not available
- Make sure Docker is running
- Check: `docker ps | grep localstack`
- View logs: `docker-compose logs localstack`
- The BUILD_IT_STRANDS agent will fail if LocalStack is not available (not a silent fallback)

### Strands import error
- Install: `pip install strands`
- Verify: `python -c "from strands import Agent"`

### DynamoDB table doesn't exist
- Run: `python backend/scripts/init_localstack_db.py`
- Verify: `aws dynamodb list-tables --endpoint-url http://localhost:4566`

## Development Workflow

1. **Make code changes** in `backend/shared/`
2. **Restart local server** (Ctrl+C, run again)
3. **Test via API** or frontend
4. **Check logs** for errors
5. **Verify provider initialization** if switching modes

## Switching Execution Modes

### To use SHIP_IT_BEDROCK (requires AWS credentials)
```bash
unset EXECUTION_MODE
export AWS_REGION=us-east-1
# Bedrock credentials will be auto-detected
python backend/local_dev_server.py
```

### To use LOCAL_HEURISTIC (no external services)
```bash
export EXECUTION_MODE=LOCAL_HEURISTIC
python backend/local_dev_server.py
```

The mode selection is explicit via `EXECUTION_MODE` env var with auto-detection fallback (never silent).

## What's NOT available in BUILD_IT_STRANDS yet

- Phase 6+: Cedar authorization (uses local auth instead)
- Phase 2: OpenSearch retrieval (uses in-memory fallback)
- Real receipt/bill processing (P2 feature)

## Next Steps

1. Verify all prerequisites are installed
2. Start LocalStack: `docker-compose up localstack`
3. Start Ollama: `ollama serve` (if installed)
4. Initialize DB: `python backend/scripts/init_localstack_db.py`
5. Load seed data: `python backend/scripts/seed_household.py`
6. Start backend: `python backend/local_dev_server.py`
7. Start frontend: `npm run dev` from `frontend/`
8. Test via `http://localhost:5173`

