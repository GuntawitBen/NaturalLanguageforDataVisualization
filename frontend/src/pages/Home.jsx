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
import avatarImage from '../assets/avatar.png';
import './Home.css';

export default function Home() {
  const { user, sessionToken, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [greeting, setGreeting] = useState('');

  // Get randomized greeting
  useEffect(() => {
    const getGreeting = () => {
      const hour = new Date().getHours();

      // Time-based greetings
      const timeBasedGreetings = [];
      if (hour < 12) {
        timeBasedGreetings.push('Good morning', 'Morning', 'Rise and shine');
      } else if (hour < 17) {
        timeBasedGreetings.push('Good afternoon', 'Good day', 'Afternoon');
      } else {
        timeBasedGreetings.push('Good evening', 'Evening');
      }

      // General greetings (available anytime)
      const generalGreetings = [
        'Welcome back',
        'Hello',
        'Hi there',
        'Hey',
        'Greetings',
        'Nice to see you',
        'Great to have you back',
        'Welcome',
        'Happy to see you',
      ];

      // Combine all greetings
      const allGreetings = [...timeBasedGreetings, ...generalGreetings];

      // Pick random greeting
      const randomGreeting = allGreetings[Math.floor(Math.random() * allGreetings.length)];
      return randomGreeting;
    };

    setGreeting(getGreeting());
  }, []);

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

  // Get user initials for avatar
  const getUserInitials = () => {
    if (!user?.name) return 'U';
    const nameParts = user.name.trim().split(' ');
    if (nameParts.length === 1) {
      return nameParts[0].charAt(0).toUpperCase();
    }
    const firstInitial = nameParts[0].charAt(0).toUpperCase();
    const lastInitial = nameParts[nameParts.length - 1].charAt(0).toUpperCase();
    return firstInitial + lastInitial;
  };

  return (
    <div className="home-page">
      {/* Header with Welcome */}
      <div className="home-header">
        <div>
          <h1>{greeting}, {user?.name || 'User'}!</h1>
          <p className="subtitle">Manage your datasets and visualizations</p>
        </div>
      </div>

      {/* Statistics Section */}
      <div className="stats-grid">
        {/* Total Datasets Card */}
        <div className="stat-card">
          <div className="stat-icon">
            <Database size={28} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Datasets</p>
            <p className="stat-value">{datasets.length}</p>
          </div>
        </div>

        {/* Total Rows Card */}
        <div className="stat-card">
          <div className="stat-icon">
            <BarChart3 size={28} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Rows</p>
            <p className="stat-value">{totalRows.toLocaleString()}</p>
          </div>
        </div>

        {/* Total Storage Card */}
        <div className="stat-card">
          <div className="stat-icon">
            <FileText size={28} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Storage</p>
            <p className="stat-value">{formatFileSize(totalSize)}</p>
          </div>
        </div>
      </div>

      {/* Recent Datasets Section */}
      <div className="datasets-section">
        <div className="section-header">
          <div>
            <h2>Recent Datasets</h2>
            <p className="section-subtitle">
              {datasets.length === 0 ? 'No datasets yet' : `Showing ${Math.min(6, datasets.length)} of ${datasets.length}`}
            </p>
          </div>
          <button
            className="upload-button"
            onClick={() => navigate('/data-cleaning')}
          >
            <Upload size={20} />
            Upload Dataset
          </button>
        </div>

        {datasets.length === 0 ? (
          <div className="empty-state">
            <Database size={64} className="empty-icon" />
            <h3>No datasets yet</h3>
            <p>Upload your first CSV file to get started with data visualization</p>
            <button
              className="upload-button-large"
              onClick={() => navigate('/data-cleaning')}
            >
              <Upload size={20} />
              Upload Your First Dataset
            </button>
          </div>
        ) : (
          <div className="datasets-grid">
            {datasets.slice(0, 6).map((dataset) => (
              <div key={dataset.dataset_id} className="dataset-card">
                {/* Card Header */}
                <div className="dataset-card-header">
                  <div className="dataset-icon">
                    <FileText size={24} />
                  </div>
                  <div className="dataset-info">
                    <h3>{dataset.dataset_name}</h3>
                    <p className="dataset-filename">{dataset.original_filename}</p>
                  </div>
                </div>

                {/* Card Stats */}
                <div className="dataset-stats">
                  <div className="stat">
                    <BarChart3 size={16} />
                    {dataset.row_count.toLocaleString()} rows
                  </div>
                  <div className="stat">
                    <Database size={16} />
                    {dataset.column_count} cols
                  </div>
                  <div className="stat">
                    <Calendar size={16} />
                    {formatDate(dataset.upload_date)}
                  </div>
                  <div className="stat">
                    <FileText size={16} />
                    {formatFileSize(dataset.file_size_bytes)}
                  </div>
                </div>

                {/* Card Actions */}
                <div className="dataset-actions">
                  <button
                    className="action-button view"
                    onClick={() => navigate(`/datasets/${dataset.dataset_id}`)}
                  >
                    <Eye size={16} />
                    View
                  </button>
                  <button
                    className="action-button delete"
                    onClick={() => handleDelete(dataset.dataset_id, dataset.dataset_name)}
                  >
                    <Trash2 size={16} />
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
