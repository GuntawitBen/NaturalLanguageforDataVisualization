import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import { Responsive as ResponsiveGridLayout, useContainerWidth } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import {
  ArrowLeft,
  ChevronDown,
  Send,
  Sparkles,
  Plus,
  MessageSquare,
  Trash2,
  Database,
  BarChart3,
  Grid3X3,
  HardDrive,
  Calendar,
  FileText,
  Terminal,
  Zap,
  Activity,
  Table,
  MessageCircle,
  LayoutDashboard,
  Clock,
  ChevronRight,
  X,
  Code,
  Play,
  Loader2,
  AlertCircle,
  Eye,
  TrendingUp
} from 'lucide-react';
import DataTable from '../components/DataTable';
import ChartRenderer from '../components/ChartRenderer';
import '../components/DataPreviewPanel.css';
import './DatasetDetails.css';

export default function DatasetDetails() {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { sessionToken } = useAuth();

  const resumedSessionId = location.state?.resumedSessionId;
  const [dataset, setDataset] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('conversations');
  const [showInfoPanel, setShowInfoPanel] = useState(false);

  // Conversations tab state
  const [conversationsView, setConversationsView] = useState('list');
  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);

  // Text-to-SQL state
  const [sqlSessionId, setSqlSessionId] = useState(null);
  const [sqlSessionLoading, setSqlSessionLoading] = useState(false);
  const [sqlMessages, setSqlMessages] = useState([]);
  const [sqlInputValue, setSqlInputValue] = useState('');
  const [sqlSending, setSqlSending] = useState(false);
  const [sqlError, setSqlError] = useState(null);
  const [pinnedCharts, setPinnedCharts] = useState([]); // Array of {data, suggestion, visualization_id}
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});
  const [chartLayout, setChartLayout] = useState([]);
  const { width, containerRef, mounted } = useContainerWidth();
  const sqlSessionStarted = useRef(false);

  const toggleSection = (sectionKey) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionKey]: !prev[sectionKey]
    }));
  };

  // Load chart layout from localStorage or generate default
  const loadChartLayout = (charts) => {
    const storageKey = `dashboard-layout-${datasetId}`;
    const savedLayout = localStorage.getItem(storageKey);

    if (savedLayout) {
      try {
        const parsed = JSON.parse(savedLayout);
        // Filter to only include existing chart IDs
        const validLayout = parsed.filter(item =>
          charts.some(c => c.visualization_id === item.i)
        );
        setChartLayout(validLayout);
        return;
      } catch (e) {
        console.error('Failed to parse saved layout:', e);
      }
    }

    // Generate default layout (2 columns)
    const defaultLayout = charts.map((chart, idx) => ({
      i: chart.visualization_id,
      x: (idx % 2) * 6,
      y: Math.floor(idx / 2) * 30, // Increased spacing between rows relative to rowHeight
      w: 6,
      h: 22 // Adjusted height for better proportions with rowHeight 10
    }));
    setChartLayout(defaultLayout);
  };

  // Save layout to localStorage
  const saveChartLayout = (layout) => {
    const storageKey = `dashboard-layout-${datasetId}`;
    localStorage.setItem(storageKey, JSON.stringify(layout));
  };

  // Handle layout change from GridLayout
  const handleLayoutChange = (newLayout) => {
    // Only save if it's not the initial empty layout
    if (newLayout.length > 0) {
      setChartLayout(newLayout);
      saveChartLayout(newLayout);
    }
  };
  const messagesEndRef = useRef(null);
  const recommendPromptIndex = useRef(0);

  const recommendPrompts = [
    "Recommend some interesting questions I should explore about this data.",
    "What patterns or trends might be hidden in this dataset?",
    "Suggest some analytical questions that could reveal insights.",
    "What are some unusual or surprising things I should look for?",
    "What comparisons or breakdowns would be most valuable to analyze?",
  ];

  useEffect(() => {
    fetchDatasetDetails();
    fetchDashboard();
  }, [datasetId]);

  const fetchDashboard = async () => {
    if (!datasetId) return;
    setDashboardLoading(true);
    try {
      const response = await fetch(API_ENDPOINTS.DATASETS.DASHBOARD(datasetId), {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) throw new Error('Failed to fetch dashboard');
      const data = await response.json();

      // Convert saved visualizations to pinnedCharts format
      const charts = (data.visualizations || []).map(viz => ({
        visualization_id: viz.visualization_id,
        data: viz.visualization_config?.data || [],
        suggestion: {
          title: viz.title,
          chart_type: viz.chart_type,
          x_axis: viz.visualization_config?.x_axis,
          y_axis: viz.visualization_config?.y_axis,
          description: viz.description || viz.visualization_config?.description,
          ...viz.visualization_config?.suggestion
        }
      }));
      setPinnedCharts(charts);

      // Load layout from localStorage or generate default
      loadChartLayout(charts);
    } catch (err) {
      console.error('Error fetching dashboard:', err);
    } finally {
      setDashboardLoading(false);
    }
  };

  const currentSessionRef = useRef(null);
  useEffect(() => {
    currentSessionRef.current = sqlSessionId;
  }, [sqlSessionId]);

  useEffect(() => {
    const handleBeforeUnload = () => {
      if (currentSessionRef.current) {
        navigator.sendBeacon(
          API_ENDPOINTS.TEXT_TO_SQL.END_SESSION(currentSessionRef.current),
          JSON.stringify({ method: 'DELETE' })
        );
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (currentSessionRef.current) {
        endSqlSession(currentSessionRef.current);
      }
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [sqlMessages]);

  useEffect(() => {
    if (activeTab === 'conversations' && conversationsView === 'list') {
      fetchDatasetConversations();
    }
  }, [activeTab, conversationsView]);

  useEffect(() => {
    if (resumedSessionId) {
      setActiveTab('conversations');
      setConversationsView('chat');
    }
  }, [resumedSessionId]);

  useEffect(() => {
    if (activeTab === 'conversations' && conversationsView === 'chat' && !sqlSessionId && !sqlSessionStarted.current) {
      if (resumedSessionId) {
        resumeSqlSession(resumedSessionId);
      } else {
        startSqlSession();
      }
    }
  }, [activeTab, conversationsView]);

  const fetchDatasetConversations = async () => {
    setConversationsLoading(true);
    try {
      const response = await fetch(API_ENDPOINTS.TEXT_TO_SQL.HISTORY_BY_DATASET(datasetId), {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) throw new Error('Failed to fetch conversations');
      const data = await response.json();
      setConversations(data.conversations || []);
    } catch (err) {
      console.error('Error fetching conversations:', err);
    } finally {
      setConversationsLoading(false);
    }
  };

  const handleNewChat = async () => {
    if (sqlSessionId) {
      await endSqlSession(sqlSessionId);
    }
    setSqlSessionId(null);
    setSqlMessages([]);
    sqlSessionStarted.current = false;
    setConversationsView('chat');
    startSqlSession();
  };

  const handleSelectConversation = async (sessionId) => {
    if (sqlSessionId && sqlSessionId !== sessionId) {
      await endSqlSession(sqlSessionId);
    }
    setSqlSessionId(null);
    setSqlMessages([]);
    sqlSessionStarted.current = false;
    setConversationsView('chat');
    resumeSqlSession(sessionId);
  };

  const handleDeleteConversation = async (sessionId) => {
    if (!window.confirm('Delete this conversation?')) return;
    try {
      const response = await fetch(API_ENDPOINTS.TEXT_TO_SQL.DELETE_HISTORY(sessionId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) throw new Error('Failed to delete');
      setConversations(prev => prev.filter(c => c.session_id !== sessionId));
    } catch (err) {
      console.error('Error deleting:', err);
      alert('Failed to delete conversation');
    }
  };

  const handleBackToList = () => {
    setConversationsView('list');
    fetchDatasetConversations();
  };

  const formatRelativeTime = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 10) / 10 + ' ' + sizes[i];
  };

  const formatNumber = (num) => {
    if (!num) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toLocaleString();
  };

  const fetchDatasetDetails = async () => {
    setLoading(true);
    setError(null);

    try {
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

      const previewResponse = await fetch(`${API_ENDPOINTS.DATASETS.PREVIEW(datasetId)}?limit=1000`, {
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

  const startSqlSession = async () => {
    sqlSessionStarted.current = true;
    setSqlSessionLoading(true);
    setSqlError(null);

    try {
      const response = await fetch(API_ENDPOINTS.TEXT_TO_SQL.START_SESSION, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ dataset_id: datasetId }),
      });

      if (!response.ok) {
        throw new Error('Failed to start text-to-SQL session');
      }

      const data = await response.json();

      if (!data.session_id) {
        throw new Error('No session ID returned from server');
      }

      setSqlSessionId(data.session_id);

      // Build initial message with conversational intro
      const initialMessages = [];

      if (data.intro_message && data.sample_questions?.length > 0) {
        // Use the GPT-generated conversational intro with recommendations
        initialMessages.push({
          role: 'assistant',
          content: data.intro_message,
          recommendations: data.sample_questions,
        });
      } else {
        // Fallback if GPT failed
        initialMessages.push({
          role: 'assistant',
          content: `Ready to explore your data! Ask me anything or click "Recommend" for suggestions.`,
        });
      }

      setSqlMessages(initialMessages);
    } catch (err) {
      console.error('Error starting SQL session:', err);
      setSqlError(err.message);
      sqlSessionStarted.current = false;
    } finally {
      setSqlSessionLoading(false);
    }
  };

  const resumeSqlSession = async (sessionId) => {
    if (!sessionId) {
      console.error('No session ID provided for resume');
      setSqlError('No session to resume');
      return;
    }

    sqlSessionStarted.current = true;
    setSqlSessionLoading(true);
    setSqlError(null);

    try {
      const resumeResponse = await fetch(API_ENDPOINTS.TEXT_TO_SQL.RESUME_SESSION(sessionId), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!resumeResponse.ok) {
        throw new Error('Failed to resume session');
      }

      const historyResponse = await fetch(API_ENDPOINTS.TEXT_TO_SQL.GET_HISTORY(sessionId), {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!historyResponse.ok) {
        throw new Error('Failed to load conversation history');
      }

      const historyData = await historyResponse.json();
      setSqlSessionId(sessionId);

      const restoredMessages = [];

      if (historyData.messages && historyData.messages.length > 0) {
        for (const msg of historyData.messages) {
          const uiMessage = {
            role: msg.role,
            content: msg.content,
          };

          if (msg.sql_query) {
            uiMessage.sql_query = msg.sql_query;
          }

          if (msg.query_result && msg.query_result.data && msg.query_result.columns) {
            uiMessage.results = {
              columns: msg.query_result.columns,
              data: msg.query_result.data,
              row_count: msg.query_result.row_count || msg.query_result.data.length,
            };
          }

          // Handle visualization_config which can contain either:
          // - Chart recommendations (array)
          // - Intro recommendations (object with 'recommendations' key)
          const vizConfig = msg.visualization_config || msg.visualization_recommendations;
          if (vizConfig) {
            if (Array.isArray(vizConfig)) {
              // It's an array of chart recommendations
              uiMessage.visualization_recommendations = vizConfig;
            } else if (vizConfig.recommendations) {
              // It's intro message with text recommendations
              uiMessage.recommendations = vizConfig.recommendations;
            }
          }

          restoredMessages.push(uiMessage);
        }
      }

      setSqlMessages(restoredMessages);

      window.history.replaceState({}, document.title);

    } catch (err) {
      console.error('Error resuming SQL session:', err);
      setSqlError(err.message);
      sqlSessionStarted.current = false;
    } finally {
      setSqlSessionLoading(false);
    }
  };

  const endSqlSession = async (sessionId) => {
    try {
      await fetch(API_ENDPOINTS.TEXT_TO_SQL.END_SESSION(sessionId), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });
    } catch (err) {
      console.error('Error ending SQL session:', err);
    }
  };

  const sendSqlMessage = async (message) => {
    if (!message.trim() || !sqlSessionId || sqlSending) return;

    const userMessage = message.trim();
    setSqlInputValue('');
    setSqlSending(true);

    // Check if user is responding to follow-up prompt with an affirmative
    const lastMessage = sqlMessages[sqlMessages.length - 1];
    const wantsRecommendations = lastMessage?.isFollowUpPrompt &&
      /^(yes|yeah|sure|ok|okay|recommend|suggest|show me|please|go ahead)/i.test(userMessage);

    if (wantsRecommendations) {
      // Remove the prompt message and fetch recommendations instead
      setSqlMessages(prev => [...prev.filter(msg => !msg.isFollowUpPrompt), { role: 'user', content: userMessage }]);
      await fetchFollowUpSuggestions();
      setSqlSending(false);
      return;
    }

    // Remove follow-up prompt if user typed something else (proceeding with their query)
    setSqlMessages(prev => [...prev.filter(msg => !msg.isFollowUpPrompt), { role: 'user', content: userMessage }]);

    try {
      const response = await fetch(API_ENDPOINTS.TEXT_TO_SQL.CHAT, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sqlSessionId,
          message: userMessage,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to process your question');
      }

      const data = await response.json();

      if (data.status === 'recommendations' && data.recommendations) {
        setSqlMessages(prev => [...prev, {
          role: 'assistant',
          content: data.message || 'Here are some questions you might find interesting:',
          recommendations: data.recommendations,
        }]);
        return;
      }

      let results = null;
      if (data.results && Array.isArray(data.results) && data.results.length > 0 && data.columns) {
        results = {
          columns: data.columns,
          data: data.results,
          row_count: data.row_count || data.results.length,
        };
      }

      setSqlMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message || 'Query executed.',
        sql_query: data.sql_query || null,
        results: results,
        visualization_recommendations: data.visualization_recommendations || null,
        error: data.status === 'error',
      }]);

      // Ask user if they want follow-up suggestions (conversational approach)
      if (data.status === 'success' && results && results.data?.length > 0) {
        setSqlMessages(prev => [...prev, {
          role: 'assistant',
          content: "Would you like me to suggest some follow-up questions, or do you have something specific in mind?",
          isFollowUpPrompt: true,
        }]);
      }
    } catch (err) {
      console.error('Error sending message:', err);
      setSqlMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message}. Please try again.`,
        error: true,
      }]);
    } finally {
      setSqlSending(false);
    }
  };

  const fetchFollowUpSuggestions = async () => {
    if (!sqlSessionId) return;

    try {
      const response = await fetch(API_ENDPOINTS.TEXT_TO_SQL.FOLLOW_UP(sqlSessionId), {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) return;

      const data = await response.json();
      if (data.suggestions && data.suggestions.length > 0 && data.intro_message) {
        // Add a new assistant message with the follow-up suggestions
        setSqlMessages(prev => [...prev, {
          role: 'assistant',
          content: data.intro_message,
          recommendations: data.suggestions, // Use recommendations format (same as intro)
        }]);
      }
    } catch (err) {
      console.error('Error fetching follow-up suggestions:', err);
      // Silent fail - follow-up suggestions are optional
    }
  };

  const handleSqlSubmit = (e) => {
    e.preventDefault();
    sendSqlMessage(sqlInputValue);
  };

  const handleRecommend = () => {
    const prompt = recommendPrompts[recommendPromptIndex.current];
    recommendPromptIndex.current = (recommendPromptIndex.current + 1) % recommendPrompts.length;
    sendSqlMessage(prompt);
  };

  const handleRecommendationClick = (question) => {
    sendSqlMessage(question);
  };

  const handleAddToDashboard = async (data, suggestion) => {
    // Prevent duplicates
    const exists = pinnedCharts.some(c => c.suggestion.title === suggestion.title);
    if (exists) return;

    try {
      const response = await fetch(API_ENDPOINTS.DATASETS.DASHBOARD(datasetId), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: suggestion.title,
          chart_type: suggestion.chart_type,
          query_sql: '',
          visualization_config: {
            data: data,
            x_axis: suggestion.x_axis,
            y_axis: suggestion.y_axis,
            description: suggestion.description,
            suggestion: suggestion
          },
          description: suggestion.description
        }),
      });

      if (!response.ok) throw new Error('Failed to save visualization');

      const result = await response.json();
      const newChart = {
        visualization_id: result.visualization_id,
        data,
        suggestion
      };
      setPinnedCharts(prev => [...prev, newChart]);

      // Add layout entry for new chart (place at bottom)
      const maxY = chartLayout.length > 0 ? Math.max(...chartLayout.map(l => l.y + l.h)) : 0;
      const newLayoutItem = {
        i: result.visualization_id,
        x: 0,
        y: maxY,
        w: 6,
        h: 22 // Matching default height
      };
      const newLayout = [...chartLayout, newLayoutItem];
      setChartLayout(newLayout);
      saveChartLayout(newLayout);
    } catch (err) {
      console.error('Error adding to dashboard:', err);
    }
  };

  const handleRemoveFromDashboard = async (title) => {
    const chart = pinnedCharts.find(c => c.suggestion.title === title);
    if (!chart || !chart.visualization_id) {
      // Fallback for charts without ID (shouldn't happen normally)
      setPinnedCharts(prev => prev.filter(c => c.suggestion.title !== title));
      return;
    }

    try {
      const response = await fetch(
        API_ENDPOINTS.DATASETS.DASHBOARD_REMOVE(datasetId, chart.visualization_id),
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) throw new Error('Failed to remove visualization');

      setPinnedCharts(prev => prev.filter(c => c.suggestion.title !== title));

      // Remove from layout
      const newLayout = chartLayout.filter(item => item.i !== chart.visualization_id);
      setChartLayout(newLayout);
      saveChartLayout(newLayout);
    } catch (err) {
      console.error('Error removing from dashboard:', err);
    }
  };

  const handleUpdateDashboard = async (visualization_id, updatedConfig) => {
    const currentChart = pinnedCharts.find(c => c.visualization_id === visualization_id);
    if (!currentChart) return;

    // Ensure we persist the data
    const fullConfig = {
      data: currentChart.data,
      ...updatedConfig,
      suggestion: updatedConfig
    };

    try {
      const response = await fetch(API_ENDPOINTS.DATASETS.DASHBOARD_UPDATE(datasetId, visualization_id), {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: updatedConfig.title || 'Updated Visualization',
          chart_type: updatedConfig.chart_type || 'bar',
          visualization_config: fullConfig
        }),
      });

      if (!response.ok) throw new Error('Failed to update visualization');

      // Update local state
      setPinnedCharts(prev => prev.map(chart => {
        if (chart.visualization_id === visualization_id) {
          return {
            ...chart,
            suggestion: updatedConfig
          };
        }
        return chart;
      }));

    } catch (err) {
      console.error('Error updating dashboard:', err);
    }
  };

  // Loading State
  if (loading) {
    return (
      <div className="dataset-details-page">
        <div className="loading-state">
          <div className="loading-terminal">
            <div className="terminal-header">
              <span className="terminal-dot red"></span>
              <span className="terminal-dot yellow"></span>
              <span className="terminal-dot green"></span>
              <span className="terminal-title">loading_dataset.exe</span>
            </div>
            <div className="terminal-body">
              <div className="terminal-line">
                <span className="prompt">$</span>
                <span className="command">fetch --dataset {datasetId?.slice(0, 8)}...</span>
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

  // Error State
  if (error) {
    return (
      <div className="dataset-details-page">
        <div className="error-state">
          <div className="error-icon">
            <AlertCircle size={32} />
          </div>
          <h2>Connection Failed</h2>
          <p className="error-code">ERROR: {error}</p>
          <button onClick={() => navigate(-1)} className="back-btn">
            <ArrowLeft size={16} />
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dataset-details-page">
      {/* Header Section */}
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={18} />
          <span>Back</span>
        </button>

        <div className="header-main">
          <div className="header-icon">
            <Database size={24} />
            <div className="icon-pulse"></div>
          </div>
          <div className="header-text">
            <h1>
              <span className="text-muted">~/datasets/</span>
              {dataset?.dataset_name}
              <span className="header-cursor">_</span>
            </h1>
            <p className="header-filename">
              <FileText size={12} />
              {dataset?.original_filename}
            </p>
          </div>
        </div>

        <button
          className={`info-toggle ${showInfoPanel ? 'active' : ''}`}
          onClick={() => setShowInfoPanel(!showInfoPanel)}
        >
          <ChevronDown size={20} />
        </button>
      </header>

      {/* Info Panel */}
      {showInfoPanel && (
        <div className="info-panel">
          <div className="info-stat">
            <div className="info-stat-icon">
              <BarChart3 size={18} />
            </div>
            <div className="info-stat-content">
              <span className="info-stat-value">{formatNumber(dataset?.row_count)}</span>
              <span className="info-stat-label">Rows</span>
            </div>
          </div>
          <div className="info-stat">
            <div className="info-stat-icon blue">
              <Grid3X3 size={18} />
            </div>
            <div className="info-stat-content">
              <span className="info-stat-value">{dataset?.column_count}</span>
              <span className="info-stat-label">Columns</span>
            </div>
          </div>
          <div className="info-stat">
            <div className="info-stat-icon purple">
              <HardDrive size={18} />
            </div>
            <div className="info-stat-content">
              <span className="info-stat-value">{formatFileSize(dataset?.file_size_bytes)}</span>
              <span className="info-stat-label">Size</span>
            </div>
          </div>
          <div className="info-stat">
            <div className="info-stat-icon green">
              <Calendar size={18} />
            </div>
            <div className="info-stat-content">
              <span className="info-stat-value">
                {dataset?.upload_date ? new Date(dataset.upload_date).toLocaleDateString() : '—'}
              </span>
              <span className="info-stat-label">Uploaded</span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <nav className="tabs-nav">
        <button
          className={`tab-btn ${activeTab === 'conversations' ? 'active' : ''}`}
          onClick={() => setActiveTab('conversations')}
        >
          <MessageCircle size={16} />
          <span>Conversations</span>
          {conversations.length > 0 && (
            <span className="tab-badge">{conversations.length}</span>
          )}
        </button>
        <button
          className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <LayoutDashboard size={16} />
          <span>Dashboard</span>
        </button>
        <button
          className={`tab-btn ${activeTab === 'raw-data' ? 'active' : ''}`}
          onClick={() => setActiveTab('raw-data')}
        >
          <Table size={16} />
          <span>Data Preview</span>
        </button>
      </nav>

      {/* Tab Content */}
      <div className="tab-content">
        {/* Conversations Tab */}
        {activeTab === 'conversations' && (
          <div className="conversations-tab">
            {conversationsView === 'list' ? (
              <div className="conversations-list-view">
                <div className="conversations-header">
                  <div className="conversations-title">
                    <MessageSquare size={20} />
                    <h2>Conversations</h2>
                    <span className="count-badge">{conversations.length}</span>
                  </div>
                  <button className="new-chat-btn" onClick={handleNewChat}>
                    <Plus size={18} />
                    <span>New Chat</span>
                    <div className="btn-shine"></div>
                  </button>
                </div>

                {conversationsLoading ? (
                  <div className="conversations-loading">
                    <Loader2 size={24} className="spin" />
                    <span>Loading conversations...</span>
                  </div>
                ) : conversations.length === 0 ? (
                  <div className="conversations-empty">
                    <div className="empty-visual">
                      <div className="empty-rings">
                        <div className="ring ring-1"></div>
                        <div className="ring ring-2"></div>
                        <div className="ring ring-3"></div>
                      </div>
                      <div className="empty-icon">
                        <MessageSquare size={32} />
                      </div>
                    </div>
                    <h3>No Conversations</h3>
                    <p>Start a new chat to explore your data with AI</p>
                    <button className="empty-cta" onClick={handleNewChat}>
                      <Plus size={18} />
                      <span>Start New Chat</span>
                      <Sparkles size={16} className="sparkle" />
                    </button>
                  </div>
                ) : (
                  <div className="conversations-list">
                    {conversations.map((conv, index) => (
                      <div
                        key={conv.session_id}
                        className="conversation-card"
                        style={{ '--index': index }}
                        onClick={() => handleSelectConversation(conv.session_id)}
                      >
                        <div className="conversation-icon">
                          <MessageCircle size={18} />
                        </div>
                        <div className="conversation-content">
                          <h4>{conv.title || conv.first_question || 'Untitled conversation'}</h4>
                          <div className="conversation-meta">
                            <span className="meta-item">
                              <MessageSquare size={12} />
                              {conv.message_count} messages
                            </span>
                            <span className="meta-item">
                              <Clock size={12} />
                              {formatRelativeTime(conv.updated_at)}
                            </span>
                          </div>
                        </div>
                        <div className="conversation-actions">
                          <button
                            className="action-btn view"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectConversation(conv.session_id);
                            }}
                            title="View conversation"
                          >
                            <Eye size={20} strokeWidth={2} />
                          </button>
                          <button
                            className="action-btn danger"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteConversation(conv.session_id);
                            }}
                            title="Delete conversation"
                          >
                            <Trash2 size={20} strokeWidth={2} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="chat-view">
                <div className="chat-header">
                  <button className="back-to-list" onClick={handleBackToList}>
                    <ArrowLeft size={16} />
                    <span>Back to Conversations</span>
                  </button>
                  <div className="session-status">
                    <Activity size={14} />
                    <span>Session Active</span>
                  </div>
                </div>

                {sqlSessionLoading ? (
                  <div className="chat-loading">
                    <div className="loading-terminal small">
                      <div className="terminal-line">
                        <span className="prompt">$</span>
                        <span className="command">initializing session...</span>
                        <span className="cursor"></span>
                      </div>
                    </div>
                  </div>
                ) : sqlError ? (
                  <div className="chat-error">
                    <AlertCircle size={24} />
                    <p>{sqlError}</p>
                    <button onClick={() => { sqlSessionStarted.current = false; startSqlSession(); }}>
                      <Zap size={14} />
                      Retry
                    </button>
                  </div>
                ) : !sqlSessionId ? (
                  <div className="chat-error">
                    <Terminal size={24} />
                    <p>Session not initialized</p>
                    <button onClick={() => { sqlSessionStarted.current = false; startSqlSession(); }}>
                      <Play size={14} />
                      Start Session
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="chat-messages">
                      {sqlMessages.map((msg, index) => {
                        if (!msg) return null;
                        return (
                          <div key={index} className={`message ${msg.role || 'assistant'} ${msg.error ? 'error' : ''}`}>
                            <div className="message-bubble">
                              <p className="message-text">{msg.content || ''}</p>

                              {msg.sql_query && (
                                <div className={`sql-block ${expandedSections[`sql-${index}`] ? 'expanded' : 'collapsed'}`}>
                                  <div
                                    className="sql-header"
                                    onClick={() => toggleSection(`sql-${index}`)}
                                  >
                                    <Code size={14} />
                                    <span>SQL Query</span>
                                    <ChevronDown size={14} className="collapse-icon" />
                                  </div>
                                  {expandedSections[`sql-${index}`] && (
                                    <pre><code>{msg.sql_query}</code></pre>
                                  )}
                                </div>
                              )}

                              {msg.results && msg.results.data && msg.results.columns && (
                                <div className={`results-block ${expandedSections[`results-${index}`] ? 'expanded' : 'collapsed'}`}>
                                  <div
                                    className="results-header"
                                    onClick={() => toggleSection(`results-${index}`)}
                                  >
                                    <Table size={14} />
                                    <span>Results</span>
                                    <span className="results-count">
                                      {msg.results.row_count} row{msg.results.row_count !== 1 ? 's' : ''}
                                    </span>
                                    <ChevronDown size={14} className="collapse-icon" />
                                  </div>
                                  {expandedSections[`results-${index}`] && (
                                    <div className="results-table-wrapper">
                                      <table className="results-table">
                                        <thead>
                                          <tr>
                                            {msg.results.columns.map((col, colIndex) => (
                                              <th key={colIndex}>{col}</th>
                                            ))}
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {msg.results.data.map((row, rowIndex) => {
                                            if (!row || typeof row !== 'object') return null;
                                            return (
                                              <tr key={rowIndex}>
                                                {msg.results.columns.map((col, cellIndex) => {
                                                  const cell = row[col];
                                                  return (
                                                    <td key={cellIndex}>
                                                      {cell !== null && cell !== undefined ? String(cell) : '—'}
                                                    </td>
                                                  );
                                                })}
                                              </tr>
                                            );
                                          })}
                                        </tbody>
                                      </table>
                                    </div>
                                  )}
                                </div>
                              )}

                              {msg.results && msg.results.data && msg.results.data.length > 0 && (
                                msg.visualization_recommendations && msg.visualization_recommendations.length > 0 ? (
                                  <div className="viz-recommendations">
                                    <div className="chart-explanations">
                                      {msg.visualization_recommendations.map((rec, rIndex) => (
                                        <p key={rIndex} className="chart-explanation-text">
                                          <strong>{rec.title}:</strong> {rec.description}
                                        </p>
                                      ))}
                                    </div>
                                    <div className="viz-grid">
                                      {msg.visualization_recommendations.map((rec, rIndex) => (
                                        <div key={rIndex} className="viz-card">
                                          <div className="viz-card-header">
                                            <span className="viz-type">{rec.chart_type}</span>
                                            <h5>{rec.title}</h5>
                                          </div>
                                          <div className="viz-axes">
                                            <span><strong>X:</strong> {rec.x_axis}</span>
                                            <span><strong>Y:</strong> {rec.y_axis}</span>
                                          </div>
                                          <div className="auto-rendered-chart">
                                            <ChartRenderer
                                              data={msg.results.data}
                                              suggestion={rec}
                                              onAdd={() => handleAddToDashboard(msg.results.data, rec)}
                                              isPinned={pinnedCharts.some(c => c.suggestion.title === rec.title)}
                                            />
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                ) : (
                                  <div className="viz-recommendations">
                                    <div className="viz-header">
                                      <Table size={14} />
                                      <span>Table View</span>
                                    </div>
                                    <div className="viz-grid">
                                      <ChartRenderer
                                        data={msg.results.data}
                                        suggestion={{
                                          chart_type: 'table',
                                          title: 'Data Table',
                                          description: 'Tabular view of query results',
                                          explanation: `Displaying ${msg.results.row_count} row${msg.results.row_count !== 1 ? 's' : ''} of data.`,
                                          x_axis: null,
                                          y_axis: null,
                                        }}
                                        onAdd={() => handleAddToDashboard(msg.results.data, {
                                          chart_type: 'table',
                                          title: 'Data Table',
                                          description: 'Tabular view of query results',
                                          explanation: `Displaying ${msg.results.row_count} row${msg.results.row_count !== 1 ? 's' : ''} of data.`,
                                          x_axis: null,
                                          y_axis: null,
                                        })}
                                        isPinned={pinnedCharts.some(c => c.suggestion.chart_type === 'table' && c.suggestion.title === 'Data Table')}
                                      />
                                    </div>
                                  </div>
                                )
                              )}

                              {msg.recommendations && msg.recommendations.length > 0 && (
                                <div className="suggestion-list">
                                  {msg.recommendations.map((question, qIndex) => (
                                    <button
                                      key={qIndex}
                                      className="suggestion-btn"
                                      onClick={() => handleRecommendationClick(question)}
                                      disabled={sqlSending}
                                    >
                                      <ChevronRight size={14} />
                                      {question}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}

                      {sqlSending && (
                        <div className="message assistant thinking">
                          <div className="message-bubble">
                            <div className="typing-indicator">
                              <span></span>
                              <span></span>
                              <span></span>
                            </div>
                          </div>
                        </div>
                      )}
                      <div ref={messagesEndRef} />
                    </div>

                    <form className="chat-input-form" onSubmit={handleSqlSubmit}>
                      <button
                        type="button"
                        className="recommend-btn"
                        onClick={handleRecommend}
                        disabled={sqlSending || !sqlSessionId}
                      >
                        <Sparkles size={18} />
                        <span>Recommend</span>
                      </button>
                      <div className="input-wrapper">
                        <input
                          type="text"
                          placeholder="Ask a question about your data..."
                          value={sqlInputValue}
                          onChange={(e) => setSqlInputValue(e.target.value)}
                          disabled={sqlSending || !sqlSessionId}
                        />
                        {sqlInputValue && (
                          <button
                            type="button"
                            className="clear-input"
                            onClick={() => setSqlInputValue('')}
                          >
                            <X size={14} />
                          </button>
                        )}
                      </div>
                      <button
                        type="submit"
                        className="send-btn"
                        disabled={sqlSending || !sqlInputValue.trim() || !sqlSessionId}
                      >
                        <Send size={18} />
                      </button>
                    </form>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="dashboard-tab">
            {dashboardLoading ? (
              <div className="dashboard-loading">
                <Loader2 size={24} className="spin" />
                <span>Loading dashboard...</span>
              </div>
            ) : pinnedCharts.length > 0 ? (
              <div className="dashboard-grid">
                <div className="dashboard-header-info">
                  <div className="dashboard-title-row">
                    <h2>
                      <LayoutDashboard size={20} />
                      Your Dashboard
                      <span className="pinned-count">{pinnedCharts.length} chart{pinnedCharts.length !== 1 ? 's' : ''}</span>
                    </h2>
                    <p>Visualizations pinned from your data exploration. Drag to reposition, resize from corners.</p>
                  </div>
                </div>
                <div className="dashboard-grid-container" ref={containerRef}>
                  {mounted && (
                    <ResponsiveGridLayout
                      className="charts-container"
                      width={width}
                      layouts={{ lg: chartLayout }}
                      breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xss: 0 }}
                      cols={{ lg: 12, md: 10, sm: 6, xs: 4, xss: 2 }}
                      rowHeight={10}
                      onLayoutChange={handleLayoutChange}
                      draggableHandle=".chart-drag-handle"
                      compactType="vertical"
                      preventCollision={false}
                      margin={[20, 20]} // Spacing between items
                    >
                      {pinnedCharts.map((item) => (
                        <div key={item.visualization_id} className="dashboard-grid-item">
                          <div className="dashboard-chart-wrapper">
                            <ChartRenderer
                              data={item.data}
                              suggestion={item.suggestion}
                              isPinned={true}
                              onRemove={() => handleRemoveFromDashboard(item.suggestion.title)}
                              onUpdate={(config) => handleUpdateDashboard(item.visualization_id, config)}
                            />
                          </div>
                        </div>
                      ))}
                    </ResponsiveGridLayout>
                  )}
                </div>
              </div>
            ) : (
              <div className="dashboard-placeholder">
                <div className="placeholder-icon">
                  <LayoutDashboard size={48} />
                </div>
                <h2>No Charts Pinned Yet</h2>
                <p>Start a conversation and pin visualizations to build your custom dashboard</p>
                <div className="empty-hint">
                  <Sparkles size={14} />
                  <span>Tip: Click the pin icon on any chart to add it here</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Raw Data Tab */}
        {activeTab === 'raw-data' && (
          <div className="raw-data-tab">
            <div className="data-header">
              <div className="data-title">
                <Table size={20} />
                <h2>Data Preview</h2>
              </div>
              {previewData && (
                <div className="data-stats">
                  <span className="data-stat">
                    <strong>{formatNumber(previewData.total_rows)}</strong> rows
                  </span>
                  <span className="data-separator">×</span>
                  <span className="data-stat">
                    <strong>{previewData.columns?.length}</strong> columns
                  </span>
                  <span className="data-note">
                    Showing {formatNumber(previewData.showing_rows)} of {formatNumber(previewData.total_rows)}
                  </span>
                </div>
              )}
            </div>
            <div className="data-table-container">
              <DataTable
                data={previewData?.data}
                columns={previewData?.columns}
                columnsInfo={dataset?.columns_info}
                loading={loading}
                error={error}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
