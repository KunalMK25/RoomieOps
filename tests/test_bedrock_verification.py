"""
Bedrock Live Invocation Verification Test

Verifies:
1. AWS credentials available
2. Bedrock service access
3. Claude model availability
4. Actual model invocation

Status determination:
- VERIFIED: Credentials present, Bedrock accessible, model responds
- BLOCKED: No credentials or service access denied
"""

import sys
import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError


def test_aws_credentials():
    """Test 1: Are AWS credentials available?"""
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✓ AWS Credentials: FOUND")
        print(f"  Account: {identity.get('Account')}")
        print(f"  User: {identity.get('Arn')}")
        return True
    except NoCredentialsError as e:
        print(f"✗ AWS Credentials: NOT FOUND - {e}")
        return False
    except ClientError as e:
        print(f"✗ AWS Credentials: ERROR - {e}")
        return False


def test_bedrock_access():
    """Test 2: Can we access Bedrock?"""
    try:
        bedrock = boto3.client('bedrock')
        models = bedrock.list_foundation_models()
        print(f"✓ Bedrock Access: SUCCESS")
        print(f"  Available models: {len(models.get('modelSummaries', []))}")
        return True
    except ClientError as e:
        print(f"✗ Bedrock Access: DENIED - {e}")
        return False
    except Exception as e:
        print(f"✗ Bedrock Access: ERROR - {e}")
        return False


def test_bedrock_model_available():
    """Test 3: Is Claude Sonnet 4.5 available?"""
    try:
        bedrock = boto3.client('bedrock')
        
        # Target model (latest Claude Sonnet)
        target_model_id = "anthropic.claude-sonnet-4-5-20250929-v1:0"
        
        models = bedrock.list_foundation_models()
        available_models = [m['modelId'] for m in models.get('modelSummaries', [])]
        
        if target_model_id in available_models:
            print(f"✓ Bedrock Model: {target_model_id} AVAILABLE")
            return True
        else:
            # Check for any Claude Sonnet
            claude_models = [m for m in available_models if 'claude-sonnet' in m.lower()]
            if claude_models:
                print(f"✓ Bedrock Model: Claude Sonnet available ({claude_models[0]})")
                return True
            else:
                print(f"✗ Bedrock Model: {target_model_id} NOT AVAILABLE")
                print(f"  Available: {available_models[:5]}")
                return False
    except Exception as e:
        print(f"✗ Bedrock Model: ERROR - {e}")
        return False


def test_bedrock_invocation():
    """Test 4: Can we actually invoke Claude?"""
    try:
        bedrock_runtime = boto3.client('bedrock-runtime')
        
        model_id = "anthropic.claude-sonnet-4-5-20250929-v1:0"
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-06-01",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": "Respond with only: OK"
                    }
                ]
            })
        )
        
        result = json.loads(response['body'].read())
        print(f"✓ Bedrock Invocation: SUCCESS")
        print(f"  Response: {result.get('content', [{}])[0].get('text', 'N/A')[:50]}")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'UNKNOWN')
        if error_code == 'AccessDeniedException':
            print(f"✗ Bedrock Invocation: ACCESS DENIED - {e}")
        else:
            print(f"✗ Bedrock Invocation: ERROR - {error_code}: {e}")
        return False
    except Exception as e:
        print(f"✗ Bedrock Invocation: ERROR - {e}")
        return False


def test_bedrock_execution_mode():
    """Test 5: Determine Bedrock execution mode"""
    print("="*50)
    print("BEDROCK LIVE INVOCATION VERIFICATION")
    print("="*50)
    
    creds_ok = test_aws_credentials()
    if not creds_ok:
        print("\n" + "="*50)
        print("BEDROCK: BLOCKED (no credentials)")
        print("="*50)
        return "BLOCKED"
    
    access_ok = test_bedrock_access()
    if not access_ok:
        print("\n" + "="*50)
        print("BEDROCK: BLOCKED (no Bedrock access)")
        print("="*50)
        return "BLOCKED"
    
    model_ok = test_bedrock_model_available()
    if not model_ok:
        print("\n" + "="*50)
        print("BEDROCK: BLOCKED (model not available)")
        print("="*50)
        return "BLOCKED"
    
    try:
        invoke_ok = test_bedrock_invocation()
        if invoke_ok:
            print("\n" + "="*50)
            print("BEDROCK: VERIFIED")
            print("="*50)
            return "VERIFIED"
    except Exception:
        pass
    
    print("\n" + "="*50)
    print("BEDROCK: BLOCKED (invocation failed)")
    print("="*50)
    return "BLOCKED"


if __name__ == "__main__":
    mode = test_bedrock_execution_mode()
    sys.exit(0 if mode == "VERIFIED" else 1)
