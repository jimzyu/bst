# Sandbox Password Setup Instructions

## Step 1: Deploy Updated Code

Deploy these updated files to your Streamlit Cloud app:
- study.py
- config.py

## Step 2: Add Secrets to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Click on your Bible Study app
3. Click on "Settings" (⚙️ icon)
4. Click on "Secrets"
5. Add these two lines to your secrets:

```toml
# Existing secrets (keep these)
GEMINI_API_KEY = "your-existing-key"
GOOGLE_SHEETS_ID = "your-existing-id"
# BIBLE_API_KEY = "your-bible-key"  # (commented out as discussed)

[google_service_account]
# ... your existing service account config ...

# NEW: Add these two lines for sandbox mode
SANDBOX_MODE = true
SANDBOX_PASSWORD = "your-secure-password-here"
```

6. Click "Save"

## Step 3: Test

1. Visit your app URL
2. You should see a login screen: "🔒 Bible Study Tool - Sandbox Mode"
3. Enter your password
4. Click "Login"
5. You should see "✅ Authentication successful!" and the app loads

## Step 4: When Ready to Go Public

When you're ready to let users access your app without a password:

1. Go back to Settings → Secrets
2. Change this line:
   ```toml
   SANDBOX_MODE = true
   ```
   To:
   ```toml
   SANDBOX_MODE = false
   ```
3. Save
4. App will no longer require password

## Security Notes

- Choose a strong password (mix of letters, numbers, symbols)
- Don't share your password publicly
- Anyone with the password can access the app
- The password is stored securely in Streamlit Secrets (encrypted)

## Example Password Ideas

Good passwords:
- MyBibleStudy2026!
- TestMode#BibleApp
- Sandbox@Dev123

Avoid:
- "password"
- "123456"
- Your actual name

## Troubleshooting

**Problem**: "SANDBOX_MODE not found" error
**Solution**: Make sure you added both SANDBOX_MODE and SANDBOX_PASSWORD to secrets

**Problem**: Password not working
**Solution**: Check for typos in your secrets.toml. Password is case-sensitive.

**Problem**: App still asks for password after disabling
**Solution**: Make sure SANDBOX_MODE = false (not "false" in quotes, just false)
