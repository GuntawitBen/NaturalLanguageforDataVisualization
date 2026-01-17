import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import { ArrowLeft, ChevronDown, Send, Sparkles } from 'lucide-react';
import './DatasetDetails.css';

export default function DatasetDetails() {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const { sessionToken } = useAuth();
  const [dataset, setDataset] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('raw-data');
  const [showInfoDropdown, setShowInfoDropdown] = useState(false);

  // Text-to-SQL state
  const [sqlSessionId, setSqlSessionId] = useState(null);
  const [sqlSessionLoading, setSqlSessionLoading] = useState(false);
  const [sqlMessages, setSqlMessages] = useState([]);
  const [sqlRecommendations, setSqlRecommendations] = useState([]);
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

  // Start SQL session when visualize tab is opened
  useEffect(() => {
    if (activeTab === 'visualize' && !sqlSessionId && !sqlSessionStarted.current) {
      startSqlSession();
    }
  }, [activeTab]);

  // Cleanup session on unmount
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (sqlSessionId) {
        // Use sendBeacon for reliable cleanup
        navigator.sendBeacon(
          API_ENDPOINTS.TEXT_TO_SQL.END_SESSION(sqlSessionId),
          JSON.stringify({ method: 'DELETE' })
        );
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (sqlSessionId) {
        endSqlSession(sqlSessionId);
      }
    };
  }, [sqlSessionId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [sqlMessages]);

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

      // Handle recommendations
      if (data.status === 'recommendations' && data.recommendations) {
        setSqlRecommendations(data.recommendations);
        setSqlMessages(prev => [...prev, {
          role: 'assistant',
          content: data.message || 'Here are some questions you might find interesting:',
        }]);
        return;
      }

      // Clear recommendations when user asks a regular question
      setSqlRecommendations([]);

      // Build results object if available
      let results = null;
      if (data.results && Array.isArray(data.results) && data.results.length > 0 && data.columns) {
        results = {
          columns: data.columns,
          data: data.results,
          row_count: data.row_count || data.results.length,
        };
      }

      // Add assistant response with results included
      setSqlMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message || 'Query executed.',
        sql_query: data.sql_query || null,
        results: results,
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
    setSqlRecommendations([]);  // Clear recommendations
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
          className={`tab-button ${activeTab === 'visualize' ? 'active' : ''}`}
          onClick={() => setActiveTab('visualize')}
        >
          Visualize
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
      {activeTab === 'visualize' && (
        <div className="tab-content sql-chat-container">
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

              {/* Recommended Questions */}
              {sqlRecommendations.length > 0 && (
                <div className="sql-recommendations">
                  <span className="recommendations-label">Try:</span>
                  <div className="recommendations-chips">
                    {sqlRecommendations.map((question, index) => (
                      <button
                        key={index}
                        className="recommendation-chip"
                        onClick={() => handleRecommendationClick(question)}
                        disabled={sqlSending}
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              )}

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

      {activeTab === 'dashboard' && (
        <div className="tab-content">
          <div className="placeholder-content">
            <h2>Dashboard</h2>
            <p>View your data dashboard</p>
          </div>
        </div>
      )}

      {activeTab === 'raw-data' && (
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
      )}
    </div>
  );
}
