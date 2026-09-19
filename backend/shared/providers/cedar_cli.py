"""Cedar CLI integration for authorization decisions.

Invokes the actual Cedar Policy CLI executable to perform authorization checks.
No Python membership logic — Cedar is the source of truth.
"""

import json
import subprocess
import logging
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class CedarCLIError(Exception):
    """Raised when Cedar CLI invocation fails."""
    pass


class CedarCLIAdapter:
    """Adapter for invoking real Cedar Policy CLI (cedar.exe)."""
    
    # Windows path to Cedar CLI executable
    # Can be overridden via CEDAR_CLI_PATH environment variable
    DEFAULT_CEDAR_PATH = r"C:\Users\user\Downloads\cedar-4.13.0\cedar-4.13.0\target\release\cedar.exe"
    
    def __init__(self, cedar_path: Optional[str] = None, schema_dir: Optional[str] = None):
        """Initialize Cedar CLI adapter.
        
        Args:
            cedar_path: Path to cedar.exe. If None, uses DEFAULT_CEDAR_PATH or CEDAR_CLI_PATH env var.
            schema_dir: Directory containing Cedar policy/schema files. Defaults to backend/cedar/.
        """
        # Determine cedar executable path
        if cedar_path:
            self.cedar_path = cedar_path
        else:
            self.cedar_path = os.environ.get("CEDAR_CLI_PATH", self.DEFAULT_CEDAR_PATH)
        
        # Validate cedar executable exists
        if not Path(self.cedar_path).exists():
            raise CedarCLIError(f"Cedar CLI executable not found at: {self.cedar_path}")
        
        # Determine schema directory
        if schema_dir:
            self.schema_dir = schema_dir
        else:
            # Assume this file is at backend/shared/providers/cedar_cli.py
            # Schema is at backend/cedar/
            backend_dir = Path(__file__).parent.parent.parent  # Go up to backend/
            self.schema_dir = str(backend_dir / "cedar")
        
        if not Path(self.schema_dir).exists():
            raise CedarCLIError(f"Cedar schema directory not found at: {self.schema_dir}")
        
        self.schema_file = Path(self.schema_dir) / "roomieops.cedarschema"
        self.policy_file = Path(self.schema_dir) / "roomieops.cedar"
        
        logger.info(f"Cedar CLI adapter initialized: {self.cedar_path}")
        logger.info(f"Schema directory: {self.schema_dir}")
    
    def authorize(
        self,
        principal: str,
        action: str,
        resource: str,
        entities: List[Dict[str, Any]]
    ) -> bool:
        """Check authorization using real Cedar CLI.
        
        Args:
            principal: Principal UID (e.g., "User::kunal")
            action: Action name (e.g., "read_household")
            resource: Resource UID (e.g., "Household::household-a")
            entities: List of Cedar entities in array format
            
        Returns:
            True if ALLOW, False if DENY
            
        Raises:
            CedarCLIError if invocation fails
        """
        try:
            # Build request JSON in memory
            request = {
                "principal": principal,
                "action": action,
                "resource": resource,
                "context": {}
            }
            
            # Write request to temp file
            request_file = Path(self.schema_dir) / "_temp_request.json"
            entities_file = Path(self.schema_dir) / "_temp_entities.json"
            
            try:
                with open(request_file, "w") as f:
                    json.dump(request, f)
                
                with open(entities_file, "w") as f:
                    json.dump(entities, f)
                
                logger.debug(f"Request: {json.dumps(request)}")
                logger.debug(f"Entities: {json.dumps(entities)}")
                
                # Invoke cedar.exe authorize
                cmd = [
                    self.cedar_path,
                    "authorize",
                    "--schema", str(self.schema_file),
                    "--schema-format", "cedar",
                    "--policies", str(self.policy_file),
                    "--entities", str(entities_file),
                    "--request-json", str(request_file)
                ]
                
                logger.debug(f"Cedar command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Check result
                if "ALLOW" in result.stdout:
                    logger.info(f"Cedar ALLOW: {principal} {action} {resource}")
                    return True
                elif "DENY" in result.stdout:
                    logger.info(f"Cedar DENY: {principal} {action} {resource}")
                    return False
                else:
                    # Unexpected output
                    logger.error(f"Cedar unexpected output: {result.stdout}")
                    logger.error(f"Cedar stderr: {result.stderr}")
                    raise CedarCLIError(f"Cedar returned unexpected output: {result.stdout}")
            
            finally:
                # Clean up temp files
                try:
                    request_file.unlink(missing_ok=True)
                    entities_file.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp files: {e}")
        
        except subprocess.TimeoutExpired:
            raise CedarCLIError("Cedar CLI authorization check timed out")
        except Exception as e:
            logger.error(f"Cedar CLI error: {e}")
            raise CedarCLIError(f"Cedar authorization failed: {e}")
    
    def validate_policy(self) -> bool:
        """Validate policy against schema.
        
        Returns:
            True if valid, False if validation fails
            
        Raises:
            CedarCLIError if validation cannot be performed
        """
        try:
            cmd = [
                self.cedar_path,
                "validate",
                "--schema", str(self.schema_file),
                "--schema-format", "cedar",
                "--policies", str(self.policy_file)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "validation passed" in result.stdout:
                logger.info("Cedar policy validation passed")
                return True
            else:
                logger.error(f"Cedar policy validation failed: {result.stdout}")
                return False
        
        except subprocess.TimeoutExpired:
            raise CedarCLIError("Cedar policy validation timed out")
        except Exception as e:
            logger.error(f"Cedar validation error: {e}")
            raise CedarCLIError(f"Cedar policy validation failed: {e}")
