import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import {
  Database,
  Calendar,
  FileText,
  Trash2,
  Eye,
  BarChart3,
  Upload,
  TrendingUp
} from 'lucide-react';
import './Home.css';

export default function Home() {
  const { user, sessionToken, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  // Calculate statistics
  const totalRows = datasets.reduce((sum, ds) => sum + ds.row_count, 0);
  const totalSize = datasets.reduce((sum, ds) => sum + ds.file_size_bytes, 0);

  if (loading) {
    return (
      <div className="home-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading your data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="home-page">
      {/* Header with Welcome */}
      <div className="home-header">
        <div>
          <h1>Welcome back, {user?.name || 'User'}!</h1>
          <p className="subtitle">Manage your datasets and visualizations</p>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">
            <Database size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Datasets</p>
            <p className="stat-value">{datasets.length}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <BarChart3 size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Rows</p>
            <p className="stat-value">{totalRows.toLocaleString()}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <FileText size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Storage</p>
            <p className="stat-value">{formatFileSize(totalSize)}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <TrendingUp size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Account</p>
            <p className="stat-value">{user?.email}</p>
          </div>
        </div>
      </div>

      {/* Datasets Section */}
      <div className="datasets-section">
        <div className="section-header">
          <div>
            <h2>My Datasets</h2>
            <p className="section-subtitle">
              {datasets.length} {datasets.length === 1 ? 'dataset' : 'datasets'} available
            </p>
          </div>
          <button
            className="upload-button"
            onClick={() => navigate('/upload')}
          >
            <Upload size={20} />
            Upload Dataset
          </button>
        </div>

        {error && (
          <div className="error-container">
            <p className="error-message">Error: {error}</p>
            <button onClick={fetchDatasets} className="retry-button">
              Retry
            </button>
          </div>
        )}

        {datasets.length === 0 ? (
          <div className="empty-state">
            <Database size={64} className="empty-icon" />
            <h3>No datasets yet</h3>
            <p>Upload your first CSV file to get started with data visualization</p>
            <button
              className="upload-button-large"
              onClick={() => navigate('/upload')}
            >
              <Upload size={20} />
              Upload Your First Dataset
            </button>
          </div>
        ) : (
          <div className="datasets-grid">
            {datasets.map((dataset) => (
              <div key={dataset.dataset_id} className="dataset-card">
                <div className="dataset-card-header">
                  <div className="dataset-icon">
                    <FileText size={24} />
                  </div>
                  <div className="dataset-info">
                    <h3>{dataset.dataset_name}</h3>
                    <p className="dataset-filename">{dataset.original_filename}</p>
                  </div>
                </div>

                <div className="dataset-stats">
                  <div className="stat">
                    <BarChart3 size={16} />
                    <span>{dataset.row_count.toLocaleString()} rows</span>
                  </div>
                  <div className="stat">
                    <Database size={16} />
                    <span>{dataset.column_count} columns</span>
                  </div>
                  <div className="stat">
                    <Calendar size={16} />
                    <span>{formatDate(dataset.upload_date)}</span>
                  </div>
                  <div className="stat">
                    <FileText size={16} />
                    <span>{formatFileSize(dataset.file_size_bytes)}</span>
                  </div>
                </div>

                <div className="dataset-actions">
                  <button
                    className="action-button view"
                    onClick={() => navigate(`/datasets/${dataset.dataset_id}`)}
                    title="View details"
                  >
                    <Eye size={18} />
                    View
                  </button>
                  <button
                    className="action-button delete"
                    onClick={() => handleDelete(dataset.dataset_id, dataset.dataset_name)}
                    title="Delete dataset"
                  >
                    <Trash2 size={18} />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
