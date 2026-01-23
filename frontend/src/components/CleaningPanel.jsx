import React from 'react';
import ProblemCard from './ProblemCard';
import './CleaningPanel.css';

export default function CleaningPanel({
  currentProblem,
  problemHistory,
  viewingIndex,
  onNavigate,
  onApplyOperation,
  onConfirmOperation,
  onDiscardOperation,
  onUndoOperation,
  operationInProgress,
  pendingOperation,
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

  // Navigation handlers - Prev button now triggers undo
  const canGoPrev = solvedCount > 0 && !operationInProgress;

  return (
    <div className="cleaning-panel">
      {/* Header */}
      <div className="card-flipper-header">
        <h3 className="panel-title">Data Cleaning</h3>
      </div>

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
            onConfirmOperation={onConfirmOperation}
            onDiscardOperation={onDiscardOperation}
            disabled={operationInProgress || isViewingHistory}
            recommendation={displayProblem.recommendation}
            isHistorical={isViewingHistory}
            appliedOptionId={isViewingHistory ? displayProblem.appliedOptionId : null}
            pendingOptionId={pendingOperation?.optionId}
            problemNumber={currentViewIndex + 1}
            totalProblems={isViewingHistory ? totalDots : (currentProblem?.total_problems || totalDots)}
            onPrevious={onUndoOperation}
            canGoPrevious={canGoPrev}
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
            {/*<p>Applying...</p>*/}
          </div>
        )}
      </div>
    </div>
  );
}
