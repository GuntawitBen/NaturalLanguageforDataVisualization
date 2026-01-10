import React from 'react';
import CleaningOptionCard from './CleaningOptionCard';
import './ProblemCard.css';

export default function ProblemCard({
  problem,
  options,
  onSelectOption,
  onSkip,
  disabled,
  currentIndex,
  totalProblems
}) {
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

  return (
    <div className="problem-card">
      <div className="problem-progress">
        Problem {currentIndex + 1} of {totalProblems}
      </div>

      <div className="problem-header">
        <span className={`severity-badge ${getSeverityClass(problem.severity)}`}>
          {problem.severity}
        </span>
        <h4 className="problem-title">{problem.title}</h4>
      </div>

      <p className="problem-description">{problem.description}</p>

      {problem.affected_columns && problem.affected_columns.length > 0 && (
        <div className="affected-columns">
          <strong>Affected Columns:</strong> {problem.affected_columns.join(', ')}
        </div>
      )}

      <div className="visualization-impact">
        <div className="impact-label">
          <span className="impact-icon">📊</span>
          <strong>Visualization Impact</strong>
        </div>
        <p>{problem.visualization_impact}</p>
      </div>

      <div className="cleaning-options-section">
        <h5 className="options-heading">Choose a cleaning approach:</h5>
        <div className="cleaning-options">
          {options.map((option) => (
            <CleaningOptionCard
              key={option.option_id}
              option={option}
              onSelect={() => onSelectOption(option.option_id)}
              disabled={disabled}
            />
          ))}
        </div>
      </div>

      <div className="problem-actions">
        <button
          onClick={onSkip}
          className="skip-button"
          disabled={disabled}
        >
          Skip this problem
        </button>
      </div>
    </div>
  );
}
