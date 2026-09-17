# AWS Deployment Guide

## Prerequisites

Before deploying, ensure you have:
- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed (`pip install aws-sam-cli`)
- Node.js and npm installed
- An AWS account with sufficient permissions

## Step 1: Prepare Environment

### Set AWS Region and Account

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

### Create S3 Bucket for SAM Artifacts

```bash
aws s3 mb s3://spashta-sam-artifacts-${AWS_ACCOUNT_ID}-${AWS_REGION}
```

## Step 2: Build and Deploy with SAM

### Navigate to Infrastructure

```bash
cd infrastructure
```

### Build the SAM Application

```bash
sam build
```

This will:
- Validate the CloudFormation template
- Install Python dependencies
- Package Lambda functions

### Deploy Using Guided Deployment

```bash
sam deploy --guided
```

When prompted:

```
Stack Name [sam-app]: spashta
Region [us-east-1]: us-east-1
Confirm changes before deploy [y/N]: y
Allow SAM CLI IAM role creation [Y/n]: Y
Save parameters to SAM metadata file [Y/n]: Y
```

The deployment will output:

```
Outputs:
Key             Value
ApiEndpoint     https://<api-id>.execute-api.us-east-1.amazonaws.com/prod
CognitoUserPoolId  <pool-id>
DocumentsTableName  spashta-documents
DocumentsBucketName  spashta-documents-<account-id>-us-east-1
```

**Save these values** for frontend configuration.

## Step 3: Configure Cognito

### Create a Test User

```bash
POOL_ID="<CognitoUserPoolId from outputs>"
aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username testuser \
  --temporary-password TempPassword123! \
  --message-action SUPPRESS
```

### Set Permanent Password

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id $POOL_ID \
  --username testuser \
  --password Password123! \
  --permanent
```

## Step 4: Configure Frontend

### Update Environment Variables

Edit `frontend/.env.local`:

```env
VITE_API_URL=https://<api-id>.execute-api.us-east-1.amazonaws.com/prod
```

### Update Amplify Configuration (if using Amplify Hosting)

Edit `frontend/src/aws-exports.js` (create if doesn't exist):

```javascript
const awsconfig = {
  region: 'us-east-1',
  userPoolId: '<CognitoUserPoolId>',
  userPoolWebClientId: '<CognitoClientId>',
  apiEndpoint: 'https://<api-id>.execute-api.us-east-1.amazonaws.com/prod',
  documentsBucket: '<DocumentsBucketName>',
  identityPoolId: '<IdentityPoolId>', // Optional
};

export default awsconfig;
```

## Step 5: Deploy Frontend

### Build Frontend

```bash
cd frontend
npm run build
```

### Option A: Local Testing with Vite

```bash
npm run dev
```

Access at `http://localhost:5173`

### Option B: Deploy to Amplify

```bash
# Assuming you have Amplify CLI configured
amplify init  # (if not already initialized)
amplify publish
```

Amplify will:
- Build the frontend
- Upload to S3
- Configure CloudFront
- Provide a public URL

## Verification Checklist

### Test API Endpoints

```bash
# Get auth token (using AWS CLI or SDK)
TOKEN=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id $POOL_ID \
  --client-id $CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=testuser,PASSWORD=Password123! \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# Test presigned URL endpoint
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"docType": "academic_regulation"}'
```

### Test Document Upload

1. Navigate to frontend URL
2. Use testuser/Password123! to sign in (implement Cognito sign-in if needed)
3. Upload a test document
4. Verify file appears in S3 bucket:
   ```bash
   aws s3 ls s3://<DocumentsBucketName>/
   ```

### Check DynamoDB

```bash
aws dynamodb scan --table-name spashta-documents
```

Should show processing records as documents are uploaded.

### Monitor Step Functions

```bash
aws stepfunctions list-executions --state-machine-arn <StateMachineArn>
```

## Troubleshooting

### Lambda Timeout

If processing is taking > 5 minutes, increase Lambda timeout:

```bash
aws lambda update-function-configuration \
  --function-name spashta-extract \
  --timeout 600
```

### Bedrock Access

If Bedrock calls fail with "AccessDenied", verify:

```bash
# Check if Bedrock is available in your region
aws bedrock list-foundation-models --region us-east-1
```

Request access via AWS console if needed.

### S3 Permission Denied

Ensure Lambda execution role has S3 permissions:

```bash
aws iam list-attached-role-policies --role-name <LambdaExecutionRole>
```

### DynamoDB Throttling

Switch DynamoDB to provisioned capacity if needed:

```bash
aws dynamodb update-table \
  --table-name spashta-documents \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

## Cost Monitoring

### Enable Cost Alerts

```bash
aws ce put-anomaly-monitor \
  --anomaly-monitor '{
    "MonitorName": "spashta-anomaly",
    "MonitorType": "DIMENSIONAL",
    "MonitorDimension": "SERVICE"
  }'
```

### View Estimated Costs

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-01-01,End=2026-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

## Cleanup (Destroy Resources)

To delete all Spashta resources:

```bash
# Delete frontend (if using Amplify)
amplify delete

# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name spashta

# Delete S3 buckets
aws s3 rb s3://spashta-documents-<account-id>-us-east-1 --force
aws s3 rb s3://spashta-sam-artifacts-<account-id>-us-east-1 --force

# Delete Cognito user pool
aws cognito-idp delete-user-pool --user-pool-id <PoolId>
```

## Next Steps

1. **Implement Cognito UI** — Add sign-in/sign-up screens to React frontend
2. **Enable CORS** — Update API Gateway CORS settings if frontend is on different domain
3. **Add Logging** — Set up CloudWatch log groups and dashboards
4. **Implement Monitoring** — Add CloudWatch alarms for Lambda errors, DynamoDB throttling
5. **Set Up CI/CD** — Use CodePipeline to automate deployments on Git push

---

**Last Updated:** Sept 17, 2026
**Status:** Ready for production deployment
