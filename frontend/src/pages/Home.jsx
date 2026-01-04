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

      {/* Avatar with Floating Stats */}
      <div className="avatar-stats-container">
        {/* Avatar in center */}
        <div className="avatar-section">
          <div className="avatar-placeholder">
            <img src={avatarImage} alt="User Avatar" className="avatar" />
          </div>
        </div>

        {/* Floating Statistics Cards */}
        <div className="stat-card floating-stat top-left">
          <div className="stat-icon">
            <Database size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Datasets</p>
            <p className="stat-value">{datasets.length}</p>
          </div>
        </div>

        <div className="stat-card floating-stat top-right upload-card">
            <div className="stat-icon">
              <Upload size={24} />
            </div>
            {/*<h3 className="stat-label">Upload New Dataset</h3>*/}
            <button
              className="upload-card-button"
              onClick={() => navigate('/data-cleaning')}
            >
              Upload Dataset
            </button>
          </div>

        <div className="stat-card floating-stat bottom-right">
          <div className="stat-icon">
            <FileText size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Storage</p>
            <p className="stat-value">{formatFileSize(totalSize)}</p>
          </div>
        </div>

        <div className="stat-card floating-stat bottom-left">
            <div className="stat-icon">
                <Upload size={24} />
            </div>
            {/*<h3 className="stat-label">Upload New Dataset</h3>*/}
            <button
                className="upload-card-button"
                onClick={() => navigate('/recents')}
            >
                View Recents
            </button>
        </div>
      </div>
    </div>
  );
}
