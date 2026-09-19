# RoomieOps

## AI-Powered Shared-Living Operations Copilot

RoomieOps is an AI-powered household coordination platform for shared living spaces—roommates, co-living communities, hostels, and shared apartments. It unifies shared expenses, chores, maintenance, and shopping into a single household state, with an AI copilot that understands natural language requests, orchestrates multi-step operations, and explains results.

**One household. One shared state. One copilot.**

---

## Why RoomieOps?

Shared living creates operational friction across multiple domains:

- **Expenses:** Who paid what? Who owes whom? How should costs split?
- **Chores:** What needs doing? Who's assigned? Is it getting done?
- **Maintenance:** What's broken? What's urgent? What's scheduled?
- **Shopping:** What do we need? Who's buying it?
- **Coordination:** How do these workflows interact?

Existing tools handle one category at a time—expense apps for money, to-do lists for chores, spreadsheets for shopping. RoomieOps brings these workflows into one shared household state with an AI copilot capable of:

- Understanding household intent in natural language
- Retrieving household state and context
- Selecting and executing appropriate tools
- Coordinating multi-step operations
- Explaining results back to residents

---

## Key Features

### 💰 Shared Expenses

- Create and categorize household expenses
- Automatic and manual expense splits (equal, exact amount, percentage)
- Real-time balance tracking (who owes whom)
- Audit trail and expense history

### 🧹 Chores

- Create household chores and tasks
- Assign chores to residents
- Track completion and rotation
- Shared chore state across household

### 🔧 Maintenance

- Log and track maintenance issues
- Organize by priority and status
- Household maintenance visibility

### 🛒 Shopping

- Shared household shopping list
- Add/remove items with ease
- Coordination around household purchases

### 🤖 AI Copilot

- Natural-language household requests ("split rent equally", "who owes money?", "assign chores")
- Tool selection and orchestration
- Multi-step operation handling
- Household state retrieval and context
- Deterministic backend execution—AI orchestrates, backend validates and persists

---

## How It Works

```
User Request (Natural Language)
    ↓
React Frontend (Browser)
    ↓
API Layer (Bearer Token Auth)
    ↓
Authentication
    ↓
Authorization (Cedar)
    ↓
Domain Services + Household State
    ↓
AI Copilot / Strands Agent Tool Execution
    ↓
Deterministic Backend Services
    ↓
Persistent Storage (DynamoDB / Local)
```

## Design Principle

The AI copilot is responsible for:

- Understanding user intent
- Retrieving context and household state
- Selecting appropriate tools
- Orchestrating multi-step workflows
- Explaining results

The backend is responsible for:

- Authentication
- Authorization
- Input validation
- Deterministic arithmetic and calculations
- Database mutations and consistency
- Authoritative household state

**AI orchestrates; the backend remains authoritative for trusted operations.** Financial calculations, authorization decisions, and data persistence never leave the backend.

---

## Architecture

### Frontend

- **React 18** with TypeScript
- **Vite** for fast development and optimized production builds
- **Component-based UI** for households, expenses, chores, copilot, shopping, maintenance
- **API client** with Bearer token authentication

### Backend

- **Python 3.11** with Flask (local development)
- **AWS Lambda** (production deployment architecture)
- **Provider Abstraction Layer** for environment flexibility

### AI & LLM

- **Strands Agents** for tool selection and orchestration
- **Ollama** (local, `llama3.2:3b`)
- **AWS Bedrock** integration (production)

### Authentication

- Local authentication for development
- Amazon Cognito for AWS deployment architecture

### Authorization

- **Cedar** (AWS authorization engine) for household-scoped access control
- Server-side authorization before all protected operations
- Fail-closed authorization behavior

### Data

- **DynamoDB** (AWS architecture)
- **LocalStack** (local Docker simulation of AWS services)
- **In-memory storage** (development/testing)

### Infrastructure (AWS)

- **API Gateway** (HTTP routing)
- **Lambda** (serverless compute)
- **DynamoDB** (data persistence)
- **S3** (document storage)
- **Cognito** (user identity)
- **Bedrock** (managed LLM)
- **Step Functions** (workflow orchestration)
- **IAM** (role-based access control)

---

## Provider Architecture

RoomieOps supports multiple execution modes via a provider abstraction layer. This allows the same application code to run locally and on AWS without modification:

### LOCAL_HEURISTIC

- In-memory storage
- No external dependencies
- Fastest for development and testing

### BUILD_IT_STRANDS

- Local Ollama (`llama3.2:3b`)
- LocalStack for AWS-compatible local services
- Strands Agents for tool orchestration
- Intended for local Build It development and integration testing

### SHIP_IT_BEDROCK

- AWS Bedrock LLM
- AWS DynamoDB
- AWS Cognito
- Full production deployment architecture

The provider system ensures that application logic remains decoupled from infrastructure—allowing you to build and test locally, then deploy to AWS without code changes.

---

## Authorization & Security

RoomieOps enforces household-scoped authorization at the backend level:

- **User Authentication:** Bearer tokens from localStorage (local dev) or Cognito (production)
- **Household Isolation:** Each user only sees households they are members of
- **Operation Authorization:** Cedar makes authorization decisions before any state mutation
- **Fail-Closed:** Denied operations return 403; authorization never defaults to allow
- **Backend Authority:** Frontend cannot bypass backend authorization checks
- **Secrets Management:** AWS credentials, API keys, and sensitive configuration supplied via environment variables (never committed to source)

---

## Project Structure

```
RoomieOps/
├── frontend/                      # React + TypeScript + Vite
│   ├── src/
│   │   ├── api/                   # API client
│   │   ├── screens/               # UI components
│   │   └── types/                 # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── shared/                    # Shared Python modules
│   │   ├── finance_engine.py      # Deterministic expense calculations
│   │   ├── dynamodb_ops.py        # DynamoDB operations
│   │   ├── auth.py                # Authentication
│   │   ├── providers/             # Provider abstraction (LLM, storage, auth, authorization)
│   │   └── strands_agent.py       # Strands agent orchestration
│   ├── lambdas/                   # AWS Lambda handlers
│   │   ├── households/
│   │   ├── expenses/
│   │   ├── chores/
│   │   ├── copilot/
│   │   └── ...
│   ├── cedar/                     # Cedar authorization policies
│   ├── scripts/                   # Testing and utilities
│   ├── local_dev_server.py        # Local Flask development server
│   └── requirements-dev.txt
├── infrastructure/
│   └── template.yaml              # AWS SAM deployment template
├── docker-compose.yml
└── README.md
```

---

## Running Locally

### Prerequisites

- **Python 3.11+** (backend)
- **Node.js 18+** (frontend)
- **npm**

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173`.

### Backend

```bash
cd backend
pip install -r requirements-dev.txt
python local_dev_server.py
```

The backend runs on `http://localhost:5000`.

### Configuration

The backend auto-detects its execution mode:

- **LOCAL_HEURISTIC** (default): Uses in-memory storage, no external dependencies
- **BUILD_IT_STRANDS**: Requires `docker-compose up` (LocalStack + Ollama)
- **SHIP_IT_BEDROCK**: Requires AWS credentials and active services

Environment configuration via `.env` file (see `.env.example`):

```bash
cp .env.example .env
# Edit .env with your configuration
```

---

## Testing

### Frontend Production Build

```bash
cd frontend
npm run build
```

Verifies TypeScript compilation and Vite bundling. Output in `frontend/dist/`.

### Backend Python Validation

```bash
cd backend
python -m py_compile shared/*.py lambdas/*/*.py
```

Checks that the selected Python files compile successfully.

### Integration Tests

```bash
# Frontend/backend contract verification (no external dependencies)
python backend/scripts/test_phase3_frontend_backend_contract.py

# Real HTTP integration (requires backend running on :5000)
python backend/scripts/test_phase4_integration.py
```

---

## Known Limitations

- **AWS Deployment:** Requires an AWS account with active DynamoDB, Lambda, Bedrock, and Cognito services. Some AWS accounts may have service subscription restrictions.
- **LocalStack Build It Mode:** Full end-to-end validation against LocalStack was not completed because Docker and LocalStack environment were unavailable during final testing. The provider architecture and multi-tool orchestration are verified locally, but comprehensive Build It runtime validation is pending Docker/LocalStack availability.

---

## Roadmap

Future enhancements planned for RoomieOps:

- Receipt extraction from images
- Policy-aware household workflows
- Absence handling and escalation
- Rich notifications (SMS, push, email)
- Advanced search and retrieval
- Payment integration (UPI, Stripe)
- Voice interaction
- Multilingual support
- Anomaly detection
- Fairness-aware household coordination
- Multi-property management
- Household analytics

---

## Contributing

We welcome contributions! Please feel free to open issues, submit pull requests, or suggest improvements.


