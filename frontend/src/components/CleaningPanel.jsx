import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ProblemCard from './ProblemCard';
import './CleaningPanel.css';

export default function CleaningPanel({
  currentProblem,
  problemHistory,
  viewingIndex,
  onNavigate,
  onApplyOperation,
  onUndoOperation,
  operationInProgress,
  sessionLoading,
  sessionError,
  sessionComplete
}) {
  // Calculate total problems and current position
  const solvedCount = problemHistory?.length || 0;
  const hasCurrentProblem = currentProblem !== null;
  const totalDots = hasCurrentProblem ? solvedCount + 1 : solvedCount;

  // viewingIndex: -1 means viewing current problem, 0+ means viewing history
  const isViewingHistory = viewingIndex >= 0;
  const currentViewIndex = isViewingHistory ? viewingIndex : solvedCount;

  // Get the problem to display
  const displayProblem = isViewingHistory
    ? problemHistory[viewingIndex]
    : currentProblem;

  // Navigation handlers
  const canGoPrev = currentViewIndex > 0;
  const canGoNext = isViewingHistory && (viewingIndex < solvedCount - 1 || hasCurrentProblem);

  const handlePrev = () => {
    if (!canGoPrev) return;
    if (isViewingHistory) {
      onNavigate(viewingIndex - 1);
    } else {
      onNavigate(solvedCount - 1);
    }
  };

  const handleNext = () => {
    if (!canGoNext) return;
    if (viewingIndex === solvedCount - 1 && hasCurrentProblem) {
      onNavigate(-1); // Go to current problem
    } else {
      onNavigate(viewingIndex + 1);
    }
  };

  // Progress label
  const getProgressLabel = () => {
    if (sessionComplete) return 'All issues resolved';
    if (isViewingHistory) {
      return `Viewing problem ${viewingIndex + 1} of ${totalDots}`;
    }
    return `Problem ${solvedCount + 1} of ${currentProblem?.total_problems || totalDots}`;
  };

  return (
    <div className="cleaning-panel">
      {/* Navigation Header */}
      <div className="card-flipper-header">
        <button
          className="nav-btn prev"
          onClick={handlePrev}
          disabled={!canGoPrev || operationInProgress}
          aria-label="Previous problem"
        >
          <ChevronLeft size={20} />
          <span>Prev</span>
        </button>

        <div className="progress-section">
          <span className="progress-label">{getProgressLabel()}</span>
          {totalDots > 0 && (
            <div className="progress-dots">
              {Array.from({ length: totalDots }).map((_, index) => {
                const isSolved = index < solvedCount;
                const isCurrent = index === currentViewIndex;
                return (
                  <button
                    key={index}
                    className={`progress-dot ${isSolved ? 'completed' : ''} ${isCurrent ? 'active' : ''}`}
                    onClick={() => {
                      if (index < solvedCount) {
                        onNavigate(index);
                      } else if (hasCurrentProblem) {
                        onNavigate(-1);
                      }
                    }}
                    disabled={operationInProgress}
                    aria-label={`Go to problem ${index + 1}`}
                  />
                );
              })}
            </div>
          )}
        </div>

        <button
          className="nav-btn next"
          onClick={handleNext}
          disabled={!canGoNext || operationInProgress}
          aria-label="Next problem"
        >
          <span>Next</span>
          <ChevronRight size={20} />
        </button>
      </div>

      {/* Undo Button Section (only if there are solved problems) */}
      {solvedCount > 0 && (
        <div className="undo-section">
          <button
            className="undo-btn"
            onClick={onUndoOperation}
            disabled={operationInProgress}
            title="Undo last action and return to previous problem"
          >
            <ChevronLeft size={16} />
            Previous Step (Undo)
          </button>
        </div>
      )}

      {/* Card Container */}
      <div className="card-container">
        {/* Loading State */}
        {sessionLoading && (
          <div className="loading-state">
            <div className="loading-content">
              <h4>Analyzing your dataset...</h4>
              <p>Looking for data quality issues</p>
              <div className="loading-spinner">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {sessionError && !sessionLoading && (
          <div className="error-state">
            <div className="error-content">
              <h4>Something went wrong</h4>
              <p>{sessionError}</p>
            </div>
          </div>
        )}

        {/* Problem Card */}
        {displayProblem && !sessionLoading && !sessionError && (
          <ProblemCard
            problem={displayProblem.problem}
            options={displayProblem.options}
            onSelectOption={onApplyOperation}
            disabled={operationInProgress || isViewingHistory}
            recommendation={displayProblem.recommendation}
            isHistorical={isViewingHistory}
            appliedOptionId={isViewingHistory ? displayProblem.appliedOptionId : null}
          />
        )}

        {/* Session Complete State */}
        {sessionComplete && !displayProblem && !sessionLoading && !sessionError && (
          <div className="complete-state">
            <div className="complete-content">
              <div className="complete-icon">✓</div>
              <h4>All issues resolved!</h4>
              <p>Your dataset is now ready for visualization. Click "Complete & Save" to proceed.</p>
            </div>
          </div>
        )}

        {/* Operation in progress overlay */}
        {operationInProgress && (
          <div className="operation-overlay">
            <div className="loading-spinner">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <p>Applying...</p>
          </div>
        )}
      </div>
    </div>
  );
}
