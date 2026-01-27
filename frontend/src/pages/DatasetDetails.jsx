import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import { ArrowLeft, ChevronDown, Send, Sparkles, Plus, MessageSquare, Trash2 } from 'lucide-react';
import DataTable from '../components/DataTable';
import '../components/DataPreviewPanel.css';
import './DatasetDetails.css';

export default function DatasetDetails() {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { sessionToken } = useAuth();

  // Check if we're resuming a session from history
  const resumedSessionId = location.state?.resumedSessionId;
  const [dataset, setDataset] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('conversations');
  const [showInfoDropdown, setShowInfoDropdown] = useState(false);

  // Conversations tab state
  const [conversationsView, setConversationsView] = useState('list'); // 'list' | 'chat'
  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);

  // Text-to-SQL state
  const [sqlSessionId, setSqlSessionId] = useState(null);
  const [sqlSessionLoading, setSqlSessionLoading] = useState(false);
  const [sqlMessages, setSqlMessages] = useState([]);
  const [sqlInputValue, setSqlInputValue] = useState('');
  const [sqlSending, setSqlSending] = useState(false);
  const [sqlError, setSqlError] = useState(null);
  const sqlSessionStarted = useRef(false);
  const messagesEndRef = useRef(null);
  const recommendPromptIndex = useRef(0);

  // Cycling prompts for the Recommend button
  const recommendPrompts = [
    "Recommend some interesting questions I should explore about this data.",
    "What patterns or trends might be hidden in this dataset?",
    "Suggest some analytical questions that could reveal insights.",
    "What are some unusual or surprising things I should look for?",
    "What comparisons or breakdowns would be most valuable to analyze?",
  ];

  useEffect(() => {
    fetchDatasetDetails();
  }, [datasetId]);

  // Track current session ID in a ref for cleanup
  const currentSessionRef = useRef(null);
  useEffect(() => {
    currentSessionRef.current = sqlSessionId;
  }, [sqlSessionId]);

  // Cleanup session only on page unload or component unmount
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (currentSessionRef.current) {
        // Use sendBeacon for reliable cleanup
        navigator.sendBeacon(
          API_ENDPOINTS.TEXT_TO_SQL.END_SESSION(currentSessionRef.current),
          JSON.stringify({ method: 'DELETE' })
        );
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // Only cleanup on actual unmount (leaving the page), not when switching sessions
      if (currentSessionRef.current) {
        endSqlSession(currentSessionRef.current);
      }
    };
  }, []); // Empty dependency - only runs on mount/unmount

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [sqlMessages]);

  // Fetch conversations when conversations tab is opened (list view)
  useEffect(() => {
    if (activeTab === 'conversations' && conversationsView === 'list') {
      fetchDatasetConversations();
    }
  }, [activeTab, conversationsView]);

  // Handle resumedSessionId from navigation - go to conversations chat view
  useEffect(() => {
    if (resumedSessionId) {
      setActiveTab('conversations');
      setConversationsView('chat');
    }
  }, [resumedSessionId]);

  // Start session when entering chat view in conversations tab
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
    // Reset any existing session
    if (sqlSessionId) {
      await endSqlSession(sqlSessionId);
    }

    // Reset chat state
    setSqlSessionId(null);
    setSqlMessages([]);
    sqlSessionStarted.current = false;

    // Switch to chat view
    setConversationsView('chat');

    // Start new session directly (don't rely on useEffect which may not trigger)
    startSqlSession();
  };

  const handleSelectConversation = async (sessionId) => {
    // Reset current session state
    if (sqlSessionId && sqlSessionId !== sessionId) {
      await endSqlSession(sqlSessionId);
    }

    setSqlSessionId(null);
    setSqlMessages([]);
    sqlSessionStarted.current = false;

    // Set up for resuming and switch to chat view
    // We'll use a ref or state to track which session to resume
    setConversationsView('chat');

    // Resume the session
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

      // Remove from local state
      setConversations(prev => prev.filter(c => c.session_id !== sessionId));
    } catch (err) {
      console.error('Error deleting:', err);
      alert('Failed to delete conversation');
    }
  };

  const handleBackToList = () => {
    setConversationsView('list');
    // Refresh conversations list
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

      // Add welcome message
      setSqlMessages([{
        role: 'assistant',
        content: `Hi! I'm here to help you explore your data. Ask me any question, or click the "Recommend" button to get suggestions for interesting things to explore!`,
      }]);
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
      // First, resume the session on the backend
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

      // Then, fetch the conversation history
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

      // Set the session ID
      setSqlSessionId(sessionId);

      // Convert history messages to UI format
      const restoredMessages = [];

      // Add a "session restored" message first
      restoredMessages.push({
        role: 'assistant',
        content: 'Session restored. Here is your previous conversation:',
      });

      // Add all previous messages
      if (historyData.messages && historyData.messages.length > 0) {
        for (const msg of historyData.messages) {
          const uiMessage = {
            role: msg.role,
            content: msg.content,
          };

          // Add SQL query if present
          if (msg.sql_query) {
            uiMessage.sql_query = msg.sql_query;
          }

          // Add results if present
          if (msg.query_result && msg.query_result.data && msg.query_result.columns) {
            uiMessage.results = {
              columns: msg.query_result.columns,
              data: msg.query_result.data,
              row_count: msg.query_result.row_count || msg.query_result.data.length,
            };
          }

          // Add visualization recommendations if present
          if (msg.visualization_recommendations) {
            uiMessage.visualization_recommendations = msg.visualization_recommendations;
          }

          restoredMessages.push(uiMessage);
        }
      }

      // Add a continuation prompt
      restoredMessages.push({
        role: 'assistant',
        content: 'You can continue asking questions about your data.',
      });

      setSqlMessages(restoredMessages);

      // Clear the location state to prevent re-resuming on refresh
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

    // Add user message immediately
    setSqlMessages(prev => [...prev, { role: 'user', content: userMessage }]);

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
      console.log('[TextToSQL] Response:', data);

      // Handle recommendations - include them in the message
      if (data.status === 'recommendations' && data.recommendations) {
        setSqlMessages(prev => [...prev, {
          role: 'assistant',
          content: data.message || 'Here are some questions you might find interesting:',
          recommendations: data.recommendations,
        }]);
        return;
      }

      // Build results object if available
      let results = null;
      if (data.results && Array.isArray(data.results) && data.results.length > 0 && data.columns) {
        results = {
          columns: data.columns,
          data: data.results,
          row_count: data.row_count || data.results.length,
        };
      }

      // Add assistant response with results and viz recommendations included
      setSqlMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message || 'Query executed.',
        sql_query: data.sql_query || null,
        results: results,
        visualization_recommendations: data.visualization_recommendations || null, // PROACTIVE
        error: data.status === 'error',
      }]);
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
          <button onClick={() => navigate(-1)} className="back-button">
            Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dataset-details-page">
      {/* Header */}
      <div className="details-header">
        <button onClick={() => navigate(-1)} className="back-button">
          <ArrowLeft size={20} />
          Back
        </button>

        <div className="dataset-title-row">
          <div className="dataset-info">
            <h1>{dataset?.dataset_name}</h1>
            <p className="dataset-filename">{dataset?.original_filename}</p>
          </div>

          <button
            className={`info-dropdown-toggle ${showInfoDropdown ? 'open' : ''}`}
            onClick={() => setShowInfoDropdown(!showInfoDropdown)}
          >
            <ChevronDown size={20} />
          </button>
        </div>
      </div>

      {showInfoDropdown && (
        <div className="info-dropdown">
          <div className="info-dropdown-item">
            <span className="info-label">Dataset Name</span>
            <span className="info-value">{dataset?.dataset_name}</span>
          </div>
          <div className="info-dropdown-item">
            <span className="info-label">Original Filename</span>
            <span className="info-value">{dataset?.original_filename}</span>
          </div>
          <div className="info-dropdown-item">
            <span className="info-label">Rows</span>
            <span className="info-value">{dataset?.row_count?.toLocaleString()}</span>
          </div>
          <div className="info-dropdown-item">
            <span className="info-label">Columns</span>
            <span className="info-value">{dataset?.column_count}</span>
          </div>
          <div className="info-dropdown-item">
            <span className="info-label">File Size</span>
            <span className="info-value">{dataset?.file_size_bytes ? `${(dataset.file_size_bytes / 1024).toFixed(2)} KB` : '—'}</span>
          </div>
          <div className="info-dropdown-item">
            <span className="info-label">Uploaded</span>
            <span className="info-value">{dataset?.upload_date ? new Date(dataset.upload_date).toLocaleDateString() : '—'}</span>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="details-tabs">
        <button
          className={`tab-button ${activeTab === 'conversations' ? 'active' : ''}`}
          onClick={() => setActiveTab('conversations')}
        >
          Conversations
        </button>
        <button
          className={`tab-button ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          Dashboard
        </button>
        <button
          className={`tab-button ${activeTab === 'raw-data' ? 'active' : ''}`}
          onClick={() => setActiveTab('raw-data')}
        >
          Raw Data
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'conversations' && (
        <div className="tab-content conversations-container">
          {conversationsView === 'list' ? (
            /* Conversations List View */
            <div className="conversations-list-container">
              <div className="conversations-header">
                <h3>Conversations</h3>
                <button className="new-chat-button" onClick={handleNewChat}>
                  <Plus size={18} />
                  New Chat
                </button>
              </div>

              {conversationsLoading && (
                <div className="conversations-loading">
                  <div className="spinner"></div>
                  <p>Loading conversations...</p>
                </div>
              )}

              {!conversationsLoading && conversations.length === 0 && (
                <div className="conversations-empty">
                  <MessageSquare size={48} />
                  <h4>No conversations yet</h4>
                  <p>Start a new chat to explore your data</p>
                  <button className="new-chat-button" onClick={handleNewChat}>
                    <Plus size={18} />
                    Start New Chat
                  </button>
                </div>
              )}

              {!conversationsLoading && conversations.length > 0 && (
                <div className="conversations-list">
                  {conversations.map(conv => (
                    <div
                      key={conv.session_id}
                      className="conversation-item"
                      onClick={() => handleSelectConversation(conv.session_id)}
                    >
                      <div className="conversation-item-content">
                        <h4>{conv.title || conv.first_question || 'Untitled conversation'}</h4>
                        <span className="conversation-meta">
                          {conv.message_count} message{conv.message_count !== 1 ? 's' : ''} · {formatRelativeTime(conv.updated_at)}
                        </span>
                      </div>
                      <button
                        className="delete-conversation-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteConversation(conv.session_id);
                        }}
                        title="Delete conversation"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Chat View */
            <div className="sql-chat-container">
              <button className="back-to-list-button" onClick={handleBackToList}>
                <ArrowLeft size={18} />
                Back to Conversations
              </button>

              {sqlSessionLoading ? (
                <div className="sql-loading">
                  <div className="spinner"></div>
                  <p>Starting session...</p>
                </div>
              ) : sqlError ? (
                <div className="sql-error">
                  <p>Error: {sqlError}</p>
                  <button onClick={() => { sqlSessionStarted.current = false; startSqlSession(); }} className="retry-button">
                    Retry
                  </button>
                </div>
              ) : !sqlSessionId ? (
                <div className="sql-error">
                  <p>Session not started</p>
                  <button onClick={() => { sqlSessionStarted.current = false; startSqlSession(); }} className="retry-button">
                    Start Session
                  </button>
                </div>
              ) : (
                <>
                  {/* Chat Messages */}
                  <div className="sql-messages">
                    {sqlMessages.map((msg, index) => {
                      if (!msg) return null;
                      return (
                        <div key={index} className={`sql-message ${msg.role || 'assistant'}`}>
                          <div className="message-content">
                            <p>{msg.content || ''}</p>
                            {msg.sql_query && (
                              <div className="sql-code-block">
                                <div className="sql-code-header">
                                  <span>SQL Query</span>
                                </div>
                                <pre><code>{msg.sql_query}</code></pre>
                              </div>
                            )}
                            {msg.results && msg.results.data && msg.results.columns && (
                              <div className="sql-results-inline">
                                <div className="sql-results-header-inline">
                                  <span>Results</span>
                                  <span className="results-count-inline">
                                    {msg.results.row_count} row{msg.results.row_count !== 1 ? 's' : ''}
                                  </span>
                                </div>
                                <div className="sql-results-table-wrapper-inline">
                                  <table className="sql-results-table">
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
                              </div>
                            )}
                            {msg.visualization_recommendations && msg.visualization_recommendations.length > 0 && (
                              <div className="visualization-recommendations">
                                <h4>Proactive Chart Recommendations</h4>
                                <div className="viz-rec-list">
                                  {msg.visualization_recommendations.map((rec, rIndex) => (
                                    <div key={rIndex} className="viz-rec-card">
                                      <div className="viz-rec-header">
                                        <span className="viz-type-badge">{rec.chart_type}</span>
                                        <h5>{rec.title}</h5>
                                      </div>
                                      <p className="viz-rec-desc">{rec.description}</p>
                                      <div className="viz-rec-details">
                                        <span><strong>X:</strong> {rec.x_axis}</span>
                                        <span><strong>Y:</strong> {rec.y_axis}</span>
                                      </div>
                                      <button
                                        className="view-chart-btn"
                                        onClick={() => {
                                          // For now just alert, but could navigate to dashboard or show modal
                                          alert(`Chart suggested: ${rec.title}\\nType: ${rec.chart_type}\\nX: ${rec.x_axis}\\nY: ${rec.y_axis}`);
                                        }}
                                      >
                                        View Recommendation
                                      </button>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {msg.recommendations && msg.recommendations.length > 0 && (
                              <div className="message-recommendations">
                                {msg.recommendations.map((question, qIndex) => (
                                  <button
                                    key={qIndex}
                                    className="recommendation-option"
                                    onClick={() => handleRecommendationClick(question)}
                                    disabled={sqlSending}
                                  >
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
                      <div className="sql-message assistant">
                        <div className="message-content">
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

                  {/* Input Form */}
                  <form className="sql-input-form" onSubmit={handleSqlSubmit}>
                    <button
                      type="button"
                      className="sql-recommend-button"
                      onClick={handleRecommend}
                      disabled={sqlSending || !sqlSessionId}
                      title="Get a recommendation"
                    >
                      <Sparkles size={20} />
                      <span>Recommend</span>
                    </button>
                    <input
                      type="text"
                      className="sql-input"
                      placeholder="Ask a question about your data..."
                      value={sqlInputValue}
                      onChange={(e) => setSqlInputValue(e.target.value)}
                      disabled={sqlSending || !sqlSessionId}
                    />
                    <button
                      type="submit"
                      className="sql-send-button"
                      disabled={sqlSending || !sqlInputValue.trim() || !sqlSessionId}
                    >
                      <Send size={20} />
                    </button>
                  </form>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'dashboard' && (
        <div className="tab-content">
          <div className="placeholder-content">
            <h2>Dashboard</h2>
            <p>View your data dashboard</p>
          </div>
        </div>
      )}

      {activeTab === 'raw-data' && (
        <div className="data-preview-panel">
          <div className="panel-header">
            <div className="header-content">
              <h3>Data Preview</h3>
              {previewData && (
                <div className="data-stats">
                  <span className="stat-item">
                    <strong>{previewData.total_rows?.toLocaleString()}</strong> rows
                  </span>
                  <span className="stat-separator">×</span>
                  <span className="stat-item">
                    <strong>{previewData.columns?.length}</strong> columns
                  </span>
                </div>
              )}
            </div>
            {previewData && (
              <span className="preview-note">
                Previewing {previewData.showing_rows?.toLocaleString()} of {previewData.total_rows?.toLocaleString()} rows
              </span>
            )}
          </div>

          <DataTable
            data={previewData?.data}
            columns={previewData?.columns}
            columnsInfo={dataset?.columns_info}
            loading={loading}
            error={error}
          />
        </div>
      )}
    </div>
  );
}
