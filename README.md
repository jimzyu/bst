# Bible Study Tool - Refactored Version with Quiz Mode

A Streamlit application that generates Bible study guides using Google Gemini AI, with support for Traditional Chinese, Simplified Chinese, and English. Features both **Study Mode** for generating comprehensive study guides and **Quiz Mode** for interactive learning with AI-powered feedback.

## Features

✨ **Key Improvements:**
- **Quiz Mode (NEW!)**: Interactive learning with AI evaluation and qualitative feedback
- **Parallel API Calls**: Deep mode now generates 3 drafts simultaneously (4x faster)
- **Retry Logic**: Automatic retry with exponential backoff for failed API calls
- **Better Error Handling**: Specific exception types and detailed error messages
- **Rate Limiting**: 5-second cooldown between requests to prevent abuse
- **Google Sheets Logging**: Automatic logging of all studies and quiz responses with scores
- **Session Management**: Complete study history tracking with timestamps
- **Modular Architecture**: Clean separation of concerns (config, prompts, parsers, API client)
- **Enhanced Validation**: Improved prompt engineering with few-shot examples
- **Comprehensive Logging**: Console logging for debugging and monitoring
- **Type Hints**: Full type annotations for better code quality

## Project Structure

```
.
├── study.py              # Main application entry point
├── config.py             # Configuration and constants
├── prompts.py            # All prompt templates (study + quiz evaluation)
├── parsers.py            # Response parsing and UI rendering
├── api_client.py         # Gemini API client with retry logic + Google Sheets logging
├── session_manager.py    # Streamlit session state management
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Installation

1. **Clone or download the files**

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up Streamlit secrets:**

Create `.streamlit/secrets.toml` in your project directory:
```toml
GEMINI_API_KEY = "your-gemini-api-key"
GOOGLE_SHEETS_ID = "your-spreadsheet-id"

[google_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCB...
(paste your full multi-line private key here)
...
-----END PRIVATE KEY-----
"""
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
universe_domain = "googleapis.com"
```

Or set up secrets in Streamlit Cloud dashboard if deploying online.

**Google Sheets Setup:**
1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable the Google Sheets API
3. Create a Service Account and download the JSON key file
4. Create a Google Sheet and copy its ID from the URL (the long string between `/d/` and `/edit`)
5. Share the Google Sheet with the service account email (found in the JSON as `client_email`), giving it **Editor** access
6. Copy all fields from the JSON into your secrets file as shown above

## Usage

### Local Development

```bash
streamlit run study.py
```

### Deploying to Streamlit Cloud

1. Push code to GitHub
2. Connect repository in Streamlit Cloud
3. Add secrets to Streamlit Cloud dashboard:
   - `GEMINI_API_KEY`
   - `GOOGLE_SHEETS_ID`
   - `[google_service_account]` section with all fields
4. Deploy!

## How It Works

### Study Mode (Original Feature)

Generate comprehensive Bible study guides with reflection questions and thematic summaries.

#### Standard Mode
1. Single API call to generate study guide
2. Fast response (~3-5 seconds)
3. Balanced theological perspective

#### Deep Mode
1. **Parallel Generation**: 3 drafts generated simultaneously
   - Draft 1: Standard evangelical theology
   - Draft 2: Historical/cultural context
   - Draft 3: Practical life application
2. **Intelligent Merging**: Combines best elements from all drafts
3. **Comprehensive Output**: Rich study guide with multiple perspectives
4. Response time: ~10-15 seconds (vs 30-40 seconds in original sequential version)

### Quiz Mode (NEW! 🎯)

Interactive learning mode where you answer questions and receive AI-powered feedback.

#### How It Works
1. **Generate Questions**: Enter a Bible reference and check "Quiz Mode"
2. **Answer Progressively**: Questions appear one at a time:
   - 📖 Observation (觀察): What does the text say?
   - 🤔 Interpretation (解釋): What does the text mean?
   - 💡 Application (應用): How does it apply to life?
3. **Receive Feedback**: After each answer, get qualitative feedback:
   - **Strengths (優點)**: What you captured well
   - **Gaps (不足)**: What you missed
   - **Suggestions (建議)**: How to improve
   - **Score**: 0-10 holistic evaluation (in parentheses)
4. **Review Summary**: See all your answers and feedback
5. **View Answer Key**: Option to reveal AI's complete study guide

#### Quiz Mode Options
- **Quiz Standard**: Uses single comprehensive answer key (4 API calls total)
- **Quiz Deep**: Uses deep mode answer key with 3 perspectives (7 API calls total)

## Configuration

Edit `config.py` to customize:

```python
MODEL_NAME = 'gemini-2.5-flash'  # Gemini model to use
TEMPERATURE = 0.3                 # Lower = more consistent
MAX_RETRIES = 3                   # API retry attempts
REQUEST_COOLDOWN_SECONDS = 5      # Rate limit cooldown
ENABLE_DRAFT_LOGGING = True       # Google Sheets logging (True/False)
```

## Google Sheets Logging

All studies and quizzes are automatically logged to Google Sheets with the following structure:

### Column Layout

| Column | Content |
|--------|---------|
| A: Timestamp | ISO format timestamp of when the study/quiz was generated |
| B: Reference | Bible reference (e.g., "Matthew 5:1-12") |
| C: Mode | "standard", "deep", "quiz_standard", or "quiz_deep" |
| D: Draft 1 | Standard theological view (Deep mode only) |
| E: Draft 2 | Historical & cultural context (Deep mode only) |
| F: Draft 3 | Practical life application (Deep mode only) |
| G: Final Result / AI Answer Key | The final merged study guide or quiz answer key |
| H: User Answer - Observation | User's answer to observation question (Quiz mode only) |
| I: Feedback - Observation | AI feedback on observation answer (Quiz mode only) |
| J: User Answer - Interpretation | User's answer to interpretation question (Quiz mode only) |
| K: Feedback - Interpretation | AI feedback on interpretation answer (Quiz mode only) |
| L: User Answer - Application | User's answer to application question (Quiz mode only) |
| M: Feedback - Application | AI feedback on application answer (Quiz mode only) |
| N: Score - Observation | 0-10 score for observation answer (Quiz mode only) |
| O: Score - Interpretation | 0-10 score for interpretation answer (Quiz mode only) |
| P: Score - Application | 0-10 score for application answer (Quiz mode only) |

### Mode-Specific Logging

**Study Mode (Standard/Deep):**
- Columns A-G populated
- Columns H-P empty

**Quiz Mode (Standard/Deep):**
- Columns A-G populated (with answer key in G)
- Columns H-P populated as user progresses through questions
- Scores automatically extracted from feedback and logged separately

**To disable logging**, set `ENABLE_DRAFT_LOGGING = False` in `config.py`.

## API Usage

### Study Mode
- **Standard Mode**: 1 API call (~3-5 seconds)
- **Deep Mode**: 4 API calls (3 parallel + 1 merge, ~10-15 seconds)

### Quiz Mode
- **Quiz Standard Mode**: 4 API calls total
  - 1 call: Generate answer key
  - 3 calls: Evaluate each answer (sequential as user progresses)
  - Total time: ~15-20 seconds (spread over quiz session)
- **Quiz Deep Mode**: 7 API calls total
  - 4 calls: Generate answer key (3 parallel + 1 merge)
  - 3 calls: Evaluate each answer (sequential as user progresses)
  - Total time: ~25-30 seconds (spread over quiz session)

**Rate Limit**: 5 seconds cooldown between initial requests

## Key Improvements Explained

### 1. Parallel API Calls (4x Speed Boost)
**Before:** Sequential calls took 30-40 seconds
```python
draft_1 = model.generate_content(prompt_1)  # Wait 10s
draft_2 = model.generate_content(prompt_2)  # Wait 10s
draft_3 = model.generate_content(prompt_3)  # Wait 10s
```

**After:** Parallel calls take 10-15 seconds
```python
with ThreadPoolExecutor(max_workers=3):
    drafts = parallel_generate([prompt_1, prompt_2, prompt_3])
```

### 2. Retry Logic with Exponential Backoff
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def generate_content(prompt):
    # Automatically retries on failure with increasing wait times
```

### 3. Quiz Mode AI Evaluation

The AI evaluates answers using:
- **Holistic Scoring**: 0-10 scale based on overall understanding
  - 9-10: Exceptional understanding
  - 7-8: Strong understanding
  - 5-6: Adequate understanding
  - 3-4: Limited understanding
  - 0-2: Insufficient understanding
- **Qualitative Feedback**: Specific strengths, gaps, and suggestions
- **Bilingual Output**: Feedback provided in both Chinese and English

## Error Handling

The app handles various error scenarios:
- **Invalid Bible references**: Clear user feedback
- **API failures**: Automatic retry with exponential backoff
- **Rate limiting**: Enforced cooldown periods
- **Content blocking**: Specific error messages
- **Network issues**: Graceful degradation
- **Google Sheets errors**: Quiz continues even if logging fails (best effort logging)

## Development Tips

### Enable Debug Info
Uncomment in `study.py`:
```python
# SessionManager.show_debug_info()
```

### Adjust Rate Limiting
In `config.py`:
```python
REQUEST_COOLDOWN_SECONDS = 0  # Disable for testing
```

### Test Quiz Mode
```python
# Try different references
"John 3:16"      # Short passage
"Matthew 5:1-12" # Longer passage (Beatitudes)
"Psalm 23"       # Poetic text

# Test invalid references (should show error)
"Chicken Soup"   # Should show [INVALID_REF]
"Batman"         # Should show [INVALID_REF]
```

## Performance Benchmarks

| Mode | API Calls | Time | Use Case |
|------|-----------|------|----------|
| Study Standard | 1 | ~3-5s | Quick study guide |
| Study Deep | 4 | ~10-15s | Comprehensive multi-perspective study |
| Quiz Standard | 4 | ~15-20s | Interactive learning (spread over session) |
| Quiz Deep | 7 | ~25-30s | In-depth interactive learning (spread over session) |

## Troubleshooting

### Quiz Mode Issues

**"Quiz ready!" but no questions appear**
- This was fixed with `st.rerun()` - make sure you have the latest `study.py`

**Google Sheets logging errors during quiz**
- The app uses batch updates and defensive error handling
- Quiz will continue even if logging fails
- Check logs for specific Google Sheets API errors
- Common causes: rate limits (handled with 0.5s delay), quota issues, permission problems

### Google Sheets Logging Issues

**"Draft logging: Disabled" in logs**

**Cause**: Either `GOOGLE_SHEETS_ID` or `google_service_account` couldn't be loaded from secrets.

**Solution**:
1. Check your secrets file has exactly these names (case-sensitive):
   - `GOOGLE_SHEETS_ID` (all caps with underscore)
   - `[google_service_account]` (lowercase with underscore)
2. Verify all required fields are present in the service account section
3. Reboot the app after changing secrets

**No rows appearing in Google Sheet**

**Cause**: Service account doesn't have permission to write to the sheet.

**Solution**:
1. Open your Google Sheet
2. Click "Share" button
3. Add the service account email (from `client_email` in your JSON)
4. Give it **Editor** access
5. Uncheck "Notify people" (service accounts can't receive emails)
6. Try running another study

**"private_key" format errors**

**Cause**: The private key field isn't properly formatted in TOML.

**Solution**: Use triple quotes around the entire key:
```toml
private_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCB...
(keep the actual line breaks)
...
-----END PRIVATE KEY-----
"""
```

Do NOT use:
- Single quotes `'...'`
- Regular double quotes `"..."` 
- Escaped newlines `\n`

**Verify logging is working**

Check the console logs for:
```
INFO:api_client:SheetsLogger initialized successfully
INFO:api_client:Deep study logged to Google Sheets for: [reference]
INFO:api_client:Quiz answer logged for observation (row X, score: Y/10)
```

If you don't see these lines, logging isn't working.

## License

This is a refactored version incorporating best practices for:
- Error handling
- Performance optimization
- Code organization
- Type safety
- Logging and monitoring
- Interactive learning (Quiz Mode)

## Support

For issues or questions:
1. Check logs for detailed error messages
2. Verify API key is correctly set
3. Ensure stable internet connection
4. Check Gemini API quota limits
5. For Google Sheets logging issues:
   - Verify the service account email has Editor access to the sheet
   - Check that all fields in `[google_service_account]` are present
   - Ensure `private_key` uses triple quotes `"""`
   - Look for "SheetsLogger initialized successfully" in logs

## Credits

Refactored and optimized version with improvements in:
- Parallel processing (4x speed improvement in deep mode)
- Error handling with automatic retry
- Code architecture and maintainability
- User experience with interactive quiz mode
- Comprehensive logging to Google Sheets

## Changelog

### v2.0 - Quiz Mode Release
- **NEW**: Interactive Quiz Mode with AI-powered evaluation
- **NEW**: Progressive question flow (Observation → Interpretation → Application)
- **NEW**: Qualitative feedback with holistic 0-10 scoring
- **NEW**: Individual score tracking in Google Sheets (columns N, O, P)
- **IMPROVED**: Google Sheets logging with batch updates to avoid rate limits
- **IMPROVED**: Defensive error handling - quiz continues even if logging fails
- **IMPROVED**: Enhanced prompt templates for quiz evaluation

### v1.0 - Initial Refactored Release
- Parallel API calls for 4x speed improvement
- Modular architecture (6 files)
- Google Sheets logging for study sessions
- Retry logic with exponential backoff
- Rate limiting protection
- Comprehensive session management
