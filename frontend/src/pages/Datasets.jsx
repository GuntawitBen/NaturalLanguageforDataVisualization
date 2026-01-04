import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import { Database, Calendar, FileText, Trash2, Eye, BarChart3, ChevronDown, ChevronUp } from 'lucide-react';
import './Datasets.css';

export default function Datasets() {
  const { sessionToken, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    fetchDatasets();
  }, [isAuthenticated, navigate]);

  const fetchDatasets = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(API_ENDPOINTS.DATASETS.LIST, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch datasets');
      }

      const data = await response.json();
      setDatasets(data);
    } catch (err) {
      console.error('Error fetching datasets:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (datasetId, datasetName) => {
    if (!window.confirm(`Are you sure you want to delete "${datasetName}"?`)) {
      return;
    }

    try {
      const response = await fetch(API_ENDPOINTS.DATASETS.DELETE(datasetId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete dataset');
      }

      // Refresh the list
      fetchDatasets();
    } catch (err) {
      console.error('Error deleting dataset:', err);
      alert('Failed to delete dataset: ' + err.message);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="datasets-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading your datasets...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="datasets-page">
        <div className="error-container">
          <p className="error-message">Error: {error}</p>
          <button onClick={fetchDatasets} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="datasets-page">
      <div className="datasets-header">
        <div>
          <h1>My Datasets</h1>
          <p className="subtitle">
            {datasets.length} {datasets.length === 1 ? 'dataset' : 'datasets'} available
          </p>
        </div>
        <button
          className="upload-button"
          onClick={() => navigate('/data-cleaning')}
        >
          <Database size={20} />
          Upload Dataset
        </button>
      </div>

      {datasets.length === 0 ? (
        <div className="empty-state">
          <Database size={64} className="empty-icon" />
          <h2>No datasets yet</h2>
          <p>Upload your first CSV file to get started with data visualization</p>
          <button
            className="upload-button-large"
            onClick={() => navigate('/data-cleaning')}
          >
            Upload Your First Dataset
          </button>
        </div>
      ) : (
        <div className="datasets-list">
          {datasets.map((dataset) => {
            const isExpanded = expandedId === dataset.dataset_id;
            return (
              <div key={dataset.dataset_id} className="dataset-row">
                <div
                  className="dataset-row-header"
                  onClick={() => setExpandedId(isExpanded ? null : dataset.dataset_id)}
                >
                  <div className="dataset-row-main">
                    <FileText size={20} className="dataset-row-icon" />
                    <div className="dataset-row-info">
                      <h3>{dataset.dataset_name}</h3>
                      <span className="dataset-row-filename">{dataset.original_filename}</span>
                    </div>
                  </div>

                  <div className="dataset-row-stats">
                    <span className="stat-badge">
                      <BarChart3 size={14} />
                      {dataset.row_count.toLocaleString()} rows
                    </span>
                    <span className="stat-badge">
                      <Database size={14} />
                      {dataset.column_count} cols
                    </span>
                    <span className="stat-badge">
                      <FileText size={14} />
                      {formatFileSize(dataset.file_size_bytes)}
                    </span>
                  </div>

                  <button className="expand-button">
                    {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </button>
                </div>

                {isExpanded && (
                  <div className="dataset-row-details">
                    <div className="details-content">
                      <div className="detail-item">
                        <Calendar size={16} />
                        <div>
                          <span className="detail-label">Uploaded</span>
                          <span className="detail-value">{formatDate(dataset.upload_date)}</span>
                        </div>
                      </div>

                      <div className="detail-item">
                        <BarChart3 size={16} />
                        <div>
                          <span className="detail-label">Total Rows</span>
                          <span className="detail-value">{dataset.row_count.toLocaleString()}</span>
                        </div>
                      </div>

                      <div className="detail-item">
                        <Database size={16} />
                        <div>
                          <span className="detail-label">Total Columns</span>
                          <span className="detail-value">{dataset.column_count}</span>
                        </div>
                      </div>

                      <div className="detail-item">
                        <FileText size={16} />
                        <div>
                          <span className="detail-label">File Size</span>
                          <span className="detail-value">{formatFileSize(dataset.file_size_bytes)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="details-actions">
                      <button
                        className="action-button view"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/datasets/${dataset.dataset_id}`);
                        }}
                      >
                        <Eye size={18} />
                        View Details
                      </button>
                      <button
                        className="action-button delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(dataset.dataset_id, dataset.dataset_name);
                        }}
                      >
                        <Trash2 size={18} />
                        Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
