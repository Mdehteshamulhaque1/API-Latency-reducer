"""
JWT Token Type Validation - Implementation Guide

ISSUE FIXED:
- AuthMiddleware accepted any valid JWT (access or refresh tokens)
- Refresh tokens could be used to access protected endpoints
- No token type validation was performed

SOLUTION IMPLEMENTED:
1. Access tokens now include type="access" claim
2. Refresh tokens include type="refresh" claim (already existed)
3. AuthMiddleware validates token type after decoding
4. Fixed verify_token_type() logic
5. Protected endpoints only accept access tokens
6. Refresh endpoint only accepts refresh tokens
"""

# ============================================================================
# CHANGE SUMMARY
# ============================================================================

## File 1: backend/app/core/security.py
### Change 1: Add type claim to access tokens
Before:
    to_encode.update({"exp": expire})

After:
    to_encode.update({"exp": expire, "type": "access"})

Reason: Access tokens now explicitly include type="access" to be validated by middleware

---

### Change 2: Fix verify_token_type() logic
Before:
    token_type = payload.get("type", expected_type)
    if expected_type != "access" and token_type != expected_type:
        raise AuthenticationError(f"Invalid token type. Expected {expected_type}")

After:
    token_type = payload.get("type")
    if token_type != expected_type:
        raise AuthenticationError(
            f"Invalid token type. Expected '{expected_type}', got '{token_type}'"
        )

Reason: 
- Previous logic had a bug: it only checked type if expected_type was NOT "access"
- New logic always validates, properly comparing the actual token type to expected type
- Throws error if token type is None or mismatched
- Provides clear error message showing both expected and actual types


## File 2: backend/app/middleware/auth.py
### Change: Add token type validation after decoding
Before:
    try:
        payload = JWTHandler.decode_token(token)
        # Add user info to request state
        request.state.user_id = payload.get("sub")
        request.state.user_role = payload.get("role")
        request.state.payload = payload

After:
    try:
        payload = JWTHandler.decode_token(token)
        
        # Verify token type is 'access' (not 'refresh' or other types)
        JWTHandler.verify_token_type(payload, "access")
        
        # Add user info to request state
        request.state.user_id = payload.get("sub")
        request.state.user_role = payload.get("role")
        request.state.payload = payload

Reason: Protected endpoints now explicitly verify that only access tokens are accepted


# ============================================================================
# VALIDATION EXAMPLES
# ============================================================================

## Example 1: Login Flow (No Changes)
```
POST /api/v1/auth/login
{
  "username": "admin",
  "password": "password123"
}

Response (HTTP 200):
{
  "access_token": "eyJhbGc...",     # type="access"
  "refresh_token": "eyJhbGc...",    # type="refresh"
  "expires_in": 1800
}
```
Note: Login flow is UNCHANGED. Tokens are created correctly with proper types.

---

## Example 2: Access Protected Endpoint with Access Token ✓ ALLOWED
```
GET /api/v1/analytics
Authorization: Bearer eyJhbGc...   # access token with type="access"

Response (HTTP 200):
{
  "total_requests": 1234,
  "cache_hit_rate": 75.5,
  ...
}
```

---

## Example 3: Access Protected Endpoint with Refresh Token ✗ REJECTED
```
GET /api/v1/analytics
Authorization: Bearer eyJhbGc...   # refresh token with type="refresh"

Response (HTTP 401):
{
  "detail": "Invalid token type. Expected 'access', got 'refresh'",
  "error_code": "AUTHENTICATION_ERROR"
}
```

---

## Example 4: Refresh Endpoint with Refresh Token ✓ ALLOWED
```
POST /api/v1/auth/refresh
{
  "refresh_token": "eyJhbGc..."   # type="refresh"
}

Response (HTTP 200):
{
  "access_token": "eyJhbGc...",    # NEW access token
  "refresh_token": "eyJhbGc...",   # NEW refresh token (optional rotation)
  "expires_in": 1800
}
```
Note: Refresh endpoint is in UNPROTECTED_PATHS, so AuthMiddleware skips it.
The endpoint handler validates that the token is a refresh token.

---

## Example 5: Refresh Endpoint with Access Token ✗ REJECTED
```
POST /api/v1/auth/refresh
{
  "refresh_token": "eyJhbGc..."   # access token with type="access"
}

Response (HTTP 401):
{
  "detail": "Invalid token type. Expected 'refresh', got 'access'",
  "error_code": "AUTHENTICATION_ERROR"
}
```
Note: AuthService.refresh_access_token() explicitly validates token type.


# ============================================================================
# TOKEN STRUCTURE (JWT Claims)
# ============================================================================

### Access Token (type="access")
{
  "sub": "123",                    # user ID
  "role": "admin",                 # user role
  "type": "access",               # ← NEW: token type claim
  "exp": 1234567890,              # expiration (30 minutes)
  "iat": 1234567800               # issued at
}

### Refresh Token (type="refresh")
{
  "sub": "123",                    # user ID
  "role": "admin",                 # user role
  "type": "refresh",              # token type claim
  "exp": 1234654890,              # expiration (7 days)
  "iat": 1234567890               # issued at
}


# ============================================================================
# VALIDATION TEST SCENARIOS
# ============================================================================

Test file: backend/tests/test_jwt_token_type.py

### Tests Included:
1. test_access_token_has_type_access
   - Verifies access tokens include type="access"

2. test_refresh_token_has_type_refresh
   - Verifies refresh tokens include type="refresh"

3. test_verify_token_type_accepts_correct_type
   - Access token passes access validation
   - Refresh token passes refresh validation

4. test_verify_token_type_rejects_wrong_type
   - Refresh token fails access validation (security fix!)
   - Access token fails refresh validation

5. test_verify_token_type_rejects_missing_type
   - Tokens without type claim are rejected

6. test_access_token_cannot_be_used_as_refresh_token
   - Security scenario: access token rejected for refresh

7. test_middleware_accepts_access_token
   - AuthMiddleware accepts valid access tokens

8. test_middleware_rejects_refresh_token (CRITICAL)
   - AuthMiddleware rejects refresh tokens on protected endpoints

9. test_security_scenario_refresh_token_injection
   - Demonstrates security fix: refresh token cannot be used as access token

### Run Tests:
cd backend
pytest tests/test_jwt_token_type.py -v


# ============================================================================
# SECURITY IMPACT
# ============================================================================

### Vulnerability Fixed:
- Token Type Confusion Attack
  - Attacker could use a refresh token to call protected endpoints
  - Impact: Unauthorized access to analytics, rules management, etc.
  - Severity: HIGH (now resolved)

### Key Security Improvements:
1. Strict token type validation on every protected request
2. Access tokens cannot be used for refresh
3. Refresh tokens cannot be used for protected endpoints
4. Clear error messages on token type mismatch
5. Middleware-level validation prevents bypasses


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

### Breaking Changes:
- Existing issued refresh tokens will continue to work
  (they already had type="refresh" claim)

- New access tokens MUST include type="access"
  (old tokens without type will be rejected on protected endpoints)

### Action Required:
- Users must re-authenticate to get new access tokens with type="access"
- Refresh tokens from before this change will still work for /auth/refresh
  (the verify_token_type check uses .get() which returns None if missing,
   then compares None != "refresh", raising an error on protected endpoints)

### Migration Path:
1. Deploy the code changes
2. Existing access tokens without type claim will be rejected on next request
3. Users will need to re-login to get new typed tokens
4. New tokens will have proper type claims


# ============================================================================
# IMPLEMENTATION VERIFICATION
# ============================================================================

### Step 1: Check Access Token Has Type Claim
```python
from app.core.security import JWTHandler
from jose import jwt
from app.config import settings

# Create token
token = JWTHandler.create_access_token({"sub": "123"})

# Decode and verify
decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
assert decoded.get("type") == "access"
print("✓ Access tokens have type='access'")
```

### Step 2: Check Middleware Validates Type
```python
# Access token passes
decoded = JWTHandler.decode_token(access_token)
JWTHandler.verify_token_type(decoded, "access")  # ✓ passes

# Refresh token fails
decoded = JWTHandler.decode_token(refresh_token)
JWTHandler.verify_token_type(decoded, "access")  # ✗ raises AuthenticationError
print("✓ Middleware validates token type")
```

### Step 3: Run Test Suite
```bash
pytest backend/tests/test_jwt_token_type.py -v
# All tests should pass
```

### Step 4: Manual Integration Test
1. Register a new user via /api/v1/auth/register
2. Login via /api/v1/auth/login (get access + refresh tokens)
3. Use access token on protected endpoint (/api/v1/analytics) → Should work ✓
4. Try using refresh token on protected endpoint → Should get 401 ✗
5. Use refresh token on /api/v1/auth/refresh → Should work ✓
"""

print(__doc__)
