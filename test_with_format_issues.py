#!/usr/bin/env python3
"""
Test with a dataset that HAS format inconsistencies.
This will prove the detection order is correct.
"""

import sys
import os
import pandas as pd

# Add backend to path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_path)

from Agents.cleaning_agent.detection import detect_all_problems

# Load test dataset with format issues
test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_dataset_with_formats.csv')
df = pd.read_csv(test_file)

print("=" * 70)
print("TEST: Dataset WITH Format Inconsistencies")
print("=" * 70)
print(f"\nDataset shape: {df.shape[0]} rows, {df.shape[1]} columns\n")

print("Sample data:")
print(df.to_string())
print()

# Detect problems
problems = detect_all_problems(df)

print("=" * 70)
print(f"DETECTED {len(problems)} PROBLEMS (in priority order):")
print("=" * 70)

for i, problem in enumerate(problems, 1):
    print(f"\n{i}. [{problem.severity.upper()}] {problem.problem_type.value}")
    print(f"   {problem.title}")
    
    if problem.problem_type.value == "format_inconsistency":
        format_type = problem.metadata.get("format_type", "unknown")
        detected_formats = problem.metadata.get("detected_formats", {})
        print(f"   📋 Format type: {format_type}")
        print(f"   📋 Detected formats: {detected_formats}")

print("\n" + "=" * 70)
print("VERIFICATION:")
print("=" * 70)

# Categorize problems
format_positions = [i for i, p in enumerate(problems) if p.problem_type.value == "format_inconsistency"]
missing_positions = [i for i, p in enumerate(problems) if p.problem_type.value == "missing_values"]
outlier_positions = [i for i, p in enumerate(problems) if p.problem_type.value == "outliers"]

print(f"\nFormat inconsistency positions: {format_positions}")
print(f"Missing value positions: {missing_positions}")
print(f"Outlier positions: {outlier_positions}")

# Verify order
all_pass = True

if format_positions and missing_positions:
    if max(format_positions) < min(missing_positions):
        print("\n✅ PASS: Format issues detected BEFORE missing values")
    else:
        print("\n❌ FAIL: Format issues NOT before missing values")
        all_pass = False

if format_positions and outlier_positions:
    if max(format_positions) < min(outlier_positions):
        print("✅ PASS: Format issues detected BEFORE outliers")
    else:
        print("❌ FAIL: Format issues NOT before outliers")
        all_pass = False

if missing_positions and outlier_positions:
    if max(missing_positions) < min(outlier_positions):
        print("✅ PASS: Missing values detected BEFORE outliers")
    else:
        print("❌ FAIL: Missing values NOT before outliers")
        all_pass = False

if all_pass:
    print("\n" + "=" * 70)
    print("🎉 SUCCESS: Detection order is CORRECT!")
    print("   Format → Missing Values → Outliers")
    print("=" * 70)
