import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import { CheckCircle2, ArrowRight, ArrowLeft } from 'lucide-react';
import CSVUpload from '../components/CSVUpload';
import './DataCleaning.css';

export default function DataCleaning() {
  const navigate = useNavigate();
  const { sessionToken } = useAuth();

  // State for uploaded file info
  const [tempFilePath, setTempFilePath] = useState(null);
  const [datasetName, setDatasetName] = useState('');
  const [originalFilename, setOriginalFilename] = useState('');
  const [fileSize, setFileSize] = useState(0);

  const [currentStage, setCurrentStage] = useState(1);
  const [finalizing, setFinalizing] = useState(false);
  const [finalized, setFinalized] = useState(false);
  const [error, setError] = useState(null);

  // EDA Analysis state
  const [edaReport, setEdaReport] = useState(null);
  const [edaLoading, setEdaLoading] = useState(false);
  const [edaError, setEdaError] = useState(null);
  const [edaCompleted, setEdaCompleted] = useState(false);

  // Progress tracking state
  const [progressStage, setProgressStage] = useState('');
  const [progressMessage, setProgressMessage] = useState('');
  const [enrichmentProgress, setEnrichmentProgress] = useState({ current: 0, total: 0, issue: '' });

  // Chat interface state
  const [chatMessages, setChatMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);

  // Ref for EventSource to cancel streaming analysis
  const eventSourceRef = useRef(null);

  const stages = [
    { id: 1, name: 'Upload Dataset', description: 'Upload your CSV file' },
    { id: 2, name: 'Data Inspection', description: 'Review and validate your data' },
    { id: 3, name: 'Data Processing', description: 'Clean and transform your data' }
  ];

  // Handle successful upload from CSVUpload component
  const handleUploadSuccess = (tempData) => {
    console.log('Temp upload successful:', tempData);

    // Store temp file info
    setTempFilePath(tempData.temp_file_path);
    setDatasetName(tempData.dataset_name);
    setOriginalFilename(tempData.original_filename);
    setFileSize(tempData.file_size_bytes);

    // Move to next stage
    setCurrentStage(2);
  };

  const handleUploadError = (error) => {
    console.error('Upload error:', error);
    setError(error);
  };

  // Cleanup temp file when component unmounts (if not finalized)
  useEffect(() => {
    return () => {
      // Cancel ongoing analysis on unmount
      if (eventSourceRef.current) {
        console.log('Component unmounting, canceling analysis...');
        eventSourceRef.current.close();
      }

      // Only cleanup if we have a temp file and it wasn't finalized
      if (tempFilePath && !finalized) {
        const cleanupTempFile = async () => {
          try {
            const formData = new FormData();
            formData.append('temp_file_path', tempFilePath);

            await fetch(API_ENDPOINTS.DATASETS.CLEANUP_TEMP, {
              method: 'DELETE',
              headers: {
                'Authorization': `Bearer ${sessionToken}`,
              },
              body: formData,
            });
          } catch (err) {
            // Silently fail - cleanup is best effort
            console.warn('Failed to cleanup temp file:', err);
          }
        };

        cleanupTempFile();
      }
    };
  }, [tempFilePath, sessionToken, finalized]);

  // Cancel ongoing analysis
  const cancelAnalysis = () => {
    if (eventSourceRef.current) {
      console.log('Canceling analysis...');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setEdaLoading(false);
      setIsTyping(false);
      setProgressStage('');
      setProgressMessage('');
      setEnrichmentProgress({ current: 0, total: 0, issue: '' });
    }
  };

  const handleNext = () => {
    // Stage 1: Upload - can't go next without uploading
    if (currentStage === 1 && !tempFilePath) {
      setError('Please upload a file first');
      return;
    }

    // Stage 2: If analysis is in progress, show confirmation
    if (currentStage === 2 && edaLoading) {
      const confirmLeave = window.confirm(
        'Data analysis is still in progress. Are you sure you want to leave? The analysis will be canceled.'
      );
      if (!confirmLeave) {
        return;
      }
      cancelAnalysis();
    }

    if (currentStage < stages.length) {
      setCurrentStage(currentStage + 1);
      setError(null);
    }
  };

  const handleBack = () => {
    // If analysis is in progress on Stage 2, show confirmation
    if (currentStage === 2 && edaLoading) {
      const confirmLeave = window.confirm(
        'Data analysis is still in progress. Are you sure you want to go back? The analysis will be canceled.'
      );
      if (!confirmLeave) {
        return;
      }
      cancelAnalysis();
    }

    if (currentStage > 1) {
      setCurrentStage(currentStage - 1);
      setError(null);
    }
  };

  // Trigger EDA analysis with streaming when entering Stage 2
  const runEDAAnalysis = () => {
    if (!tempFilePath) {
      setEdaError('No file uploaded for analysis');
      return;
    }

    setEdaLoading(true);
    setEdaError(null);
    setProgressStage('initializing');
    setProgressMessage('Starting analysis...');
    setEnrichmentProgress({ current: 0, total: 0, issue: '' });

    // Build EventSource URL with query params and auth header
    // Note: EventSource doesn't support POST or custom headers, so we need to use a workaround
    // We'll send the request body as query parameters
    const requestBody = {
      temp_file_path: tempFilePath,
      include_sample_rows: true,
      max_sample_rows: 20
    };

    // Create a POST request to get the streaming response
    const startStreamingAnalysis = async () => {
      try {
        const response = await fetch(API_ENDPOINTS.EDA.ANALYZE_STREAM, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
          throw new Error('Failed to start streaming analysis');
        }

        // Read the stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          // Decode the chunk and add to buffer
          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE messages
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('event:')) {
              const eventType = line.substring(6).trim();
              continue;
            }

            if (line.startsWith('data:')) {
              const data = JSON.parse(line.substring(5).trim());

              // Handle different event types
              if (data.stage) {
                setProgressStage(data.stage);
                setProgressMessage(data.message || '');

                // If enrichment stage, initialize progress
                if (data.stage === 'enrichment' && data.total) {
                  setEnrichmentProgress({ current: 0, total: data.total, issue: '' });
                }
              }

              if (data.current !== undefined && data.total !== undefined) {
                // Progress update
                setEnrichmentProgress({
                  current: data.current,
                  total: data.total,
                  issue: data.issue_title || ''
                });
              }

              if (data.error) {
                setEdaError(data.error);
                setEdaLoading(false);
                return;
              }

              if (data.success !== undefined) {
                // Complete event with full report
                setEdaReport(data);
                setEdaCompleted(true);
                setEdaLoading(false);
                setProgressStage('complete');
                setProgressMessage('Analysis complete!');

                // Build and display chat messages progressively
                buildChatMessages(data);
                return;
              }
            }
          }
        }

      } catch (err) {
        console.error('Streaming analysis error:', err);
        setEdaError(err.message);
        setEdaLoading(false);
      }
    };

    startStreamingAnalysis();
  };

  // Build chat messages from EDA report
  const buildChatMessages = async (report) => {
    const messages = [];

    // 1. Greeting message
    messages.push({
      id: 'greeting',
      type: 'assistant',
      content: `Hi! I've finished analyzing your dataset "${datasetName}". Let me walk you through what I found.`
    });

    // 2. Summary message
    const summaryContent = `📊 **Dataset Overview**\n\n` +
      `• **${report.dataset_summary.row_count.toLocaleString()} rows** and **${report.dataset_summary.column_count} columns**\n` +
      `• Data completeness: **${report.dataset_summary.overall_completeness.toFixed(1)}%**\n` +
      `• Duplicate rows: **${report.dataset_summary.duplicate_row_count}**\n\n` +
      report.gpt_summary;

    messages.push({
      id: 'summary',
      type: 'assistant',
      content: summaryContent
    });

    // 3. Critical issues
    const criticalIssues = report.issues.filter(issue => issue.severity === 'critical');
    if (criticalIssues.length > 0) {
      messages.push({
        id: 'critical-intro',
        type: 'assistant',
        content: `🚨 I found **${criticalIssues.length} critical issue${criticalIssues.length > 1 ? 's' : ''}** that need your attention:`
      });

      criticalIssues.forEach((issue, idx) => {
        messages.push({
          id: `critical-${idx}`,
          type: 'assistant',
          severity: 'critical',
          content: `**${issue.title}**\n\n${issue.description}\n\n` +
            (issue.affected_columns.length > 0 ? `📍 Affected columns: ${issue.affected_columns.join(', ')}\n\n` : '') +
            `📊 **Impact on Visualization:** ${issue.visualization_impact}`
        });
      });
    }

    // 4. Warnings
    const warnings = report.issues.filter(issue => issue.severity === 'warning');
    if (warnings.length > 0) {
      messages.push({
        id: 'warning-intro',
        type: 'assistant',
        content: `⚠️ I also noticed **${warnings.length} warning${warnings.length > 1 ? 's' : ''}**:`
      });

      warnings.forEach((issue, idx) => {
        messages.push({
          id: `warning-${idx}`,
          type: 'assistant',
          severity: 'warning',
          content: `**${issue.title}**\n\n${issue.description}\n\n` +
            (issue.affected_columns.length > 0 ? `📍 Affected columns: ${issue.affected_columns.join(', ')}\n\n` : '') +
            `📊 **Impact on Visualization:** ${issue.visualization_impact}`
        });
      });
    }

    // 5. Info items (grouped)
    const infoIssues = report.issues.filter(issue => issue.severity === 'info');
    if (infoIssues.length > 0) {
      let infoContent = `ℹ️ Here are **${infoIssues.length} additional observation${infoIssues.length > 1 ? 's' : ''}** about your data:\n\n`;
      infoIssues.forEach((issue, idx) => {
        infoContent += `**${idx + 1}. ${issue.title}**\n${issue.description}\n`;
        if (issue.affected_columns.length > 0) {
          infoContent += `Affected: ${issue.affected_columns.join(', ')}\n`;
        }
        infoContent += `\n`;
      });

      messages.push({
        id: 'info-group',
        type: 'assistant',
        severity: 'info',
        content: infoContent
      });
    }

    // 6. Visualization concerns
    if (report.visualization_concerns.length > 0) {
      let vizContent = `📈 **Visualization Concerns:**\n\n`;
      report.visualization_concerns.forEach((concern, idx) => {
        vizContent += `${idx + 1}. ${concern}\n`;
      });

      messages.push({
        id: 'viz-concerns',
        type: 'assistant',
        content: vizContent
      });
    }

    // 7. Final advice
    const finalAdvice = report.issues.length === 0
      ? `✅ Great news! Your dataset looks clean and ready for visualization. You can proceed to the next stage with confidence.`
      : report.critical_issues_count > 0
        ? `⚠️ I recommend addressing the critical issues before proceeding. These could significantly impact your visualizations.`
        : `✅ Your dataset is in good shape! The warnings are optional to fix, but addressing them will improve your visualizations.`;

    messages.push({
      id: 'final-advice',
      type: 'assistant',
      content: finalAdvice
    });

    // Display messages progressively
    setChatMessages([]);
    for (let i = 0; i < messages.length; i++) {
      setIsTyping(true);
      await new Promise(resolve => setTimeout(resolve, 800)); // Delay between messages
      setChatMessages(prev => [...prev, messages[i]]);
      setIsTyping(false);
      await new Promise(resolve => setTimeout(resolve, 300)); // Brief pause after message appears
    }
  };

  // Auto-trigger EDA when entering Stage 2
  useEffect(() => {
    if (currentStage === 2 && tempFilePath && !edaCompleted && !edaLoading) {
      runEDAAnalysis();
    }
  }, [currentStage, tempFilePath]);

  const handleComplete = async () => {
    setFinalizing(true);
    setError(null);

    try {
      // Create form data for finalize endpoint
      const formData = new FormData();
      formData.append('temp_file_path', tempFilePath);
      formData.append('dataset_name', datasetName);
      formData.append('original_filename', originalFilename);

      const response = await fetch(API_ENDPOINTS.DATASETS.FINALIZE, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to finalize dataset');
      }

      const dataset = await response.json();

      // Mark as finalized so cleanup doesn't happen
      setFinalized(true);

      // Navigate to dataset details page
      navigate(`/datasets/${dataset.dataset_id}`);
    } catch (err) {
      console.error('Error finalizing dataset:', err);
      setError(err.message);
      setFinalizing(false);
    }
  };

  return (
    <div className="data-cleaning-page">
      {/* Header */}
      <div className="cleaning-header">
        <button onClick={() => navigate('/datasets')} className="back-link">
          <ArrowLeft size={20} />
          Back to Datasets
        </button>
        <h1>Upload & Clean Dataset</h1>
        <p className="subtitle">
          {datasetName ? `Preparing: ${datasetName}` : 'Upload and prepare your dataset for analysis'}
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          <p className="error-message">{error}</p>
        </div>
      )}

      {/* Progress Stepper */}
      <div className="progress-stepper">
        {stages.map((stage, index) => (
          <div key={stage.id} className="step-container">
            <div className={`step ${currentStage >= stage.id ? 'active' : ''} ${currentStage > stage.id ? 'completed' : ''}`}>
              <div className="step-indicator">
                {currentStage > stage.id ? (
                  <CheckCircle2 size={32} className="step-icon completed" />
                ) : (
                  <div className={`step-number ${currentStage === stage.id ? 'active' : ''}`}>
                    {stage.id}
                  </div>
                )}
              </div>
              <div className="step-info">
                <h3>{stage.name}</h3>
                <p>{stage.description}</p>
              </div>
            </div>
            {index < stages.length - 1 && (
              <div className={`step-connector ${currentStage > stage.id ? 'completed' : ''}`}></div>
            )}
          </div>
        ))}
      </div>

      {/* Stage Content */}
      <div className="stage-content">
        {/* Stage 1: Upload */}
        {currentStage === 1 && (
          <div className="stage-panel">
            <div className="stage-header">
              <h2>Stage 1: Upload Dataset</h2>
              <p>Upload your CSV file to begin the data cleaning process</p>
            </div>
            <div className="stage-body">
              <CSVUpload
                onUploadSuccess={handleUploadSuccess}
                onUploadError={handleUploadError}
              />
            </div>
          </div>
        )}

        {/* Stage 2: AI Data Quality Analysis */}
        {currentStage === 2 && (
          <div className="stage-panel">
            <div className="stage-header">
              <h2>Stage 2: Data Inspection</h2>
              <p>AI-powered Inspection Agent analyzing your dataset for potential issues</p>
            </div>
            <div className="stage-body">
              {/* Loading State - Chat Interface with Progress */}
              {edaLoading && (
                <div className="chat-container">
                  <div className="chat-messages">
                    {/* Greeting message */}
                    <div className="chat-message">
                      <div className="message-avatar">
                        <div className="avatar-icon">AI</div>
                      </div>
                      <div className="message-content">
                        <div className="message-text">
                          <strong>Hi there! 👋</strong>
                          <br /><br />
                          I'm your data inspection assistant. Let me take a look at your dataset and check for any issues that might affect your visualizations.
                        </div>
                      </div>
                    </div>

                    {/* Progress message */}
                    <div className="chat-message">
                      <div className="message-avatar">
                        <div className="avatar-icon">AI</div>
                      </div>
                      <div className="message-content">
                        <div className="message-text">
                          <strong>
                            {progressStage === 'loading' && '📂 Loading dataset...'}
                            {progressStage === 'summary' && '📊 Calculating summary statistics...'}
                            {progressStage === 'statistics' && '📈 Analyzing column statistics...'}
                            {progressStage === 'detection' && '🔍 Detecting data quality issues...'}
                            {progressStage === 'enrichment' && '✨ Generating AI insights...'}
                            {progressStage === 'summary' && '📝 Creating final summary...'}
                            {!progressStage && 'Analyzing your dataset...'}
                          </strong>
                          {progressMessage && (
                            <>
                              <br /><br />
                              {progressMessage}
                            </>
                          )}

                          {/* Enrichment progress bar */}
                          {progressStage === 'enrichment' && enrichmentProgress.total > 0 && (
                            <>
                              <br /><br />
                              <div style={{ marginTop: '1rem' }}>
                                <div style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  marginBottom: '0.5rem',
                                  fontSize: '0.9rem',
                                  color: '#666'
                                }}>
                                  <span>
                                    {enrichmentProgress.current > 0 && enrichmentProgress.issue &&
                                      `Analyzing: ${enrichmentProgress.issue.substring(0, 50)}...`
                                    }
                                  </span>
                                  <span>
                                    <strong>{enrichmentProgress.current}</strong> / {enrichmentProgress.total}
                                  </span>
                                </div>
                                <div style={{
                                  width: '100%',
                                  height: '8px',
                                  backgroundColor: '#e0e0e0',
                                  borderRadius: '4px',
                                  overflow: 'hidden'
                                }}>
                                  <div style={{
                                    width: `${(enrichmentProgress.current / enrichmentProgress.total) * 100}%`,
                                    height: '100%',
                                    backgroundColor: '#4CAF50',
                                    transition: 'width 0.3s ease'
                                  }}></div>
                                </div>
                              </div>
                            </>
                          )}

                          {/* General progress items */}
                          {progressStage !== 'enrichment' && (
                            <>
                              <br /><br />
                              I'm checking for:
                              <br />
                              <div className="bullet-item" style={{ opacity: progressStage === 'loading' ? 1 : 0.5 }}>
                                {progressStage === 'loading' ? '🔄' : '✓'} Missing values and data completeness
                              </div>
                              <div className="bullet-item" style={{ opacity: progressStage === 'detection' ? 1 : 0.5 }}>
                                {progressStage === 'detection' ? '🔄' : '✓'} Outliers and anomalies
                              </div>
                              <div className="bullet-item" style={{ opacity: progressStage === 'statistics' ? 1 : 0.5 }}>
                                {progressStage === 'statistics' ? '🔄' : '✓'} Data type consistency
                              </div>
                              <div className="bullet-item" style={{ opacity: progressStage === 'enrichment' ? 1 : 0.5 }}>
                                {progressStage === 'enrichment' ? '🔄' : '✓'} Visualization concerns
                              </div>
                            </>
                          )}
                        </div>
                        <div className="typing-indicator" style={{ marginTop: '1rem' }}>
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Error State - Chat Interface */}
              {edaError && !edaLoading && (
                <div className="chat-container">
                  <div className="chat-messages">
                    <div className="chat-message">
                      <div className="message-avatar">
                        <div className="avatar-icon">AI</div>
                      </div>
                      <div className="message-content error-message">
                        <div className="message-text">
                          <strong>Oops! Something went wrong 😔</strong>
                          <br /><br />
                          I encountered an error while analyzing your dataset:
                          <br /><br />
                          <em>{edaError}</em>
                          <br /><br />
                          Would you like me to try again?
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="chat-actions">
                    <button onClick={runEDAAnalysis} className="secondary-button">
                      Yes, Retry Analysis
                    </button>
                  </div>
                </div>
              )}

              {/* Chat Interface Results */}
              {edaReport && !edaLoading && (
                <div className="chat-container">
                  <div className="chat-messages">
                    {chatMessages.map((message) => (
                      <div key={message.id} className={`chat-message ${message.severity || ''}`}>
                        <div className="message-avatar">
                          <div className="avatar-icon">AI</div>
                        </div>
                        <div className="message-content">
                          <div className="message-text">
                            {message.content.split('\n').map((line, idx) => {
                              // Simple markdown-like rendering
                              let processedLine = line;

                              // Bold **text**
                              processedLine = processedLine.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

                              // Bullets •
                              if (processedLine.trim().startsWith('•')) {
                                processedLine = `<div class="bullet-item">${processedLine}</div>`;
                              }

                              return (
                                <div key={idx} dangerouslySetInnerHTML={{ __html: processedLine || '<br/>' }} />
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Typing indicator */}
                    {isTyping && (
                      <div className="chat-message">
                        <div className="message-avatar">
                          <div className="avatar-icon">AI</div>
                        </div>
                        <div className="message-content">
                          <div className="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Action button */}
                  <div className="chat-actions">
                    <button onClick={runEDAAnalysis} className="secondary-button">
                      Re-analyze Dataset
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Stage 3: Processing */}
        {currentStage === 3 && (
          <div className="stage-panel">
            <div className="stage-header">
              <h2>Stage 3: Data Processing</h2>
              <p>Apply transformations and prepare your data for analysis</p>
            </div>
            <div className="stage-body">
              <div className="dataset-summary">
                <div className="summary-card">
                  <h4>Processing Options</h4>
                  <p>Select the cleaning and transformation operations you want to apply to your dataset.</p>
                </div>

                <div className="info-card">
                  <h4>What happens in this stage?</h4>
                  <p>Handle missing values, remove duplicates, normalize data formats, and apply any necessary transformations.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="stage-navigation">
        <button
          onClick={handleBack}
          className="nav-button secondary"
          disabled={currentStage === 1 || edaLoading}
          title={edaLoading ? 'Please wait for analysis to complete' : ''}
        >
          <ArrowLeft size={20} />
          Previous
        </button>

        {currentStage < stages.length ? (
          <button
            onClick={handleNext}
            className="nav-button primary"
            disabled={finalizing || (currentStage === 1 && !tempFilePath) || (currentStage === 2 && edaLoading)}
            title={edaLoading ? 'Please wait for analysis to complete' : ''}
          >
            {currentStage === 2 && edaLoading ? 'Analyzing...' : 'Next'}
            <ArrowRight size={20} />
          </button>
        ) : (
          <button onClick={handleComplete} className="nav-button primary" disabled={finalizing}>
            {finalizing ? 'Processing...' : 'Complete & Save'}
            <CheckCircle2 size={20} />
          </button>
        )}
      </div>
    </div>
  );
}
