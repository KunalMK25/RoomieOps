# Deployment Checklist — Spashta

Use this checklist to verify all components are working before the demo and official submission.

## Pre-Deployment (Local)

### Frontend
- [ ] `npm run build` completes without errors
- [ ] Frontend builds to `dist/` directory
- [ ] All TypeScript types validate (`npm run type-check`)
- [ ] No ESLint warnings (`npm run lint`)
- [ ] Vite dev server runs locally (`npm run dev`)
- [ ] All three screens render correctly
- [ ] Mock pipeline simulation works (11 seconds total)
- [ ] Language switching works (English → Kannada)

### Backend
- [ ] All Lambda functions have requirements.txt
- [ ] No syntax errors in Python files
- [ ] Shared utilities import correctly
- [ ] Bedrock client is configurable via environment variables
- [ ] All Lambda handlers return proper API response format
- [ ] Error handling covers all identified edge cases

### Documentation
- [ ] ARCHITECTURE.md is complete and accurate
- [ ] AWS_DEPLOYMENT.md has step-by-step instructions
- [ ] DEVELOPMENT.md explains frontend architecture
- [ ] TESTING.md has comprehensive test scenarios
- [ ] README has project overview (to be finalized post-deploy)

### Data & Prompts
- [ ] Demo regulation document exists and is valid
- [ ] All 4 prompts are in `prompts/` directory
- [ ] Prompts have proper placeholders for substitution
- [ ] Mock clauses and explanations cover all scenarios

## Deployment (AWS)

### Cognito Setup
- [ ] User pool created via SAM
- [ ] Test user account created
- [ ] Test user password set to permanent value
- [ ] User can authenticate

### S3 Configuration
- [ ] Bucket created with versioning enabled
- [ ] Public access blocked
- [ ] Lifecycle policies configured (delete old versions after 30 days)
- [ ] Test document can be uploaded with presigned URL

### DynamoDB Setup
- [ ] Table created with correct schema
- [ ] Partition key is `documentId`
- [ ] GSI for querying by owner created
- [ ] Table is in ACTIVE state
- [ ] Sample record can be written and read

### Lambda Functions
- [ ] All 7 Lambda functions deployed
- [ ] Environment variables set for all:
  - AWS_REGION
  - BEDROCK_MODEL_ID
  - DYNAMODB_TABLE
  - S3_BUCKET
  - STATE_MACHINE_ARN (for API functions)
- [ ] Execution role has permissions for:
  - S3: GetObject, PutObject
  - DynamoDB: GetItem, UpdateItem, Query
  - Bedrock: InvokeModel
  - Logs: CreateLogGroup, CreateLogStream, PutLogEvents

### Step Functions
- [ ] State machine created with correct definition
- [ ] State machine can be executed
- [ ] All state transitions work
- [ ] Error states properly handle failures
- [ ] Results are written to DynamoDB

### API Gateway
- [ ] All three endpoints created:
  - POST /documents (presigned URL)
  - POST /documents/{id}/process (start processing)
  - GET /documents/{id} (fetch results)
- [ ] Cognito authorizer attached to all endpoints
- [ ] CORS configured correctly
- [ ] Test requests return 401 without auth token
- [ ] Test requests return 200 with valid token

## Bedrock Verification

- [ ] Bedrock access enabled in your region
- [ ] Model `anthropic.claude-3-sonnet-20240229-v1:0` available
- [ ] IAM role has `bedrock:InvokeModel` permission
- [ ] Test invocation succeeds:
  ```bash
  aws bedrock-runtime invoke-model \
    --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
    --body '{"prompt": "Hello", "max_tokens": 100}' \
    /tmp/response.json
  ```

## Integration Testing

### Test Full Pipeline
- [ ] Upload regulation document via presigned URL
- [ ] Start processing via API
- [ ] Observe Step Functions execution
- [ ] Processing completes within 5 minutes
- [ ] All 4 stages execute successfully
- [ ] DynamoDB record updated with results
- [ ] Results contain:
  - extractedClauses (array)
  - riskResult (object with tier, reasoning, confidence)
  - explanations (object with language keys)

### Test Different Scenarios
- [ ] High attendance (85%) → Green result
- [ ] Low attendance (60%) → Red result
- [ ] Medical exemption (72% + medical) → Yellow result
- [ ] Kannada explanation works
- [ ] Low confidence result shows fallback message

### Test Error Cases
- [ ] Empty clause extraction handled gracefully
- [ ] Invalid Bedrock JSON caught and retried
- [ ] S3 missing document returns 400
- [ ] Unauthorized access returns 403
- [ ] Timeout after 5 minutes

## Security Review

- [ ] No AWS credentials in repository
- [ ] No hardcoded secrets in code
- [ ] All environment variables use defaults or must be set
- [ ] S3 bucket has no public ACLs
- [ ] S3 presigned URLs have 5-minute expiry
- [ ] DynamoDB ownership field enforced
- [ ] API requires Cognito authentication
- [ ] Lambda execution roles follow principle of least privilege
- [ ] CORS configured to allow only known origins
- [ ] No sensitive data in CloudWatch logs

## Performance Validation

- [ ] Document upload: < 1 second
- [ ] Processing pipeline: 5–10 seconds
- [ ] Result retrieval: < 1 second
- [ ] Lambda cold start: < 3 seconds
- [ ] Bedrock API call: < 5 seconds per invocation
- [ ] Under load (10 concurrent): no timeouts

## Documentation Review

- [ ] README exists with:
  - Project description
  - Problem statement
  - Solution overview
  - Architecture diagram link
  - Deployment instructions link
  - Demo video link
  - Team credits
- [ ] Code comments explain complex logic
- [ ] Prompts are well-formatted and clear
- [ ] API responses documented with examples
- [ ] Error codes documented

## Demo Preparation

### Assets
- [ ] Demo regulation document prepared
- [ ] Test user account ready
- [ ] Sample situations written for demo
- [ ] Kannada text verified for display

### Rehearsal
- [ ] Full user flow tested end-to-end
- [ ] Upload → Processing → Results works smoothly
- [ ] No errors or timeouts during demo
- [ ] Language switching demonstrated
- [ ] "Why?" expansion explained
- [ ] All three risk tiers shown (or selected scenarios)

### Backup Plan
- [ ] Fallback to mock data if AWS unavailable
- [ ] Frontend can run locally without backend
- [ ] Screenshots/video prepared for offline demo
- [ ] All demo URLs and credentials documented

## Final Submission

### Code Quality
- [ ] No console errors or warnings
- [ ] No commented-out debug code
- [ ] Consistent code style throughout
- [ ] No TODOs left in critical paths
- [ ] All imports resolve correctly

### Git History
- [ ] Commits are meaningful with good messages
- [ ] No merge conflicts
- [ ] Branch is up to date with main
- [ ] 12 commits covering all phases

### Submission Materials
- [ ] Public GitHub repository link
- [ ] README is clear and discoverable
- [ ] License included (MIT or similar)
- [ ] Architecture diagram added
- [ ] Demo video recorded (optional but recommended)
- [ ] AI tool disclosures made (if using Kiro, Claude, etc.)

## Post-Submission

- [ ] CloudFormation stack can be deleted cleanly
- [ ] No orphaned resources left in AWS
- [ ] Final logs and metrics exported for analysis
- [ ] Team feedback collected and documented

---

**Completed Date:** _______________
**Deployment Engineer:** _______________
**Notes:** _______________

**All items checked ✓ = Ready for demo/submission**
