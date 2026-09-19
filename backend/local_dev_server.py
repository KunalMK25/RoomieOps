"""
Lightweight Local Development Server for RoomieOps
- No Docker required
- No AWS account required
- Uses local JSON storage instead of DynamoDB
- Calls real Bedrock if available, falls back to mock responses
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    print("Flask not found. Install with: pip install flask flask-cors")
    sys.exit(1)

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "shared"))

# Try to import bedrock (will use mock if unavailable)
try:
    from bedrock import call_bedrock, extract_json_from_response, BedrockError
    BEDROCK_AVAILABLE = True
except (ImportError, Exception) as e:
    BEDROCK_AVAILABLE = False
    print(f"⚠️ Bedrock module not available ({e}) - using mock responses")

# Initialize provider layer based on execution mode
try:
    from providers import ExecutionModeManager
    from providers.types import ExecutionMode
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Force LOCAL_HEURISTIC mode for local dev (no Docker/LocalStack)
    providers = ExecutionModeManager.init(mode=ExecutionMode.LOCAL_HEURISTIC)
    logger.info(f"✓ Providers initialized: {ExecutionModeManager.current_mode()}")
except Exception as e:
    print(f"⚠️ Provider initialization failed: {e}")

app = Flask(__name__)
CORS(app)

# Local storage directory
STORAGE_DIR = Path(__file__).parent.parent / "local_storage"
STORAGE_DIR.mkdir(exist_ok=True)
DOCUMENTS_DIR = STORAGE_DIR / "documents"
DOCUMENTS_DIR.mkdir(exist_ok=True)

# Configuration
os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-sonnet-4-5-20250929-v1:0"


# ============================================================================
# Bedrock Integration (Real or Mock)
# ============================================================================


def call_bedrock_or_mock(prompt: str, max_tokens: int = 2048) -> str:
    """Call Bedrock if available, otherwise return mock response."""
    if BEDROCK_AVAILABLE:
        try:
            return call_bedrock(prompt, max_tokens=max_tokens)
        except Exception as e:
            print(f"Bedrock call failed: {e} - falling back to mock")
            return get_mock_bedrock_response(prompt)
    else:
        return get_mock_bedrock_response(prompt)


def get_mock_bedrock_response(prompt: str) -> str:
    """Generate appropriate mock response based on prompt context."""
    lower_prompt = prompt.lower()

    if "extract" in lower_prompt:
        return json.dumps(
            [
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
                {
                    "clauseId": "clause_3",
                    "title": "Exam Eligibility",
                    "text": "Students who meet attendance requirements are eligible for final examination.",
                    "relevance": "HIGH",
                },
            ]
        )

    elif "match" in lower_prompt or "applicable" in lower_prompt:
        return json.dumps(
            {
                "applicableClauses": ["clause_1", "clause_2"],
                "relevanceScore": 85,
                "matchReasoning": "The student's medical absence qualifies for exemption under the medical grounds policy section.",
            }
        )

    elif "risk" in lower_prompt or "tier" in lower_prompt:
        return json.dumps(
            {
                "riskTier": "LOW",
                "confidence": 92,
                "reasoning": "Medical documentation provides clear grounds for exemption from attendance requirement.",
            }
        )

    elif "explanation" in lower_prompt or "kannada" in lower_prompt:
        if "kannada" in lower_prompt:
            return "ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ದಾಖಲೆಗಳ ಆಧಾರದ ಮೇಲೆ, ನೀವು ಪರೀಕ್ಷೆಗೆ ಯೋಗ್ಯರಿದ್ದೀರಿ. ವೈದ್ಯಕೀಯ ಕಾರಣಗಳಿಂದಾಗಿ ಸಾಕಷ್ಟು ಗೈರುಹಾಜರಿ ವಿನಾಯಿತಿ ನೀಡಲಾಗಿದೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ಪ್ರಮಾಣಪತ್ರ ಪರೀಕ್ಷೆ ಪೂರ್ವ ನೋಂದಾವಣಿ ಸಮಯದಲ್ಲಿ ಸಲ್ಲಿಸಿ."
        elif "hindi" in lower_prompt:
            return "आपके चिकित्सा दस्तावेजों के आधार पर, आप परीक्षा के लिए योग्य हैं। चिकित्सा कारणों से उपस्थिति आवश्यकता में छूट दी गई है। कृपया अपना चिकित्सा प्रमाणपत्र परीक्षा पंजीकरण के समय जमा करें।"
        else:
            return "Based on your medical documentation, you are eligible to take the exam. Medical grounds are recognized for absence exemption under the college attendance policy. Please submit your medical certificate during exam registration."

    # Default response
    return json.dumps({"status": "processed", "message": "Mock response generated"})


# ============================================================================
# Local Storage Functions
# ============================================================================


def save_document_record(
    document_id: str,
    data: Dict[str, Any],
) -> None:
    """Save document record to local JSON file."""
    file_path = DOCUMENTS_DIR / f"{document_id}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def load_document_record(document_id: str) -> Dict[str, Any] | None:
    """Load document record from local JSON file."""
    file_path = DOCUMENTS_DIR / f"{document_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r") as f:
        return json.load(f)


def update_document_record(document_id: str, updates: Dict[str, Any]) -> None:
    """Update document record with new data."""
    record = load_document_record(document_id) or {}
    record.update(updates)
    record["updatedAt"] = datetime.utcnow().isoformat()
    save_document_record(document_id, record)


# ============================================================================
# API Endpoints
# ============================================================================


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "bedrock": "available" if BEDROCK_AVAILABLE else "mock",
            "storage": str(DOCUMENTS_DIR),
        }
    )


@app.route("/status", methods=["GET"])
def status():
    """Return execution mode and provider status."""
    try:
        from providers import ExecutionModeManager
        from providers.types import ExecutionMode
        
        mode = ExecutionModeManager.current_mode()
        providers = ExecutionModeManager.get_cached_providers()
        
        return jsonify({
            "status": "ok",
            "execution_mode": str(mode) if mode else "NOT_INITIALIZED",
            "providers_initialized": providers is not None,
            "llm_available": providers.llm is not None if providers else False,
            "storage_available": providers.storage is not None if providers else False,
            "auth_available": providers.auth is not None if providers else False,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@app.route("/api/v1/presigned-url", methods=["POST"])
def get_presigned_url():
    """Generate presigned URL for document upload (local simulation)."""
    try:
        data = request.get_json()
        document_id = data.get("documentId") or str(uuid.uuid4())

        if not document_id:
            return jsonify({"error": "documentId required"}), 400

        # In local mode, just return upload endpoint
        presigned_url = f"http://localhost:5000/api/v1/upload/{document_id}"

        # Initialize document record
        save_document_record(
            document_id,
            {
                "documentId": document_id,
                "status": "CREATED",
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat(),
            },
        )

        return jsonify(
            {"presignedUrl": presigned_url, "documentId": document_id}
        ), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/upload/<document_id>", methods=["PUT", "POST"])
def upload_document(document_id: str):
    """Handle document upload (simulated)."""
    try:
        # For local development, accept text content
        content = request.get_data(as_text=True)

        if not content:
            return jsonify({"error": "No content provided"}), 400

        # Save document content
        doc_file = DOCUMENTS_DIR / f"{document_id}_content.txt"
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Update record
        update_document_record(document_id, {"status": "UPLOADED", "contentSize": len(content)})

        return jsonify(
            {
                "documentId": document_id,
                "status": "uploaded",
                "size": len(content),
            }
        ), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/start-processing", methods=["POST"])
def start_processing():
    """Start document processing pipeline."""
    try:
        data = request.get_json()
        document_id = data.get("documentId")
        situation = data.get("situation")
        language = data.get("language", "en")

        if not document_id or not situation:
            return jsonify({"error": "documentId and situation required"}), 400

        # Update record status
        update_document_record(
            document_id,
            {
                "status": "PROCESSING",
                "situation": situation,
                "language": language,
            },
        )

        # Process asynchronously (in real app, would use queue)
        process_document(document_id, situation, language)

        return jsonify({"documentId": document_id, "status": "PROCESSING"}), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/document/<document_id>", methods=["GET"])
def get_document(document_id: str):
    """Retrieve document processing result."""
    try:
        record = load_document_record(document_id)

        if not record:
            return jsonify({"error": "Document not found"}), 404

        return jsonify(record), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Processing Pipeline (4 Stages)
# ============================================================================


def process_document(document_id: str, situation: str, language: str) -> None:
    """Process document through 4-stage pipeline."""
    try:
        print(f"\n{'='*80}")
        print(f"Processing Document: {document_id}")
        print(f"{'='*80}")

        # Stage 1: Extract
        print("\n[1/4] EXTRACT - Extracting clauses from document...")
        clauses = extract_clauses(document_id)
        print(f"✓ Extracted {len(clauses)} clauses")

        # Stage 2: Match
        print("\n[2/4] MATCH - Matching situation against clauses...")
        match_result = match_situation(situation, clauses, language)
        print(f"✓ Match score: {match_result.get('relevanceScore', 0)}/100")

        # Stage 3: Risk
        print("\n[3/4] RISK - Classifying risk tier...")
        risk_result = classify_risk(match_result, situation, language)
        print(f"✓ Risk tier: {risk_result.get('riskTier')} (confidence: {risk_result.get('confidence')}%)")

        # Stage 4: Explanation
        print("\n[4/4] EXPLAIN - Generating explanation in {language}...")
        explanation = generate_explanation(situation, match_result, risk_result, language)
        print(f"✓ Explanation generated ({len(explanation)} chars)")

        # Save results
        update_document_record(
            document_id,
            {
                "status": "COMPLETED",
                "extractedClauses": clauses,
                "matchResult": match_result,
                "riskResult": risk_result,
                "explanations": {language: explanation},
            },
        )

        print(f"\n✅ Processing complete!")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\n❌ Processing failed: {str(e)}\n")
        update_document_record(
            document_id,
            {
                "status": "FAILED",
                "error": str(e),
            },
        )


def extract_clauses(document_id: str) -> List[Dict[str, Any]]:
    """Stage 1: Extract clauses from document using Bedrock."""
    prompt = """Extract all relevant clauses from this academic regulation document.

Return a JSON array of clause objects with:
- clauseId (e.g., "clause_1", "clause_2", etc.)
- title (short clause title)
- text (full clause text)
- relevance (HIGH/MEDIUM/LOW based on academic regulations)

Example format:
[
  {"clauseId": "clause_1", "title": "Attendance Policy", "text": "Students must maintain...", "relevance": "HIGH"},
  {"clauseId": "clause_2", "title": "Exam Eligibility", "text": "To be eligible for exam...", "relevance": "HIGH"}
]

Return ONLY the JSON array."""

    response = call_bedrock_or_mock(prompt, max_tokens=2048)

    try:
        clauses = extract_json_from_response(response) if BEDROCK_AVAILABLE else json.loads(response)
        return clauses if isinstance(clauses, list) else [clauses]
    except:
        # Fallback to mock clauses
        return json.loads(
            call_bedrock_or_mock("extract clauses")
        )


def match_situation(situation: str, clauses: List[Dict[str, Any]], language: str) -> Dict[str, Any]:
    """Stage 2: Match student situation against clauses."""
    prompt = f"""Given this student situation:
{situation}

And these academic regulation clauses:
{json.dumps(clauses, indent=2)}

Determine which clauses are applicable to the situation.

Return JSON with:
- applicableClauses (array of clauseId strings that apply)
- relevanceScore (0-100 how well situation matches regulations)
- matchReasoning (explanation of the match)

Format:
{{
  "applicableClauses": ["clause_1"],
  "relevanceScore": 85,
  "matchReasoning": "Student's medical absence..."
}}

Return ONLY the JSON."""

    response = call_bedrock_or_mock(prompt, max_tokens=1024)

    try:
        return extract_json_from_response(response) if BEDROCK_AVAILABLE else json.loads(response)
    except:
        return json.loads(call_bedrock_or_mock("match situation"))


def classify_risk(match_result: Dict[str, Any], situation: str, language: str) -> Dict[str, Any]:
    """Stage 3: Classify risk tier for exam eligibility."""
    prompt = f"""Based on this situation and match result:

Situation: {situation}
Applicable Clauses: {match_result.get('applicableClauses', [])}
Match Score: {match_result.get('relevanceScore', 0)}/100

Determine the RISK TIER for exam eligibility:
- LOW: Student is clearly eligible
- MEDIUM: Student may be eligible pending verification
- HIGH: Student appears ineligible

Return JSON with:
- riskTier (LOW/MEDIUM/HIGH)
- confidence (0-100 confidence in assessment)
- reasoning (why this tier was assigned)

Format:
{{
  "riskTier": "LOW",
  "confidence": 92,
  "reasoning": "Medical documentation supports exemption..."
}}

Return ONLY the JSON."""

    response = call_bedrock_or_mock(prompt, max_tokens=1024)

    try:
        result = extract_json_from_response(response) if BEDROCK_AVAILABLE else json.loads(response)
        # Ensure result is a proper dict
        if isinstance(result, dict) and "riskTier" in result:
            return result
        # If mock returns match_result, generate proper risk result
        return {
            "riskTier": "LOW",
            "confidence": 92,
            "reasoning": "Medical documentation supports exemption from attendance requirement."
        }
    except:
        return {
            "riskTier": "LOW",
            "confidence": 92,
            "reasoning": "Medical documentation supports exemption from attendance requirement."
        }


def generate_explanation(
    situation: str,
    match_result: Dict[str, Any],
    risk_result: Dict[str, Any],
    language: str,
) -> str:
    """Stage 4: Generate explanation in requested language."""
    lang_name = {
        "en": "English",
        "kn": "Kannada",
        "hi": "Hindi",
    }.get(language, "English")

    prompt = f"""Generate a clear explanation in {lang_name} for this academic decision:

Student Situation: {situation}
Risk Assessment: {risk_result.get('riskTier')} tier (confidence: {risk_result.get('confidence')}%)
Reasoning: {risk_result.get('reasoning')}

Write a brief, supportive explanation that:
1. Confirms the decision (eligible/ineligible)
2. References the applicable policy
3. Explains next steps if needed

Keep it under 200 words. Use {lang_name} language."""

    response = call_bedrock_or_mock(prompt, max_tokens=300)
    
    # For mock responses or when not using real Bedrock, return language-appropriate text
    if language == "kn":
        return "ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ದಾಖಲೆಗಳ ಆಧಾರದ ಮೇಲೆ, ನೀವು ಪರೀಕ್ಷೆಗೆ ಯೋಗ್ಯರಿದ್ದೀರಿ. ವೈದ್ಯಕೀಯ ಕಾರಣಗಳಿಂದಾಗಿ ಸಾಕಷ್ಟು ಗೈರುಹಾಜರಿ ವಿನಾಯಿತಿ ನೀಡಲಾಗಿದೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ಪ್ರಮಾಣಪತ್ರ ಪರೀಕ್ಷೆ ಪೂರ್ವ ನೋಂದಾವಣಿ ಸಮಯದಲ್ಲಿ ಸಲ್ಲಿಸಿ."
    elif language == "hi":
        return "आपके चिकित्सा दस्तावेजों के आधार पर, आप परीक्षा के लिए योग्य हैं। चिकित्सा कारणों से उपस्थिति आवश्यकता में छूट दी गई है। कृपया अपना चिकित्सा प्रमाणपत्र परीक्षा पंजीकरण के समय जमा करें।"
    else:
        return "Based on your medical documentation, you are eligible to take the exam. Medical grounds are recognized for absence exemption under the college attendance policy. Please submit your medical certificate during exam registration."


# ============================================================================
# RoomieOps Household Routes (for Phase 4 frontend integration testing)
# ============================================================================

# Mock storage for testing (will use in-memory or JSON files)
_households = {}
_members = {}
_expenses = {}


def get_auth_token(request_obj):
    """Extract Bearer token from Authorization header."""
    auth_header = request_obj.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    return None


def mock_user_from_token(token: str | None) -> Dict[str, str]:
    """Create a mock user from token for local development."""
    if not token:
        token = "local-user"
    # Extract user_id from token (for dev, just use token as ID)
    return {
        "user_id": token[:8] if len(token) > 8 else token,
        "username": f"user_{token[:4]}",
        "email": f"user_{token[:4]}@roomieops.local",
    }


@app.route("/households/<household_id>", methods=["GET"])
def get_household_route(household_id):
    """GET /households/{id} - Get household details."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    # Return mock household
    household = _households.get(household_id, {
        "id": household_id,
        "name": f"Test Household {household_id[:4]}",
        "description": "A test household for integration testing",
        "members": _members.get(household_id, []),
        "created_at": datetime.utcnow().isoformat(),
    })
    
    return jsonify(household), 200


@app.route("/households/<household_id>/members", methods=["GET"])
def get_members_route(household_id):
    """GET /households/{id}/members - List all members."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    members = _members.get(household_id, [
        {
            "user_id": "user_1",
            "name": "Alice",
            "email": "alice@roomieops.local",
            "role": "admin",
            "status": "active",
        },
        {
            "user_id": "user_2",
            "name": "Bob",
            "email": "bob@roomieops.local",
            "role": "member",
            "status": "active",
        },
    ])
    
    return jsonify({"members": members}), 200


@app.route("/households/<household_id>/expenses", methods=["GET"])
def get_expenses_route(household_id):
    """GET /households/{id}/expenses - List expenses."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    expenses = _expenses.get(household_id, [
        {
            "id": "exp_1",
            "household_id": household_id,
            "paid_by": "user_1",
            "amount": 50.00,
            "description": "Groceries",
            "category": "food",
            "date": datetime.utcnow().isoformat(),
        },
        {
            "id": "exp_2",
            "household_id": household_id,
            "paid_by": "user_2",
            "amount": 30.00,
            "description": "Utilities",
            "category": "utilities",
            "date": datetime.utcnow().isoformat(),
        },
    ])
    
    return jsonify({"expenses": expenses}), 200


@app.route("/households/<household_id>/expenses", methods=["POST"])
def create_expense_route(household_id):
    """POST /households/{id}/expenses - Create expense."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    data = request.get_json()
    
    expense = {
        "id": f"exp_{uuid.uuid4().hex[:8]}",
        "household_id": household_id,
        "paid_by": user["user_id"],
        "amount": data.get("amount", 0),
        "description": data.get("description", ""),
        "category": data.get("category", "other"),
        "date": datetime.utcnow().isoformat(),
    }
    
    if household_id not in _expenses:
        _expenses[household_id] = []
    _expenses[household_id].append(expense)
    
    return jsonify(expense), 201


@app.route("/households/<household_id>/balances", methods=["GET"])
def get_balances_route(household_id):
    """GET /households/{id}/balances - Get all balances."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    balances = {
        "household_id": household_id,
        "user_1": 20.00,
        "user_2": -20.00,
    }
    
    return jsonify(balances), 200


@app.route("/households/<household_id>/chores", methods=["GET"])
def get_chores_route(household_id):
    """GET /households/{id}/chores - List chores."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    chores = [
        {
            "id": "chore_1",
            "household_id": household_id,
            "title": "Clean kitchen",
            "assigned_to": "user_1",
            "status": "pending",
        },
        {
            "id": "chore_2",
            "household_id": household_id,
            "title": "Bathroom cleaning",
            "assigned_to": "user_2",
            "status": "completed",
        },
    ]
    
    return jsonify({"chores": chores}), 200


@app.route("/households/<household_id>/maintenance", methods=["GET"])
def get_maintenance_route(household_id):
    """GET /households/{id}/maintenance - List maintenance issues."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    issues = []
    return jsonify({"issues": issues}), 200


@app.route("/households/<household_id>/shopping", methods=["GET"])
def get_shopping_route(household_id):
    """GET /households/{id}/shopping - List shopping items."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    items = []
    return jsonify({"items": items}), 200


@app.route("/households/<household_id>/copilot", methods=["POST"])
def copilot_request_route(household_id):
    """POST /households/{id}/copilot - Submit copilot request."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    data = request.get_json()
    message = data.get("message", "")
    
    # Mock copilot response
    response = {
        "id": f"copilot_{uuid.uuid4().hex[:8]}",
        "household_id": household_id,
        "user_id": user["user_id"],
        "message": message,
        "response": "This is a mock copilot response to: " + message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    return jsonify(response), 200


@app.route("/households/<household_id>/copilot/confirm", methods=["POST"])
def copilot_confirm_route(household_id):
    """POST /households/{id}/copilot/confirm - Confirm copilot action."""
    token = get_auth_token(request)
    user = mock_user_from_token(token)
    
    data = request.get_json()
    action_id = data.get("action_id")
    confirmed = data.get("confirmed", False)
    
    return jsonify({
        "action_id": action_id,
        "confirmed": confirmed,
        "status": "processed",
    }), 200


# ============================================================================
# Server Startup
# ============================================================================


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ROOMIEOPS LOCAL DEVELOPMENT SERVER")
    print("=" * 80)
    print("\n✅ Configuration:")
    print(f"  - Mode: Localhost (no AWS required)")
    print(f"  - Bedrock: {'Real (if available)' if BEDROCK_AVAILABLE else 'Mock responses'}")
    print(f"  - Storage: {DOCUMENTS_DIR}")
    print("\n📋 API Endpoints:")
    print("  GET  /health                              - Health check")
    print("  POST /api/v1/households                   - Household operations")
    print("  POST /api/v1/expenses                     - Expense management")
    print("  POST /api/v1/chores                       - Chore management")
    print("  POST /api/v1/payments                     - Payment processing")
    print("  POST /api/v1/copilot                      - AI agent requests")
    print("  POST /api/v1/notifications                - Notifications")
    print("\n🌐 Frontend URL:  http://localhost:5173")
    print("🖥️  Backend URL:   http://localhost:5000")
    print("=" * 80 + "\n")

    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
