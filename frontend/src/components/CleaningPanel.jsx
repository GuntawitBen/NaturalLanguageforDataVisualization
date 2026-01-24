import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle2, ArrowRight, AlertTriangle } from 'lucide-react';
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
  sessionComplete,
  onComplete,
  finalizing
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

  // Intro card state - show intro when problems are first loaded
  const [showIntro, setShowIntro] = useState(true);
  const totalProblems = currentProblem?.total_problems || 0;

  // Card swipe animation state
  const [animationClass, setAnimationClass] = useState('');
  const prevIndexRef = useRef(currentViewIndex);
  const prevSolvedCountRef = useRef(solvedCount);

  useEffect(() => {
    const prevSolvedCount = prevSolvedCountRef.current;

    // Detect if we moved forward (next problem / confirm) or backward (undo / prev)
    if (solvedCount > prevSolvedCount) {
      // Moving to next problem (confirmed an operation)
      // Only swipe in from right - the "Applied" animation already covers the exit
      setAnimationClass('swipe-in-right');
      setTimeout(() => setAnimationClass(''), 300);
    } else if (solvedCount < prevSolvedCount) {
      // Moving back (undo operation) - full swipe out then in
      setAnimationClass('swipe-out-right');
      setTimeout(() => {
        setAnimationClass('swipe-in-left');
        setTimeout(() => setAnimationClass(''), 300);
      }, 200);
    }

    prevIndexRef.current = currentViewIndex;
    prevSolvedCountRef.current = solvedCount;
  }, [currentViewIndex, solvedCount]);

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

        {/* Intro Card */}
        {showIntro && displayProblem && !sessionLoading && !sessionError && solvedCount === 0 && (
          <div className="intro-card">
            <div className="intro-card-content">
              <div className="intro-icon">
                <AlertTriangle size={48} />
              </div>
              <h2 className="intro-title">
                Detected <span className="problem-count">{totalProblems}</span> {totalProblems === 1 ? 'Issue' : 'Issues'}
              </h2>
              <p className="intro-description">
                We found some data quality issues that need your attention.
                Review each problem and choose how to resolve it.
              </p>
              <button
                className="intro-start-btn"
                onClick={() => setShowIntro(false)}
              >
                Start Cleaning
                <ArrowRight size={20} />
              </button>
            </div>
          </div>
        )}

        {/* Problem Card */}
        {displayProblem && !sessionLoading && !sessionError && (!showIntro || solvedCount > 0) && (
          <div className={`card-swipe-container ${animationClass}`}>
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
          </div>
        )}

        {/* Session Complete State */}
        {sessionComplete && !displayProblem && !sessionLoading && !sessionError && (
          <div className="complete-state-overlay">
            <div className="complete-state-content">
              <div className="complete-checkmark">
                <svg className="complete-checkmark-svg" viewBox="0 0 52 52">
                  <circle className="complete-checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
                  <path className="complete-checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
                </svg>
              </div>
              <span className="complete-text">All Issues Resolved</span>
              <button
                onClick={onComplete}
                className="complete-save-btn"
                disabled={finalizing || operationInProgress}
              >
                {finalizing ? 'Processing...' : 'Complete & Save'}
                <CheckCircle2 size={20} />
              </button>
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
