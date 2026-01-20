import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useNavigationGuard } from '../contexts/NavigationGuardContext';
import { API_ENDPOINTS } from '../config';
import { CheckCircle2, ArrowRight } from 'lucide-react';
import CSVUpload from '../components/CSVUpload';
import CleaningPanel from '../components/CleaningPanel';
import DataPreviewPanel from '../components/DataPreviewPanel';
import './DataCleaning.css';

export default function DataCleaning() {
  const navigate = useNavigate();
  const { sessionToken } = useAuth();
  const { blockNavigation, unblockNavigation } = useNavigationGuard();

  // State for uploaded file info
  const [tempFilePath, setTempFilePath] = useState(null);
  const [datasetName, setDatasetName] = useState('');
  const [originalFilename, setOriginalFilename] = useState('');
  const [fileSize, setFileSize] = useState(0);

  const [currentStage, setCurrentStage] = useState(1);
  const [finalizing, setFinalizing] = useState(false);
  const [finalized, setFinalized] = useState(false);
  const [error, setError] = useState(null);

  // Cleaning session state
  const [cleaningSessionId, setCleaningSessionId] = useState(null);
  const [sessionState, setSessionState] = useState(null);
  const [currentProblem, setCurrentProblem] = useState(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState(null);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState(false);

  // Chat interface state
  const [chatMessages, setChatMessages] = useState([]);

  // Preview refresh trigger
  const [previewRefreshKey, setPreviewRefreshKey] = useState(0);

  const stages = [
    { id: 1, name: 'Upload Dataset', description: 'Upload your CSV file' },
    { id: 2, name: 'Data Cleaning', description: 'Review inspection results and preview your data' }
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

  // Cleanup temp file function
  const cleanupTempFile = useCallback(() => {
    if (tempFilePath && !finalized) {
      try {
        const formData = new FormData();
        formData.append('temp_file_path', tempFilePath);

        // Use keepalive to ensure request completes even during page unload
        fetch(API_ENDPOINTS.DATASETS.CLEANUP_TEMP, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
          },
          body: formData,
          keepalive: true,
        }).catch(() => {
          // Silently fail - best effort cleanup
        });
      } catch (err) {
        console.warn('Failed to cleanup temp file:', err);
      }
    }
  }, [tempFilePath, sessionToken, finalized]);

  // Cleanup temp file when component unmounts (if not finalized)
  useEffect(() => {
    return () => {
      cleanupTempFile();
    };
  }, [cleanupTempFile]);

  // Block navigation at all stages until finalized (includes browser close/refresh)
  useEffect(() => {
    if (!finalized) {
      blockNavigation(
        'Are you sure you want to leave? All current progress will be deleted.',
        cleanupTempFile
      );
    } else {
      unblockNavigation();
    }

    // Cleanup on unmount
    return () => {
      unblockNavigation();
    };
  }, [finalized, blockNavigation, unblockNavigation, cleanupTempFile]);

  const handleNext = () => {
    // Stage 1: Upload - can't go next without uploading
    if (currentStage === 1 && !tempFilePath) {
      setError('Please upload a file first');
      return;
    }

    // Stage 2: If cleaning is in progress, show confirmation
    if (currentStage === 2 && operationInProgress) {
      const confirmLeave = window.confirm(
        'An operation is in progress. Are you sure you want to continue?'
      );
      if (!confirmLeave) {
        return;
      }
    }

    // Stage 2 goes directly to completion
    if (currentStage === 2) {
      handleComplete();
      return;
    }

    // Otherwise move to next stage
    if (currentStage < stages.length) {
      setCurrentStage(currentStage + 1);
      setError(null);
    }
  };

  const handleBack = () => {
    // If cleaning is in progress on Stage 2, show confirmation
    if (currentStage === 2 && operationInProgress) {
      const confirmLeave = window.confirm(
        'An operation is in progress. Are you sure you want to go back?'
      );
      if (!confirmLeave) {
        return;
      }
    }

    if (currentStage > 1) {
      setCurrentStage(currentStage - 1);
      setError(null);
    }
  };

  // Start cleaning session
  const startCleaningSession = async () => {
    if (!tempFilePath) {
      setSessionError('No file uploaded');
      return;
    }

    setSessionLoading(true);
    setSessionError(null);
    setChatMessages([]);

    try {
      const response = await fetch(API_ENDPOINTS.CLEANING.START_SESSION, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          temp_file_path: tempFilePath,
          dataset_name: datasetName
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to start cleaning session');
      }

      const data = await response.json();

      // Store session info
      setCleaningSessionId(data.session_id);
      setSessionState(data.session_state);
      setCurrentProblem(data.first_problem);

      // Add summary message
      addChatMessage({
        id: 'summary',
        content: data.summary
      });

      // If we have problems, add a message introducing the workflow
      if (data.first_problem) {
        addChatMessage({
          id: 'workflow-intro',
          content: `Let's go through each issue one by one. For each problem, I'll provide you with cleaning options along with their pros and cons to help you decide.`
        });
        setSessionComplete(false);
      } else {
        setSessionComplete(true);
      }

      setSessionLoading(false);
    } catch (err) {
      console.error('Failed to start cleaning session:', err);
      setSessionError(err.message);
      setSessionLoading(false);
    }
  };

  // Apply selected cleaning operation
  const handleApplyOperation = async (optionId, customValue = null) => {
    if (!cleaningSessionId || operationInProgress) return;

    setOperationInProgress(true);

    try {
      const body = {
        session_id: cleaningSessionId,
        option_id: optionId
      };

      if (customValue !== null) {
        body.custom_parameters = { value: customValue };
      }

      const response = await fetch(API_ENDPOINTS.CLEANING.APPLY_OPERATION, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to apply operation');
      }

      const result = await response.json();

      // Add success message
      addChatMessage({
        id: `operation-${Date.now()}`,
        content: `${result.message}`
      });

      // Update state
      setCurrentProblem(result.next_problem);
      setSessionComplete(result.session_complete);

      // If session complete, add completion message
      if (result.session_complete) {
        addChatMessage({
          id: 'complete',
          content: `All problems have been addressed! Your dataset is now ready. You can proceed to finalize and save your cleaned dataset.`
        });
      }

      setOperationInProgress(false);

      // Force preview refresh by incrementing the refresh key
      setPreviewRefreshKey(prev => prev + 1);
    } catch (err) {
      console.error('Failed to apply operation:', err);
      addChatMessage({
        id: `error-${Date.now()}`,
        type: 'error',
        content: `Error: ${err.message}`
      });
      setOperationInProgress(false);
    }
  };

  // Undo last operation
  const handleUndoLast = async () => {
    if (!cleaningSessionId || operationInProgress) return;

    setOperationInProgress(true);

    try {
      const response = await fetch(API_ENDPOINTS.CLEANING.UNDO_LAST, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: cleaningSessionId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to undo operation');
      }

      const result = await response.json();

      if (result.success) {
        // Add undo message
        addChatMessage({
          id: `undo-${Date.now()}`,
          content: `↩️ ${result.message}`
        });

        // Update state
        setCurrentProblem(result.next_problem);
        setSessionComplete(result.session_complete);
      } else {
        addChatMessage({
          id: `undo-error-${Date.now()}`,
          content: `ℹ️ ${result.message}`
        });
      }

      setOperationInProgress(false);

      // Force preview refresh by incrementing the refresh key
      setPreviewRefreshKey(prev => prev + 1);
    } catch (err) {
      console.error('Failed to undo operation:', err);
      addChatMessage({
        id: `error-${Date.now()}`,
        type: 'error',
        content: `❌ Error: ${err.message}`
      });
      setOperationInProgress(false);
    }
  };

  // Helper to add chat messages
  const addChatMessage = (message) => {
    setChatMessages(prev => [...prev, message]);
  };

  // Auto-trigger cleaning session when entering Stage 2
  useEffect(() => {
    if (currentStage === 2 && tempFilePath && !cleaningSessionId && !sessionLoading) {
      startCleaningSession();
    }
  }, [currentStage, tempFilePath]);

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

        {/* Stage 2: Data Cleaning with Split View */}
        {currentStage === 2 && (
          <div className="stage-panel stage-cleaning">
            <div className="stage-header">
              <h2>Stage 2: Interactive Data Cleaning</h2>
              <p>Review data quality issues and apply cleaning operations</p>
            </div>
            <div className="split-view-container">
              <div className="split-view-panel left-panel">
                <CleaningPanel
                  sessionState={sessionState}
                  currentProblem={currentProblem}
                  chatMessages={chatMessages}
                  onApplyOperation={handleApplyOperation}
                  onUndoLast={handleUndoLast}
                  operationInProgress={operationInProgress}
                  sessionLoading={sessionLoading}
                  sessionError={sessionError}
                />
              </div>
              <div className="split-view-panel right-panel">
                <DataPreviewPanel
                  tempFilePath={tempFilePath}
                  datasetName={datasetName}
                  sessionToken={sessionToken}
                  refreshKey={previewRefreshKey}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="stage-navigation">
        {currentStage === 1 ? (
          <button
            onClick={handleNext}
            className="nav-button primary"
            disabled={!tempFilePath}
          >
            Next
            <ArrowRight size={20} />
          </button>
        ) : (
          <button
            onClick={handleNext}
            className="nav-button success"
            disabled={finalizing || operationInProgress || !sessionComplete}
            title={
              operationInProgress ? 'Please wait for operation to complete' :
                !sessionComplete ? 'Please resolve all data quality issues first' : ''
            }
          >
            {finalizing ? 'Processing...' : 'Complete & Save'}
            <CheckCircle2 size={20} />
          </button>
        )}
      </div>
    </div>
  );
}
