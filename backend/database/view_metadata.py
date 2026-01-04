"""
Metadata Viewer - Inspect dataset metadata
Usage:
    python view_metadata.py <dataset_id>                    # View basic metadata
    python view_metadata.py <dataset_id> --stats            # Include column statistics
    python view_metadata.py <dataset_id> --json             # Output as JSON
    python view_metadata.py <dataset_id> --history          # Show metadata history
"""
import sys
import json
from database import get_dataset
from utils.metadata_extractor import (
    extract_comprehensive_metadata,
    format_metadata_for_display,
    get_metadata_history
)

def view_metadata(dataset_id: str, include_stats: bool = False, output_json: bool = False):
    """View metadata for a dataset"""
    # Get dataset info
    dataset = get_dataset(dataset_id)

    if not dataset:
        print(f"[ERROR] Dataset not found: {dataset_id}")
        return

    table_name = dataset['table_name']

    print(f"\n[INFO] Extracting metadata for dataset: {dataset['dataset_name']}")
    print(f"[INFO] Table: {table_name}")

    # Extract metadata
    metadata = extract_comprehensive_metadata(table_name, include_stats=include_stats)

    # Add dataset info
    metadata['dataset_id'] = dataset_id
    metadata['dataset_name'] = dataset['dataset_name']
    metadata['original_filename'] = dataset['original_filename']
    metadata['upload_date'] = dataset['upload_date'].isoformat() if dataset['upload_date'] else None

    # Output
    if output_json:
        print(json.dumps(metadata, indent=2))
    else:
        print(format_metadata_for_display(metadata))

def view_history(dataset_id: str):
    """View metadata history for a dataset"""
    dataset = get_dataset(dataset_id)

    if not dataset:
        print(f"[ERROR] Dataset not found: {dataset_id}")
        return

    history = get_metadata_history(dataset_id)

    if not history:
        print(f"\n[INFO] No metadata history found for dataset: {dataset['dataset_name']}")
        return

    print(f"\n{'='*80}")
    print(f"METADATA HISTORY: {dataset['dataset_name']}")
    print(f"{'='*80}\n")

    for i, snapshot in enumerate(history, 1):
        print(f"Snapshot {i}:")
        print(f"  Time: {snapshot['snapshot_time']}")
        print(f"  Rows: {snapshot['metadata'].get('row_count', 'N/A'):,}")
        print(f"  Columns: {snapshot['metadata'].get('column_count', 'N/A')}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    dataset_id = sys.argv[1]

    # Parse flags
    include_stats = '--stats' in sys.argv
    output_json = '--json' in sys.argv
    show_history = '--history' in sys.argv

    if show_history:
        view_history(dataset_id)
    else:
        view_metadata(dataset_id, include_stats=include_stats, output_json=output_json)
