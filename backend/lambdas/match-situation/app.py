import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Stage 2: Match user's situation against extracted clauses.
    
    Input:
    {
        "documentId": "d-001",
        "clauses": [...],
        "situation": "I have 72% attendance and missed classes because of a medical reason."
    }
    
    Output:
    {
        "matches": [
            {
                "clauseId": "c1",
                "relevance": "direct",
                "userFact": "72% attendance"
            }
        ]
    }
    """
    try:
        logger.info(f"Situation matching started for document: {event.get('documentId')}")
        
        # TODO: Implement situational matching
        # 1. Call Bedrock with matching prompt
        # 2. Pass clauses and situation
        # 3. Validate clause IDs against extracted clauses
        # 4. Return matching results
        
        # Placeholder response
        matches = [
            {
                "clauseId": "c1",
                "relevance": "direct",
                "userFact": "72% attendance"
            }
        ]
        
        response = {
            "statusCode": 200,
            "body": {
                "matches": matches
            }
        }
        
        logger.info(f"Situation matching completed. Found {len(matches)} matches.")
        return response
        
    except Exception as e:
        logger.error(f"Situation matching failed: {str(e)}")
        raise
