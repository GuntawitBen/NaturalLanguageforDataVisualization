import React from 'react';
import './CleaningOptionCard.css';

export default function CleaningOptionCard({ option, onSelect, disabled, isRecommended, recommendationReason }) {
  return (
    <div
      className={`cleaning-option-card ${disabled ? 'disabled' : ''} ${isRecommended ? 'recommended' : ''}`}
      onClick={!disabled ? onSelect : null}
      role="button"
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(e) => {
        if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onSelect();
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
    </div>
  );
}
