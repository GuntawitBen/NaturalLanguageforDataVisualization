import React, { useState } from 'react';
import {
  ArrowLeft,
  ChevronRight,
  Loader2,
  Table,
  AlertCircle,
  Lightbulb,
  History
} from 'lucide-react';
import { API_ENDPOINTS } from '../config';
import './ExplorationFlow.css';

export default function ExplorationFlow({
  session,
  observation,
  onExit,
  // datasetId is available for future use (e.g., chart rendering)
  // eslint-disable-next-line no-unused-vars
  datasetId,
  sessionToken
}) {
  const [currentObservation, setCurrentObservation] = useState(observation);
  const [availableChoices, setAvailableChoices] = useState(session?.available_choices || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [explorationHistory, setExplorationHistory] = useState([]);
  const [currentResults, setCurrentResults] = useState(null);

  const handleChoiceClick = async (choice) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        API_ENDPOINTS.PROACTIVE.CHOOSE(session.session_id),
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sessionToken}`,
          },
          body: JSON.stringify({ choice_id: choice.choice_id }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to process choice');
      }

      const data = await response.json();

      // Add to history
      setExplorationHistory(prev => [
        ...prev,
        {
          observation: currentObservation,
          choice: choice,
          results: data.results,
          resultCount: data.result_count,
          sql: data.sql_executed,
        }
      ]);

      // Update current state
      setCurrentResults({
        data: data.results,
        count: data.result_count,
        sql: data.sql_executed,
        message: data.message,
      });

      // Update observation and choices if we have follow-ups
      if (data.follow_up_observation) {
        setCurrentObservation(data.follow_up_observation);
      }
      setAvailableChoices(data.follow_up_choices || []);

    } catch (err) {
      console.error('Error making choice:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderResultsTable = () => {
    if (!currentResults?.data || currentResults.data.length === 0) {
      return (
        <div className="no-results">
          <Table size={24} />
          <p>No results found</p>
        </div>
      );
    }

    const columns = Object.keys(currentResults.data[0]);
    const rows = currentResults.data.slice(0, 50); // Limit display

    return (
      <div className="results-table-container">
        <div className="results-header">
          <span className="results-count">
            Showing {rows.length} of {currentResults.count} rows
          </span>
          {currentResults.sql && (
            <details className="sql-details">
              <summary>View SQL</summary>
              <pre>{currentResults.sql}</pre>
            </details>
          )}
        </div>
        <div className="results-table-wrapper">
          <table className="results-table">
            <thead>
              <tr>
                {columns.map(col => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {columns.map(col => (
                    <td key={col}>
                      {row[col] !== null && row[col] !== undefined
                        ? String(row[col])
                        : '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="exploration-flow">
      {/* Header */}
      <div className="exploration-header">
        <button className="back-btn" onClick={onExit}>
          <ArrowLeft size={16} />
          <span>Back to Insights</span>
        </button>
        <div className="step-indicator">
          Step {explorationHistory.length + 1}
        </div>
      </div>

      {/* Current Observation */}
      <div className="current-observation">
        <div className="observation-icon">
          <Lightbulb size={20} />
        </div>
        <div className="observation-content">
          <span className="observation-label">Current Finding</span>
          <p className="observation-text">{currentObservation?.text}</p>
        </div>
      </div>

      {/* Results Section */}
      {currentResults && (
        <div className="results-section">
          <h4>Query Results</h4>
          {renderResultsTable()}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="exploration-error">
          <AlertCircle size={20} />
          <p>{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="exploration-loading">
          <Loader2 size={24} className="spinning" />
          <span>Executing query...</span>
        </div>
      )}

      {/* Choices Section */}
      {!loading && availableChoices.length > 0 && (
        <div className="choices-section">
          <h4>What would you like to explore next?</h4>
          <div className="choices-grid">
            {availableChoices.map((choice) => (
              <button
                key={choice.choice_id}
                className="exploration-choice"
                onClick={() => handleChoiceClick(choice)}
                disabled={loading}
              >
                <span className="choice-text">{choice.text}</span>
                <div className="choice-meta">
                  <span className="chart-type">{choice.suggested_chart}</span>
                  <ChevronRight size={14} />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* End State */}
      {!loading && availableChoices.length === 0 && currentResults && (
        <div className="exploration-end">
          <p>You've reached the end of this exploration path.</p>
          <button className="restart-btn" onClick={onExit}>
            Explore Other Insights
          </button>
        </div>
      )}

      {/* Exploration History */}
      {explorationHistory.length > 0 && (
        <div className="exploration-history">
          <h4>
            <History size={16} />
            <span>Exploration Path</span>
          </h4>
          <div className="history-timeline">
            {explorationHistory.map((step, i) => (
              <div key={i} className="history-step">
                <div className="step-number">{i + 1}</div>
                <div className="step-content">
                  <p className="step-observation">{step.observation?.text}</p>
                  <p className="step-choice">{step.choice?.text}</p>
                  <span className="step-results">
                    {step.resultCount} rows returned
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
