import { useState, useEffect } from 'react';
import { API_ENDPOINTS } from '../config';
import DataTable from './DataTable';
import './DataPreviewPanel.css';

export default function DataPreviewPanel({ tempFilePath, datasetName, sessionToken, refreshKey }) {
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (tempFilePath) {
      fetchPreview();
    }
  }, [tempFilePath, refreshKey]);

  const fetchPreview = async () => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('temp_file_path', tempFilePath);
      formData.append('limit', '100');

      const response = await fetch(API_ENDPOINTS.DATASETS.PREVIEW_TEMP, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to load preview');
      }

      const result = await response.json();
      setPreviewData(result);
    } catch (err) {
      console.error('Error fetching preview:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="data-preview-panel">
      <div className="panel-header">
        <div className="header-content">
          <h3>Data Preview</h3>
          {previewData && (
            <div className="data-stats">
              <span className="stat-item">
                <strong>{previewData.row_count.toLocaleString()}</strong> rows
              </span>
              <span className="stat-separator">×</span>
              <span className="stat-item">
                <strong>{previewData.column_count}</strong> columns
              </span>
            </div>
          )}
        </div>
        {previewData && (
          <span className="preview-note">
            Showing first {previewData.showing_rows} rows
          </span>
        )}
      </div>

      <DataTable
        data={previewData?.data}
        columns={previewData?.columns}
        columnsInfo={previewData?.columns_info}
        loading={loading}
        error={error}
      />
    </div>
  );
}
