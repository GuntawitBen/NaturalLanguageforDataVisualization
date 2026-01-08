# OpenAI Rate Limit Handling Implementation

## Problem

Your OpenAI account has restrictive free-tier rate limits:
- **3 requests per minute (RPM)**
- **100,000 tokens per minute (TPM)**

The inspection agent makes multiple API calls:
1. One call per data quality issue (for visualization_impact)
2. One call for final summary generation

With 8 issues, that's 9 total calls, which exceeds the 3 RPM limit and causes `RateLimitError 429`.

---

## Solution Implemented

### 1. **Intelligent Retry Logic with Exponential Backoff**

Added `_call_with_retry()` method in `OpenAIClient`:

```python
def _call_with_retry(self, func, *args, max_retries=None, **kwargs):
    """
    Call OpenAI API with exponential backoff retry logic

    - Parses retry_after time from error message
    - Waits suggested time before retrying
    - Falls back to exponential backoff (2^attempt)
    - Max retries configurable (default: 2)
    """
```

**Features:**
- ✅ Detects `RateLimitError` specifically
- ✅ Parses "Please try again in Xs" or "Xm" from error message
- ✅ Respects API's suggested retry time
- ✅ Uses exponential backoff as fallback
- ✅ Configurable max retries

**Example Log:**
```
[WARNING] Rate limit hit (attempt 1/3). Waiting 20.0s before retry...
[WARNING] Rate limit hit (attempt 2/3). Waiting 20.0s before retry...
[WARNING] Rate limit exceeded after 2 retries. Skipping.
```

---

### 2. **Graceful Fallback Messages**

When rate limits are exhausted after retries:

**For Issue Enrichment:**
```python
return "This data quality issue may affect the accuracy and clarity of your visualizations. (AI analysis unavailable due to rate limits)"
```

**For Summary Generation:**
```python
return f"Analysis complete. Found {len(issues)} issue(s): {critical} critical, {warning} warnings. (Detailed AI summary unavailable due to API rate limits)"
```

**Benefits:**
- ✅ Analysis continues even if GPT-4 is unavailable
- ✅ User sees clear message about rate limits
- ✅ Core data quality detection still works (pandas-based)
- ✅ Report is still generated with programmatic findings

---

### 3. **Configurable Rate Limit Delay**

Added environment variable configuration in `config.py`:

```python
OPENAI_RATE_LIMIT_DELAY = float(os.getenv("OPENAI_RATE_LIMIT_DELAY", "20.0"))
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
```

**Default Settings:**
- **Delay between requests:** 20 seconds
- **Max retries:** 2 attempts

**Why 20 seconds?**
- Free tier: 3 requests per minute = 1 request every 20 seconds
- Ensures you stay under RPM limit
- Can be adjusted via environment variable

---

### 4. **Updated Analyzer Enrichment Loop**

Modified `analyzer.py` to use configurable delay:

```python
# Add delay between API calls to avoid rate limiting
if idx < len(issues) - 1:
    print(f"  [INFO] Waiting {OPENAI_RATE_LIMIT_DELAY}s before next request...")
    time.sleep(OPENAI_RATE_LIMIT_DELAY)
```

**Impact:**
- With 8 issues: 7 delays × 20s = **140 seconds total wait time**
- Ensures compliance with 3 RPM limit
- Progress indicator shows waiting status

---

## Configuration Options

### Environment Variables

Set in your `.env` file or environment:

```bash
# Delay between OpenAI API calls (seconds)
OPENAI_RATE_LIMIT_DELAY=20.0

# Maximum retry attempts for rate limit errors
OPENAI_MAX_RETRIES=2

# Use a different model if needed
OPENAI_MODEL=gpt-4o-mini
```

### For Paid Accounts

If you upgrade to a paid account with higher limits:

```bash
# Reduce delay for faster analysis
OPENAI_RATE_LIMIT_DELAY=1.0

# More aggressive retries
OPENAI_MAX_RETRIES=5
```

---

## How It Works

### Request Flow with Rate Limits

```
Issue 1: Generate visualization_impact
    ├─ Attempt 1: [SUCCESS] ✓
    └─ Wait 20s...

Issue 2: Generate visualization_impact
    ├─ Attempt 1: [RATE LIMIT 429]
    ├─ Parse retry_after: 20s
    ├─ Wait 20s and retry...
    ├─ Attempt 2: [SUCCESS] ✓
    └─ Wait 20s...

Issue 3: Generate visualization_impact
    ├─ Attempt 1: [RATE LIMIT 429]
    ├─ Wait 20s and retry...
    ├─ Attempt 2: [RATE LIMIT 429]
    ├─ Max retries exhausted
    └─ Use fallback message ⚠️

...continues for all issues...

Final Summary: Generate GPT summary
    ├─ Attempt 1: [SUCCESS] ✓
    └─ Complete!
```

---

## Error Messages Explained

### Before Implementation

```
[ERROR] Failed to generate visualization impact: RateLimitError: Error code: 429
[ERROR] Full traceback: <long stack trace>
[ERROR] Failed to generate visualization impact: RateLimitError: Error code: 429
[ERROR] Full traceback: <long stack trace>
...repeated for every issue...
```

**Problems:**
- ❌ Scary error messages
- ❌ Analysis failed completely
- ❌ No retry logic
- ❌ User didn't know what to do

### After Implementation

```
[INFO] Enriching 8 issues with GPT-4 visualization impacts...
[1/8] Generating impact for: Missing values in 'age'
[GPT-4] Generated impact successfully (245 chars)
✓ Success: Missing values in 'age'...
[INFO] Waiting 20.0s before next request (rate limit protection)...

[2/8] Generating impact for: Outliers detected in 'price'
[WARNING] Rate limit hit (attempt 1/3). Waiting 20.0s before retry...
[GPT-4] Generated impact successfully (198 chars)
✓ Success: Outliers detected in 'price'...
[INFO] Waiting 20.0s before next request (rate limit protection)...

[3/8] Generating impact for: Duplicate rows detected
[WARNING] Rate limit hit (attempt 1/3). Waiting 20.0s before retry...
[WARNING] Rate limit hit (attempt 2/3). Waiting 20.0s before retry...
[WARNING] Rate limit exceeded for issue 'Duplicate rows detected'. Using fallback message.
✗ Failed: Duplicate rows detected
[INFO] Waiting 20.0s before next request (rate limit protection)...

[INFO] Enrichment complete: 2/8 successful
```

**Benefits:**
- ✅ Clear progress indicator
- ✅ Shows retry attempts
- ✅ User understands what's happening
- ✅ Analysis completes with partial results

---

## Files Modified

### 1. `backend/Agents/inspection_agent/openai_client.py`

**Changes:**
- Added `RateLimitError` import
- Added `_parse_retry_after()` method
- Added `_call_with_retry()` method with exponential backoff
- Updated `generate_visualization_impact()` to use retry logic
- Updated `generate_summary()` to use retry logic
- Added graceful fallback for rate limit errors

**Lines changed:** ~100 lines added/modified

### 2. `backend/Agents/inspection_agent/config.py`

**Changes:**
- Added `OPENAI_RATE_LIMIT_DELAY` configuration
- Added `OPENAI_MAX_RETRIES` configuration

**Lines added:** 2 lines

### 3. `backend/Agents/inspection_agent/analyzer.py`

**Changes:**
- Imported `OPENAI_RATE_LIMIT_DELAY` from config
- Updated enrichment loop to use configurable delay
- Added log messages showing wait time

**Lines modified:** 10 lines

---

## Testing Recommendations

### Test Rate Limit Handling

1. **Trigger rate limits intentionally:**
   ```bash
   # Set very short delay to hit limits
   export OPENAI_RATE_LIMIT_DELAY=0.1
   ```

2. **Test retry logic:**
   - Upload dataset with 5-10 issues
   - Observe retry attempts in logs
   - Verify fallback messages appear

3. **Test with different limits:**
   ```bash
   # Simulate paid tier (faster)
   export OPENAI_RATE_LIMIT_DELAY=1.0
   export OPENAI_MAX_RETRIES=5
   ```

### Monitor Logs

Watch for these key messages:
- `[WARNING] Rate limit hit` - Retry is working
- `[WARNING] Rate limit exceeded after X retries` - Fallback activated
- `[INFO] Waiting Xs before next request` - Delay is working

---

## Performance Impact

### Analysis Time Comparison

**Before (failing with rate limits):**
- ❌ Analysis failed after 3-4 issues
- ❌ User saw errors and no results

**After (with 8 issues):**
| Stage | Time |
|-------|------|
| Detection & Stats | 2-3 seconds |
| Enrichment (8 issues) | 140-160 seconds (7 × 20s delays) |
| Summary Generation | 20-30 seconds |
| **Total** | **~3 minutes** |

**For Paid Accounts (1s delay):**
| Stage | Time |
|-------|------|
| Detection & Stats | 2-3 seconds |
| Enrichment (8 issues) | 10-15 seconds (7 × 1s delays) |
| Summary Generation | 2-3 seconds |
| **Total** | **~20 seconds** |

---

## User-Facing Changes

### Progress Indicator

The frontend progress bar now accurately reflects:
- Time spent waiting for rate limits
- Which issue is being processed
- Retry attempts (if visible in logs)

### Result Quality

With rate limits:
- ✅ All programmatic checks still run (missing values, outliers, etc.)
- ⚠️ Some visualization_impact messages may be generic
- ⚠️ Summary may be simplified
- ✅ All issues are still detected and reported

---

## Recommendations

### For Development

```bash
# Use shorter delays for faster testing
export OPENAI_RATE_LIMIT_DELAY=5.0
```

### For Free Tier Production

```bash
# Use default settings (20s delay)
export OPENAI_RATE_LIMIT_DELAY=20.0
export OPENAI_MAX_RETRIES=2
```

### For Paid Tier

```bash
# Faster analysis with higher limits
export OPENAI_RATE_LIMIT_DELAY=1.0
export OPENAI_MAX_RETRIES=5
```

### Upgrade Recommendation

To improve user experience:
1. Add payment method to OpenAI account
2. Increase rate limits to 500+ RPM
3. Reduce delay to 1-2 seconds
4. Analysis time drops from ~3 minutes to ~20 seconds

---

## Troubleshooting

### Still Getting Rate Limit Errors?

1. **Check current delay:**
   ```python
   from backend.Agents.inspection_agent.config import OPENAI_RATE_LIMIT_DELAY
   print(f"Current delay: {OPENAI_RATE_LIMIT_DELAY}s")
   ```

2. **Increase delay:**
   ```bash
   export OPENAI_RATE_LIMIT_DELAY=30.0  # More conservative
   ```

3. **Reduce retries to fail faster:**
   ```bash
   export OPENAI_MAX_RETRIES=1  # Fail fast, use fallback
   ```

### Analysis Taking Too Long?

1. **Reduce dataset issues:**
   - Clean data before uploading
   - Fewer issues = fewer API calls

2. **Skip enrichment for low-priority issues:**
   - Modify analyzer to only enrich CRITICAL/WARNING issues
   - INFO issues use fallback messages

3. **Upgrade OpenAI tier:**
   - Most effective solution
   - 500+ RPM allows 1-2s delays

---

## Summary

✅ **Implemented:**
- Exponential backoff retry logic
- Graceful fallback messages
- Configurable rate limit delays
- Clear user feedback

✅ **Benefits:**
- Analysis never fails due to rate limits
- User sees progress and wait times
- Results include all programmatic checks
- Easy to configure for different tiers

⚠️ **Trade-offs:**
- Free tier analysis takes ~3 minutes
- Some AI-generated messages may be generic
- Requires patience for multiple issues

🚀 **Next Steps:**
- Consider adding payment method to OpenAI
- Or implement batch processing for issues
- Or cache common visualization impacts
