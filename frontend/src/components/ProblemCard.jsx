import React, { useState } from 'react';
import { ChevronLeft, Info, Check } from 'lucide-react';
import './ProblemCard.css';

export default function ProblemCard({
  problem,
  options,
  onSelectOption,
  onConfirmOperation,
  onDiscardOperation,
  disabled,
  recommendation,
  isHistorical,
  appliedOptionId,
  pendingOptionId,
  problemNumber,
  totalProblems,
  onPrevious,
  canGoPrevious
}) {
  const [customValues, setCustomValues] = useState({});
  const [showImpact, setShowImpact] = useState(false);
  const [showOptionInfo, setShowOptionInfo] = useState(null); // option_id or null

  // Get letter for option index (A, B, C, etc.)
  const getLetter = (index) => String.fromCharCode(65 + index);

  // Sort options: recommended first
  const sortedOptions = [...options].sort((a, b) => {
    if (recommendation?.recommended_option_id === a.option_id) return -1;
    if (recommendation?.recommended_option_id === b.option_id) return 1;
    return 0;
  });

  const handleOptionClick = (option) => {
    if (disabled || isHistorical) return;

    // Don't allow clicking other options when there's a pending operation
    if (pendingOptionId) return;

    // For options requiring input, don't apply on card click
    if (option.requires_input) return;

    onSelectOption(option.option_id, null);
  };

  const handleCustomApply = (option, e) => {
    e.stopPropagation();
    if (disabled || isHistorical) return;

    const value = customValues[option.option_id] || '';
    if (value.trim()) {
      onSelectOption(option.option_id, value);
    }
  };

  const handleCustomValueChange = (optionId, value) => {
    setCustomValues(prev => ({ ...prev, [optionId]: value }));
  };

  const handleKeyDown = (option, e) => {
    if (e.key === 'Enter' && option.requires_input) {
      handleCustomApply(option, e);
    }
  };

  return (
    <div className="problem-card">
      <div className="problem-header">
        <span className="problem-number">Problem {problemNumber} of {totalProblems}</span>
        <div className="problem-nav-row">
          <button
            className="problem-prev-btn"
            onClick={onPrevious}
            disabled={!canGoPrevious || disabled || pendingOptionId}
            aria-label="Previous problem"
          >
            <ChevronLeft size={16} />
            <span>Prev</span>
          </button>
          <div className="problem-progress-bar">
            <div
              className="problem-progress-fill"
              style={{ width: `${(problemNumber / totalProblems) * 100}%` }}
            />
          </div>
        </div>
        <div className="problem-title-row">
          <h4 className="problem-title">{problem.title}</h4>
          <div className="info-btn-wrapper">
            <button
              className={`info-btn ${showImpact ? 'active' : ''}`}
              onClick={() => setShowImpact(!showImpact)}
              aria-label="Show visualization impact"
            >
              <Info size={18} />
            </button>
            {showImpact && (
              <div className="visualization-impact-popup">
                <p>{problem.visualization_impact}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <p className="problem-description">{problem.description}</p>

      <div className="cleaning-options-section">
        <h5 className="options-heading">
          {isHistorical ? 'Applied approach:' : 'Choose an approach:'}
        </h5>
        <div className="cleaning-options">
          {sortedOptions.map((option, index) => {
            const isRecommended = recommendation?.recommended_option_id === option.option_id;
            const isApplied = isHistorical && appliedOptionId === option.option_id;
            const isPending = pendingOptionId === option.option_id;
            const letter = getLetter(index);

            return (
              <div
                key={option.option_id}
                className={`option-card ${isRecommended ? 'recommended' : ''} ${isApplied ? 'applied' : ''} ${isPending ? 'pending' : ''} ${disabled ? 'disabled' : ''} ${isHistorical && !isApplied ? 'faded' : ''} ${pendingOptionId && !isPending ? 'greyed-out' : ''}`}
                onClick={() => handleOptionClick(option)}
                role="button"
                tabIndex={disabled || isHistorical ? -1 : 0}
                onKeyDown={(e) => {
                  if ((e.key === 'Enter' || e.key === ' ') && !option.requires_input) {
                    handleOptionClick(option);
                  }
                }}
              >
                <div className={`option-radio ${isPending || isApplied ? 'checked' : ''}`}>
                  {(isPending || isApplied) && <Check size={16} strokeWidth={3} />}
                </div>

                <div className="option-content">
                  <div className="option-header">
                    <span className="option-name">{option.option_name}</span>
                    {isRecommended && (
                      <span className="recommended-badge">Recommended</span>
                    )}
                    {isApplied && (
                      <span className="applied-badge">Applied</span>
                    )}
                    <div className="option-info-wrapper" onClick={(e) => e.stopPropagation()}>
                      <button
                        className={`option-info-btn ${showOptionInfo === option.option_id ? 'active' : ''}`}
                        onClick={() => setShowOptionInfo(showOptionInfo === option.option_id ? null : option.option_id)}
                        aria-label="Show advantages and disadvantages"
                      >
                        <Info size={14} />
                      </button>
                      {showOptionInfo === option.option_id && (
                        <div className="option-pros-cons-popup">
                          <div className="pros">
                            <span className="pros-icon">+</span>
                            <span>{option.pros}</span>
                          </div>
                          <div className="cons">
                            <span className="cons-icon">-</span>
                            <span>{option.cons}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {isRecommended && recommendation?.reason && (
                    <p className="recommendation-reason">{recommendation.reason}</p>
                  )}

                  {option.requires_input && !isHistorical && (
                    <div className="option-input-section" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        className="option-input"
                        placeholder="Enter value..."
                        value={customValues[option.option_id] || ''}
                        onChange={(e) => handleCustomValueChange(option.option_id, e.target.value)}
                        onKeyDown={(e) => handleKeyDown(option, e)}
                        disabled={disabled || pendingOptionId}
                      />
                      <button
                        className="option-apply-btn"
                        onClick={(e) => handleCustomApply(option, e)}
                        disabled={disabled || !customValues[option.option_id]?.trim() || pendingOptionId}
                      >
                        Apply
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
}
