import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useNavigationGuard } from '../contexts/NavigationGuardContext';
import { API_ENDPOINTS } from '../config';
import {
  Upload,
  Database,
  Sparkles,
  CheckCircle2,
  ArrowRight,
  FileText,
  Zap,
  Terminal,
  Activity,
  Shield,
  ChevronRight,
  AlertTriangle,
  HardDrive,
  Layers
} from 'lucide-react';
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

  // Refs for state that needs to be accessed in cleanup/unload events
  const finalizedRef = useRef(false);
  const isFinalizingRef = useRef(false);

  // Keep refs in sync with state
  useEffect(() => {
    finalizedRef.current = finalized;
  }, [finalized]);

  useEffect(() => {
    isFinalizingRef.current = finalizing;
  }, [finalizing]);

  // Cleaning session state
  const [cleaningSessionId, setCleaningSessionId] = useState(null);
  const [sessionState, setSessionState] = useState(null);
  const [currentProblem, setCurrentProblem] = useState(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState(null);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState(false);
  const [operationType, setOperationType] = useState(null);

  // Problem history for card navigation
  const [problemHistory, setProblemHistory] = useState([]);
  const [viewingIndex, setViewingIndex] = useState(-1);

  // Preview refresh trigger
  const [previewRefreshKey, setPreviewRefreshKey] = useState(0);

  // Pending operation state
  const [pendingOperation, setPendingOperation] = useState(null);

  // Success animation state
  const [showSuccessAnimation, setShowSuccessAnimation] = useState(false);

  const stages = [
    { id: 1, name: 'Upload', icon: Upload, command: 'upload --file' },
    { id: 2, name: 'Clean & Validate', icon: Shield, command: 'clean --auto' }
  ];

  // Handle successful upload from CSVUpload component
  const handleUploadSuccess = (tempData) => {
    setTempFilePath(tempData.temp_file_path);
    setDatasetName(tempData.dataset_name);
    setOriginalFilename(tempData.original_filename);
    setFileSize(tempData.file_size_bytes);
    setCurrentStage(2);
  };

  const handleUploadError = (error) => {
    console.error('Upload error:', error);
    setError(error);
  };

  // Cleanup temp file function
  const cleanupTempFile = useCallback(() => {
    if (tempFilePath && !finalizedRef.current && !isFinalizingRef.current) {
      try {
        const formData = new FormData();
        formData.append('temp_file_path', tempFilePath);

        fetch(API_ENDPOINTS.DATASETS.CLEANUP_TEMP, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
          },
          body: formData,
          keepalive: true,
        }).catch((err) => {
          console.warn('Silent cleanup fail:', err);
        });
      } catch (err) {
        console.warn('Failed to cleanup temp file:', err);
      }
    }
  }, [tempFilePath, sessionToken]);

  // Cleanup temp file when component unmounts
  useEffect(() => {
    return () => {
      cleanupTempFile();
    };
  }, [cleanupTempFile]);

  // Block navigation until finalized
  useEffect(() => {
    if (!finalized) {
      blockNavigation(
        'Are you sure you want to leave? All current progress will be deleted.',
        cleanupTempFile
      );
    } else {
      unblockNavigation();
    }

    return () => {
      unblockNavigation();
    };
  }, [finalized, blockNavigation, unblockNavigation, cleanupTempFile]);

  const handleNext = () => {
    if (currentStage === 1 && !tempFilePath) {
      setError('Please upload a file first');
      return;
    }

    if (currentStage === 2 && operationInProgress) {
      const confirmLeave = window.confirm(
        'An operation is in progress. Are you sure you want to continue?'
      );
      if (!confirmLeave) return;
    }

    if (currentStage === 2) {
      handleComplete();
      return;
    }

    if (currentStage < stages.length) {
      setCurrentStage(currentStage + 1);
      setError(null);
    }
  };

  const handleBack = () => {
    if (currentStage === 2 && operationInProgress) {
      const confirmLeave = window.confirm(
        'An operation is in progress. Are you sure you want to go back?'
      );
      if (!confirmLeave) return;
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
    setProblemHistory([]);
    setViewingIndex(-1);

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

      setCleaningSessionId(data.session_id);
      setSessionState(data.session_state);
      setCurrentProblem(data.first_problem);

      if (!data.first_problem) {
        setSessionComplete(true);
      } else {
        setSessionComplete(false);
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

    if (viewingIndex >= 0) {
      setViewingIndex(-1);
      return;
    }

    setOperationInProgress(true);
    setOperationType('applying');

    if (pendingOperation) {
      try {
        const undoResponse = await fetch(API_ENDPOINTS.CLEANING.UNDO_LAST, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ session_id: cleaningSessionId })
        });

        if (!undoResponse.ok) {
          setPendingOperation(null);
          setOperationInProgress(false);
          setPreviewRefreshKey(prev => prev + 1);
          return;
        }

        const undoResult = await undoResponse.json();

        if (undoResult.next_problem) {
          setCurrentProblem(undoResult.next_problem);
          const restoredOption = undoResult.next_problem.options?.find(
            opt => opt.option_id === optionId
          );
          if (!restoredOption) {
            setPendingOperation(null);
            setOperationInProgress(false);
            setPreviewRefreshKey(prev => prev + 1);
            return;
          }
        }

        setPendingOperation(null);
      } catch (err) {
        setPendingOperation(null);
        setOperationInProgress(false);
        return;
      }
    }

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
        throw new Error(`Failed to apply operation: ${response.status}`);
      }

      setPendingOperation({ optionId, customValue });
      setOperationInProgress(false);
      setPreviewRefreshKey(prev => prev + 1);
    } catch (err) {
      console.error('Failed to apply operation:', err);
      setPendingOperation(null);
      setOperationInProgress(false);
    }
  };

  // Confirm the pending operation
  const handleConfirmOperation = async () => {
    if (!pendingOperation) return;

    setShowSuccessAnimation(true);

    const problemToStore = {
      ...currentProblem,
      appliedOptionId: pendingOperation.optionId
    };

    const minAnimationTime = new Promise(resolve => setTimeout(resolve, 800));

    const fetchNextProblem = async () => {
      try {
        const response = await fetch(API_ENDPOINTS.CLEANING.CONFIRM_OPERATION, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ session_id: cleaningSessionId })
        });

        if (response.ok) {
          return await response.json();
        }
        return { next_problem: null, session_complete: true };
      } catch (err) {
        return { next_problem: null, session_complete: true };
      }
    };

    const [, result] = await Promise.all([minAnimationTime, fetchNextProblem()]);

    setProblemHistory(prev => [...prev, problemToStore]);
    setCurrentProblem(result.next_problem);
    setSessionComplete(result.session_complete);
    setPendingOperation(null);
    setViewingIndex(-1);
    setShowSuccessAnimation(false);
  };

  // Discard the pending operation
  const handleDiscardOperation = async () => {
    if (!cleaningSessionId || operationInProgress || !pendingOperation) return;

    setOperationInProgress(true);

    try {
      const response = await fetch(API_ENDPOINTS.CLEANING.UNDO_LAST, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: cleaningSessionId })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to discard operation');
      }

      const result = await response.json();

      if (result.next_problem) {
        setCurrentProblem(result.next_problem);
      }

      setPendingOperation(null);
      setOperationInProgress(false);
      setPreviewRefreshKey(prev => prev + 1);
    } catch (err) {
      console.error('Failed to discard operation:', err);
      setOperationInProgress(false);
    }
  };

  // Undo the last operation
  const handleUndoOperation = async () => {
    if (!cleaningSessionId || operationInProgress || problemHistory.length === 0) return;

    setOperationInProgress(true);

    try {
      const response = await fetch(API_ENDPOINTS.CLEANING.UNDO_LAST, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: cleaningSessionId })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to undo operation');
      }

      const result = await response.json();

      setProblemHistory(prev => prev.slice(0, -1));
      setCurrentProblem(result.next_problem);
      setSessionComplete(result.session_complete);
      setViewingIndex(-1);
      setOperationInProgress(false);
      setPreviewRefreshKey(prev => prev + 1);
    } catch (err) {
      console.error('Failed to undo operation:', err);
      setOperationInProgress(false);
      setError(err.message);
    }
  };

  // Navigate between problems
  const handleNavigate = (index) => {
    setViewingIndex(index);
  };

  // Auto-trigger cleaning session when entering Stage 2
  useEffect(() => {
    if (currentStage === 2 && tempFilePath && !cleaningSessionId && !sessionLoading) {
      startCleaningSession();
    }
  }, [currentStage, tempFilePath]);

  const handleComplete = async () => {
    setFinalizing(true);
    isFinalizingRef.current = true;
    setError(null);

    try {
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

      unblockNavigation();
      setFinalized(true);
      finalizedRef.current = true;
      navigate('/datasets');
    } catch (err) {
      console.error('Error finalizing dataset:', err);
      setError(err.message);
      setFinalizing(false);
      isFinalizingRef.current = false;
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 10) / 10 + ' ' + sizes[i];
  };

  return (
    <div className="data-cleaning-page">
      {/* Header */}
      <header className="page-header">
        <div className="header-left">
          <div className="header-icon">
            <Database size={24} />
            <div className="icon-pulse"></div>
          </div>
          <div className="header-text">
            <h1>
              <span className="text-muted">~/</span>data-pipeline
              <span className="header-cursor">_</span>
            </h1>
            <p className="header-subtitle">
              <Terminal size={12} />
              <span>Upload and prepare your dataset</span>
            </p>
          </div>
        </div>

        {tempFilePath && (
          <div className="file-info-badge">
            <FileText size={14} />
            <span className="file-name">{datasetName || originalFilename}</span>
            <span className="file-size">{formatFileSize(fileSize)}</span>
          </div>
        )}
      </header>

      {/* Pipeline Progress */}
      <div className="pipeline-progress">
        <div className="pipeline-track">
          {stages.map((stage, index) => {
            const Icon = stage.icon;
            const isActive = currentStage === stage.id;
            const isCompleted = currentStage > stage.id;

            return (
              <div key={stage.id} className="pipeline-stage-wrapper">
                <div className={`pipeline-stage ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}>
                  <div className="stage-node">
                    {isCompleted ? (
                      <CheckCircle2 size={20} />
                    ) : (
                      <Icon size={20} />
                    )}
                  </div>
                  <div className="stage-info">
                    <span className="stage-name">{stage.name}</span>
                    <code className="stage-command">$ {stage.command}</code>
                  </div>
                </div>
                {index < stages.length - 1 && (
                  <div className={`pipeline-connector ${isCompleted ? 'completed' : ''}`}>
                    <ChevronRight size={16} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Stage Content */}
      <div className="stage-content">
        {/* Stage 1: Upload */}
        {currentStage === 1 && (
          <div className="stage-panel upload-stage">
            <div className="panel-header">
              <div className="panel-title">
                <Upload size={18} />
                <h2>Initialize Data Source</h2>
              </div>
              <p className="panel-description">
                Drop your CSV file to begin the data pipeline
              </p>
            </div>

            <div className="panel-body">
              <CSVUpload
                onUploadSuccess={handleUploadSuccess}
                onUploadError={handleUploadError}
              />
            </div>

            <div className="stage-footer">
              <div className="supported-formats">
                <span className="format-label">Supported:</span>
                <code>.csv</code>
                <span className="format-divider">|</span>
                <span className="format-limit">Max 100MB</span>
              </div>
            </div>
          </div>
        )}

        {/* Stage 2: Data Cleaning */}
        {currentStage === 2 && (
          <div
            className="stage-panel cleaning-stage"
            style={{ height: 'calc(100vh - 100px)', minHeight: '850px', maxHeight: 'calc(100vh - 100px)' }}
          >
            <div className="split-view" style={{ height: '100%', maxHeight: '100%' }}>
              {/* Left Panel - Cleaning */}
              <div
                className="split-panel left-panel"
                style={{ maxHeight: '100%', overflow: 'hidden' }}
              >
                <div className="panel-header compact">
                  <div className="panel-title">
                    <Shield size={16} />
                    <h3>Data Quality Inspector</h3>
                  </div>
                  <div className="panel-status">
                    {sessionComplete ? (
                      <span className="status-badge success">
                        <CheckCircle2 size={12} />
                        All Clear
                      </span>
                    ) : currentProblem ? (
                      <span className="status-badge warning">
                        <Activity size={12} />
                        Issues Found
                      </span>
                    ) : sessionLoading ? (
                      <span className="status-badge loading">
                        <Zap size={12} />
                        Scanning...
                      </span>
                    ) : null}
                  </div>
                </div>

                {/* Success Animation Overlay */}
                {showSuccessAnimation && (
                  <div className="success-overlay">
                    <div className="success-content">
                      <div className="success-checkmark">
                        <svg className="checkmark-svg" viewBox="0 0 52 52">
                          <circle className="checkmark-circle" cx="26" cy="26" r="25" fill="none" />
                          <path className="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8" />
                        </svg>
                      </div>
                      <span className="success-text">Applied</span>
                    </div>
                  </div>
                )}

                <div className="panel-content">
                  <CleaningPanel
                    currentProblem={currentProblem}
                    problemHistory={problemHistory}
                    viewingIndex={viewingIndex}
                    onNavigate={handleNavigate}
                    onApplyOperation={handleApplyOperation}
                    onConfirmOperation={handleConfirmOperation}
                    onDiscardOperation={handleDiscardOperation}
                    onUndoOperation={handleUndoOperation}
                    operationInProgress={operationInProgress}
                    pendingOperation={pendingOperation}
                    sessionLoading={sessionLoading}
                    sessionError={sessionError}
                    sessionComplete={sessionComplete}
                    onComplete={handleNext}
                    finalizing={finalizing}
                  />
                </div>
              </div>

              {/* Right Panel - Preview */}
              <div className="split-panel right-panel">
                <div className="panel-header compact">
                  <div className="panel-title">
                    <Layers size={16} />
                    <h3>Data Preview</h3>
                  </div>
                  {pendingOperation && (
                    <span className="status-badge pending">
                      <Sparkles size={12} />
                      Pending Changes
                    </span>
                  )}
                </div>

                <div className="panel-content">
                  <DataPreviewPanel
                    tempFilePath={tempFilePath}
                    datasetName={datasetName}
                    sessionToken={sessionToken}
                    refreshKey={previewRefreshKey}
                    hasUnsavedChanges={!!pendingOperation}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Action Bar */}
      <div className="action-bar">
        <div className="action-info">
          {currentStage === 2 && (
            <div className="progress-stats">
              <span className="stat">
                <CheckCircle2 size={14} />
                {problemHistory.length} resolved
              </span>
              {!sessionComplete && currentProblem && (
                <span className="stat pending">
                  <AlertTriangle size={14} />
                  Issues remaining
                </span>
              )}
            </div>
          )}
        </div>

        <div className="action-buttons">
          {currentStage === 1 ? (
            <button
              onClick={handleNext}
              className="action-btn primary"
              disabled={!tempFilePath}
            >
              <span>Continue</span>
              <ArrowRight size={18} />
            </button>
          ) : (
            <button
              onClick={handleNext}
              className={`action-btn ${sessionComplete ? 'success' : 'primary'}`}
              disabled={finalizing || operationInProgress || !sessionComplete}
            >
              {finalizing ? (
                <>
                  <div className="btn-spinner"></div>
                  <span>Finalizing...</span>
                </>
              ) : (
                <>
                  <span>{sessionComplete ? 'Save Dataset' : 'Resolve Issues First'}</span>
                  {sessionComplete ? <CheckCircle2 size={18} /> : <ArrowRight size={18} />}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
