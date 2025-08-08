# Auth Flow Testing Guide

## 1. 401 Storm Fix Testing

### Before (Expected Behavior):
- Multiple 401 errors in console
- Frontend gets stuck in retry loops
- User sees loading states indefinitely

### After (Expected Behavior):
- Single 401 followed by automatic token refresh
- Silent retry with new token
- User never sees authentication errors

### Test Steps:
1. Start the development server: `./scripts/dev.sh`
2. Log in normally
3. Wait for access token to expire (or manually expire it in dev tools)
4. Make an API call (navigate to different pages)
5. Check console - should see "🔄 Attempting silent token refresh..." followed by "✅ Token refresh successful"

## 2. Plaid Link Initialization Fix Testing

### Before (Expected Issues):
- "Query data cannot be undefined" errors
- Duplicate Plaid script loading warnings
- Plaid Link components failing to initialize

### After (Expected Behavior):
- No "Query data cannot be undefined" errors
- Single Plaid script load
- Clean Plaid Link initialization

### Test Steps:
1. Navigate to Dashboard
2. Check console for Plaid-related errors (should be none)
3. Try to connect a bank account (should work smoothly)
4. Check Network tab - should see single script load

## 3. Magic Link Email Confirmation Testing

### Backend Testing:
1. Register a new user
2. Check backend logs for magic link URL
3. Copy the magic link from logs
4. Visit the magic link in browser
5. Should redirect to dashboard with user logged in

### Frontend Testing:
1. Registration should show "Please check your email" message
2. Magic link click should log user in automatically
3. No additional login screen should appear
4. User should land on dashboard with full session

### Test Registration:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "display_name": "Test User",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### Expected Response:
```json
{
  "user": {
    "id": "...",
    "email": "test@example.com",
    "emailSent": true
  },
  "message": "Registration successful! Please check your email for a confirmation link.",
  "requiresEmailConfirmation": true
}
```

## 4. Complete Integration Test

### Test Scenario:
1. **Fresh Start**: Clear all browser data
2. **Register**: Create new account
3. **Magic Link**: Click confirmation link from logs
4. **Dashboard**: Verify user lands on dashboard
5. **API Calls**: Verify protected endpoints work
6. **Token Refresh**: Wait for token expiration, verify silent refresh
7. **Plaid Integration**: Try connecting bank account
8. **Logout/Login**: Test normal login flow still works

### Success Criteria:
- ✅ No console errors during registration
- ✅ Magic link redirects and logs user in
- ✅ Dashboard loads with user data
- ✅ Protected API calls work (accounts, transactions, etc.)
- ✅ Token refresh happens silently
- ✅ Plaid Link works without errors
- ✅ Normal login still functions

## 5. Error Handling Testing

### Test Cases:
1. **Expired Magic Link**: Use old magic link (should show error)
2. **Invalid Magic Link**: Modify token (should show error)
3. **Network Issues**: Disconnect internet during requests
4. **Server Restart**: Restart backend during active session

### Expected Behavior:
- Graceful error messages
- No infinite loading states
- Proper fallback to login page when needed

## Development Notes

- Magic links are currently logged to console (search for "Magic link for")
- In production, implement proper email service (SendGrid, etc.)
- CORS must allow credentials for cookie-based auth
- HTTPS required in production for secure cookies