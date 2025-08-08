#\!/bin/bash
echo "🧪 Testing Complete Authentication Flow"
echo "======================================"

# Test 1: Auth /me endpoint
echo "1️⃣ Testing /auth/me endpoint..."
AUTH_ME_RESULT=$(curl -s -w "\n%{http_code}" -X GET http://localhost:8000/api/auth/me -H "Authorization: Bearer dev-mock-token-12345" -H "Content-Type: application/json")
AUTH_ME_CODE=$(echo "$AUTH_ME_RESULT" | tail -n1)
AUTH_ME_BODY=$(echo "$AUTH_ME_RESULT" | head -n -1)
echo "Status: $AUTH_ME_CODE"
if [ "$AUTH_ME_CODE" = "200" ]; then
    echo "✅ PASS - User authentication working"
else
    echo "❌ FAIL - Authentication failed"
    echo "Response: $AUTH_ME_BODY"
fi
echo ""

# Test 2: Plaid link token
echo "2️⃣ Testing Plaid link token..."
PLAID_RESULT=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/accounts/plaid/link-token -H "Authorization: Bearer dev-mock-token-12345" -H "Content-Type: application/json" -d '{}')
PLAID_CODE=$(echo "$PLAID_RESULT" | tail -n1)
PLAID_BODY=$(echo "$PLAID_RESULT" | head -n -1)
echo "Status: $PLAID_CODE"
if [ "$PLAID_CODE" = "200" ]; then
    echo "✅ PASS - Plaid integration working"
else
    echo "❌ FAIL - Plaid integration failed"
    echo "Response: $PLAID_BODY"
fi
echo ""

# Test 3: Connection status
echo "3️⃣ Testing connection status..."
STATUS_RESULT=$(curl -s -w "\n%{http_code}" -X GET http://localhost:8000/api/accounts/connection-status -H "Authorization: Bearer dev-mock-token-12345" -H "Content-Type: application/json")
STATUS_CODE=$(echo "$STATUS_RESULT" | tail -n1)
STATUS_BODY=$(echo "$STATUS_RESULT" | head -n -1)
echo "Status: $STATUS_CODE"
if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ PASS - Connection status working"
else
    echo "❌ FAIL - Connection status failed"
    echo "Response: $STATUS_BODY"
fi
echo ""

# Test 4: Frontend health check
echo "4️⃣ Testing frontend availability..."
FRONTEND_RESULT=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:3000)
echo "Status: $FRONTEND_RESULT"
if [ "$FRONTEND_RESULT" = "200" ]; then
    echo "✅ PASS - Frontend accessible"
else
    echo "❌ FAIL - Frontend not accessible"
fi
echo ""

echo "📊 Test Summary"
echo "==============="
echo "Auth /me: $([ "$AUTH_ME_CODE" = "200" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "Plaid link: $([ "$PLAID_CODE" = "200" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "Connection status: $([ "$STATUS_CODE" = "200" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "Frontend: $([ "$FRONTEND_RESULT" = "200" ] && echo "✅ PASS" || echo "❌ FAIL")"

if [ "$AUTH_ME_CODE" = "200" ] && [ "$PLAID_CODE" = "200" ] && [ "$STATUS_CODE" = "200" ] && [ "$FRONTEND_RESULT" = "200" ]; then
    echo ""
    echo "🎉 ALL TESTS PASSED\! Authentication system is working correctly."
    echo ""
    echo "Next steps:"
    echo "- Open http://localhost:3000 in your browser"
    echo "- Use the 'Dev Auth Bypass' button to test the frontend integration"
    echo "- Open debug-auth-flow.html for additional testing tools"
else
    echo ""
    echo "⚠️  Some tests failed. Check the output above for details."
fi
