"""
Verify AWS credentials and Bedrock availability
"""

import boto3
import os
from botocore.exceptions import ClientError

print("=== AWS Credential Resolution ===\n")
print(f"AWS_REGION: {os.environ.get('AWS_REGION', 'not set')}")
print(f"AWS_PROFILE: {os.environ.get('AWS_PROFILE', 'not set')}")
print(f"AWS_ACCESS_KEY_ID: {'set' if os.environ.get('AWS_ACCESS_KEY_ID') else 'NOT set'}")
print(f"AWS_SECRET_ACCESS_KEY: {'set' if os.environ.get('AWS_SECRET_ACCESS_KEY') else 'NOT set'}")

# Try to get session credentials
session = boto3.Session()
credentials = session.get_credentials()

print("\n=== boto3 Session ===")
if credentials:
    print(f"Credentials FOUND")
    print(f"  Access Key: {credentials.access_key[:10]}..." if credentials.access_key else "  Access Key: None")
    print(f"  Provider: {credentials.method if hasattr(credentials, 'method') else 'unknown'}")
else:
    print("Credentials NOT FOUND in boto3 session")
    print("  Credential chain checked: IAM role, env vars, ~/.aws/credentials, ~/.aws/config")

# Try STS to verify identity
print("\n=== AWS STS Identity ===")
try:
    sts = boto3.client('sts', region_name='us-east-1')
    identity = sts.get_caller_identity()
    print(f"Identity verified:")
    print(f"  Account: {identity['Account']}")
    print(f"  User ARN: {identity['Arn']}")
except ClientError as e:
    error_code = e.response['Error']['Code']
    print(f"Identity check FAILED: {error_code}")
    print(f"  Message: {e.response['Error']['Message']}")
except Exception as e:
    print(f"Error: {str(e)}")

# Try Bedrock invocation
print("\n=== Bedrock Invocation Test ===")
try:
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    print("Bedrock client created")
    
    model_id = "anthropic.claude-sonnet-4-5-20250929-v1:0"
    print(f"Model: {model_id}")
    
    response = bedrock.invoke_model(
        modelId=model_id,
        contentType='application/json',
        accept='application/json',
        body='{"prompt": "What is RoomieOps?", "max_tokens": 100}'
    )
    
    import json
    body = json.loads(response['body'].read())
    
    print(f"\n✓ Bedrock invocation SUCCESSFUL")
    print(f"  Response keys: {list(body.keys())}")
    print(f"  Status code: {response['ResponseMetadata']['HTTPStatusCode']}")
    
except ClientError as e:
    error_code = e.response['Error']['Code']
    print(f"\n✗ Bedrock invocation BLOCKED: {error_code}")
    print(f"  Message: {e.response['Error']['Message']}")
    
    if error_code == 'AccessDenied':
        print(f"\n  DIAGNOSIS: AWS account lacks Bedrock access in us-east-1")
        print(f"  ACTION: Bedrock is structurally integrated but cannot be tested locally")
        print(f"  FALLBACK: Using local heuristic detection for development")
        
except Exception as e:
    print(f"\n✗ Bedrock invocation ERROR: {str(e)}")
