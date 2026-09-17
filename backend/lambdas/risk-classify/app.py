import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Stage 3: Classify risk based on matches.
    
    Input:
    {
        "documentId": "d-001",
        "matches": [...],
        "situation": "..."
    }
    
    Output:
    {
        "riskTier": "red",
        "clauseId": "c1",
        "reasoning": "Stated attendance (72%) is below the 75% threshold...",
        "confidence": "high"
    }
    """
    try:
        logger.info(f"Risk classification started for document: {event.get('documentId')}")
        
        # TODO: Implement risk classification
        # 1. Call Bedrock with risk classification prompt
        # 2. Validate risk tier (green|yellow|red)
        # 3. Validate confidence (high|medium|low)
        # 4. Return classification
        
        # Placeholder response
        risk_result = {
            "riskTier": "red",
            "clauseId": "c1",
            "reasoning": "Stated attendance (72%) is below the 75% threshold in clause 4.2.",
            "confidence": "high"
        }
        
        response = {
            "statusCode": 200,
            "body": risk_result
        }
        
        logger.info(f"Risk classification completed: {risk_result['riskTier']}")
        return response
        
    except Exception as e:
        logger.error(f"Risk classification failed: {str(e)}")
        raise
