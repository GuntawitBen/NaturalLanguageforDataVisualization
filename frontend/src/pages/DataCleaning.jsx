import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import { CheckCircle2, ArrowRight, ArrowLeft } from 'lucide-react';
import CSVUpload from '../components/CSVUpload';
import './DataCleaning.css';

export default function DataCleaning() {
  const navigate = useNavigate();
  const { sessionToken } = useAuth();

  // State for uploaded file info
  const [tempFilePath, setTempFilePath] = useState(null);
  const [datasetName, setDatasetName] = useState('');
  const [originalFilename, setOriginalFilename] = useState('');
  const [fileSize, setFileSize] = useState(0);

  const [currentStage, setCurrentStage] = useState(1);
  const [finalizing, setFinalizing] = useState(false);
  const [finalized, setFinalized] = useState(false);
  const [error, setError] = useState(null);

  const stages = [
    { id: 1, name: 'Upload Dataset', description: 'Upload your CSV file' },
    { id: 2, name: 'Data Inspection', description: 'Review and validate your data' },
    { id: 3, name: 'Data Processing', description: 'Clean and transform your data' }
  ];

  // Handle successful upload from CSVUpload component
  const handleUploadSuccess = (tempData) => {
    console.log('Temp upload successful:', tempData);

    // Store temp file info
    setTempFilePath(tempData.temp_file_path);
    setDatasetName(tempData.dataset_name);
    setOriginalFilename(tempData.original_filename);
    setFileSize(tempData.file_size_bytes);

    // Move to next stage
    setCurrentStage(2);
  };

  const handleUploadError = (error) => {
    console.error('Upload error:', error);
    setError(error);
  };

  // Cleanup temp file when component unmounts (if not finalized)
  useEffect(() => {
    return () => {
      // Only cleanup if we have a temp file and it wasn't finalized
      if (tempFilePath && !finalized) {
        const cleanupTempFile = async () => {
          try {
            const formData = new FormData();
            formData.append('temp_file_path', tempFilePath);

            await fetch(API_ENDPOINTS.DATASETS.CLEANUP_TEMP, {
              method: 'DELETE',
              headers: {
                'Authorization': `Bearer ${sessionToken}`,
              },
              body: formData,
            });
          } catch (err) {
            // Silently fail - cleanup is best effort
            console.warn('Failed to cleanup temp file:', err);
          }
        };

        cleanupTempFile();
      }
    };
  }, [tempFilePath, sessionToken, finalized]);

  const handleNext = () => {
    // Stage 1: Upload - can't go next without uploading
    if (currentStage === 1 && !tempFilePath) {
      setError('Please upload a file first');
      return;
    }

    if (currentStage < stages.length) {
      setCurrentStage(currentStage + 1);
      setError(null);
    }
  };

  const handleBack = () => {
    if (currentStage > 1) {
      setCurrentStage(currentStage - 1);
      setError(null);
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

      // Mark as finalized so cleanup doesn't happen
      setFinalized(true);

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
        <h1>Upload & Clean Dataset</h1>
        <p className="subtitle">
          {datasetName ? `Preparing: ${datasetName}` : 'Upload and prepare your dataset for analysis'}
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          <p className="error-message">{error}</p>
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
        {/* Stage 1: Upload */}
        {currentStage === 1 && (
          <div className="stage-panel">
            <div className="stage-header">
              <h2>Stage 1: Upload Dataset</h2>
              <p>Upload your CSV file to begin the data cleaning process</p>
            </div>
            <div className="stage-body">
              <CSVUpload
                onUploadSuccess={handleUploadSuccess}
                onUploadError={handleUploadError}
              />
            </div>
          </div>
        )}

        {/* Stage 2: Inspection */}
        {currentStage === 2 && (
          <div className="stage-panel">
            <div className="stage-header">
              <h2>Stage 2: Data Inspection</h2>
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

        {/* Stage 3: Processing */}
        {currentStage === 3 && (
          <div className="stage-panel">
            <div className="stage-header">
              <h2>Stage 3: Data Processing</h2>
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
          <button
            onClick={handleNext}
            className="nav-button primary"
            disabled={finalizing || (currentStage === 1 && !tempFilePath)}
          >
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
