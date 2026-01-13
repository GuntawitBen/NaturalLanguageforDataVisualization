#!/usr/bin/env python3
"""
Test script to verify format inconsistencies are detected first.
"""

import sys
import os
import pandas as pd

# Add backend to path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_path)

from Agents.cleaning_agent.detection import detect_all_problems
from Agents.cleaning_agent.models import ProblemType

def test_detection_order():
    """Test that format inconsistencies are detected before other issues."""
    
    # Create test data with multiple issues
    test_data = {
        'date_column': ['2024-01-01', 'N/A', '01/03/2024', 'null', '2024-01-05'],  # Format + missing
        'price_column': ['$10.99', '$25.50', '$1,234.56', '15.00', '$999.99'],     # Format issue
        'age_column': [25, None, 30, 200, 35],                                      # Missing + outlier
        'status': ['Yes', 'No', '1', '0', 'yes']                                    # Boolean format
    }
    
    df = pd.DataFrame(test_data)
    
    # Detect all problems
    problems = detect_all_problems(df)
    
    print("=" * 60)
    print("DETECTION ORDER TEST")
    print("=" * 60)
    print(f"\nTotal problems detected: {len(problems)}\n")
    
    # Print problems in order
    for i, problem in enumerate(problems, 1):
        print(f"{i}. [{problem.severity.upper()}] {problem.problem_type.value}")
        print(f"   Title: {problem.title}")
        print(f"   Columns: {', '.join(problem.affected_columns)}")
        print()
    
    # Verify format issues come first
    print("=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    format_indices = [i for i, p in enumerate(problems) if p.problem_type == ProblemType.FORMAT_INCONSISTENCY]
    missing_indices = [i for i, p in enumerate(problems) if p.problem_type == ProblemType.MISSING_VALUES]
    outlier_indices = [i for i, p in enumerate(problems) if p.problem_type == ProblemType.OUTLIERS]
    
    print(f"\nFormat inconsistency positions: {format_indices}")
    print(f"Missing value positions: {missing_indices}")
    print(f"Outlier positions: {outlier_indices}")
    
    # Check priority order
    if format_indices and missing_indices:
        if max(format_indices) < min(missing_indices):
            print("\n✅ PASS: All format issues detected before missing values")
        else:
            print("\n❌ FAIL: Format issues NOT detected before missing values")
            return False
    
    if format_indices and outlier_indices:
        if max(format_indices) < min(outlier_indices):
            print("✅ PASS: All format issues detected before outliers")
        else:
            print("❌ FAIL: Format issues NOT detected before outliers")
            return False
    
    if missing_indices and outlier_indices:
        if max(missing_indices) < min(outlier_indices):
            print("✅ PASS: All missing values detected before outliers")
        else:
            print("❌ FAIL: Missing values NOT detected before outliers")
            return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Detection order is correct!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_detection_order()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
