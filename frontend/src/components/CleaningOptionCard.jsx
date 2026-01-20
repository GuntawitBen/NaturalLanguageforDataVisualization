import React, { useState } from 'react';
import './CleaningOptionCard.css';

export default function CleaningOptionCard({ option, onSelect, disabled, isRecommended, recommendationReason }) {
  const [customValue, setCustomValue] = useState('');

  const handleApply = (e) => {
    e.stopPropagation();
    if (disabled) return;
    onSelect(customValue);
  };

  const handleCardClick = () => {
    if (disabled) return;
    if (!option.requires_input) {
      onSelect();
    }
  };

  return (
    <div
      className={`cleaning-option-card ${disabled ? 'disabled' : ''} ${isRecommended ? 'recommended' : ''} ${option.requires_input ? 'has-input' : ''}`}
      onClick={handleCardClick}
      role="button"
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(e) => {
        if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          handleCardClick();
        }
      }}
    >
      {isRecommended && (
        <div className="recommendation-banner">
          <span className="recommendation-badge">Recommended</span>
          {recommendationReason && (
            <p className="recommendation-reason">{recommendationReason}</p>
          )}
        </div>
      )}
      <div className="option-header">
        <h6 className="option-name">{option.option_name}</h6>
        {option.impact_metrics?.rows_affected !== undefined && option.impact_metrics.rows_affected !== null && (
          <span className="impact-badge">
            {option.impact_metrics.rows_affected} rows affected
          </span>
        )}
      </div>

      <div className="pros-cons-container">
        <div className="pros-section">
          <div className="section-label">
            <span className="icon">✓</span>
            <strong>Advantages</strong>
          </div>
          <p className="section-content">{option.pros}</p>
        </div>

        <div className="cons-section">
          <div className="section-label">
            <span className="icon">✗</span>
            <strong>Disadvantages</strong>
          </div>
          <p className="section-content">{option.cons}</p>
        </div>
      </div>

      {option.impact_metrics?.notes && (
        <div className="impact-notes">
          <strong>Note:</strong> {option.impact_metrics.notes}
        </div>
      )}

      {option.requires_input && (
        <div className="option-input-container" onClick={(e) => e.stopPropagation()}>
          <div className="input-group">
            <input
              type="text"
              placeholder="Enter default value..."
              value={customValue}
              onChange={(e) => setCustomValue(e.target.value)}
              className="custom-value-input"
              disabled={disabled}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleApply(e);
                }
              }}
            />
            <button
              onClick={handleApply}
              disabled={disabled || !customValue.trim()}
              className="apply-value-button"
            >
              Apply
            </button>
          </div>
          <p className="input-hint">This value will be used to fill all missing entries in the column.</p>
        </div>
      )}
    </div>
  );
}
