import './InspectionPanel.css';

export default function InspectionPanel({
  edaReport,
  edaLoading,
  edaError,
  edaCompleted,
  chatMessages,
  isTyping,
  progressStage,
  progressMessage,
  enrichmentProgress,
  onReanalyze,
  datasetName
}) {
  return (
    <div className="inspection-panel">
      <div className="panel-header">
        <h3>AI Data Inspection</h3>
        {edaCompleted && (
          <span className="status-badge complete">Analysis Complete</span>
        )}
        {edaLoading && (
          <span className="status-badge loading">Analyzing...</span>
        )}
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {/* Loading State - Chat Interface with Progress */}
          {edaLoading && (
            <>
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
            </>
          )}

          {/* Error State - Chat Interface */}
          {edaError && !edaLoading && (
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
          )}

          {/* Chat Interface Results */}
          {edaReport && !edaLoading && (
            <>
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
            </>
          )}
        </div>

        {/* Action button */}
        {(edaError || edaCompleted) && (
          <div className="chat-actions">
            <button onClick={onReanalyze} className="secondary-button">
              Re-analyze Dataset
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
