# 🧪 SSO Testing Guide

This guide shows you how to test that SSO is properly implemented and working.

## 🚀 Quick Test (2 minutes)

### Step 1: Run the SSO Test Script
```bash
cd /Users/russellgrocott/Projects/sprint-reports-v2/backend
python test_sso_live.py
```

**Expected Output**: All tests should show ✅ PASS

### Step 2: Start the Application
```bash
cd /Users/russellgrocott/Projects/sprint-reports-v2/backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Test SSO Config Endpoint
Open in browser: **http://localhost:8000/api/v1/auth/sso/config**

**Expected Response**:
```json
{
  "sso_enabled": true,
  "providers": {
    "google": {
      "name": "Google",
      "client_id": "your-google-client-id",
      "redirect_uri": "http://localhost:8000/auth/callback/google"
    }
  }
}
```

### Step 4: Test Google OAuth Flow
Open in browser: **http://localhost:8000/api/v1/auth/sso/google/initiate**

**Expected**: Redirect to Google OAuth consent screen

---

## 🔧 Detailed Testing

### Environment Setup
Make sure your `.env` file has:
```bash
SSO_ENABLED=true
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### API Endpoints to Test

1. **SSO Configuration**: `GET /api/v1/auth/sso/config`
   - Shows available SSO providers
   - Should include Google configuration

2. **Google OAuth Initiation**: `GET /api/v1/auth/sso/google/initiate`
   - Redirects to Google OAuth
   - Includes proper state parameter for CSRF protection

3. **Google OAuth Callback**: `GET /api/v1/auth/sso/google/callback`
   - Handles OAuth callback from Google
   - Creates/updates user account
   - Returns JWT tokens

4. **OAuth2 Token Exchange**: `POST /api/v1/auth/sso/google/token`
   - Exchanges authorization code for tokens
   - Creates user session

### Manual Testing Steps

#### Test 1: Configuration Loading
```bash
curl http://localhost:8000/api/v1/auth/sso/config
```
**Expected**: JSON with Google provider configuration

#### Test 2: OAuth Initiation
```bash
curl -v http://localhost:8000/api/v1/auth/sso/google/initiate
```
**Expected**: 302 redirect to accounts.google.com

#### Test 3: Complete OAuth Flow
1. Visit: `http://localhost:8000/api/v1/auth/sso/google/initiate`
2. Sign in with Google account
3. **Expected**: Successful authentication and user creation

#### Test 4: User Auto-Provisioning
After successful OAuth:
- Check database for new user record
- Verify user has Google SSO information stored
- Confirm JWT tokens are generated

### Frontend Testing (if frontend is running)

#### Test 1: SSO Provider Selection
- Visit the login page
- **Expected**: "Sign in with Google" button

#### Test 2: OAuth Flow
- Click "Sign in with Google"
- **Expected**: Smooth redirect to Google OAuth
- **Expected**: Return to application after authentication

### Security Testing

#### Test 1: CSRF Protection
- Verify state parameter is included in OAuth URLs
- **Expected**: Each OAuth initiation has unique state

#### Test 2: Domain Restrictions (if configured)
- Test with allowed/disallowed email domains
- **Expected**: Proper domain validation

#### Test 3: Error Handling
- Test with invalid OAuth responses
- **Expected**: Proper error messages without information leakage

---

## 🐛 Troubleshooting

### Issue: "SSO not enabled"
**Solution**: Check `.env` file has `SSO_ENABLED=true`

### Issue: "Google Client ID not configured"
**Solution**: Verify Google OAuth credentials in `.env`

### Issue: "Redirect URI mismatch"
**Solution**: 
1. Check Google OAuth console
2. Add redirect URI: `http://localhost:8000/auth/callback/google`

### Issue: "Import errors"
**Solution**: 
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Database connection error"
**Solution**: Start PostgreSQL and Redis services

---

## 📊 Expected Test Results

### ✅ Successful SSO Implementation Should Show:

1. **Configuration Test**: ✅ PASS
   - SSO enabled in config
   - Google credentials loaded
   - AuthenticationService working

2. **API Endpoints Test**: ✅ PASS
   - SSO config endpoint returns provider info
   - Google OAuth initiation works
   - All endpoints respond correctly

3. **Frontend Test**: ✅ PASS
   - SSO components exist
   - UI elements properly implemented

4. **Security Test**: ✅ PASS
   - CSRF protection active
   - Domain restrictions working
   - Proper error handling

### 🎉 Ready for Production When:
- All tests pass ✅
- Google OAuth flow completes successfully ✅
- User auto-provisioning works ✅
- Security measures validated ✅

---

## 🔗 Additional Resources

- **SSO Implementation Guide**: `/backlog/docs/Development/guides/SSO_IMPLEMENTATION_GUIDE.md`
- **Google OAuth Console**: https://console.developers.google.com/
- **FastAPI Docs**: http://localhost:8000/docs (when running)
- **OpenAPI Spec**: http://localhost:8000/redoc (when running)