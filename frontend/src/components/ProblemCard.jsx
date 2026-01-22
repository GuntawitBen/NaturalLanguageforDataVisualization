import React, { useState } from 'react';
import './ProblemCard.css';

export default function ProblemCard({
  problem,
  options,
  onSelectOption,
  disabled,
  recommendation,
  isHistorical,
  appliedOptionId
}) {
  const [customValues, setCustomValues] = useState({});

  // Get letter for option index (A, B, C, etc.)
  const getLetter = (index) => String.fromCharCode(65 + index);

  // Determine severity badge color
  const getSeverityClass = (severity) => {
      switch (severity) {
          case 'critical':
              return 'severity-critical';
          case 'warning':
              return 'severity-warning';
          case 'info':
              return 'severity-info';
          default:
              return '';
      }
  };

        // Sort options: recommended first
  const sortedOptions = [...options].sort((a, b) => {
    if (recommendation?.recommended_option_id === a.option_id) return -1;
    if (recommendation?.recommended_option_id === b.option_id) return 1;
    return 0;
  });

  const handleOptionClick = (option) => {
    if (disabled || isHistorical) return;

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
        <span className={`severity-badge ${getSeverityClass(problem.severity)}`}>
          {problem.severity}
        </span>
        <h4 className="problem-title">{problem.title}</h4>
      </div>

      <p className="problem-description">{problem.description}</p>

      <div className="visualization-impact">
        <div className="impact-label">
          <span className="impact-icon">📊</span>
          <strong>Visualization Impact</strong>
        </div>
        <p>{problem.visualization_impact}</p>
      </div>

      <div className="cleaning-options-section">
        <h5 className="options-heading">
          {isHistorical ? 'Applied approach:' : 'Choose an approach:'}
        </h5>
        <div className="cleaning-options">
          {sortedOptions.map((option, index) => {
            const isRecommended = recommendation?.recommended_option_id === option.option_id;
            const isApplied = isHistorical && appliedOptionId === option.option_id;
            const letter = getLetter(index);

            return (
              <div
                key={option.option_id}
                className={`option-card ${isRecommended ? 'recommended' : ''} ${isApplied ? 'applied' : ''} ${disabled ? 'disabled' : ''} ${isHistorical && !isApplied ? 'faded' : ''}`}
                onClick={() => handleOptionClick(option)}
                role="button"
                tabIndex={disabled || isHistorical ? -1 : 0}
                onKeyDown={(e) => {
                  if ((e.key === 'Enter' || e.key === ' ') && !option.requires_input) {
                    handleOptionClick(option);
                  }
                }}
              >
                <div className="option-letter">{letter}</div>

                <div className="option-content">
                  <div className="option-header">
                    <span className="option-name">{option.option_name}</span>
                    {isRecommended && (
                      <span className="recommended-badge">Recommended</span>
                    )}
                    {isApplied && (
                      <span className="applied-badge">Applied</span>
                    )}
                  </div>

                  {isRecommended && recommendation?.reason && (
                    <p className="recommendation-reason">{recommendation.reason}</p>
                  )}

                  <div className="option-pros-cons">
                    <div className="pros">
                      <span className="pros-icon">+</span>
                      <span>{option.pros}</span>
                    </div>
                    <div className="cons">
                      <span className="cons-icon">-</span>
                      <span>{option.cons}</span>
                    </div>
                  </div>

                  {option.requires_input && !isHistorical && (
                    <div className="option-input-section" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        className="option-input"
                        placeholder="Enter value..."
                        value={customValues[option.option_id] || ''}
                        onChange={(e) => handleCustomValueChange(option.option_id, e.target.value)}
                        onKeyDown={(e) => handleKeyDown(option, e)}
                        disabled={disabled}
                      />
                      <button
                        className="option-apply-btn"
                        onClick={(e) => handleCustomApply(option, e)}
                        disabled={disabled || !customValues[option.option_id]?.trim()}
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
