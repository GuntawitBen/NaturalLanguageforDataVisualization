
import sys
import os
import pandas as pd
import unittest
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from backend.Agents.cleaning_agent.state_manager import session_manager
from backend.Agents.cleaning_agent.detection import detect_all_problems
from backend.Agents.cleaning_agent.models import ProblemType

class TestCleaningAgentState(unittest.TestCase):
    def setUp(self):
        # Create a test CSV with a specific issue
        # Row 0: Outlier in 'Value'
        # Row 1: Normal
        # Row 2: Missing 'Category'
        
        self.test_data = {
            'ID': [1, 2, 3, 4, 5, 6, 7],
            'Value': [1000, 10, 20, 15, 12, 18, 14],  # 1000 is an outlier
            'Category': ['A', 'B', None, 'C', 'A', 'B', 'C'] # Missing value in row 2 (index 2)
        }
        self.df = pd.DataFrame(self.test_data)
        self.temp_file = "test_data_state_repro.csv"
        self.df.to_csv(self.temp_file, index=False)
        self.dataset_name = "test_dataset"

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_state_update_after_operation(self):
        """
        Verify that problems are updated after an operation.
        Specific case: Removing outliers should update the problem list.
        """
        # Detect initial problems
        print("\n[TEST] Detecting initial problems...")
        initial_problems = detect_all_problems(self.df)
        
        # We expect Outliers and Missing Values
        outlier_prob = next((p for p in initial_problems if p.problem_type == ProblemType.OUTLIERS), None)
        missing_prob = next((p for p in initial_problems if p.problem_type == ProblemType.MISSING_VALUES), None)
        
        self.assertIsNotNone(outlier_prob, "Should detect outlier problem")
        self.assertIsNotNone(missing_prob, "Should detect missing value problem")
        
        print(f"[TEST] Initial problems: {[p.title for p in initial_problems]}")

        # Start a session
        session_id = session_manager.create_session(self.temp_file, self.dataset_name, initial_problems)
        session = session_manager.get_session(session_id)
        
        # Apply "Remove Outliers" operation
        # This should remove the first row (ID=1, Value=1000)
        print("[TEST] Applying 'remove_outliers'...")
        
        # Simulate options for removing outliers
        # In the actual agent, we'd get these from get_next_problem/generate_options
        # Here we just manually construct the parameters
        
        # Use a generic option ID
        option_id = "test-option-remove-outliers"
        
        # Apply operation via session manager
        record = session_manager.apply_operation(
            session_id=session_id,
            operation_type="remove_outliers",
            parameters={"columns": ["Value"]},
            option_id=option_id,
            problem_id=outlier_prob.problem_id
        )
        
        print(f"[TEST] Operation applied. Rows before: {record.stats_before.row_count}, After: {record.stats_after.row_count}")
        
        # CRITICAL TEST: Check if problems are automatically updated in the session
        # Currently (before fix), they are NOT updated.
        # After fix, they should be updated.
        
        # We need to manually trigger the update if we are simulating the agent logic
        # OR the session_manager should do it itself?
        # The plan says session_manager should have `update_problems_after_operation`.
        
        if hasattr(session_manager, 'update_problems_after_operation'):
            print("[TEST] Triggering problem update...")
            session_manager.update_problems_after_operation(session_id)
        else:
            print("[TEST] update_problems_after_operation NOT FOUND (Expected before fix)")
            
        current_problems = session.problems
        print(f"[TEST] Current problems: {[p.title for p in current_problems]}")
        
        # Check if the Outlier problem is gone or updated
        current_outlier = next((p for p in current_problems if p.problem_type == ProblemType.OUTLIERS), None)
        
        if current_outlier:
             # Even if outlier problem persists (maybe other outliers?), it should be a fresh check
             pass
        else:
            print("[TEST] Outlier problem is gone (Correct)")

        # In this specific test case:
        # One outlier was 1000. Removed.
        # Remaining values: 10, 20. No outliers.
        # So outlier problem should be GONE.
        
        if hasattr(session_manager, 'update_problems_after_operation'):
             self.assertIsNone(current_outlier, "Outlier problem should be resolved and removed from list")
        
        # Check ID persistence (if implemented)
        # The missing value problem should persist.
        # Row 3 (ID=3) has missing category. It was NOT removed.
        # So missing value problem should still exist.
        
        current_missing = next((p for p in current_problems if p.problem_type == ProblemType.MISSING_VALUES), None)
        self.assertIsNotNone(current_missing, "Missing value problem should still exist")
        
        # Check if ID is preserved
        if hasattr(session_manager, 'update_problems_after_operation'):
            print(f"[TEST] Original Missing ID: {missing_prob.problem_id}")
            print(f"[TEST] Current Missing ID:  {current_missing.problem_id}")
            self.assertEqual(missing_prob.problem_id, current_missing.problem_id, "Problem ID should be preserved")


if __name__ == '__main__':
    unittest.main()
