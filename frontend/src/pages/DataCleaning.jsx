import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import { CheckCircle2, Circle, ArrowRight, ArrowLeft } from 'lucide-react';
import './DataCleaning.css';

export default function DataCleaning() {
  const navigate = useNavigate();
  const { sessionToken } = useAuth();
  const [searchParams] = useSearchParams();

  // Get temp file info from URL params
  const tempFilePath = searchParams.get('tempFilePath');
  const datasetName = searchParams.get('datasetName');
  const originalFilename = searchParams.get('originalFilename');
  const fileSize = searchParams.get('fileSize');

  const [currentStage, setCurrentStage] = useState(1);
  const [finalizing, setFinalizing] = useState(false);
  const [error, setError] = useState(null);

  const stages = [
    { id: 1, name: 'Data Inspection', description: 'Review and validate your data' },
    { id: 2, name: 'Data Processing', description: 'Clean and transform your data' }
  ];

  useEffect(() => {
    if (!tempFilePath || !datasetName) {
      navigate('/upload');
    }
  }, [tempFilePath, datasetName]);

  const handleNext = () => {
    if (currentStage < stages.length) {
      setCurrentStage(currentStage + 1);
    }
  };

  const handleBack = () => {
    if (currentStage > 1) {
      setCurrentStage(currentStage - 1);
    }
  };

  const handleComplete = async () => {
    setFinalizing(true);
    setError(null);

    try {
      // Create form data for finalize endpoint
      const formData = new FormData();
      formData.append('temp_file_path', tempFilePath);
      formData.append('dataset_name', datasetName);
      formData.append('original_filename', originalFilename);

      const response = await fetch(API_ENDPOINTS.DATASETS.FINALIZE, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to finalize dataset');
      }

      const dataset = await response.json();

      // Navigate to dataset details page
      navigate(`/datasets/${dataset.dataset_id}`);
    } catch (err) {
      console.error('Error finalizing dataset:', err);
      setError(err.message);
      setFinalizing(false);
    }
  };

  return (
    <div className="data-cleaning-page">
      {/* Header */}
      <div className="cleaning-header">
        <button onClick={() => navigate('/datasets')} className="back-link">
          <ArrowLeft size={20} />
          Back to Datasets
        </button>
        <h1>Data Cleaning</h1>
        <p className="subtitle">
          Prepare your dataset: <strong>{datasetName}</strong>
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          <p className="error-message">{error}</p>
          <button onClick={() => navigate('/upload')} className="retry-button">
            Back to Upload
          </button>
        </div>
      )}

      {/* Progress Stepper */}
      <div className="progress-stepper">
        {stages.map((stage, index) => (
          <div key={stage.id} className="step-container">
            <div className={`step ${currentStage >= stage.id ? 'active' : ''} ${currentStage > stage.id ? 'completed' : ''}`}>
              <div className="step-indicator">
                {currentStage > stage.id ? (
                  <CheckCircle2 size={32} className="step-icon completed" />
                ) : (
                  <div className={`step-number ${currentStage === stage.id ? 'active' : ''}`}>
                    {stage.id}
                  </div>
                )}
              </div>
              <div className="step-info">
                <h3>{stage.name}</h3>
                <p>{stage.description}</p>
              </div>
            </div>
            {index < stages.length - 1 && (
              <div className={`step-connector ${currentStage > stage.id ? 'completed' : ''}`}></div>
            )}
          </div>
        ))}
      </div>

      {/* Stage Content */}
      <div className="stage-content">
        {currentStage === 1 && (
          <div className="stage-panel">
            <div className="stage-header">
              <h2>Stage 1: Data Inspection</h2>
              <p>Review your uploaded data and check for any issues</p>
            </div>
            <div className="stage-body">
              <div className="dataset-summary">
                <div className="summary-card">
                  <h4>Dataset Information</h4>
                  <ul>
                    <li><span>Name:</span> {datasetName}</li>
                    <li><span>File:</span> {originalFilename}</li>
                    <li><span>Size:</span> {(fileSize / 1024).toFixed(2)} KB</li>
                    <li><span>Status:</span> Pending Processing</li>
                  </ul>
                </div>

                <div className="info-card">
                  <h4>What happens in this stage?</h4>
                  <p>Review your data structure, check column types, and identify any missing values or anomalies.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {currentStage === 2 && (
          <div className="stage-panel">
            <div className="stage-header">
              <h2>Stage 2: Data Processing</h2>
              <p>Apply transformations and prepare your data for analysis</p>
            </div>
            <div className="stage-body">
              <div className="dataset-summary">
                <div className="summary-card">
                  <h4>Processing Options</h4>
                  <p>Select the cleaning and transformation operations you want to apply to your dataset.</p>
                </div>

                <div className="info-card">
                  <h4>What happens in this stage?</h4>
                  <p>Handle missing values, remove duplicates, normalize data formats, and apply any necessary transformations.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="stage-navigation">
        <button
          onClick={handleBack}
          className="nav-button secondary"
          disabled={currentStage === 1}
        >
          <ArrowLeft size={20} />
          Previous
        </button>

        {currentStage < stages.length ? (
          <button onClick={handleNext} className="nav-button primary" disabled={finalizing}>
            Next
            <ArrowRight size={20} />
          </button>
        ) : (
          <button onClick={handleComplete} className="nav-button primary" disabled={finalizing}>
            {finalizing ? 'Processing...' : 'Complete & Save'}
            <CheckCircle2 size={20} />
          </button>
        )}
      </div>
    </div>
  );
}
