import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import {
  Database,
  FileText,
  Trash2,
  Eye,
  BarChart3,
  Grid3X3,
  List,
  Search,
  Upload,
  Calendar,
  HardDrive,
  Layers,
  TrendingUp,
  Zap,
  Terminal,
  ChevronRight,
  Sparkles,
  Activity,
  Clock,
  Filter,
  SortDesc,
  Plus,
  X
} from 'lucide-react';
import './Datasets.css';

export default function Datasets() {
  const { sessionToken, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('recent');
  const [deleteConfirm, setDeleteConfirm] = useState(null);

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

      setDeleteConfirm(null);
      fetchDatasets();
    } catch (err) {
      console.error('Error deleting dataset:', err);
      alert('Failed to delete dataset: ' + err.message);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      if (diffHours === 0) {
        const diffMins = Math.floor(diffMs / (1000 * 60));
        return `${diffMins}m ago`;
      }
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    }

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 10) / 10 + ' ' + sizes[i];
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  };

  // Stats calculations
  const stats = useMemo(() => {
    const totalRows = datasets.reduce((acc, d) => acc + d.row_count, 0);
    const totalSize = datasets.reduce((acc, d) => acc + d.file_size_bytes, 0);
    const totalCols = datasets.reduce((acc, d) => acc + d.column_count, 0);
    return { totalRows, totalSize, totalCols, count: datasets.length };
  }, [datasets]);

  // Filtered and sorted datasets
  const filteredDatasets = useMemo(() => {
    let filtered = datasets.filter(d =>
      d.dataset_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
    );

    switch (sortBy) {
      case 'recent':
        filtered.sort((a, b) => new Date(b.upload_date) - new Date(a.upload_date));
        break;
      case 'name':
        filtered.sort((a, b) => a.dataset_name.localeCompare(b.dataset_name));
        break;
      case 'size':
        filtered.sort((a, b) => b.file_size_bytes - a.file_size_bytes);
        break;
      case 'rows':
        filtered.sort((a, b) => b.row_count - a.row_count);
        break;
      default:
        break;
    }

    return filtered;
  }, [datasets, searchQuery, sortBy]);

  // Generate random sparkline data for visual effect
  const getSparklineData = (seed) => {
    const data = [];
    let value = 50;
    for (let i = 0; i < 12; i++) {
      value = Math.max(10, Math.min(90, value + (Math.sin(seed + i) * 20)));
      data.push(value);
    }
    return data;
  };

  if (loading) {
    return (
      <div className="datasets-page">
        <div className="loading-state">
          <div className="loading-terminal">
            <div className="terminal-header">
              <span className="terminal-dot red"></span>
              <span className="terminal-dot yellow"></span>
              <span className="terminal-dot green"></span>
              <span className="terminal-title">data_loader.exe</span>
            </div>
            <div className="terminal-body">
              <div className="terminal-line">
                <span className="prompt">$</span>
                <span className="command">fetching datasets...</span>
                <span className="cursor"></span>
              </div>
              <div className="loading-bar">
                <div className="loading-progress"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="datasets-page">
        <div className="error-state">
          <div className="error-icon">
            <Terminal size={32} />
          </div>
          <h2>Connection Failed</h2>
          <p className="error-code">ERROR: {error}</p>
          <button onClick={fetchDatasets} className="retry-btn">
            <Zap size={16} />
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="datasets-page">
      {/* Header Section */}
      <header className="page-header">
        <div className="header-left">
          <div className="header-icon">
            <Database size={24} />
            <div className="icon-pulse"></div>
          </div>
          <div className="header-text">
            <h1>
              <span className="text-muted">~/</span>datasets
              <span className="header-cursor">_</span>
            </h1>
            <p className="header-subtitle">
              <Activity size={12} />
              <span>{datasets.length} active connections</span>
            </p>
          </div>
        </div>

        <button className="upload-btn" onClick={() => navigate('/data-cleaning')}>
          <Plus size={18} />
          <span>New Dataset</span>
          <div className="btn-shine"></div>
        </button>
      </header>

      {/* Stats Dashboard */}
      {datasets.length > 0 && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <Layers size={20} />
            </div>
            <div className="stat-content">
              <span className="stat-value">{stats.count}</span>
              <span className="stat-label">Datasets</span>
            </div>
            <div className="stat-indicator up">
              <TrendingUp size={14} />
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon blue">
              <BarChart3 size={20} />
            </div>
            <div className="stat-content">
              <span className="stat-value">{formatNumber(stats.totalRows)}</span>
              <span className="stat-label">Total Rows</span>
            </div>
            <svg className="stat-sparkline" viewBox="0 0 60 30">
              <polyline
                fill="none"
                stroke="rgba(59, 130, 246, 0.5)"
                strokeWidth="2"
                points={getSparklineData(1).map((v, i) => `${i * 5},${30 - v * 0.3}`).join(' ')}
              />
            </svg>
          </div>

          <div className="stat-card">
            <div className="stat-icon purple">
              <Grid3X3 size={20} />
            </div>
            <div className="stat-content">
              <span className="stat-value">{stats.totalCols}</span>
              <span className="stat-label">Total Columns</span>
            </div>
            <svg className="stat-sparkline" viewBox="0 0 60 30">
              <polyline
                fill="none"
                stroke="rgba(168, 85, 247, 0.5)"
                strokeWidth="2"
                points={getSparklineData(2).map((v, i) => `${i * 5},${30 - v * 0.3}`).join(' ')}
              />
            </svg>
          </div>

          <div className="stat-card">
            <div className="stat-icon green">
              <HardDrive size={20} />
            </div>
            <div className="stat-content">
              <span className="stat-value">{formatFileSize(stats.totalSize)}</span>
              <span className="stat-label">Storage Used</span>
            </div>
            <div className="storage-bar">
              <div className="storage-fill" style={{ width: '45%' }}></div>
            </div>
          </div>
        </div>
      )}

      {/* Controls Bar */}
      <div className="controls-bar">
        <div className="search-container">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search datasets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          {searchQuery && (
            <button className="search-clear" onClick={() => setSearchQuery('')}>
              <X size={14} />
            </button>
          )}
        </div>

        <div className="controls-right">
          <div className="sort-dropdown">
            <Filter size={14} />
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="recent">Recent</option>
              <option value="name">Name</option>
              <option value="size">Size</option>
              <option value="rows">Rows</option>
            </select>
          </div>

          <div className="view-toggle">
            <button
              className={`toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid view"
            >
              <Grid3X3 size={16} />
            </button>
            <button
              className={`toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              title="List view"
            >
              <List size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Empty State */}
      {datasets.length === 0 ? (
        <div className="empty-state">
          <div className="empty-visual">
            <div className="empty-rings">
              <div className="ring ring-1"></div>
              <div className="ring ring-2"></div>
              <div className="ring ring-3"></div>
            </div>
            <div className="empty-icon">
              <Database size={40} />
            </div>
          </div>
          <h2>No Data Sources</h2>
          <p>Initialize your first dataset to begin analysis</p>
          <button className="empty-cta" onClick={() => navigate('/data-cleaning')}>
            <Upload size={18} />
            <span>Upload Dataset</span>
            <Sparkles size={16} className="sparkle" />
          </button>
          <div className="empty-hint">
            <Terminal size={12} />
            <code>Supported: .csv, .xlsx, .json</code>
          </div>
        </div>
      ) : filteredDatasets.length === 0 ? (
        <div className="no-results">
          <Search size={24} />
          <p>No datasets match "{searchQuery}"</p>
          <button onClick={() => setSearchQuery('')}>Clear search</button>
        </div>
      ) : (
        <>
          {/* Grid View */}
          {viewMode === 'grid' && (
            <div className="datasets-grid">
              {filteredDatasets.map((dataset, index) => (
                <div
                  key={dataset.dataset_id}
                  className="dataset-card"
                  style={{ '--index': index }}
                  onClick={() => navigate(`/datasets/${dataset.dataset_id}`)}
                >
                  <div className="card-glow"></div>

                  <div className="card-header">
                    <div className="card-icon">
                      <FileText size={20} />
                    </div>
                    <div className="card-badge">
                      <Clock size={10} />
                      {formatDate(dataset.upload_date)}
                    </div>
                  </div>

                  <div className="card-body">
                    <h3 className="card-title">{dataset.dataset_name}</h3>
                    <p className="card-filename">{dataset.original_filename}</p>

                    <div className="card-metrics">
                      <div className="metric">
                        <BarChart3 size={14} />
                        <span>{formatNumber(dataset.row_count)}</span>
                        <label>rows</label>
                      </div>
                      <div className="metric">
                        <Grid3X3 size={14} />
                        <span>{dataset.column_count}</span>
                        <label>cols</label>
                      </div>
                      <div className="metric">
                        <HardDrive size={14} />
                        <span>{formatFileSize(dataset.file_size_bytes)}</span>
                      </div>
                    </div>

                    {/* Mini visualization */}
                    <div className="card-viz">
                      <svg viewBox="0 0 100 24" preserveAspectRatio="none">
                        <defs>
                          <linearGradient id={`grad-${dataset.dataset_id}`} x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stopColor="var(--accent-yellow)" stopOpacity="0.3" />
                            <stop offset="100%" stopColor="var(--accent-yellow)" stopOpacity="0" />
                          </linearGradient>
                        </defs>
                        <path
                          d={`M0,24 ${getSparklineData(dataset.row_count).map((v, i) => `L${i * 9},${24 - v * 0.24}`).join(' ')} L100,24 Z`}
                          fill={`url(#grad-${dataset.dataset_id})`}
                        />
                        <polyline
                          fill="none"
                          stroke="var(--accent-yellow)"
                          strokeWidth="1.5"
                          points={getSparklineData(dataset.row_count).map((v, i) => `${i * 9},${24 - v * 0.24}`).join(' ')}
                        />
                      </svg>
                    </div>
                  </div>

                  <div className="card-footer">
                    <button
                      className="card-action view"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/datasets/${dataset.dataset_id}`);
                      }}
                    >
                      <Eye size={14} />
                      <span>Explore</span>
                    </button>
                    <button
                      className="card-action delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteConfirm(dataset);
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* List View */}
          {viewMode === 'list' && (
            <div className="datasets-list">
              <div className="list-header">
                <span className="col-name">Dataset</span>
                <span className="col-stats">Statistics</span>
                <span className="col-size">Size</span>
                <span className="col-date">Modified</span>
                <span className="col-actions">Actions</span>
              </div>
              {filteredDatasets.map((dataset, index) => (
                <div
                  key={dataset.dataset_id}
                  className="list-row"
                  style={{ '--index': index }}
                  onClick={() => navigate(`/datasets/${dataset.dataset_id}`)}
                >
                  <div className="col-name">
                    <div className="row-icon">
                      <FileText size={16} />
                    </div>
                    <div className="row-info">
                      <span className="row-title">{dataset.dataset_name}</span>
                      <span className="row-filename">{dataset.original_filename}</span>
                    </div>
                  </div>

                  <div className="col-stats">
                    <span className="stat-chip">
                      <BarChart3 size={12} />
                      {formatNumber(dataset.row_count)} rows
                    </span>
                    <span className="stat-chip">
                      <Grid3X3 size={12} />
                      {dataset.column_count} cols
                    </span>
                  </div>

                  <div className="col-size">
                    <span className="size-value">{formatFileSize(dataset.file_size_bytes)}</span>
                  </div>

                  <div className="col-date">
                    <Clock size={12} />
                    <span>{formatDate(dataset.upload_date)}</span>
                  </div>

                  <div className="col-actions">
                    <button
                      className="row-action"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/datasets/${dataset.dataset_id}`);
                      }}
                    >
                      <ChevronRight size={16} />
                    </button>
                    <button
                      className="row-action danger"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteConfirm(dataset);
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-icon">
              <Trash2 size={24} />
            </div>
            <h3>Delete Dataset</h3>
            <p>
              Are you sure you want to delete <strong>"{deleteConfirm.dataset_name}"</strong>?
              This action cannot be undone.
            </p>
            <div className="modal-actions">
              <button className="modal-btn cancel" onClick={() => setDeleteConfirm(null)}>
                Cancel
              </button>
              <button
                className="modal-btn confirm"
                onClick={() => handleDelete(deleteConfirm.dataset_id, deleteConfirm.dataset_name)}
              >
                <Trash2 size={14} />
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
