from huggingface_hub import hf_hub_download
import os

# Create databases directory
os.makedirs('databases', exist_ok=True)

# The databases should be in the repository
# Let's check what files are available
from huggingface_hub import list_repo_files

repo_id = "birdsql/bird_mini_dev"
files = list_repo_files(repo_id, repo_type="dataset")

print("Available files in repository:")
for f in files:
    print(f"  {f}")