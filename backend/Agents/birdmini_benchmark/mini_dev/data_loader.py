import json
import sqlite3
import os

class BIRDDataLoader:
    def __init__(self, data_path):
        self.data_path = data_path
        self.examples = self.load_data()

    def load_data(self):
        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def get_example(self, idx):
        return self.examples[idx]

    def get_stats(self):
        total = len(self.examples)
        db_ids = set(ex['db_id'] for ex in self.examples)
        difficulties = {}
        for ex in self.examples:
            diff = ex.get('difficulty', 'unknown')
            difficulties[diff] = difficulties.get(diff, 0) + 1

        return {
            'total_examples': total,
            'unique_databases': len(db_ids),
            'databases': list(db_ids),
            'difficulty_distribution': difficulties
        }

# Load the data
loader = BIRDDataLoader('data/bird_mini_dev/data/mini_dev_sqlite-00000-of-00001.json')

# Print statistics
stats = loader.get_stats()
print("Dataset Statistics:")
print(f"  Total Examples: {stats['total_examples']}")
print(f"  Unique Databases: {stats['unique_databases']}")
print(f"  Difficulty Distribution: {stats['difficulty_distribution']}")

# Show first 3 examples
print("\nFirst 3 Examples:")
for i in range(3):
    ex = loader.get_example(i)
    print(f"\nExample {i+1}:")
    print(f"  Question: {ex['question']}")
    print(f"  Database: {ex['db_id']}")
    print(f"  SQL: {ex['SQL']}")
    print(f"  Difficulty: {ex.get('difficulty', 'N/A')}")