import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  TrendingUp,
  AlertCircle,
  PieChart,
  Activity,
  BarChart3,
  ChevronRight,
  Loader2,
  RefreshCw,
  Lightbulb
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import ExplorationFlow from './ExplorationFlow';
import { API_ENDPOINTS } from '../config';
import './InsightsPanel.css';

// Map signal types to icons and colors
const SIGNAL_CONFIG = {
  trend: { icon: TrendingUp, color: '#3b82f6', label: 'Trend' },
  outlier: { icon: AlertCircle, color: '#ef4444', label: 'Outlier' },
  dominance: { icon: PieChart, color: '#8b5cf6', label: 'Dominance' },
  seasonality: { icon: Activity, color: '#10b981', label: 'Seasonality' },
  imbalance: { icon: BarChart3, color: '#f59e0b', label: 'Imbalance' },
};

const IMPORTANCE_COLORS = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#6b7280',
};

export default function InsightsPanel({ datasetId }) {
  const { sessionToken } = useAuth();
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedObservation, setSelectedObservation] = useState(null);
  const [explorationSession, setExplorationSession] = useState(null);

  // Fetch insights on mount
  useEffect(() => {
    if (sessionToken) {
      fetchInsights();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId, sessionToken]);

  const fetchInsights = async () => {
    console.log('[InsightsPanel] sessionToken:', sessionToken ? 'present' : 'missing');

    if (!sessionToken) {
      setError('Not authenticated');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_ENDPOINTS.PROACTIVE.INSIGHTS(datasetId)}`,
        {
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch insights');
      }

      const data = await response.json();
      setInsights(data);
    } catch (err) {
      console.error('Error fetching insights:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartExploration = async (observation) => {
    setSelectedObservation(observation);

    try {
      const response = await fetch(
        `${API_ENDPOINTS.PROACTIVE.EXPLORE(datasetId)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sessionToken}`,
          },
          body: JSON.stringify({
            dataset_id: datasetId,
            observation_id: observation.observation_id
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to start exploration');
      }

      const sessionData = await response.json();
      setExplorationSession(sessionData);
    } catch (err) {
      console.error('Error starting exploration:', err);
      setError(err.message);
    }
  };

  const handleExitExploration = () => {
    setSelectedObservation(null);
    setExplorationSession(null);
  };

  const getChoicesForObservation = (observationId) => {
    if (!insights?.choices) return [];
    return insights.choices.filter(c => c.observation_id === observationId);
  };

  const getSignalForObservation = (observation) => {
    if (!insights?.signals) return null;
    return insights.signals.find(s => s.signal_id === observation.signal_id);
  };

  // Show exploration flow if active
  if (explorationSession) {
    return (
      <ExplorationFlow
        session={explorationSession}
        observation={selectedObservation}
        onExit={handleExitExploration}
        datasetId={datasetId}
        sessionToken={sessionToken}
      />
    );
  }

  return (
    <div className="insights-panel">
      {/* Header */}
      <div className="insights-header">
        <div className="insights-title">
          <Sparkles size={20} />
          <h2>Data Insights</h2>
        </div>
        <button
          className="refresh-btn"
          onClick={fetchInsights}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? 'spinning' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="insights-loading">
          <div className="loading-content">
            <Loader2 size={32} className="spinning" />
            <h4>Analyzing your data...</h4>
            <p>Looking for interesting patterns and signals</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="insights-error">
          <AlertCircle size={32} />
          <h4>Failed to load insights</h4>
          <p>{error}</p>
          <button onClick={fetchInsights}>Try Again</button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && insights?.observations?.length === 0 && (
        <div className="insights-empty">
          <Lightbulb size={48} />
          <h4>No patterns detected</h4>
          <p>We couldn't find any significant patterns in this dataset. Try uploading a dataset with more data or different columns.</p>
        </div>
      )}

      {/* Observations List */}
      {!loading && !error && insights?.observations?.length > 0 && (
        <div className="observations-list">
          <div className="observations-count">
            Found <strong>{insights.observations.length}</strong> insights
          </div>

          {insights.observations.map((observation) => {
            const signal = getSignalForObservation(observation);
            const choices = getChoicesForObservation(observation.observation_id);
            const signalConfig = SIGNAL_CONFIG[signal?.signal_type] || SIGNAL_CONFIG.trend;
            const SignalIcon = signalConfig.icon;

            return (
              <div
                key={observation.observation_id}
                className="observation-card"
              >
                <div className="observation-header">
                  <div
                    className="signal-badge"
                    style={{ backgroundColor: `${signalConfig.color}20`, color: signalConfig.color }}
                  >
                    <SignalIcon size={14} />
                    <span>{signalConfig.label}</span>
                  </div>
                  <div
                    className="importance-dot"
                    style={{ backgroundColor: IMPORTANCE_COLORS[observation.importance] }}
                    title={`${observation.importance} importance`}
                  />
                </div>

                <p className="observation-text">{observation.text}</p>

                {signal && (
                  <div className="signal-details">
                    <span className="columns">
                      Columns: {signal.columns.join(', ')}
                    </span>
                    <span className="strength">
                      Strength: {(signal.strength * 100).toFixed(0)}%
                    </span>
                  </div>
                )}

                <div className="choices-section">
                  <span className="choices-label">Explore this finding:</span>
                  <div className="choices-list">
                    {choices.map((choice) => (
                      <button
                        key={choice.choice_id}
                        className="choice-btn"
                        onClick={() => handleStartExploration(observation)}
                      >
                        <span>{choice.text}</span>
                        <ChevronRight size={14} />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
