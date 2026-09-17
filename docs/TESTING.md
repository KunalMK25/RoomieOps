# Testing Guide

## Manual Testing Checklist

### Frontend Manual Tests

#### Upload Screen
- [ ] Can select a document file (any type)
- [ ] Can choose document type from dropdown
- [ ] Can enter situation text
- [ ] Can select language (English/Kannada)
- [ ] Clicking "Analyze" generates a documentId
- [ ] Validation shows error if file missing
- [ ] Validation shows error if situation empty

#### Processing Screen
- [ ] All 5 stages appear in order
- [ ] Stages animate with active indicator
- [ ] Progress bar fills from 0 to 100%
- [ ] Each stage shows completion checkmark
- [ ] Screen transitions to Results after completion
- [ ] Takes approximately 11 seconds total

#### Results Screen
- [ ] Risk card displays with correct emoji (🟢🟡🔴)
- [ ] Risk tier label is correct (Normal/Pay Attention/Potential Issue)
- [ ] Risk description is appropriate
- [ ] Explanation text displays
- [ ] "Why?" button expands/collapses
- [ ] Source clause displays in expanded section
- [ ] Clause section reference visible
- [ ] Confidence badge shows correct level
- [ ] Confidence note appears for "low" confidence
- [ ] Language selector changes explanation text
- [ ] Kannada text displays correctly
- [ ] Disclaimer is visible
- [ ] "Back" button returns to Upload
- [ ] "Analyze Another" button resets flow

### API Manual Tests

#### Test Presigned URL Endpoint

```bash
# Get auth token
TOKEN=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id <POOL_ID> \
  --client-id <CLIENT_ID> \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=testuser,PASSWORD=Password123! \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# Request presigned URL
curl -X POST https://<API_ID>.execute-api.us-east-1.amazonaws.com/prod/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"docType": "academic_regulation"}'

# Expected response:
# {
#   "statusCode": 200,
#   "body": {
#     "documentId": "doc-...",
#     "uploadUrl": "https://s3.../...",
#     "s3Key": "documents/..."
#   }
# }
```

#### Test Upload to S3

```bash
UPLOAD_URL="<from previous response>"
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: text/plain" \
  --data-binary @data/attendance-regulation.md

# Should return 200 OK
```

#### Test Start Processing

```bash
DOC_ID="<documentId from presigned URL>"
curl -X POST https://<API_ID>.execute-api.us-east-1.amazonaws.com/prod/documents/$DOC_ID/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "situation": "I have 72% attendance and missed classes because of medical reasons.",
    "language": "en"
  }'

# Expected response:
# {
#   "statusCode": 200,
#   "body": {
#     "documentId": "doc-...",
#     "status": "processing",
#     "executionArn": "arn:aws:states:..."
#   }
# }
```

#### Test Get Document Status

```bash
# Immediately after starting processing:
curl -X GET https://<API_ID>.execute-api.us-east-1.amazonaws.com/prod/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"

# Should return status: "processing"

# After ~11 seconds:
curl -X GET https://<API_ID>.execute-api.us-east-1.amazonaws.com/prod/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"

# Should return status: "complete" with results
```

## End-to-End Test Scenarios

### Scenario 1: Happy Path - High Attendance

**Setup:**
- Situation: "I have 85% attendance"
- Language: English

**Expected Result:**
- Risk Tier: 🟢 Green (Normal)
- Explanation: "Your attendance exceeds the 75% threshold..."
- Confidence: High

**Verification:**
- [ ] Frontend shows green card
- [ ] "Why?" reveals high confidence
- [ ] Source clause is c1 (75% threshold)

### Scenario 2: Low Attendance Without Exemption

**Setup:**
- Situation: "I have 60% attendance with no reason"
- Language: English

**Expected Result:**
- Risk Tier: 🔴 Red (Potential Issue)
- Explanation: "Your attendance is significantly below the 75% threshold..."
- Confidence: High

**Verification:**
- [ ] Frontend shows red card
- [ ] Reasoning mentions threshold breach
- [ ] Suggests reviewing exemption policy

### Scenario 3: Low Attendance with Medical Reason

**Setup:**
- Situation: "I have 72% attendance and missed classes because of medical reason"
- Language: English

**Expected Result:**
- Risk Tier: 🟡 Yellow (Pay Attention)
- Explanation: "Your attendance is below threshold. You may qualify for condonation with medical documentation..."
- Confidence: High

**Verification:**
- [ ] Frontend shows yellow card
- [ ] Mentions condonation possibility
- [ ] References medical exemption clause

### Scenario 4: Language Translation - Kannada

**Setup:**
- Situation: "I have 72% attendance with medical reason"
- Language: Kannada

**Expected Result:**
- Explanation in Kannada
- Risk Tier: 🟡 Yellow

**Verification:**
- [ ] Kannada script displays correctly
- [ ] Can read and understand explanation
- [ ] No mojibake or encoding issues

### Scenario 5: Low Confidence Ambiguous Case

**Setup:**
- Situation: "I have 70% attendance but the regulation is unclear"
- Language: English

**Expected Result:**
- Risk Tier: 🟡 Yellow with Low Confidence
- Explanation: "This requires manual verification..."
- Confidence Badge: ⚠ Low

**Verification:**
- [ ] Low confidence indicator visible
- [ ] Manual review recommendation shown
- [ ] No false certainty implied

## Automated Testing

### Unit Tests for Lambda Functions

```bash
cd backend
python -m pytest tests/ -v
```

### Integration Tests

```bash
python tests/test_integration.py
```

### Frontend Tests (if Jest configured)

```bash
cd frontend
npm test
```

## Load Testing

### Generate Test Traffic

```bash
# Install apache bench
brew install httpd  # macOS
# or apt install apache2-utils  # Linux

# Test extraction endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 \
  -H "Authorization: Bearer $TOKEN" \
  https://<API_ID>.execute-api.us-east-1.amazonaws.com/prod/documents
```

### Monitor CloudWatch Metrics

```bash
# Watch Lambda invocation metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=spashta-extract \
  --start-time 2026-09-17T00:00:00Z \
  --end-time 2026-09-18T00:00:00Z \
  --period 300 \
  --statistics Sum,Average
```

## Debugging

### View Lambda Logs

```bash
# Stream logs in real-time
aws logs tail /aws/lambda/spashta-extract --follow

# View specific time range
aws logs filter-log-events \
  --log-group-name /aws/lambda/spashta-extract \
  --start-time 1695000000000
```

### View Step Functions Execution

```bash
# Get execution details
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn <execution-arn>
```

### Check DynamoDB Records

```bash
# Scan all documents
aws dynamodb scan --table-name spashta-documents

# Get specific document
aws dynamodb get-item \
  --table-name spashta-documents \
  --key '{"documentId": {"S": "doc-123"}}'
```

## Common Issues

### Lambda Timeout

**Symptom:** Step Functions state machine times out, Lambda not responding

**Fix:**
```bash
aws lambda update-function-configuration \
  --function-name spashta-extract \
  --timeout 600  # 10 minutes
```

### Bedrock Access Denied

**Symptom:** "AccessDenied" error when calling Bedrock

**Fix:**
1. Ensure Lambda execution role has Bedrock permissions
2. Verify Bedrock access is enabled in your region
3. Check IAM policy includes `bedrock:InvokeModel`

### S3 NoSuchKey

**Symptom:** Lambda fails to read document from S3

**Fix:**
1. Verify document was actually uploaded to S3
2. Check S3 bucket name matches environment variable
3. Verify S3 key path is correct
4. Check IAM permissions for Lambda role

### DynamoDB Throttling

**Symptom:** DynamoDB errors during high load

**Fix:**
```bash
aws dynamodb update-table \
  --table-name spashta-documents \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10
```

## Test Coverage Goals

- Frontend: All 3 screens with happy path + error states (6 scenarios)
- API: All 3 endpoints authenticated and unauthorized (6 tests)
- Lambda: All 7 functions with valid and invalid inputs (21 tests)
- Pipeline: 5 end-to-end scenarios (5 tests)
- **Total: 38+ test cases**

---

**Last Updated:** Sept 17, 2026
**Status:** Manual testing framework complete, automated tests ready
