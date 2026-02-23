# 📖 Bible Study Tool with AI-Powered Learning

A comprehensive Streamlit application that generates Bible study guides using Google Gemini AI, with support for **Traditional Chinese, Simplified Chinese, and English**. Features both **Study Mode** for generating comprehensive study guides and **Quiz Mode** for interactive learning with AI-powered feedback and confidence scoring.

## ✨ Features Overview

### 🎓 Study Mode
- **Standard Mode**: Single comprehensive study guide with reflection questions
- **Deep Mode**: 3 parallel drafts merged intelligently for richer insights
- **AI Understanding Confidence**: See how confident the AI is in understanding each passage
- **Trilingual Output**: Traditional Chinese, Simplified Chinese, and English tabs

### 🎯 Quiz Mode
- **Interactive Learning**: Answer questions progressively (Observation → Interpretation → Application)
- **AI Evaluation**: Get detailed qualitative feedback on your answers
- **Scoring System**: 0-10 holistic scores + evaluation confidence percentages
- **Case Studies**: Practical real-world scenarios after Application question
- **Standard & Deep Options**: Choose between quick quiz or comprehensive quiz with multiple perspectives

### 📊 Advanced Features
- **Dual Confidence Scoring**:
  - **Understanding Confidence**: AI's confidence in understanding the passage (displayed as color-coded banner)
  - **Evaluation Confidence**: AI's confidence in evaluating your quiz answers (shown with scores)
- **Google Sheets Logging**: Automatic tracking of all studies, quiz responses, scores, and confidence metrics (20 columns)
- **Sandbox Mode**: Password-protected testing environment
- **Bible Passage Display**: Optional API integration to show Bible text (currently disabled)
- **Parallel API Calls**: Deep mode generates 3 drafts simultaneously (4x faster than sequential)
- **Retry Logic**: Automatic retry with exponential backoff for failed API calls
- **Rate Limiting**: 5-second cooldown between requests

## 🏗️ Project Structure

```
.
├── study.py              # Main application entry point and UI
├── config.py             # Configuration, constants, and secrets management
├── prompts.py            # All prompt templates (study + quiz + case study)
├── parsers.py            # Response parsing and content rendering
├── api_client.py         # Gemini API client + Google Sheets logger
├── session_manager.py    # Streamlit session state management
├── bible_api.py          # Bible API integration (optional)
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── SANDBOX_SETUP.md      # Password protection setup guide
├── BIBLE_API_SETUP.md    # Bible passage display setup guide
├── LOGGING_GUIDE.md      # Google Sheets logging documentation
└── COMPARISON.md         # Refactored vs original comparison
```

## 📦 Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ai-tools
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Requirements:**
- `streamlit>=1.28.0` - Web app framework
- `google-generativeai>=0.3.0` - Gemini AI SDK
- `opencc-python-reimplemented>=0.1.7` - Chinese conversion (Traditional ↔ Simplified)
- `tenacity>=8.2.0` - Retry logic with exponential backoff
- `gspread>=6.0.0` - Google Sheets API
- `requests>=2.31.0` - HTTP requests (for Bible API)

### 3. Set Up Secrets

#### For Local Development

Create `.streamlit/secrets.toml` in your project directory:

```toml
# Required: Gemini API Key
GEMINI_API_KEY = "your-gemini-api-key-here"

# Required: Google Sheets ID (for logging)
GOOGLE_SHEETS_ID = "your-spreadsheet-id-here"

# Optional: Sandbox Mode (for testing)
SANDBOX_MODE = false  # Set to true to enable password protection
SANDBOX_PASSWORD = "your-password"  # Only needed if SANDBOX_MODE = true

# Optional: Bible API (currently disabled)
# BIBLE_API_KEY = "your-bible-api-key"

# Required: Google Service Account (for Sheets access)
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

#### For Streamlit Cloud Deployment

Add the same secrets to your Streamlit Cloud dashboard under Settings → Secrets.

### 4. Set Up Google Sheets (Required for Logging)

1. **Create a Google Cloud Project**: Go to https://console.cloud.google.com
2. **Enable Google Sheets API**: In APIs & Services
3. **Create Service Account**: 
   - Go to IAM & Admin → Service Accounts
   - Create account and download JSON key file
4. **Create Google Sheet**: 
   - Create a new blank spreadsheet
   - Copy the spreadsheet ID from URL (between `/d/` and `/edit`)
5. **Share Sheet with Service Account**:
   - Share the Google Sheet with the `client_email` from JSON
   - Give it **Editor** access
6. **Add Credentials to Secrets**: Copy all fields from JSON to your secrets file

See **LOGGING_GUIDE.md** for detailed setup instructions and spreadsheet structure.

### 5. Get Gemini API Key

1. Go to https://aistudio.google.com/app/apikey
2. Create a new API key
3. Copy to your secrets file

## 🚀 Usage

### Local Development

```bash
streamlit run study.py
```

The app will open in your browser at `http://localhost:8501`

### Deploying to Streamlit Cloud

1. Push code to GitHub repository
2. Go to https://share.streamlit.io
3. Click "New app" and connect your repository
4. Add all secrets from your `secrets.toml` to the Streamlit Cloud dashboard
5. Deploy!

## 📚 How to Use

### Study Mode

#### Standard Study (Fast)
1. Enter a Bible reference (e.g., "John 3:16", "Matthew 5:1-12", "創世記 1")
2. Click "開始研讀 Start Study"
3. Get comprehensive study guide in ~3-5 seconds

**What you get:**
- ✅ **AI Understanding Confidence**: Color-coded banner showing AI's confidence in understanding the passage
  - 🟢 Green (90-100%): Very confident
  - 🔵 Blue (70-89%): Moderately confident
  - 🟠 Orange (50-69%): Less confident
  - 🔴 Red (<50%): Low confidence
- Three reflection questions: Observation, Interpretation, Application
- Theme summary with theological significance
- Historical context (when applicable)
- Trilingual tabs for easy reading

**API Calls:** 1 call (~$0.0001)

#### Deep Study (Comprehensive)
1. Enter Bible reference
2. Check "🔍 啟用深度整合模式 (Deep Study Mode)"
3. Click "開始研讀 Start Study"
4. Get enriched study guide in ~10-15 seconds

**What you get:**
- All standard study features PLUS:
- Multiple theological perspectives combined
- Richer historical and cultural context
- More actionable life application insights

**How it works:**
1. Generates 3 drafts in parallel:
   - Draft 1: Standard evangelical theology
   - Draft 2: Historical/cultural deep dive
   - Draft 3: Practical life application focus
2. AI intelligently merges the best insights from all three
3. Result: Comprehensive study guide with depth

**API Calls:** 4 calls (3 drafts + 1 merge) (~$0.0004)

### Quiz Mode

#### How to Use Quiz Mode
1. Enter a Bible reference
2. Check "Quiz Mode 測驗模式"
3. (Optional) Check "Deep Study Mode" for more comprehensive answer key
4. Click "開始研讀 Start Study"

#### Question Flow
Questions appear one at a time in this order:

**1. 📖 Observation Question (觀察)**
- "What does the text say?"
- Focus on facts, events, people, actions

**2. 🤔 Interpretation Question (解釋)**
- "What does the text mean?"
- Focus on theology, context, significance

**3. 💡 Application Question (應用)**
- "How does it apply to life?"
- Focus on practical, personal, actionable insights
- **BONUS:** Case study appears after this question!

#### Feedback You Receive

After submitting each answer, you get:

```
**優點 (Strengths)**: What you captured well - specific and encouraging

**不足 (Gaps)**: What you missed - 1) key point one, 2) key point two, 3) key point three

**建議 (Suggestion)**: One concrete way to improve

(得分: 7/10, 信心度: 85%)
(Score: 7/10, Confidence: 85%)
```

**Scoring Guide:**
- **9-10**: Exceptional - all key points with depth
- **7-8**: Strong - main points well covered
- **5-6**: Adequate - basic understanding
- **3-4**: Limited - significant gaps
- **0-2**: Insufficient - major misunderstanding

**Confidence Guide:**
- **90-100%**: Very confident in evaluation
- **70-89%**: Moderately confident
- **50-69%**: Less confident (answer ambiguous)
- **Below 50%**: Low confidence (difficult to assess)

#### Case Study Feature 💡

After the Application question, a **practical case study** appears:

**Example:**
```
### 實際案例 / Practical Case Study

[2-3 paragraph modern scenario in Chinese that applies the passage principles]

[Same scenario in English]
```

These scenarios help you see how biblical principles apply to real-world situations like:
- Workplace challenges
- Family relationships
- Personal struggles
- Ethical dilemmas
- Daily decisions

#### Quiz Summary

After answering all three questions:
- Review all your answers
- See all feedback and scores
- View your overall performance
- (Optional) Reveal the AI's complete answer key

#### API Calls
- **Quiz Standard**: 4 calls (1 answer key + 3 evaluations) (~$0.0004)
- **Quiz Deep**: 7 calls (4 for answer key + 3 evaluations) (~$0.0007)

## 📊 Google Sheets Logging

### What Gets Logged

Every study and quiz is automatically logged to Google Sheets with **20 columns (A-T)**:

| Column | Content | Study | Quiz |
|--------|---------|-------|------|
| A | Timestamp | ✅ | ✅ |
| B | Bible Reference | ✅ | ✅ |
| C | Mode (standard/deep/quiz_standard/quiz_deep) | ✅ | ✅ |
| D | Draft 1 (Deep mode only) | ✅ | ✅ |
| E | Draft 2 (Deep mode only) | ✅ | ✅ |
| F | Draft 3 (Deep mode only) | ✅ | ✅ |
| G | Final Result / AI Answer Key | ✅ | ✅ |
| H | Quiz Answer - Observation | ❌ | ✅ |
| I | Quiz Answer - Interpretation | ❌ | ✅ |
| J | Quiz Answer - Application | ❌ | ✅ |
| K | Quiz Feedback - Observation | ❌ | ✅ |
| L | Quiz Feedback - Interpretation | ❌ | ✅ |
| M | Quiz Feedback - Application | ❌ | ✅ |
| N | Score - Observation (0-10) | ❌ | ✅ |
| O | Score - Interpretation (0-10) | ❌ | ✅ |
| P | Score - Application (0-10) | ❌ | ✅ |
| Q | Evaluation Confidence - Observation (%) | ❌ | ✅ |
| R | Evaluation Confidence - Interpretation (%) | ❌ | ✅ |
| S | Evaluation Confidence - Application (%) | ❌ | ✅ |
| T | AI Understanding Confidence (%) | ✅ | ✅ |

### Benefits
- Track your learning progress over time
- Analyze which question types you excel at
- See confidence patterns
- Export data for further analysis
- Share with study partners or mentors

See **LOGGING_GUIDE.md** for detailed documentation.

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# AI Model Settings
MODEL_NAME = 'gemini-2.5-flash'  # Gemini model to use
TEMPERATURE = 0.3                 # Lower = more consistent, higher = more creative

# API Behavior
MAX_RETRIES = 3                   # Retry attempts for failed API calls
REQUEST_COOLDOWN_SECONDS = 5      # Rate limit cooldown between requests

# Logging
ENABLE_DRAFT_LOGGING = True       # Enable/disable Google Sheets logging

# UI
PAGE_TITLE = "聖經研讀工具 | Bible Study Tool"
PAGE_ICON = "📖"
```

## 🔒 Sandbox Mode (Optional)

Protect your app during testing with password authentication.

### Enable Sandbox Mode

Add to your secrets:
```toml
SANDBOX_MODE = true
SANDBOX_PASSWORD = "your-secure-password"
```

### How It Works
- When enabled, users see a login screen before accessing the app
- Password is required to proceed
- Great for testing new features privately
- No monthly fee (unlike Streamlit's built-in auth)

### Disable When Ready
Set `SANDBOX_MODE = false` to make app publicly accessible.

See **SANDBOX_SETUP.md** for detailed instructions.

## 📖 Bible Passage Display (Optional)

Display actual Bible text in your study guides.

### Currently Disabled
The Bible API integration code is present but disabled by default (API key commented out).

### To Enable
1. Get API key from https://api.bible
2. Add to secrets: `BIBLE_API_KEY = "your-key"`
3. Configure Bible versions in `bible_api.py`

See **BIBLE_API_SETUP.md** for detailed setup instructions.

## 💰 Cost Estimates

Using Gemini 2.5 Flash with $300 GCP free credit:

| Operation | API Calls | Time | Cost per Use |
|-----------|-----------|------|--------------|
| Standard Study | 1 | ~3-5s | $0.0001 |
| Deep Study | 4 | ~10-15s | $0.0004 |
| Quiz Standard | 4 | ~15-20s | $0.0004 |
| Quiz Deep | 7 | ~25-30s | $0.0007 |

**Monthly Estimates:**
- 100 studies/month ≈ $0.05
- 200 studies/month ≈ $0.10
- 500 studies/month ≈ $0.25

**Your $300 credit** will last approximately **4-8 years** at typical usage!

## 🛠️ Troubleshooting

### Common Issues

**1. "API Key not found"**
- Make sure `GEMINI_API_KEY` is in your secrets
- Check for typos in the key

**2. "Failed to log to Google Sheets"**
- Verify service account has Editor access to the sheet
- Check that all service account fields are in secrets
- Confirm Google Sheets API is enabled in GCP

**3. Quiz shows "Failed to extract questions"**
- This was a previous bug - should be fixed in latest version
- Try restarting the app

**4. Case study not appearing**
- Should be very rare now with improved prompts
- Check console logs for case study extraction messages
- Deep mode quizzes preserve case studies through merge

**5. Confidence banner not showing**
- Make sure you're using the latest `study.py`
- Check for duplicate `display_results()` functions (debugging artifact)
- Reboot the app completely

### Debug Mode

For troubleshooting, check the console logs. Look for:
```
INFO: Case study extracted: CH=True, EN=True
INFO: Study mode - Confidence extracted: 85
```

## 📂 Additional Documentation

- **SANDBOX_SETUP.md**: Password protection setup
- **BIBLE_API_SETUP.md**: Bible text display integration
- **LOGGING_GUIDE.md**: Google Sheets structure and setup
- **COMPARISON.md**: Refactored vs original version comparison

## 🎯 Roadmap / Future Enhancements

Potential features for future development:

- [ ] User accounts and personal study history
- [ ] Study plans and reading schedules
- [ ] Cross-reference linking
- [ ] Export to PDF/Word
- [ ] Mobile app version
- [ ] Multi-user collaboration
- [ ] Advanced analytics dashboard
- [ ] Original language (Hebrew/Greek) integration
- [ ] Commentary integration
- [ ] Audio readings

## 🤝 Contributing

This is a personal project, but suggestions are welcome! Feel free to:
- Report bugs via GitHub issues
- Suggest features
- Share how you're using the tool

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- **Google Gemini AI** for powerful language models
- **Streamlit** for the amazing app framework
- **OpenCC** for Chinese conversion
- **Bible API** for scripture text access

## 📧 Contact

[Add your contact information]

---

**Built with ❤️ for Bible study and learning**

Last Updated: February 2026
