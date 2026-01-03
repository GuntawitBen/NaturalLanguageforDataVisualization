import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import { ArrowLeft, Download, Database } from 'lucide-react';
import './DatasetDetails.css';

export default function DatasetDetails() {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const { sessionToken } = useAuth();
  const [dataset, setDataset] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDatasetDetails();
  }, [datasetId]);

  const fetchDatasetDetails = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch dataset metadata
      const metadataResponse = await fetch(API_ENDPOINTS.DATASETS.GET(datasetId), {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!metadataResponse.ok) {
        throw new Error('Failed to fetch dataset details');
      }

      const metadata = await metadataResponse.json();
      setDataset(metadata);

      // Fetch preview data
      const previewResponse = await fetch(`${API_ENDPOINTS.DATASETS.PREVIEW(datasetId)}?limit=100`, {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!previewResponse.ok) {
        throw new Error('Failed to fetch preview data');
      }

      const preview = await previewResponse.json();
      setPreviewData(preview);
    } catch (err) {
      console.error('Error fetching dataset:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="dataset-details-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading dataset...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dataset-details-page">
        <div className="error-container">
          <p className="error-message">Error: {error}</p>
          <button onClick={() => navigate('/datasets')} className="back-button">
            Back to Datasets
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dataset-details-page">
      {/* Header */}
      <div className="details-header">
        <button onClick={() => navigate('/datasets')} className="back-button">
          <ArrowLeft size={20} />
          Back to Datasets
        </button>

        <div className="dataset-info">
          <h1>{dataset?.dataset_name}</h1>
          <p className="dataset-filename">{dataset?.original_filename}</p>
        </div>

        <div className="header-stats">
          <div className="stat-badge">
            <Database size={16} />
            {dataset?.row_count?.toLocaleString()} rows
          </div>
          <div className="stat-badge">
            <Database size={16} />
            {dataset?.column_count} columns
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="data-table-container">
        <div className="table-header">
          <h2>Raw Data Preview</h2>
          <p className="table-subtitle">
            Showing {previewData?.showing_rows} of {dataset?.row_count?.toLocaleString()} rows
          </p>
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                {previewData?.columns?.map((column, index) => (
                  <th key={index}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {previewData?.data?.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex}>{cell !== null ? cell : '—'}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
