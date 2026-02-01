# Draft Logging Feature Guide

## Overview

The refactored application now includes **automatic file logging** for all study sessions. This allows you to:
- ✅ **Verify AI outputs** by reviewing all intermediate drafts
- ✅ **Track study history** with timestamped JSON files
- ✅ **Compare drafts** to see how they were merged
- ✅ **Debug issues** by examining exact API responses

## What Gets Logged

### Standard Mode
Each study generates a JSON file containing:
- Bible reference
- Timestamp
- Complete result text
- Character count

### Deep Mode
Each study generates a JSON file containing:
- Bible reference
- Timestamp
- **All 3 intermediate drafts** (with focus descriptions)
- **Final merged result**
- Character counts for each draft
- Summary statistics

## File Locations

All logs are saved to the `logs/` directory in your project:

```
your-project/
├── study.py
├── config.py
├── ...
└── logs/
    ├── study_standard_John_3_16_20250131_103045.json
    ├── study_deep_Matthew_5_1-12_20250131_103150.json
    └── ...
```

## Log File Format

### Standard Mode Example
```json
{
  "reference": "John 3:16",
  "mode": "standard",
  "timestamp": "2025-01-31T10:30:45.123456",
  "unix_timestamp": 1706789445.123456,
  "result": "[CHINESE]\n### 啟發式提問\n...",
  "result_length": 1234
}
```

### Deep Mode Example
```json
{
  "reference": "Matthew 5:1-12",
  "mode": "deep",
  "timestamp": "2025-01-31T10:31:50.123456",
  "unix_timestamp": 1706789510.123456,
  "drafts": {
    "draft_1_standard": {
      "content": "[CHINESE]\n### 啟發式提問\n...",
      "length": 1200,
      "focus": "Standard balanced evangelical theology"
    },
    "draft_2_historical": {
      "content": "[CHINESE]\n### 啟發式提問\n...",
      "length": 1350,
      "focus": "Historical & cultural context"
    },
    "draft_3_application": {
      "content": "[CHINESE]\n### 啟發式提問\n...",
      "length": 1180,
      "focus": "Practical life application"
    }
  },
  "final_result": {
    "content": "[CHINESE]\n### 啟發式提問\n...",
    "length": 1420
  },
  "summary": {
    "total_drafts": 3,
    "draft_lengths": [1200, 1350, 1180],
    "final_length": 1420
  }
}
```

## How to Use the Logs

### 1. View a Log File
```bash
# Pretty print JSON
cat logs/study_deep_Matthew_5_1-12_20250131_103150.json | python -m json.tool
```

### 2. Extract Just the Drafts
```python
import json

with open('logs/study_deep_Matthew_5_1-12_20250131_103150.json') as f:
    data = json.load(f)

# Print each draft
for draft_name, draft_data in data['drafts'].items():
    print(f"\n{'='*60}")
    print(f"{draft_name.upper()}")
    print(f"Focus: {draft_data['focus']}")
    print(f"Length: {draft_data['length']} chars")
    print(f"{'='*60}")
    print(draft_data['content'])
```

### 3. Compare Drafts vs Final
```python
import json

with open('logs/study_deep_Matthew_5_1-12_20250131_103150.json') as f:
    data = json.load(f)

print("DRAFT 1 (Standard):")
print(data['drafts']['draft_1_standard']['content'][:500])
print("\n" + "="*60 + "\n")

print("DRAFT 2 (Historical):")
print(data['drafts']['draft_2_historical']['content'][:500])
print("\n" + "="*60 + "\n")

print("DRAFT 3 (Application):")
print(data['drafts']['draft_3_application']['content'][:500])
print("\n" + "="*60 + "\n")

print("FINAL MERGED RESULT:")
print(data['final_result']['content'][:500])
```

### 4. Search All Logs
```bash
# Find all studies of Matthew
grep -l "Matthew" logs/*.json

# Count total studies
ls -1 logs/*.json | wc -l

# Find studies from today
find logs/ -name "*.json" -newermt "today"
```

## Configuration

### Enable/Disable Logging

In `config.py`:
```python
# Enable logging (default)
ENABLE_DRAFT_LOGGING = True

# Disable logging
ENABLE_DRAFT_LOGGING = False
```

### Change Log Directory

In `config.py`:
```python
# Default
LOG_DIR = Path("logs")

# Custom location
LOG_DIR = Path("/path/to/your/logs")
```

## Console Logging

In addition to file logs, you'll see detailed console output:

```
INFO:api_client:Initialized Gemini client with model: gemini-2.5-flash
INFO:api_client:Draft logging: Enabled
INFO:api_client:Starting deep study generation for: Matthew 5:1-12
INFO:api_client:Generating 3 drafts in parallel
INFO:api_client:Draft 1 completed successfully
INFO:api_client:Draft 2 completed successfully
INFO:api_client:Draft 3 completed successfully
INFO:api_client:All 3 drafts completed in 8.42 seconds
INFO:api_client:Merging drafts into final study guide
INFO:api_client:Deep study logged to: logs/study_deep_Matthew_5_1-12_20250131_103150.json
INFO:api_client:  - Draft 1: 1200 chars
INFO:api_client:  - Draft 2: 1350 chars
INFO:api_client:  - Draft 3: 1180 chars
INFO:api_client:  - Final: 1420 chars
INFO:api_client:Deep study generation complete
```

## Verifying AI Quality

### Check Draft Diversity
Look at how different each draft's focus is:
```python
import json

with open('logs/study_deep_Matthew_5_1-12_20250131_103150.json') as f:
    data = json.load(f)

# Check if drafts have different content
drafts = [
    data['drafts']['draft_1_standard']['content'],
    data['drafts']['draft_2_historical']['content'],
    data['drafts']['draft_3_application']['content']
]

# Simple diversity check: compare first 200 chars
for i, draft in enumerate(drafts, 1):
    print(f"Draft {i} beginning: {draft[:200]}")
    print()
```

### Verify Merge Quality
Check if the final result genuinely incorporates elements from all drafts:
```python
import json

with open('logs/study_deep_Matthew_5_1-12_20250131_103150.json') as f:
    data = json.load(f)

final = data['final_result']['content']

# Check length - should be similar to longest draft, not just copying one
draft_lengths = data['summary']['draft_lengths']
final_length = data['summary']['final_length']

print(f"Draft lengths: {draft_lengths}")
print(f"Final length: {final_length}")
print(f"Average draft length: {sum(draft_lengths) / len(draft_lengths):.0f}")
print(f"Final vs average ratio: {final_length / (sum(draft_lengths) / len(draft_lengths)):.2f}")
```

### Search for Specific Content
```python
import json
import glob

# Find all logs mentioning "persecution"
for log_file in glob.glob('logs/*.json'):
    with open(log_file) as f:
        data = json.load(f)
    
    if 'persecution' in data.get('final_result', {}).get('content', '').lower():
        print(f"Found in: {log_file}")
        print(f"Reference: {data['reference']}")
```

## Privacy & Storage

### File Size
- Standard mode: ~1-3 KB per log
- Deep mode: ~4-10 KB per log (3 drafts + final)

### Disk Space Management
```bash
# Check total log size
du -sh logs/

# Remove logs older than 30 days
find logs/ -name "*.json" -mtime +30 -delete

# Keep only last 100 logs
ls -t logs/*.json | tail -n +101 | xargs rm -f
```

### Privacy Considerations
- Logs contain **full text** of AI responses
- Logs include **Bible references** you've searched
- Store logs securely if using sensitive study materials
- Consider `.gitignore` to exclude logs from version control:
  ```
  # .gitignore
  logs/
  ```

## Troubleshooting

### Logs Not Being Created
1. Check that `ENABLE_DRAFT_LOGGING = True` in config.py
2. Verify `logs/` directory permissions
3. Check console for error messages

### Cannot Read Log Files
```bash
# Check file encoding
file logs/study_*.json

# Try different JSON viewer
python -c "import json; print(json.load(open('logs/study_*.json')))"
```

### Logs Too Large
```python
# In config.py, you could add a custom filter (requires code modification)
# For now, just delete old logs periodically
```

## Example Verification Workflow

### After Each Deep Study:
1. **Check console output** for draft completion
2. **Verify log file created** in `logs/` directory
3. **Open log file** and inspect:
   - All 3 drafts are present
   - Each has different focus
   - Final result length is reasonable
   - Timestamps are correct

### Weekly Review:
```bash
# Count studies this week
find logs/ -name "*.json" -newermt "7 days ago" | wc -l

# Average response lengths
python -c "
import json, glob
lengths = []
for f in glob.glob('logs/*.json'):
    with open(f) as file:
        data = json.load(file)
        if 'final_result' in data:
            lengths.append(data['final_result']['length'])
print(f'Average: {sum(lengths)/len(lengths):.0f} chars')
print(f'Min: {min(lengths)}, Max: {max(lengths)}')
"
```

## Updates from Previous Version

### Changed Files
1. **config.py** - Added `ENABLE_DRAFT_LOGGING` and `LOG_DIR` settings
2. **api_client.py** - Added `DraftLogger` class and logging calls
3. **study.py** - Updated to pass `reference` to client methods

### No Changes Required
- prompts.py
- parsers.py
- session_manager.py
- requirements.txt

## Summary

With draft logging enabled, you now have:
- ✅ **Complete audit trail** of all AI-generated content
- ✅ **Verification capability** to check AI quality
- ✅ **Historical archive** of all studies
- ✅ **Debug information** for troubleshooting

The logging is **automatic**, **non-intrusive**, and **disabled with a single config flag** if needed.
