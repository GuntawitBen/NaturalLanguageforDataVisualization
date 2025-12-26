"""
Enhanced Metadata Extraction for CSV Datasets
Extracts comprehensive metadata including statistical analysis
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from database.db_init import get_db_connection

# ============================================================================
# BASIC METADATA EXTRACTION
# ============================================================================

def extract_basic_metadata(table_name: str) -> Dict[str, Any]:
    """
    Extract basic metadata about a dataset table

    Returns:
        - row_count: Total number of rows
        - column_count: Total number of columns
        - columns_info: List of column definitions
        - table_size_bytes: Approximate table size in bytes
    """
    conn = get_db_connection()

    try:
        # Row count
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        # Column information from information_schema
        columns_info = conn.execute(f"""
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """).fetchall()

        column_count = len(columns_info)

        # Format column info
        columns = [
            {
                "name": col[0],
                "type": col[1],
                "nullable": col[2] == 'YES'
            }
            for col in columns_info
        ]

        # Estimate table size (not exact, but good approximation)
        # DuckDB stores data efficiently, this is a rough estimate
        table_size_bytes = row_count * column_count * 50  # ~50 bytes per cell average

        return {
            "row_count": row_count,
            "column_count": column_count,
            "columns_info": columns,
            "table_size_bytes": table_size_bytes
        }

    except Exception as e:
        print(f"Error extracting basic metadata: {e}")
        raise

# ============================================================================
# COLUMN-LEVEL STATISTICS
# ============================================================================

def extract_column_statistics(table_name: str, column_name: str, data_type: str) -> Dict[str, Any]:
    """
    Extract detailed statistics for a single column

    Returns different stats based on data type:
    - Numeric: min, max, mean, median, std_dev, distinct_count, null_count
    - String: distinct_count, null_count, min_length, max_length, avg_length
    - Date: min_date, max_date, distinct_count, null_count
    - Boolean: true_count, false_count, null_count
    """
    conn = get_db_connection()
    stats = {
        "column_name": column_name,
        "data_type": data_type
    }

    try:
        # Null count (universal)
        null_count = conn.execute(f"""
            SELECT COUNT(*) FROM {table_name} WHERE "{column_name}" IS NULL
        """).fetchone()[0]
        stats["null_count"] = null_count

        # Distinct count (universal)
        distinct_count = conn.execute(f"""
            SELECT COUNT(DISTINCT "{column_name}") FROM {table_name}
        """).fetchone()[0]
        stats["distinct_count"] = distinct_count

        # Type-specific statistics
        if data_type in ['INTEGER', 'BIGINT', 'DOUBLE', 'FLOAT', 'DECIMAL', 'HUGEINT']:
            # Numeric statistics
            numeric_stats = conn.execute(f"""
                SELECT
                    MIN("{column_name}") as min_val,
                    MAX("{column_name}") as max_val,
                    AVG("{column_name}") as mean_val,
                    MEDIAN("{column_name}") as median_val,
                    STDDEV("{column_name}") as std_dev
                FROM {table_name}
                WHERE "{column_name}" IS NOT NULL
            """).fetchone()

            if numeric_stats:
                stats.update({
                    "min": float(numeric_stats[0]) if numeric_stats[0] is not None else None,
                    "max": float(numeric_stats[1]) if numeric_stats[1] is not None else None,
                    "mean": float(numeric_stats[2]) if numeric_stats[2] is not None else None,
                    "median": float(numeric_stats[3]) if numeric_stats[3] is not None else None,
                    "std_dev": float(numeric_stats[4]) if numeric_stats[4] is not None else None
                })

        elif data_type == 'VARCHAR':
            # String statistics
            string_stats = conn.execute(f"""
                SELECT
                    MIN(LENGTH("{column_name}")) as min_length,
                    MAX(LENGTH("{column_name}")) as max_length,
                    AVG(LENGTH("{column_name}")) as avg_length
                FROM {table_name}
                WHERE "{column_name}" IS NOT NULL
            """).fetchone()

            if string_stats:
                stats.update({
                    "min_length": int(string_stats[0]) if string_stats[0] is not None else None,
                    "max_length": int(string_stats[1]) if string_stats[1] is not None else None,
                    "avg_length": float(string_stats[2]) if string_stats[2] is not None else None
                })

            # Top 10 most common values (if distinct count is reasonable)
            if distinct_count <= 1000:
                top_values = conn.execute(f"""
                    SELECT "{column_name}", COUNT(*) as count
                    FROM {table_name}
                    WHERE "{column_name}" IS NOT NULL
                    GROUP BY "{column_name}"
                    ORDER BY count DESC
                    LIMIT 10
                """).fetchall()

                stats["top_values"] = [
                    {"value": str(val[0]), "count": int(val[1])}
                    for val in top_values
                ]

        elif data_type == 'DATE':
            # Date statistics
            date_stats = conn.execute(f"""
                SELECT
                    MIN("{column_name}") as min_date,
                    MAX("{column_name}") as max_date
                FROM {table_name}
                WHERE "{column_name}" IS NOT NULL
            """).fetchone()

            if date_stats:
                stats.update({
                    "min_date": str(date_stats[0]) if date_stats[0] is not None else None,
                    "max_date": str(date_stats[1]) if date_stats[1] is not None else None
                })

        elif data_type == 'BOOLEAN':
            # Boolean statistics
            bool_stats = conn.execute(f"""
                SELECT
                    SUM(CASE WHEN "{column_name}" = TRUE THEN 1 ELSE 0 END) as true_count,
                    SUM(CASE WHEN "{column_name}" = FALSE THEN 1 ELSE 0 END) as false_count
                FROM {table_name}
                WHERE "{column_name}" IS NOT NULL
            """).fetchone()

            if bool_stats:
                stats.update({
                    "true_count": int(bool_stats[0]) if bool_stats[0] is not None else 0,
                    "false_count": int(bool_stats[1]) if bool_stats[1] is not None else 0
                })

        return stats

    except Exception as e:
        print(f"Error extracting statistics for column {column_name}: {e}")
        # Return basic stats even if detailed stats fail
        return {
            "column_name": column_name,
            "data_type": data_type,
            "null_count": null_count,
            "distinct_count": distinct_count,
            "error": str(e)
        }

# ============================================================================
# COMPREHENSIVE METADATA EXTRACTION
# ============================================================================

def extract_comprehensive_metadata(table_name: str, include_stats: bool = True) -> Dict[str, Any]:
    """
    Extract comprehensive metadata including column-level statistics

    Args:
        table_name: Name of the DuckDB table
        include_stats: Whether to include detailed column statistics (slower)

    Returns:
        Complete metadata dictionary with all information
    """
    conn = get_db_connection()

    # 1. Basic metadata
    basic_metadata = extract_basic_metadata(table_name)

    metadata = {
        "table_name": table_name,
        "extraction_time": datetime.now().isoformat(),
        **basic_metadata
    }

    # 2. Column-level statistics (if requested)
    if include_stats:
        column_stats = []

        for col_info in basic_metadata['columns_info']:
            col_name = col_info['name']
            col_type = col_info['type']

            stats = extract_column_statistics(table_name, col_name, col_type)
            column_stats.append(stats)

        metadata['column_statistics'] = column_stats

    # 3. Data quality metrics
    total_cells = basic_metadata['row_count'] * basic_metadata['column_count']
    total_null_cells = 0

    if include_stats and 'column_statistics' in metadata:
        total_null_cells = sum(col['null_count'] for col in metadata['column_statistics'])

    metadata['data_quality'] = {
        "total_cells": total_cells,
        "null_cells": total_null_cells,
        "completeness_percentage": ((total_cells - total_null_cells) / total_cells * 100) if total_cells > 0 else 0
    }

    return metadata

# ============================================================================
# METADATA COMPARISON
# ============================================================================

def compare_metadata(metadata1: Dict, metadata2: Dict) -> Dict[str, Any]:
    """
    Compare two metadata dictionaries to identify differences
    Useful for detecting schema changes
    """
    differences = {
        "row_count_diff": metadata2['row_count'] - metadata1['row_count'],
        "column_count_diff": metadata2['column_count'] - metadata1['column_count'],
        "added_columns": [],
        "removed_columns": [],
        "type_changes": []
    }

    # Column comparison
    cols1 = {col['name']: col for col in metadata1['columns_info']}
    cols2 = {col['name']: col for col in metadata2['columns_info']}

    # Find added columns
    for col_name in cols2:
        if col_name not in cols1:
            differences['added_columns'].append(col_name)

    # Find removed columns
    for col_name in cols1:
        if col_name not in cols2:
            differences['removed_columns'].append(col_name)

    # Find type changes
    for col_name in cols1:
        if col_name in cols2:
            if cols1[col_name]['type'] != cols2[col_name]['type']:
                differences['type_changes'].append({
                    "column": col_name,
                    "old_type": cols1[col_name]['type'],
                    "new_type": cols2[col_name]['type']
                })

    differences['has_changes'] = (
        differences['row_count_diff'] != 0 or
        differences['column_count_diff'] != 0 or
        len(differences['added_columns']) > 0 or
        len(differences['removed_columns']) > 0 or
        len(differences['type_changes']) > 0
    )

    return differences

# ============================================================================
# METADATA STORAGE
# ============================================================================

def save_metadata_snapshot(dataset_id: str, metadata: Dict[str, Any]) -> bool:
    """
    Save a metadata snapshot for historical tracking
    This could be used to track how datasets evolve over time
    """
    conn = get_db_connection()

    try:
        # Create metadata_snapshots table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata_snapshots (
                snapshot_id VARCHAR PRIMARY KEY,
                dataset_id VARCHAR NOT NULL,
                snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata_json JSON NOT NULL
            )
        """)

        # Insert snapshot
        import uuid
        snapshot_id = str(uuid.uuid4())

        conn.execute("""
            INSERT INTO metadata_snapshots (snapshot_id, dataset_id, metadata_json)
            VALUES (?, ?, ?)
        """, [snapshot_id, dataset_id, json.dumps(metadata)])

        return True

    except Exception as e:
        print(f"Error saving metadata snapshot: {e}")
        return False

def get_metadata_history(dataset_id: str) -> List[Dict]:
    """Get historical metadata snapshots for a dataset"""
    conn = get_db_connection()

    try:
        results = conn.execute("""
            SELECT snapshot_id, snapshot_time, metadata_json
            FROM metadata_snapshots
            WHERE dataset_id = ?
            ORDER BY snapshot_time DESC
        """, [dataset_id]).fetchall()

        return [
            {
                "snapshot_id": row[0],
                "snapshot_time": row[1].isoformat(),
                "metadata": json.loads(row[2])
            }
            for row in results
        ]

    except Exception as e:
        print(f"Error getting metadata history: {e}")
        return []

# ============================================================================
# METADATA FORMATTING
# ============================================================================

def format_metadata_for_display(metadata: Dict[str, Any]) -> str:
    """Format metadata as human-readable text"""
    lines = []
    lines.append("=" * 80)
    lines.append(f"DATASET METADATA: {metadata.get('table_name', 'Unknown')}")
    lines.append("=" * 80)

    # Basic info
    lines.append(f"\nBasic Information:")
    lines.append(f"  Rows: {metadata.get('row_count', 0):,}")
    lines.append(f"  Columns: {metadata.get('column_count', 0)}")
    lines.append(f"  Size: {metadata.get('table_size_bytes', 0):,} bytes")

    # Data quality
    if 'data_quality' in metadata:
        dq = metadata['data_quality']
        lines.append(f"\nData Quality:")
        lines.append(f"  Completeness: {dq.get('completeness_percentage', 0):.2f}%")
        lines.append(f"  Total Cells: {dq.get('total_cells', 0):,}")
        lines.append(f"  Null Cells: {dq.get('null_cells', 0):,}")

    # Columns
    lines.append(f"\nColumns:")
    for col in metadata.get('columns_info', []):
        nullable = "NULL" if col.get('nullable', False) else "NOT NULL"
        lines.append(f"  - {col['name']:<30} {col['type']:<15} {nullable}")

    # Column statistics
    if 'column_statistics' in metadata:
        lines.append(f"\nColumn Statistics:")
        for col_stat in metadata['column_statistics']:
            lines.append(f"\n  {col_stat['column_name']} ({col_stat['data_type']}):")
            lines.append(f"    Distinct values: {col_stat.get('distinct_count', 'N/A')}")
            lines.append(f"    Null values: {col_stat.get('null_count', 0)}")

            if 'min' in col_stat:
                lines.append(f"    Min: {col_stat['min']}")
                lines.append(f"    Max: {col_stat['max']}")
                lines.append(f"    Mean: {col_stat.get('mean', 'N/A')}")
                lines.append(f"    Median: {col_stat.get('median', 'N/A')}")

            if 'min_length' in col_stat:
                lines.append(f"    Min length: {col_stat['min_length']}")
                lines.append(f"    Max length: {col_stat['max_length']}")
                lines.append(f"    Avg length: {col_stat.get('avg_length', 'N/A'):.1f}")

            if 'top_values' in col_stat:
                lines.append(f"    Top values:")
                for tv in col_stat['top_values'][:5]:
                    lines.append(f"      - {tv['value']}: {tv['count']} occurrences")

    lines.append("\n" + "=" * 80)

    return "\n".join(lines)
