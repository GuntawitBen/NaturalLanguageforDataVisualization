# EDA Agent Documentation

## What is the EDA Agent?

The **EDA (Exploratory Data Analysis) Agent** is an AI-powered assistant that analyzes your CSV files and tells you about potential problems that might affect your data visualizations. Think of it as having a data expert review your file before you create charts.

---

## How Does It Work? (Simple Flow)

```
1. User uploads CSV file
   ↓
2. User proceeds to Stage 2 (Data Inspection)
   ↓
3. Frontend sends analysis request to backend
   ↓
4. Backend analyzes the CSV file (statistics + AI)
   ↓
5. Backend sends results back to frontend
   ↓
6. Frontend displays results as friendly chat messages
```

---

## Step-by-Step Explanation

### Step 1: User Uploads CSV File

**What happens:**
- User selects a CSV file on their computer
- File is uploaded to the backend server
- Server saves it temporarily in `./uploads/` folder
- Server returns a temporary file path

**Example response:**
```json
{
  "temp_file_path": "./uploads/temp_abc123.csv",
  "dataset_name": "sales_data",
  "original_filename": "sales_data.csv",
  "file_size_bytes": 524288
}
```

---

### Step 2: Frontend Sends Analysis Request

**When:** Automatically when user enters Stage 2

**What is sent to backend:**
```json
{
  "temp_file_path": "./uploads/temp_abc123.csv",
  "include_sample_rows": true,
  "max_sample_rows": 20
}
```

**Explanation of fields:**
- `temp_file_path`: Where the uploaded file is stored
- `include_sample_rows`: Should we send sample data to AI? (true/false)
- `max_sample_rows`: How many example rows to send (20 is default)

**Where it's sent:**
- **Endpoint:** `POST http://localhost:8000/agents/eda/analyze`
- **Headers:** Authorization token (to verify user is logged in)

---

### Step 3: Backend Analyzes the File

The backend does **TWO types of analysis**:

#### 3A. Statistical Analysis (Python/Pandas)

**What it calculates:**

1. **Dataset Summary:**
   - Total rows and columns
   - How much data is complete (% of non-empty cells)
   - Number of duplicate rows
   - File size

2. **For Each Column:**
   - Data type (number, text, etc.)
   - Missing values count and percentage
   - Unique values count

   **If numeric column:**
   - Min, max, average, median
   - Standard deviation
   - Skewness (is data lopsided?)
   - Kurtosis (are there extreme values?)
   - Outliers detection (using IQR method)

   **If text column:**
   - Shortest and longest text length
   - Average text length
   - Cardinality level (low/medium/high/very_high)
   - Top frequent values

**What issues it detects automatically:**

1. **Missing Values**
   - Checks each column for empty cells
   - Severity:
     - `info` if < 10% missing
     - `warning` if 10-50% missing
     - `critical` if > 50% missing

2. **Outliers** (using IQR method)
   - Calculates Q1 (25th percentile) and Q3 (75th percentile)
   - IQR = Q3 - Q1
   - Values outside [Q1 - 1.5×IQR, Q3 + 1.5×IQR] are outliers
   - Severity: `warning`

3. **High Cardinality**
   - If column has > 100 unique values
   - Severity: `warning`

4. **Duplicate Rows**
   - If same data appears in multiple rows
   - Severity:
     - `info` if < 5% duplicates
     - `warning` if ≥ 5% duplicates

5. **Skewed Distribution**
   - If skewness > 1.0 or < -1.0
   - Severity: `info`

6. **Heavy Tails**
   - If kurtosis > 3.0
   - Severity: `info`

7. **Large Dataset**
   - If > 100,000 rows
   - Severity: `info`

#### 3B. AI Analysis (OpenAI GPT-4)

**What is sent to OpenAI:**

```json
{
  "dataset_summary": {
    "row_count": 1500,
    "column_count": 8,
    "duplicate_row_count": 5,
    "overall_completeness": 94.5,
    "file_size_bytes": 524288
  },
  "column_statistics": [
    {
      "column_name": "age",
      "data_type": "int64",
      "null_count": 12,
      "null_percentage": 0.8,
      "unique_count": 45,
      "min": 18,
      "max": 87,
      "mean": 42.3,
      "median": 40,
      "std_dev": 15.2,
      "skewness": 0.4,
      "kurtosis": -0.2,
      "has_outliers": true,
      "outlier_count": 8
    },
    // ... more columns
  ],
  "sample_rows": [
    {"age": 25, "name": "John", "salary": 50000},
    {"age": 34, "name": "Sarah", "salary": 65000},
    // ... up to 20 rows
  ],
  "detected_issues_summary": {
    "missing_values_count": 3,
    "outliers_count": 2,
    "high_cardinality_count": 1,
    "duplicate_rows": 5
  }
}
```

**The Prompt Sent to GPT-4:**

**System Prompt:**
```
You are an expert data quality analyst specializing in exploratory data
analysis (EDA) for data visualization projects.

Your role is to:
1. Analyze datasets for quality issues
2. Identify problems that affect visualization
3. Provide clear, actionable recommendations

Focus on issues that impact data visualization such as:
- Missing values that create gaps in charts
- Outliers that skew scales
- High cardinality that clutters categorical charts
- Distribution issues affecting chart readability
```

**User Prompt:**
```
Analyze this dataset for visualization purposes:

DATASET SUMMARY:
- Rows: 1,500
- Columns: 8
- Completeness: 94.5%
- Duplicates: 5 rows

DETECTED ISSUES:
- 3 columns with missing values
- 2 columns with outliers
- 1 high cardinality column
- 5 duplicate rows

COLUMN DETAILS:
[Full column statistics here...]

SAMPLE DATA (first 20 rows):
[Sample rows here...]

Please provide:
1. A 2-3 sentence summary of overall data quality
2. List of specific visualization concerns
3. Any additional issues not caught by automated checks

Return JSON format:
{
  "summary": "string",
  "visualization_concerns": ["string"],
  "additional_issues": [
    {
      "type": "string",
      "severity": "critical|warning|info",
      "title": "string",
      "description": "string",
      "affected_columns": ["string"],
      "recommendation": "string"
    }
  ]
}
```

**What GPT-4 Returns:**

```json
{
  "summary": "Your dataset is generally clean with 94.5% completeness. The main concerns are outliers in the age and salary columns that may skew visualizations, and high cardinality in the product_id column which could clutter categorical charts.",

  "visualization_concerns": [
    "Outliers in salary column (range: $20K-$500K) will compress the scale, making most data points hard to distinguish",
    "Product_id has 1,200 unique values - categorical charts will be unreadable without filtering",
    "Missing values in date column will create gaps in time-series visualizations"
  ],

  "additional_issues": [
    {
      "type": "data_quality",
      "severity": "warning",
      "title": "Inconsistent date formats",
      "description": "Date column contains mix of formats: MM/DD/YYYY and DD-MM-YYYY",
      "affected_columns": ["order_date"],
      "recommendation": "Standardize all dates to a single format before visualization"
    }
  ]
}
```

---

### Step 4: Backend Combines Everything

**What the backend creates:**

```json
{
  "success": true,
  "analysis_timestamp": "2026-01-06T10:30:45",

  "dataset_summary": {
    "row_count": 1500,
    "column_count": 8,
    "file_size_bytes": 524288,
    "duplicate_row_count": 5,
    "duplicate_row_percentage": 0.33,
    "overall_completeness": 94.5,
    "memory_usage_mb": 0.5
  },

  "column_statistics": [
    /* Array of all column stats */
  ],

  "issues": [
    {
      "issue_id": "uuid-1234",
      "type": "missing_values",
      "severity": "warning",
      "title": "Missing values in 'age'",
      "description": "Column 'age' has 12 missing values (0.8% of total rows).",
      "affected_columns": ["age"],
      "recommendation": "Moderate missing values. Consider: (1) imputation with mean/median/mode, (2) forward/backward fill for time series, or (3) excluding rows with missing values if acceptable.",
      "metadata": {
        "null_count": 12,
        "null_percentage": 0.8
      }
    },
    /* More issues from automated checks */
    /* Plus additional issues from GPT-4 */
  ],

  "critical_issues_count": 0,
  "warning_issues_count": 5,
  "info_issues_count": 3,

  "gpt_summary": "Your dataset is generally clean with 94.5% completeness...",

  "visualization_concerns": [
    "Outliers in salary column will compress the scale...",
    "Product_id has 1,200 unique values..."
  ],

  "analysis_duration_seconds": 3.45
}
```

**This complete report is sent back to the frontend.**

---

### Step 5: Frontend Displays Results as Chat

**How messages are built:**

The frontend takes the backend response and creates **separate chat messages**:

#### Message 1: Greeting
```
"Hi! I've finished analyzing your dataset "sales_data".
Let me walk you through what I found."
```

#### Message 2: Summary
```
📊 Dataset Overview

• 1,500 rows and 8 columns
• Data completeness: 94.5%
• Duplicate rows: 5

Your dataset is generally clean with 94.5% completeness.
The main concerns are outliers in the age and salary columns...
```

#### Message 3: Critical Issues (if any)
```
🚨 I found 1 critical issue that needs your attention:
```

Then for each critical issue:
```
**Missing values in 'email'**

Column 'email' has 750 missing values (50.0% of total rows).

📍 Affected columns: email

💡 Recommendation: High percentage of missing values. Consider:
(1) removing this column if not essential, (2) imputing with
domain knowledge, or (3) investigating data collection issues.
```

#### Message 4: Warnings (if any)
```
⚠️ I also noticed 5 warnings:
```

Then for each warning (same format as critical)

#### Message 5: Info Items (grouped)
```
ℹ️ Here are 3 additional observations about your data:

1. Skewed distribution in 'salary'
   Column 'salary' has a skewness of 1.8...

2. Heavy-tailed distribution in 'age'
   Column 'age' has kurtosis of 4.2...

3. Large dataset may impact visualization performance
   Dataset has 100,500 rows. Visualizations may be slow...
```

#### Message 6: Visualization Concerns (if any)
```
📈 Visualization Concerns:

1. Outliers in salary column will compress the scale...
2. Product_id has 1,200 unique values...
3. Missing values in date column will create gaps...
```

#### Message 7: Final Advice
```
✅ Your dataset is in good shape! The warnings are optional
to fix, but addressing them will improve your visualizations.
```

**Display Animation:**

- Messages appear **one by one**
- 800ms delay between messages
- Typing indicator (three dots) shows before each message
- Each message slides in with animation
- User feels like receiving advice from a real assistant

---

## Technical Details

### Backend Stack

**Location:** `backend/Agents/eda_agent/`

**Files:**
- `config.py` - Settings and thresholds
- `models.py` - Data structures (Pydantic)
- `statistics.py` - Statistical calculations
- `prompts.py` - GPT-4 prompt templates
- `openai_client.py` - OpenAI API integration
- `analyzer.py` - Main orchestrator

**API Endpoint:**
- Route: `POST /agents/eda/analyze`
- File: `backend/routes/eda.py`

**Dependencies:**
- `pandas` - Data analysis
- `numpy` - Numerical calculations
- `openai` - AI integration
- `fastapi` - Web framework

### Frontend Stack

**Location:** `frontend/src/pages/DataCleaning.jsx`

**Key Features:**
- Chat interface with AI avatar
- Progressive message display
- Typing animation
- Markdown-like text rendering
- Severity-based color coding

**Styling:** `frontend/src/pages/DataCleaning.css`

---

## Configuration

### Thresholds (backend/Agents/eda_agent/config.py)

```python
# Outlier Detection
OUTLIER_IQR_MULTIPLIER = 1.5

# Missing Values
MISSING_VALUE_WARNING_THRESHOLD = 0.10   # 10%
MISSING_VALUE_CRITICAL_THRESHOLD = 0.50  # 50%

# Distribution
SKEWNESS_THRESHOLD = 1.0
KURTOSIS_THRESHOLD = 3.0

# Cardinality
LOW_CARDINALITY_MAX = 10
MEDIUM_CARDINALITY_MAX = 50
HIGH_CARDINALITY_THRESHOLD = 100

# Dataset Size
LARGE_DATASET_THRESHOLD = 100000
VISUALIZATION_SAMPLE_SIZE = 10000

# OpenAI
OPENAI_MODEL = "gpt-4o"
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 2000
```

### Environment Variables

```bash
# backend/.env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o
```

---

## Issue Types Detected

| Type | Description | Auto-Detected | Severity |
|------|-------------|---------------|----------|
| Missing Values | Empty cells in columns | ✅ Yes | info/warning/critical |
| Outliers | Extreme values (IQR method) | ✅ Yes | warning |
| High Cardinality | >100 unique values | ✅ Yes | warning |
| Duplicate Rows | Identical rows | ✅ Yes | info/warning |
| Skewed Distribution | \|skewness\| > 1.0 | ✅ Yes | info |
| Heavy Tails | kurtosis > 3.0 | ✅ Yes | info |
| Large Dataset | >100K rows | ✅ Yes | info |
| Data Type Issues | Inconsistent formats | ❌ AI Only | varies |
| Domain-Specific | Business logic problems | ❌ AI Only | varies |

---

## Error Handling

### If OpenAI API Fails

The system **still works**! It uses only the automated statistical checks:

```json
{
  "success": true,
  "gpt_summary": "Analysis completed with automated checks only.",
  "visualization_concerns": [],
  "issues": [
    /* Only issues from statistical analysis */
  ]
}
```

### If File Not Found

```json
{
  "detail": "Temporary file not found. Please upload the file again."
}
```

### If Invalid File Path

```json
{
  "detail": "Invalid file path. File must be in uploads directory."
}
```

---

## Security

1. **File Path Validation**
   - Only files in `./uploads/` can be analyzed
   - Prevents directory traversal attacks

2. **Authentication Required**
   - Must have valid session token
   - Token checked via `get_current_user()` dependency

3. **API Key Protection**
   - OpenAI key stored in environment variable
   - Never exposed to frontend

4. **Temporary Files**
   - Auto-cleanup when user leaves page
   - Prevents disk space issues

---

## Performance

**Typical Analysis Time:**
- Small file (<1MB): 2-4 seconds
- Medium file (1-10MB): 4-8 seconds
- Large file (10-50MB): 8-15 seconds

**What takes time:**
- Pandas reading CSV: ~30-40%
- Statistical calculations: ~20-30%
- OpenAI API call: ~30-40%
- Frontend animation: ~1-2 seconds per message

**Optimization:**
- Only sends 20 sample rows to OpenAI (not entire dataset)
- Caches results (future enhancement)
- Uses efficient pandas operations

---

## Chat Interface Behavior

### Loading State
- Shows 2 messages immediately:
  1. Greeting: "Hi there! 👋"
  2. Analyzing message with typing indicator

### Success State
- Shows 5-10 messages progressively
- 800ms delay between messages
- Each message slides in
- Color-coded by severity

### Error State
- Shows friendly error message
- Offers retry button
- Maintains chat format

---

## Example Complete Flow

1. **User uploads:** `sales_2024.csv` (5,000 rows, 12 columns)
2. **Frontend sends:** `{"temp_file_path": "./uploads/temp_xyz.csv", ...}`
3. **Backend calculates:** Statistics for all 12 columns
4. **Backend detects:** 2 warnings (outliers, high cardinality)
5. **Backend sends to GPT-4:** Summary + stats + 20 sample rows
6. **GPT-4 responds:** "Dataset is clean overall, but..."
7. **Backend combines:** Automated issues + GPT insights
8. **Backend returns:** Complete JSON report
9. **Frontend displays:** 7 chat messages over 6 seconds
10. **User sees:** Friendly analysis conversation

---

## Customization Guide

### Change Message Delay
```javascript
// DataCleaning.jsx line 267
await new Promise(resolve => setTimeout(resolve, 800)); // Change 800 to desired ms
```

### Change Severity Thresholds
```python
# backend/Agents/eda_agent/config.py
MISSING_VALUE_WARNING_THRESHOLD = 0.10  # Change to 0.05 for stricter
```

### Change GPT Model
```python
# backend/.env
OPENAI_MODEL=gpt-4-turbo  # Or gpt-4, gpt-3.5-turbo
```

### Customize Messages
```javascript
// DataCleaning.jsx buildChatMessages() function
messages.push({
  content: `Your custom greeting here!`
});
```

---

## Troubleshooting

### "Not Found" Error
- **Cause:** Backend not running or wrong port
- **Fix:** Ensure backend on port 8000, frontend config matches

### "OpenAI API key not configured"
- **Cause:** Missing or invalid API key
- **Fix:** Set `OPENAI_API_KEY` in backend/.env

### Messages Don't Appear
- **Cause:** `buildChatMessages()` not called
- **Fix:** Check browser console for errors

### Typing Animation Stuck
- **Cause:** Promise chain broken
- **Fix:** Check for exceptions in `buildChatMessages()`

---

## Future Enhancements

1. **Caching:** Cache analysis results by file hash
2. **Streaming:** Stream GPT responses in real-time
3. **Interactive:** Let users ask follow-up questions
4. **Visualizations:** Show small charts in chat
5. **Fixes:** Suggest automatic data cleaning
6. **History:** Save past analyses
7. **Export:** Download analysis as PDF

---

## Summary

The EDA Agent is a **two-stage AI system**:

1. **Statistical Analysis (Fast, Reliable)**
   - Uses Python/Pandas
   - Detects common issues
   - Always works

2. **AI Analysis (Smart, Contextual)**
   - Uses OpenAI GPT-4
   - Provides insights
   - Falls back gracefully if fails

Combined, they provide **comprehensive data quality feedback** in a **friendly chat interface** that makes users feel like they're receiving personalized advice from a data expert.
