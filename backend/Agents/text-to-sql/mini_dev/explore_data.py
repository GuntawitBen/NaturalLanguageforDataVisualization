import json

# Load the SQLite version
with open('data/bird_mini_dev/data/mini_dev_sqlite-00000-of-00001.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total examples: {len(data)}")
print("\nFirst example structure:")
first_example = data[0]
for key in first_example.keys():
    print(f"  {key}: {type(first_example[key])}")

print("\n" + "="*50)
print("Sample Example:")
print("="*50)
print(f"Question: {first_example.get('question', 'N/A')}")
print(f"Database ID: {first_example.get('db_id', 'N/A')}")
print(f"SQL Query: {first_example.get('SQL', 'N/A')}")
print(f"Difficulty: {first_example.get('difficulty', 'N/A')}")
