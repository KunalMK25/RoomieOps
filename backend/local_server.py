"""
Local development server for RoomieOps backend.
Simulates Lambda functions and AWS services without AWS account.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

import boto3
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "shared"))

from bedrock import call_bedrock, extract_json_from_response

app = Flask(__name__)
CORS(app)

# Configure local AWS services
os.environ["AWS_ENDPOINT_URL"] = "http://localhost:4566"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["DYNAMODB_TABLE"] = "roomieops-household-state"
os.environ["S3_BUCKET"] = "roomieops-documents-local"
os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-sonnet-4-5-20250929-v1:0"

# Initialize AWS clients pointing to local services
s3 = boto3.client("s3", endpoint_url="http://localhost:4566", region_name="us-east-1")
dynamodb = boto3.resource(
    "dynamodb", endpoint_url="http://localhost:4566", region_name="us-east-1"
)
sfn = boto3.client(
    "stepfunctions", endpoint_url="http://localhost:4566", region_name="us-east-1"
)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


@app.route("/api/v1/presigned-url", methods=["POST"])
def get_presigned_url():
    """Generate presigned URL for document upload."""
    try:
        data = request.get_json()
        document_id = data.get("documentId")
        
        if not document_id:
            return jsonify({"error": "documentId required"}), 400
        
        # Create presigned URL for S3
        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": os.environ["S3_BUCKET"], "Key": f"documents/{document_id}"},
            ExpiresIn=3600,
        )
        
        return jsonify({"presignedUrl": url, "documentId": document_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/start-processing", methods=["POST"])
def start_processing():
    """Start document processing via Step Functions."""
    try:
        data = request.get_json()
        document_id = data.get("documentId")
        situation = data.get("situation")
        language = data.get("language", "en")
        
        if not document_id or not situation:
            return jsonify({"error": "documentId and situation required"}), 400
        
        # Save initial metadata to DynamoDB
        table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
        table.put_item(
            Item={
                "documentId": document_id,
                "status": "PROCESSING",
                "situation": situation,
                "language": language,
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat(),
            }
        )
        
        # For local development, directly call the processing pipeline
        # instead of Step Functions
        process_document_local(document_id, situation, language)
        
        return jsonify({"documentId": document_id, "status": "PROCESSING"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/document/<document_id>", methods=["GET"])
def get_document(document_id):
    """Retrieve document processing result."""
    try:
        table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
        response = table.get_item(Key={"documentId": document_id})
        
        if "Item" not in response:
            return jsonify({"error": "Document not found"}), 404
        
        return jsonify(response["Item"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def process_document_local(document_id: str, situation: str, language: str):
    """
    Local processing pipeline (simulates Step Functions execution).
    Calls Bedrock for extraction, matching, risk classification, and explanation.
    """
    try:
        table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
        
        # Stage 1: Extract clauses from document
        print(f"\n[1/4] Extracting clauses from document {document_id}...")
        clauses = extract_clauses_local(document_id)
        
        # Stage 2: Match situation
        print(f"[2/4] Matching situation: {situation}")
        match_result = match_situation_local(situation, clauses, language)
        
        # Stage 3: Classify risk
        print(f"[3/4] Classifying risk...")
        risk_result = classify_risk_local(match_result, situation, language)
        
        # Stage 4: Generate explanation
        print(f"[4/4] Generating explanation...")
        explanation = generate_explanation_local(
            situation, match_result, risk_result, language
        )
        
        # Save results to DynamoDB
        table.update_item(
            Key={"documentId": document_id},
            UpdateExpression="SET #status = :status, extractedClauses = :clauses, matchResult = :match, riskResult = :risk, explanations = :exp, updatedAt = :updated",
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":status": "COMPLETED",
                ":clauses": clauses,
                ":match": match_result,
                ":risk": risk_result,
                ":exp": {language: explanation},
                ":updated": datetime.utcnow().isoformat(),
            },
        )
        
        print(f"✓ Processing complete for {document_id}\n")
    except Exception as e:
        print(f"✗ Processing failed: {str(e)}\n")
        table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
        table.update_item(
            Key={"documentId": document_id},
            UpdateExpression="SET #status = :status, errorMessage = :error, updatedAt = :updated",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "FAILED",
                ":error": str(e),
                ":updated": datetime.utcnow().isoformat(),
            },
        )


def extract_clauses_local(document_id: str) -> list:
    """Extract clauses from document using Bedrock."""
    prompt = f"""Extract all relevant clauses from the academic regulation document with ID {document_id}.

Return a JSON array of clause objects, each with:
- clauseId (e.g., "clause_1")
- title
- text
- relevance (HIGH/MEDIUM/LOW)

Example format:
[
  {{"clauseId": "clause_1", "title": "Attendance Policy", "text": "Students must maintain...", "relevance": "HIGH"}},
  {{"clauseId": "clause_2", "title": "Exam Eligibility", "text": "To be eligible for exam...", "relevance": "HIGH"}}
]

Return ONLY the JSON array, no other text."""

    try:
        response = call_bedrock(prompt, max_tokens=2048)
        clauses = extract_json_from_response(response)
        return clauses if isinstance(clauses, list) else [clauses]
    except Exception as e:
        print(f"Extraction error (using mock data): {e}")
        # Return mock clauses for development
        return [
            {
                "clauseId": "clause_1",
                "title": "Attendance Policy",
                "text": "Students must maintain at least 75% attendance to be eligible for examination.",
                "relevance": "HIGH",
            },
            {
                "clauseId": "clause_2",
                "title": "Medical Exemption",
                "text": "Medical reasons are recognized as valid grounds for absence with proper documentation.",
                "relevance": "HIGH",
            },
        ]


def match_situation_local(situation: str, clauses: list, language: str) -> Dict[str, Any]:
    """Match student situation against clauses."""
    prompt = f"""Given this student situation:
{situation}

And these academic regulation clauses:
{json.dumps(clauses, indent=2)}

Determine which clauses are relevant to the situation.

Return a JSON object with:
- applicableClauses (array of clauseId strings)
- relevanceScore (0-100)
- matchReasoning

Example format:
{{
  "applicableClauses": ["clause_1", "clause_2"],
  "relevanceScore": 85,
  "matchReasoning": "Student's medical absence..."
}}

Return ONLY the JSON object."""

    try:
        response = call_bedrock(prompt, max_tokens=1024)
        return extract_json_from_response(response)
    except Exception as e:
        print(f"Matching error (using mock data): {e}")
        return {
            "applicableClauses": ["clause_1", "clause_2"],
            "relevanceScore": 85,
            "matchReasoning": "Student's medical absence qualifies for exemption under medical grounds policy.",
        }


def classify_risk_local(
    match_result: Dict[str, Any], situation: str, language: str
) -> Dict[str, Any]:
    """Classify risk tier based on match."""
    prompt = f"""Given this situation and match result:

Situation: {situation}
Applicable Clauses: {json.dumps(match_result.get('applicableClauses', []))}
Match Score: {match_result.get('relevanceScore', 0)}

Determine the RISK TIER for exam eligibility:

Return a JSON object with:
- riskTier (LOW/MEDIUM/HIGH)
- confidence (0-100)
- reasoning

Tier definitions:
- LOW: Student is clearly eligible
- MEDIUM: Student may be eligible pending verification
- HIGH: Student appears ineligible

Example format:
{{
  "riskTier": "LOW",
  "confidence": 92,
  "reasoning": "Medical documentation supports exemption..."
}}

Return ONLY the JSON object."""

    try:
        response = call_bedrock(prompt, max_tokens=1024)
        return extract_json_from_response(response)
    except Exception as e:
        print(f"Risk classification error (using mock data): {e}")
        return {
            "riskTier": "LOW",
            "confidence": 92,
            "reasoning": "Medical documentation supports exemption from attendance requirement.",
        }


def generate_explanation_local(
    situation: str,
    match_result: Dict[str, Any],
    risk_result: Dict[str, Any],
    language: str,
) -> str:
    """Generate explanation in requested language."""
    lang_prompt = ""
    if language == "kn":  # Kannada
        lang_prompt = "in Kannada language"
    elif language == "hi":  # Hindi
        lang_prompt = "in Hindi language"
    else:  # English
        lang_prompt = "in English"

    prompt = f"""Generate a clear explanation {lang_prompt} for this decision:

Student Situation: {situation}
Risk Assessment: {risk_result.get('riskTier')} (Confidence: {risk_result.get('confidence')}%)
Reasoning: {risk_result.get('reasoning')}

Write a concise, supportive explanation that:
1. Confirms the decision
2. References the applicable policy
3. Explains next steps if needed

Keep it under 200 words."""

    try:
        response = call_bedrock(prompt, max_tokens=300)
        return response.strip()
    except Exception as e:
        print(f"Explanation generation error (using mock data): {e}")
        if language == "kn":
            return "ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ದಾಖಲೆಗಳ ಆಧಾರದ ಮೇಲೆ, ನೀವು ಪರೀಕ್ಷೆಗೆ ಯೋಗ್ಯರಿದ್ದೀರಿ. ವೈದ್ಯಕೀಯ ಕಾರಣಗಳಿಂದಾಗಿ ಸಾಕಷ್ಟು ಗೈರುಹಾಜರಿ ವಿನಾಯಿತಿ ನೀಡಲಾಗಿದೆ."
        else:
            return "Based on your medical documentation, you are eligible to take the exam. Medical grounds are recognized for absence exemption under the college attendance policy."


if __name__ == "__main__":
    print("=" * 80)
    print("ROOMIEOPS LOCAL DEVELOPMENT SERVER")
    print("=" * 80)
    print("\nEndpoints:")
    print("  GET  /health                              - Health check")
    print("  POST /api/v1/households                   - Household operations")
    print("  POST /api/v1/expenses                     - Expense management")
    print("  POST /api/v1/chores                       - Chore management")
    print("  POST /api/v1/payments                     - Payment processing")
    print("  POST /api/v1/copilot                      - AI agent requests")
    print("\nStarting server on http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
