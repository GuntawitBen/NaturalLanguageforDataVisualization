import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import {
  MessageSquare,
  Database,
  Play,
  Trash2,
  Search,
  Calendar,
  TrendingUp,
  Zap,
  Clock,
  ChevronRight,
  Sparkles,
  Filter,
  X
} from 'lucide-react';
import './History.css';

// Constellation Animation Component
function ConstellationCanvas() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationId;
    let nodes = [];
    let time = 0;

    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      initNodes();
    };

    const initNodes = () => {
      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;
      nodes = [];

      // Create nodes in a pattern
      for (let i = 0; i < 15; i++) {
        nodes.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.3,
          vy: (Math.random() - 0.5) * 0.3,
          radius: Math.random() * 2 + 1,
          pulse: Math.random() * Math.PI * 2,
          color: Math.random() > 0.7 ? '#ef4444' : '#fbbf24'
        });
      }
    };

    const animate = () => {
      time += 0.02;
      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;

      ctx.clearRect(0, 0, width, height);

      // Update and draw connections
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 120) {
            const opacity = (1 - dist / 120) * 0.3;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(251, 191, 36, ${opacity})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      }

      // Update and draw nodes
      nodes.forEach(node => {
        // Update position
        node.x += node.vx;
        node.y += node.vy;

        // Bounce off edges
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;

        // Pulse effect
        const pulseScale = 1 + Math.sin(time * 2 + node.pulse) * 0.3;
        const radius = node.radius * pulseScale;

        // Glow
        const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, radius * 4);
        gradient.addColorStop(0, node.color + '40');
        gradient.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius * 4, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        // Core
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.fill();
      });

      animationId = requestAnimationFrame(animate);
    };

    resize();
    animate();

    window.addEventListener('resize', resize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="constellation-canvas" />;
}

export default function History() {
  const { sessionToken, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [resuming, setResuming] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [hoveredCard, setHoveredCard] = useState(null);

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
    if (!window.confirm(`Delete "${title || 'this conversation'}"?`)) {
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

      setConversations(prev => prev.filter(c => c.session_id !== sessionId));
    } catch (err) {
      console.error('Error deleting conversation:', err);
      alert('Failed to delete conversation: ' + err.message);
    } finally {
      setDeleting(null);
    }
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
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getTimeOfDay = (dateString) => {
    if (!dateString) return 'day';
    const hour = new Date(dateString).getHours();
    if (hour < 6) return 'night';
    if (hour < 12) return 'morning';
    if (hour < 18) return 'afternoon';
    return 'evening';
  };

  // Get unique datasets for filter
  const uniqueDatasets = useMemo(() => {
    const datasets = new Map();
    conversations.forEach(conv => {
      if (conv.dataset_id && conv.dataset_name) {
        datasets.set(conv.dataset_id, conv.dataset_name);
      }
    });
    return Array.from(datasets, ([id, name]) => ({ id, name }));
  }, [conversations]);

  // Filter conversations
  const filteredConversations = useMemo(() => {
    return conversations.filter(conv => {
      const matchesSearch = !searchQuery ||
        (conv.title?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (conv.first_question?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (conv.dataset_name?.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesDataset = !selectedDataset || conv.dataset_id === selectedDataset;

      return matchesSearch && matchesDataset;
    });
  }, [conversations, searchQuery, selectedDataset]);

  // Stats calculations
  const stats = useMemo(() => {
    const totalMessages = conversations.reduce((sum, c) => sum + (c.message_count || 0), 0);
    const datasetsExplored = uniqueDatasets.length;
    const thisWeek = conversations.filter(c => {
      const date = new Date(c.created_at);
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return date > weekAgo;
    }).length;

    return { totalMessages, datasetsExplored, thisWeek };
  }, [conversations, uniqueDatasets]);

  // Group conversations by date
  const groupedConversations = useMemo(() => {
    const groups = {};
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);

    filteredConversations.forEach(conv => {
      const date = new Date(conv.updated_at || conv.created_at);
      date.setHours(0, 0, 0, 0);

      let key;
      if (date.getTime() === today.getTime()) {
        key = 'Today';
      } else if (date.getTime() === yesterday.getTime()) {
        key = 'Yesterday';
      } else if (date > weekAgo) {
        key = 'This Week';
      } else {
        key = 'Earlier';
      }

      if (!groups[key]) groups[key] = [];
      groups[key].push(conv);
    });

    return groups;
  }, [filteredConversations]);

  if (loading) {
    return (
      <div className="history-page">
        <div className="loading-state">
          <div className="loading-terminal">
            <div className="terminal-header">
              <span className="terminal-dot red"></span>
              <span className="terminal-dot yellow"></span>
              <span className="terminal-dot green"></span>
              <span className="terminal-title">history_loader.exe</span>
            </div>
            <div className="terminal-body">
              <div className="terminal-line">
                <span className="prompt">$</span>
                <span className="command">fetching query history...</span>
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
      <div className="history-page">
        <div className="error-state">
          <div className="error-icon">!</div>
          <p>Failed to load history</p>
          <button onClick={fetchHistory} className="retry-btn">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="history-page">
      {/* Hero Section */}
      <section className="history-hero">
        <div className="hero-bg">
          <ConstellationCanvas />
        </div>
        <div className="hero-content">
          <div className="hero-badge">
            <Sparkles size={14} />
            <span>Query Chronicle</span>
          </div>
          <h1>Your Data Journey</h1>
          <p>Every question you've asked, every insight you've discovered</p>
        </div>
      </section>

      {/* Stats Dashboard */}
      <section className="stats-dashboard">
        <div className="stat-card">
          <div className="stat-icon conversations">
            <MessageSquare size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{conversations.length}</span>
            <span className="stat-label">Conversations</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon messages">
            <Zap size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats.totalMessages}</span>
            <span className="stat-label">Total Queries</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon datasets">
            <Database size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats.datasetsExplored}</span>
            <span className="stat-label">Datasets Explored</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon trending">
            <TrendingUp size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats.thisWeek}</span>
            <span className="stat-label">This Week</span>
          </div>
        </div>
      </section>

      {/* Search and Filter Bar */}
      {conversations.length > 0 && (
        <section className="filter-bar">
          <div className="search-box">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="clear-search" onClick={() => setSearchQuery('')}>
                <X size={14} />
              </button>
            )}
          </div>

          <div className="filter-chips">
            <button
              className={`filter-chip ${!selectedDataset ? 'active' : ''}`}
              onClick={() => setSelectedDataset(null)}
            >
              <Filter size={14} />
              All Datasets
            </button>
            {uniqueDatasets.slice(0, 3).map(dataset => (
              <button
                key={dataset.id}
                className={`filter-chip ${selectedDataset === dataset.id ? 'active' : ''}`}
                onClick={() => setSelectedDataset(selectedDataset === dataset.id ? null : dataset.id)}
              >
                <Database size={14} />
                {dataset.name}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Conversations Timeline */}
      {conversations.length === 0 ? (
        <div className="empty-state">
          <div className="empty-visual">
            <div className="empty-orbit">
              <div className="orbit-ring"></div>
              <div className="orbit-dot"></div>
            </div>
            <MessageSquare size={32} />
          </div>
          <h2>No conversations yet</h2>
          <p>Start exploring your data with natural language queries</p>
          <button className="empty-cta" onClick={() => navigate('/datasets')}>
            <Database size={18} />
            <span>Explore Datasets</span>
            <ChevronRight size={18} />
          </button>
        </div>
      ) : filteredConversations.length === 0 ? (
        <div className="no-results">
          <Search size={48} />
          <h3>No matching conversations</h3>
          <p>Try adjusting your search or filters</p>
        </div>
      ) : (
        <section className="timeline-section">
          {Object.entries(groupedConversations).map(([group, convs]) => (
            <div key={group} className="timeline-group">
              <div className="group-header">
                <Calendar size={14} />
                <span>{group}</span>
                <span className="group-count">{convs.length}</span>
              </div>

              <div className="timeline-cards">
                {convs.map((conv, index) => (
                  <article
                    key={conv.session_id}
                    className={`timeline-card ${hoveredCard === conv.session_id ? 'hovered' : ''}`}
                    style={{ '--delay': `${index * 50}ms` }}
                    onMouseEnter={() => setHoveredCard(conv.session_id)}
                    onMouseLeave={() => setHoveredCard(null)}
                  >
                    <div className="card-timeline-dot">
                      <div className="dot-inner"></div>
                    </div>

                    <div className="card-content">
                      <div className="card-header">
                        <div className="card-title-row">
                          <h3>{conv.title || conv.first_question || 'Untitled Conversation'}</h3>
                          <span className={`time-badge ${getTimeOfDay(conv.updated_at)}`}>
                            <Clock size={12} />
                            {formatRelativeTime(conv.updated_at)}
                          </span>
                        </div>

                        {conv.dataset_name && (
                          <div className="dataset-tag">
                            <Database size={12} />
                            <span>{conv.dataset_name}</span>
                          </div>
                        )}
                      </div>

                      <div className="card-body">
                        <div className="card-stats">
                          <div className="mini-stat">
                            <MessageSquare size={14} />
                            <span>{conv.message_count} messages</span>
                          </div>
                        </div>
                      </div>

                      <div className="card-actions">
                        <button
                          className="action-btn resume"
                          onClick={() => handleResume(conv.session_id, conv.dataset_id)}
                          disabled={resuming === conv.session_id || !conv.dataset_id}
                        >
                          {resuming === conv.session_id ? (
                            <>
                              <div className="btn-spinner"></div>
                              <span>Resuming...</span>
                            </>
                          ) : (
                            <>
                              <Play size={16} />
                              <span>Continue</span>
                              <ChevronRight size={14} className="action-chevron" />
                            </>
                          )}
                        </button>
                        <button
                          className="action-btn delete"
                          onClick={() => handleDelete(conv.session_id, conv.title || conv.first_question)}
                          disabled={deleting === conv.session_id}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
