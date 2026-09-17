# Spashta Architecture

## High-Level Overview

Spashta is a situational reasoning application for rule interpretation. It processes documents through a four-stage AI pipeline that extracts clauses, matches them to user situations, classifies risk, and provides localized explanations.

```
User → Upload + Situation
  ↓
[Frontend: React + Vite]
  ↓
[API Gateway + Cognito Auth]
  ↓
[Step Functions Orchestration]
  ├→ Lambda: Extract Clauses
  ├→ Lambda: Match Situation
  ├→ Lambda: Classify Risk
  └→ Lambda: Explain/Translate
  ↓
[Storage: S3 documents, DynamoDB results]
  ↓
[AI: Amazon Bedrock]
  ↓
Frontend: Result Display
```

## Components

### Frontend (React + Vite)

Located: `frontend/`

**Screens:**
1. **Upload** — document upload, document type selection, situation input
2. **Processing** — live pipeline progress indication
3. **Results** — risk tier display, clause citations, "Why?" explanation, language toggle

**Key Features:**
- Mobile-first responsive design
- Animated processing stages
- Interactive "Why?" expansion
- Language selection (English, Kannada)

### Backend (AWS)

#### API Layer (API Gateway)
- `POST /documents` — get presigned S3 URL for upload
- `POST /documents/{id}/process` — trigger pipeline
- `GET /documents/{id}` — fetch results

#### Compute (Lambda)
Four independent, testable stages:

1. **Extract** (`lambdas/extract/`)
   - Input: Document from S3
   - Output: Structured clauses with IDs and metadata
   - Uses Bedrock for intelligent extraction

2. **Match Situation** (`lambdas/match-situation/`)
   - Input: Clauses + user's situation
   - Output: Relevant clause matches with relevance type
   - Validates clause IDs exist in extraction output

3. **Risk Classify** (`lambdas/risk-classify/`)
   - Input: Matched clauses
   - Output: Risk tier (green|yellow|red), reasoning, confidence
   - Validates enum values and confidence thresholds

4. **Explain/Translate** (`lambdas/explanation/`)
   - Input: Risk result + target language
   - Output: Human-readable explanation in target language
   - Skipped if confidence is low

#### Orchestration (Step Functions)
- State machine coordinates the four-stage pipeline
- Implements retry logic and error handling
- Tracks processing status in DynamoDB

#### Storage

**S3 Bucket (`DocumentsBucket`)**
- Stores uploaded documents (PDFs, images)
- Versioning enabled for audit trail
- Private access (no public bucket)
- Presigned URLs for secure upload/download

**DynamoDB Table (`DocumentsTable`)**
- Partition key: `documentId`
- Attributes:
  - `ownerId` — Cognito user ID
  - `docType` — academic_regulation, rental_agreement, etc.
  - `extractedClauses` — Stage 1 output
  - `riskFlags` — Stage 3 output
  - `explanation` — Stage 4 output (multi-language)
  - `status` — processing | complete | failed
  - `createdAt` — ISO 8601 timestamp
- GSI: `OwnerIdCreatedAtIndex` for querying by user

#### Authentication (Cognito)
- User Pool: password-based authentication
- Client: generated secrets, OAuth 2.0 flows
- Frontend receives ID token for API calls

#### AI (Amazon Bedrock)
- Model: `anthropic.claude-3-sonnet-20240229-v1:0`
- Called 3–4 times per document (bounded, not open-ended)
- Each stage has a versioned prompt in `prompts/`
- JSON schema validation on all responses

### Build It (Local Development)

Located: `backend/` with SAM CLI support

**Key Technologies:**
- **Strands Agents SDK** — local agent orchestration
- **OpenSearch** — local clause retrieval (no API calls)
- **Cedar** — policy-based access control (explainable denials)
- **SAM CLI** — package Lambda locally
- **LocalStack** — simulate S3, DynamoDB locally

**Flow:**
```
Local Document
  ↓
[Strands Agent]
  ├→ OpenSearch: Retrieve clauses
  ├→ Local Model: Reasoning (via Strands)
  └→ Cedar: Policy evaluation
  ↓
Same output schema as Ship It
```

## Data Flow

### Upload

```
1. User uploads document via React
2. Frontend calls POST /documents
3. API Gateway invokes Lambda: getPresignedUrl
4. Lambda returns S3 presigned URL
5. Frontend uploads document directly to S3
6. Frontend calls POST /documents/{id}/process with situation
7. API Gateway invokes Step Functions: StartExecution
```

### Processing

```
1. Step Functions: Extract
   - Lambda reads document from S3
   - Sends to Bedrock with extraction prompt
   - Validates JSON output
   - Stores clauses in DynamoDB

2. Step Functions: Match Situation
   - Lambda retrieves clauses from previous step
   - Sends to Bedrock with matching prompt
   - Validates all clause IDs exist
   - Stores matches in DynamoDB

3. Step Functions: Classify Risk
   - Lambda processes matches
   - Sends to Bedrock with risk prompt
   - Validates risk tier and confidence
   - If confidence=low, sets low-confidence flag

4. Step Functions: Explain/Translate
   - Lambda skips if confidence=low
   - Sends to Bedrock with explanation prompt
   - Translates to target language
   - Stores explanation in DynamoDB

5. Status Update
   - DynamoDB record updated with status:complete
   - Error states handled gracefully
```

### Result Display

```
1. Frontend polls GET /documents/{id}
2. API returns complete result
3. Frontend displays:
   - Risk tier emoji (🟢🟡🔴)
   - Risk label and description
   - Explanation text
   - "Why?" expandable section
   - Source clause citation
   - Confidence indicator
   - Language selector
   - Disclaimer
```

## Security Model

**Authentication:**
- Cognito validates user identity
- API Gateway requires auth token
- User ID extracted from token

**Authorization:**
- DynamoDB records include `ownerId`
- Lambda ownership check on all reads: `ownerId == current_user`
- Returns 403 Forbidden if unauthorized

**Data Protection:**
- S3 bucket: private, no public access
- Presigned URLs: time-limited (5-min default)
- Documents encrypted at rest (S3 default)
- DynamoDB: on-demand, no always-on servers

**Responsible AI:**
- All risk results cite exact source clauses
- Low-confidence results never rendered as certain
- Fabricated clause references rejected by validation
- Disclaimer visible in UI: "does not replace official guidance"

## Error Handling

| Stage | Failure Mode | Detection | Recovery |
|-------|--------------|-----------|----------|
| Extract | Empty clauses | Schema validation | Retry once, then fail |
| Extract | Malformed JSON | JSON parse | Retry with stricter prompt |
| Match | Unknown clauseId | ID validation | Retry Stage 2 |
| Classify | Invalid risk tier | Enum validation | Retry with correction |
| Classify | Low confidence | Confidence check | Still return tier, flag for manual review |
| Explain | Translation error | Exception handling | Return English, log error |
| API | Unauthorized | Token check | Return 403 |
| API | Not found | Document check | Return 404 |
| Step Functions | Lambda timeout | State error | Error state updates DynamoDB |
| DynamoDB | Write failure | Exception | Retry with exponential backoff |

All failures are user-friendly:
- No stack traces to frontend
- Generic "processing failed" message with reason code
- Fallback messages for common failures
- Errors logged for debugging

## Deployment

### Ship It (Cloud)

**Tools:**
- AWS SAM CLI for packaging
- Amplify for frontend hosting
- CloudFormation for infrastructure

**Deployment:**
```bash
cd infrastructure
sam build
sam deploy --guided
# Follow prompts for region, stack name, parameters
```

**Frontend:**
```bash
cd frontend
npm run build
# Connect to Amplify Console via Git push
```

**Post-Deployment:**
- Verify Cognito user pool created
- Test S3 presigned URL generation
- Invoke Lambda functions with test payloads
- Check Step Functions execution history
- Confirm DynamoDB table populated

### Build It (Local)

**Setup:**
```bash
# Install SAM CLI
pip install aws-sam-cli

# Install LocalStack
pip install localstack-cli

# Start LocalStack
localstack start -d

# Install Strands SDK
pip install strands-sdk

# Install Cedar
pip install cedar-policy
```

**Local Deployment:**
```bash
cd backend
sam build
sam local start-api --docker-network localstack
sam local invoke ExtractLambda -e events/extract.json
```

## Cost Model

**Per-Document Cost (Estimated):**
- Bedrock calls: ~$0.003 (3–4 calls × ~0.001 each)
- Lambda: ~$0.0002 (4 invocations × 1–2 sec each)
- DynamoDB: ~$0.0001 (3–4 writes)
- S3: ~$0.0001 (document storage)
- **Total: ~$0.0034 per document**

**Scaling:**
- 1,000 documents/day = $3.40/day
- 10,000 documents/day = $34/day
- No fixed infrastructure cost (serverless)

## Testing Strategy

**Unit Tests:**
- Lambda extraction schema validation
- Risk tier enum validation
- Clause ID cross-reference validation
- Confidence threshold enforcement
- Language code validation

**Integration Tests:**
- Full pipeline with mock Bedrock responses
- Step Functions state machine transitions
- DynamoDB record lifecycle
- S3 upload/download with presigned URLs
- Cognito token validation

**Regression Tests:**
- Run against demo corpus
- Verify all edge cases produce expected results
- Compare against baseline results for performance

**Manual QA:**
- End-to-end flow with real documents
- Mobile UI on various devices
- Error message clarity
- Accessibility (keyboard navigation, screen readers)

## Monitoring

**CloudWatch Logs:**
- Lambda function logs (errors, processing times)
- API Gateway access logs
- Step Functions execution history

**CloudWatch Metrics:**
- Lambda duration and errors
- DynamoDB read/write throughput
- API Gateway latency and errors
- Bedrock API call counts

**Alarms:**
- Lambda error rate > 5%
- DynamoDB throttling
- API Gateway 5xx errors
- Processing timeout (> 5 min)

## Future Enhancements

**P1:**
- Multi-document upload with readiness checklist
- Kannada UI translation (currently explanation only)
- Document preview in results

**P2:**
- Cedar policy visualization
- EventBridge reminder scheduling
- Clause comparison across documents
- Search/filter clauses
- User document history

**P3:**
- Support for more Indian languages
- Mobile app (React Native)
- Document OCR improvement
- Fine-tuned local models for specific domains

---

**Last Updated:** Sept 17, 2026
**Status:** Phase 0 Complete
