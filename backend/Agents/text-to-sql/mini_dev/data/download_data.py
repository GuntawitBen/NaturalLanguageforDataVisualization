from huggingface_hub import snapshot_download

#pip install huggingface_hub
#python download_data.py

# Download the dataset
snapshot_download(
    repo_id="birdsql/bird_mini_dev",
    repo_type="dataset",
    local_dir="./data/bird_mini_dev"
)
print("Dataset downloaded successfully!")