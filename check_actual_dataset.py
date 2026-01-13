#!/usr/bin/env python3
"""
Quick check: What problems does your actual dataset have?
This will show if there are format inconsistencies to detect.
"""

import sys
import os
import pandas as pd
import glob

# Add backend to path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_path)

from Agents.cleaning_agent.detection import detect_all_problems

# Find the most recent upload
uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'uploads')
files = glob.glob(os.path.join(uploads_dir, '*.csv'))

if not files:
    print("No CSV files found in uploads directory")
    sys.exit(1)

# Get most recent file
latest_file = max(files, key=os.path.getmtime)
print(f"Analyzing: {os.path.basename(latest_file)}\n")

# Load and analyze
df = pd.read_csv(latest_file)
print(f"Dataset shape: {df.shape[0]} rows, {df.shape[1]} columns")
print(f"Columns: {', '.join(df.columns)}\n")

# Show first few rows
print("First 3 rows:")
print(df.head(3))
print()

# Detect problems
problems = detect_all_problems(df)

print("=" * 60)
print(f"DETECTED {len(problems)} PROBLEMS (in order):")
print("=" * 60)

for i, problem in enumerate(problems, 1):
    print(f"\n{i}. [{problem.severity.upper()}] {problem.problem_type.value}")
    print(f"   {problem.title}")
    print(f"   Columns: {', '.join(problem.affected_columns) if problem.affected_columns else 'All'}")
    
    # Show metadata for format issues
    if problem.problem_type.value == "format_inconsistency":
        format_type = problem.metadata.get("format_type", "unknown")
        detected_formats = problem.metadata.get("detected_formats", {})
        print(f"   Format type: {format_type}")
        print(f"   Detected formats: {detected_formats}")

print("\n" + "=" * 60)

# Check if format issues come first
format_positions = [i for i, p in enumerate(problems) if p.problem_type.value == "format_inconsistency"]
missing_positions = [i for i, p in enumerate(problems) if p.problem_type.value == "missing_values"]

if format_positions:
    print(f"✅ Format inconsistencies found at positions: {format_positions}")
    if missing_positions and max(format_positions) < min(missing_positions):
        print("✅ Format issues correctly appear BEFORE missing values")
    elif missing_positions:
        print("❌ ERROR: Format issues appear AFTER missing values!")
else:
    print("ℹ️  No format inconsistencies detected in this dataset")
    print("   (This is why missing values appear first)")
