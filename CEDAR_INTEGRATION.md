# Cedar Authorization Integration for BUILD_IT_STRANDS

This document explains how Cedar is integrated into RoomieOps BUILD_IT_STRANDS runtime.

## Overview

Cedar provides **policy-based authorization** for RoomieOps. It is **NOT** an authentication provider - Cedar only handles permissions/authorization.

**Important distinction:**
- **Authentication** (who you are): Handled by `AuthProvider` (CedarAuthProvider or LocalAuthProvider)
- **Authorization** (what you can do): Handled by `AuthorizationProvider` (CedarAuthorizationProvider)

Both are separate and independent.

## Architecture

### Authentication Layer

#### CedarAuthProvider
Extracts authenticated user from JWT tokens in `Authorization: Bearer <token>` header.

```python
from shared.providers.auth import CedarAuthProvider

provider = CedarAuthProvider(endpoint="http://localhost:8180")
event = {"headers": {"Authorization": "Bearer eyJhbGc..."}}
user = provider.extract_user(event)
# Returns: AuthenticatedUser(user_id="...", username="...", groups=[...])
```

#### LocalAuthProvider (Alternative)
For local development, extracts user from simple HTTP headers.

```python
from shared.providers.auth import LocalAuthProvider

provider = LocalAuthProvider()
event = {"headers": {
    "x-user-id": "user-1",
    "x-user-name": "Alice",
    "x-user-groups": "member,admin"
}}
user = provider.extract_user(event)
# Returns: AuthenticatedUser(user_id="user-1", ...)
```

### Authorization Layer

#### CedarAuthorizationProvider
Checks permissions by querying Cedar Policy Decision Point (PDP).

```python
from shared.providers.authorization import CedarAuthorizationProvider

provider = CedarAuthorizationProvider(endpoint="http://localhost:8180")
result = provider.check_permission(
    user=user,
    action="read",
    resource="household:hh-123"
)
# Returns: PermissionCheckResult(permitted=True/False, reason="...")
```

**Request format sent to Cedar:**
```json
{
  "principal": {
    "type": "User",
    "id": "user-1"
  },
  "action": {
    "type": "Action",
    "id": "read"
  },
  "resource": {
    "type": "Resource",
    "id": "household:hh-123"
  },
  "context": {}
}
```

**Response from Cedar:**
```json
{
  "allowed": true,
  "reason": "User is household member"
}
```

## Provider Selection in ExecutionModeManager

Based on execution mode:

### BUILD_IT_STRANDS
```python
ExecutionMode.BUILD_IT_STRANDS → {
    "auth": CedarAuthProvider(endpoint="http://localhost:8180"),
    "authorization": CedarAuthorizationProvider(endpoint="http://localhost:8180"),
    ...
}
```

Configuration via environment variables:
```bash
export CEDAR_ENDPOINT=http://localhost:8180
export EXECUTION_MODE=BUILD_IT_STRANDS
```

### SHIP_IT_BEDROCK
```python
ExecutionMode.SHIP_IT_BEDROCK → {
    "auth": CognitoAuthProvider(),
    "authorization": SimpleAuthorizationProvider(storage),
    ...
}
```

Uses AWS Cognito for authentication and DynamoDB-based membership checks for authorization.

### LOCAL_HEURISTIC
```python
ExecutionMode.LOCAL_HEURISTIC → {
    "auth": LocalAuthProvider(),
    "authorization": LocalAuthorizationProvider(),
    ...
}
```

Development mode - allows all permissions when user is present.

## Failure Modes

### Cedar PDP Unavailable
If Cedar endpoint is unreachable:
- **Authentication** continues to work (JWT is still validated)
- **Authorization** fails **closed** - all permissions denied
- No fallback to less restrictive policy

This is intentional: it's safer to deny than to allow when policy engine unavailable.

```python
# If Cedar endpoint offline:
result = authz_provider.check_permission(user, "read", "household:hh-123")
# Returns: PermissionCheckResult(
#     permitted=False,
#     reason="Authorization check failed: Connection refused"
# )
```

## Usage in RoomieOps APIs

Typical request handling:

```python
@app.route("/households/<household_id>/balances")
def get_balances(household_id):
    # 1. Extract authenticated user
    user = auth_provider.extract_user(request_event)
    if not user:
        return {"error": "Not authenticated"}, 401
    
    # 2. Check authorization
    perm = authz_provider.check_permission(
        user=user,
        action="read",
        resource=f"household:{household_id}"
    )
    if not perm.permitted:
        return {"error": perm.reason}, 403
    
    # 3. Proceed with operation
    return get_household_balances(household_id)
```

## Cedar Policy Examples

Cedar policies define who can do what. Example policies for RoomieOps:

### Policy: Household members can read balances
```cedar
permit (
    principal in Role::"member",
    action == Action::"read",
    resource == Household::"hh-123"
);
```

### Policy: Only admins can record payments
```cedar
permit (
    principal has role && principal.role == "admin",
    action == Action::"record_payment",
    resource == Household::?
);
```

### Policy: Deny payments to non-members
```cedar
forbid (
    principal not in Household::?members,
    action == Action::"record_payment",
    resource
);
```

## Local Development Setup

### With JWT authentication (like production)
```bash
# 1. Start Cedar PDP
docker run -p 8180:8180 cedar-pdp:latest

# 2. Load policies into Cedar
curl -X POST http://localhost:8180/policies -d @policies.cedar

# 3. Start RoomieOps with Cedar auth
export EXECUTION_MODE=BUILD_IT_STRANDS
export CEDAR_ENDPOINT=http://localhost:8180
python backend/local_dev_server.py

# 4. Make requests with JWT
curl -H "Authorization: Bearer $(generate_jwt)" http://localhost:5000/...
```

### With local header authentication (dev mode)
```bash
# 1. Start RoomieOps with local auth
export EXECUTION_MODE=BUILD_IT_STRANDS
python backend/local_dev_server.py

# 2. Make requests with dev headers (no Cedar needed)
curl -H "x-user-id: user-1" http://localhost:5000/...
```

Note: Even with local auth headers, Cedar authorization will be checked (and fail if Cedar unavailable). To skip authorization checks entirely, use LOCAL_HEURISTIC mode:

```bash
export EXECUTION_MODE=LOCAL_HEURISTIC
python backend/local_dev_server.py
```

## Testing

Run Cedar integration tests:

```bash
python backend/scripts/test_cedar_integration.py
```

Tests verify:
- ✓ JWT extraction from Bearer tokens
- ✓ Missing header handling
- ✓ Authorization provider initialization
- ✓ Graceful failure when Cedar unavailable
- ✓ Auth and authorization separation
- ✓ Local auth with dev headers
- ✓ Permission check results

## Resource Types and Actions

RoomieOps uses these Cedar resource types and actions:

### Resource Types
- `Household`: A household (e.g., "hh-123")
- `Member`: A household member
- `Expense`: A shared expense record
- `Chore`: A household chore assignment
- `MaintenanceIssue`: A maintenance issue report

### Actions
- `read`: Retrieve data
- `write`: Modify or create data
- `record_payment`: Record payment transactions
- `assign_chore`: Reassign chores
- `admin`: Administrative operations

## Future Enhancements

- [ ] Policy versioning and rollback
- [ ] Audit logging of authorization decisions
- [ ] Fine-grained resource-level policies
- [ ] Group-based permissions
- [ ] Time-based access control
- [ ] Integration with OpenSearch for advanced queries

## References

- [Cedar Documentation](https://cedar-policy.github.io)
- [BUILD_IT_SETUP.md](BUILD_IT_SETUP.md) - Local development guide
- [ROOMIEOPS_BUILD_SPEC.md](ROOMIEOPS_BUILD_SPEC.md) §40 - Cedar specification
