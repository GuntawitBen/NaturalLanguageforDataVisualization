import React from 'react';
import CleaningOptionCard from './CleaningOptionCard';
import './ProblemCard.css';

export default function ProblemCard({
  problem,
  options,
  onSelectOption,
  disabled,
  currentIndex,
  totalProblems,
  recommendation
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
          {/* Sort options: recommended first */}
          {[...options]
            .sort((a, b) => {
              if (recommendation?.recommended_option_id === a.option_id) return -1;
              if (recommendation?.recommended_option_id === b.option_id) return 1;
              return 0;
            })
            .map((option) => (
              <CleaningOptionCard
                key={option.option_id}
                option={option}
                onSelect={() => onSelectOption(option.option_id)}
                disabled={disabled}
                isRecommended={recommendation?.recommended_option_id === option.option_id}
                recommendationReason={
                  recommendation?.recommended_option_id === option.option_id
                    ? recommendation.reason
                    : null
                }
              />
            ))}
        </div>
      </div>
    </div>
  );
}
