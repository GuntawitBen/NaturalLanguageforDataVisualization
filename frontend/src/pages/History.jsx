import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import {
  MessageSquare,
  Calendar,
  Database,
  ChevronDown,
  ChevronUp,
  Play,
  Clock,
  Trash2
} from 'lucide-react';
import './History.css';

export default function History() {
  const { sessionToken, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [resuming, setResuming] = useState(null);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    fetchHistory();
  }, [isAuthenticated, navigate]);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(API_ENDPOINTS.TEXT_TO_SQL.HISTORY, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch history');
      }

      const data = await response.json();
      setConversations(data.conversations || []);
    } catch (err) {
      console.error('Error fetching history:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async (sessionId, datasetId) => {
    setResuming(sessionId);

    try {
      const response = await fetch(API_ENDPOINTS.TEXT_TO_SQL.RESUME_SESSION(sessionId), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to resume session');
      }

      // Navigate to the dataset details page with the resumed session
      navigate(`/datasets/${datasetId}`, {
        state: {
          resumedSessionId: sessionId,
          openChat: true
        }
      });
    } catch (err) {
      console.error('Error resuming session:', err);
      alert('Failed to resume session: ' + err.message);
    } finally {
      setResuming(null);
    }
  };

  const handleDelete = async (sessionId, title) => {
    if (!window.confirm(`Are you sure you want to delete "${title || 'this conversation'}"?`)) {
      return;
    }

    setDeleting(sessionId);

    try {
      const response = await fetch(API_ENDPOINTS.TEXT_TO_SQL.DELETE_HISTORY(sessionId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete conversation');
      }

      // Remove from local state
      setConversations(prev => prev.filter(c => c.session_id !== sessionId));

      // Collapse if expanded
      if (expandedId === sessionId) {
        setExpandedId(null);
      }
    } catch (err) {
      console.error('Error deleting conversation:', err);
      alert('Failed to delete conversation: ' + err.message);
    } finally {
      setDeleting(null);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatRelativeTime = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateString);
  };

  if (loading) {
    return (
      <div className="history-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading your conversation history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="history-page">
        <div className="error-container">
          <p className="error-message">Error: {error}</p>
          <button onClick={fetchHistory} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="history-page">
      <div className="history-header">
        <div>
          <h1>Conversation History</h1>
          <p className="subtitle">
            {conversations.length} {conversations.length === 1 ? 'conversation' : 'conversations'} saved
          </p>
        </div>
      </div>

      {conversations.length === 0 ? (
        <div className="empty-state">
          <MessageSquare size={64} className="empty-icon" />
          <h2>No conversations yet</h2>
          <p>Start asking questions about your datasets to build your history</p>
          <button
            className="start-button"
            onClick={() => navigate('/datasets')}
          >
            <Database size={20} />
            Go to Datasets
          </button>
        </div>
      ) : (
        <div className="history-list">
          {conversations.map((conv) => {
            const isExpanded = expandedId === conv.session_id;
            return (
              <div key={conv.session_id} className="history-row">
                <div
                  className="history-row-header"
                  onClick={() => setExpandedId(isExpanded ? null : conv.session_id)}
                >
                  <div className="history-row-main">
                    <MessageSquare size={20} className="history-row-icon" />
                    <div className="history-row-info">
                      <h3>{conv.title || conv.first_question || 'Untitled Conversation'}</h3>
                      {conv.dataset_name && (
                        <span className="history-row-dataset">
                          <Database size={14} />
                          {conv.dataset_name}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="history-row-stats">
                    <span className="stat-badge">
                      <MessageSquare size={14} />
                      {conv.message_count} messages
                    </span>
                    <span className="stat-badge time">
                      <Clock size={14} />
                      {formatRelativeTime(conv.updated_at)}
                    </span>
                  </div>

                  <button className="expand-button">
                    {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </button>
                </div>

                {isExpanded && (
                  <div className="history-row-details">
                    <div className="details-content">
                      <div className="detail-item">
                        <Calendar size={16} />
                        <div>
                          <span className="detail-label">Started</span>
                          <span className="detail-value">{formatDate(conv.created_at)}</span>
                        </div>
                      </div>

                      <div className="detail-item">
                        <Clock size={16} />
                        <div>
                          <span className="detail-label">Last Activity</span>
                          <span className="detail-value">{formatDate(conv.updated_at)}</span>
                        </div>
                      </div>

                      <div className="detail-item">
                        <MessageSquare size={16} />
                        <div>
                          <span className="detail-label">Messages</span>
                          <span className="detail-value">{conv.message_count}</span>
                        </div>
                      </div>

                      {conv.dataset_name && (
                        <div className="detail-item">
                          <Database size={16} />
                          <div>
                            <span className="detail-label">Dataset</span>
                            <span className="detail-value">{conv.dataset_name}</span>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="details-actions">
                      <button
                        className="action-button resume"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleResume(conv.session_id, conv.dataset_id);
                        }}
                        disabled={resuming === conv.session_id || !conv.dataset_id}
                      >
                        <Play size={18} />
                        {resuming === conv.session_id ? 'Resuming...' : 'Resume'}
                      </button>
                      <button
                        className="action-button delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(conv.session_id, conv.title || conv.first_question);
                        }}
                        disabled={deleting === conv.session_id}
                      >
                        <Trash2 size={18} />
                        {deleting === conv.session_id ? 'Deleting...' : 'Delete'}
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
