# Bible API Setup Guide

## Getting Your Free Bible API Key

The Bible passage display feature uses [api.bible](https://scripture.api.bible/) to fetch passages in English (ESV) and Chinese (CUV).

### Step 1: Create an Account

1. Go to https://scripture.api.bible/
2. Click "Sign Up" or "Get Started"
3. Fill in your details and create an account
4. Verify your email

### Step 2: Get Your API Key

1. Log in to https://scripture.api.bible/
2. Go to your Dashboard
3. Click "Create API Key" or view existing keys
4. Copy your API key (looks like: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

**Free Tier Limits:**
- 500 requests per day
- More than enough for personal Bible study use

### Step 3: Add to Streamlit Secrets

Add the API key to your `.streamlit/secrets.toml` file:

```toml
GEMINI_API_KEY = "your-gemini-key"
GOOGLE_SHEETS_ID = "your-sheet-id"
BIBLE_API_KEY = "your-bible-api-key-here"

[google_service_account]
type = "service_account"
...
```

**For Streamlit Cloud:**
1. Go to your app settings
2. Click "Secrets"
3. Add this line to your secrets:
   ```
   BIBLE_API_KEY = "your-bible-api-key-here"
   ```
4. Save

### Step 4: Deploy

The Bible passage feature will automatically activate once the API key is detected.

## Supported Translations

- **English**: NIrV (New International Reader's Version)
- **Chinese**: FEB (Free Easy-to-Read Bible - 簡明聖經)

*Both versions use simpler, modern language designed for easier reading and comprehension - perfect for Bible study!*

## How It Works in Your App

### Study Mode:
- Bible passage appears in a collapsible expander above the study guide
- User can expand to read the passage
- Doesn't interfere with main content

### Quiz Mode:
- Bible passage appears in the sidebar
- Always accessible while answering questions
- User can reference the text as needed

## Troubleshooting

### "Passage display disabled" warning in logs
**Cause**: BIBLE_API_KEY not found in secrets
**Solution**: Add the key to your secrets file

### Passage not loading
**Cause**: Reference format not recognized or API quota exceeded
**Solution**: 
- Check reference format (e.g., "Matthew 5:1-12")
- Check API quota at https://scripture.api.bible/

### Chinese passage not appearing
**Cause**: Some passages may not be available in CUV
**Solution**: English ESV should always work; Chinese is best-effort

## API Usage

**Each study/quiz session makes:**
- 1 Bible API call for English passage
- 1 Bible API call for Chinese passage
- Total: 2 Bible API calls per reference

**Daily limits with free tier:**
- 500 Bible API calls / day = ~250 studies per day
- Plenty for personal use!

## Cost Comparison

| Service | Cost | Calls per Study |
|---------|------|----------------|
| Gemini API | Pay per token | 1-7 calls |
| Bible API | FREE (500/day) | 2 calls |
| Google Sheets | FREE | 1-3 calls |

Bible passage display adds **zero cost** to your app!

## Optional: Disable Bible Passages

If you don't want Bible passage display:
1. Don't add BIBLE_API_KEY to secrets
2. Feature will automatically disable
3. App works normally without it

## Privacy

- api.bible does not track what passages you read
- No personal data is sent to Bible API
- Only the Bible reference (e.g., "Matthew 5:1-12") is sent

## Need Help?

- Bible API docs: https://scripture.api.bible/docs
- Support: https://scripture.api.bible/support
