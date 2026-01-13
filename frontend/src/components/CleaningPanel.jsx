import React from 'react';
import ProblemCard from './ProblemCard';
import './CleaningPanel.css';

export default function CleaningPanel({
  sessionState,
  currentProblem,
  chatMessages,
  onApplyOperation,
  onSkipProblem,
  onUndoLast,
  operationInProgress,
  sessionLoading,
  sessionError
}) {
  return (
    <div className="cleaning-panel">
      <div className="panel-header">
        <h3>Interactive Data Cleaning</h3>
        {sessionState && !sessionLoading && (
          <span className="progress-badge">
            {currentProblem
              ? `Problem ${currentProblem.current_index + 1} of ${currentProblem.total_problems}`
              : 'Complete'
            }
          </span>
        )}
        {sessionLoading && (
          <span className="status-badge loading">Starting...</span>
        )}
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {/* Loading State */}
          {sessionLoading && (
            <div className="chat-message">
              <div className="message-avatar">
                <div className="avatar-icon">AI</div>
              </div>
              <div className="message-content">
                <div className="message-text">
                  <strong>Hi! 👋</strong>
                  <br /><br />
                  I'm your data cleaning assistant. Let me analyze your dataset for quality issues...
                </div>
                <div className="typing-indicator" style={{ marginTop: '1rem' }}>
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          {/* Error State */}
          {sessionError && !sessionLoading && (
            <div className="chat-message">
              <div className="message-avatar">
                <div className="avatar-icon">AI</div>
              </div>
              <div className="message-content error-message">
                <div className="message-text">
                  <strong>Oops! Something went wrong 😔</strong>
                  <br /><br />
                  I encountered an error while starting the cleaning session:
                  <br /><br />
                  <em>{sessionError}</em>
                </div>
              </div>
            </div>
          )}

          {/* Chat Messages */}
          {!sessionLoading && !sessionError && chatMessages.map((message) => (
            <div key={message.id} className={`chat-message ${message.type || ''}`}>
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

          {/* Current Problem Card */}
          {currentProblem && !sessionLoading && !sessionError && (
            <ProblemCard
              problem={currentProblem.problem}
              options={currentProblem.options}
              onSelectOption={onApplyOperation}
              onSkip={onSkipProblem}
              disabled={operationInProgress}
              currentIndex={currentProblem.current_index}
              totalProblems={currentProblem.total_problems}
              recommendation={currentProblem.recommendation}
            />
          )}

          {/* Operation in progress indicator */}
          {operationInProgress && (
            <div className="chat-message">
              <div className="message-avatar">
                <div className="avatar-icon">AI</div>
              </div>
              <div className="message-content">
                <div className="message-text">
                  <strong>Applying operation...</strong>
                </div>
                <div className="typing-indicator" style={{ marginTop: '0.5rem' }}>
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Undo Button */}
        {sessionState?.operation_history && sessionState.operation_history.length > 0 && !operationInProgress && (
          <div className="chat-actions">
            <button
              onClick={onUndoLast}
              className="undo-button"
              disabled={operationInProgress}
            >
              ← Undo Last Operation
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
