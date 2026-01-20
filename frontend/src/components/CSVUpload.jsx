import { useState, useRef, useCallback } from 'react';
import { Upload, X, CheckCircle, AlertCircle, FileText, Loader } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import './CSVUpload.css';

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100 MB
const ALLOWED_TYPES = ['text/csv', 'application/vnd.ms-excel'];

export default function CSVUpload({ onUploadSuccess, onUploadError }) {
  const { sessionToken } = useAuth();
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState(null); // 'success', 'error', or null
  const [errorMessage, setErrorMessage] = useState('');
  const [uploadedDataset, setUploadedDataset] = useState(null);

  // Form fields
  const [datasetName, setDatasetName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');

  const fileInputRef = useRef(null);
  const dragCounter = useRef(0);

  // ============================================================================
  // FILE VALIDATION
  // ============================================================================

  const validateFile = (file) => {
    const errors = [];

    // Check if file exists
    if (!file) {
      errors.push('No file selected');
      return errors;
    }

    // Check file type
    const fileName = file.name.toLowerCase();
    const fileType = file.type.toLowerCase();

    if (!fileName.endsWith('.csv') && !ALLOWED_TYPES.includes(fileType)) {
      errors.push('File must be a CSV (.csv extension)');
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      errors.push(`File is too large (${sizeMB} MB). Maximum size is 100 MB.`);
    }

    if (file.size < 10) {
      errors.push('File is too small or empty');
    }

    return errors;
  };

  // ============================================================================
  // DRAG AND DROP HANDLERS
  // ============================================================================

  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    dragCounter.current = 0;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, []);

  // ============================================================================
  // FILE SELECTION
  // ============================================================================

  const handleFileSelect = (selectedFile) => {
    // Reset previous state
    setUploadStatus(null);
    setErrorMessage('');
    setUploadedDataset(null);

    // Validate file
    const errors = validateFile(selectedFile);
    if (errors.length > 0) {
      setErrorMessage(errors.join('\n'));
      setUploadStatus('error');
      setFile(null);
      return;
    }

    // Set file and auto-populate dataset name
    setFile(selectedFile);
    if (!datasetName) {
      setDatasetName(selectedFile.name.replace('.csv', ''));
    }
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    setUploadStatus(null);
    setErrorMessage('');
    setUploadedDataset(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // ============================================================================
  // FILE UPLOAD
  // ============================================================================

  const handleUpload = async () => {
    if (!file) {
      setErrorMessage('Please select a file first');
      setUploadStatus('error');
      return;
    }

    if (!sessionToken) {
      setErrorMessage('You must be logged in to upload files');
      setUploadStatus('error');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadStatus(null);
    setErrorMessage('');

    try {
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      if (datasetName) formData.append('dataset_name', datasetName);
      if (description) formData.append('description', description);
      if (tags) formData.append('tags', tags);

      // Create XMLHttpRequest for progress tracking
      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = Math.round((e.loaded / e.total) * 100);
          setUploadProgress(percentComplete);
        }
      });

      // Handle completion
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const response = JSON.parse(xhr.responseText);
          setUploadStatus('success');
          setUploadedDataset(response);

          // Call success callback (will navigate to DataCleaning page)
          if (onUploadSuccess) {
            onUploadSuccess(response);
          }
        } else {
          const error = JSON.parse(xhr.responseText);
          const errorMsg = error.detail || 'Upload failed';
          setErrorMessage(errorMsg);
          setUploadStatus('error');

          // Call error callback
          if (onUploadError) {
            onUploadError(errorMsg);
          }
        }
        setUploading(false);
      });

      // Handle errors
      xhr.addEventListener('error', () => {
        setErrorMessage('Network error. Please check your connection and try again.');
        setUploadStatus('error');
        setUploading(false);

        if (onUploadError) {
          onUploadError('Network error');
        }
      });

      // Handle timeout
      xhr.addEventListener('timeout', () => {
        setErrorMessage('Upload timeout. File may be too large.');
        setUploadStatus('error');
        setUploading(false);

        if (onUploadError) {
          onUploadError('Upload timeout');
        }
      });

      // Send request to temp upload endpoint
      xhr.open('POST', API_ENDPOINTS.DATASETS.UPLOAD_TEMP);
      xhr.setRequestHeader('Authorization', `Bearer ${sessionToken}`);
      xhr.timeout = 300000; // 5 minutes timeout
      xhr.send(formData);

    } catch (error) {
      console.error('Upload error:', error);
      setErrorMessage(`Upload error: ${error.message}`);
      setUploadStatus('error');
      setUploading(false);

      if (onUploadError) {
        onUploadError(error.message);
      }
    }
  };

  // ============================================================================
  // RESET
  // ============================================================================

  const handleReset = () => {
    setFile(null);
    setDatasetName('');
    setDescription('');
    setTags('');
    setUploadProgress(0);
    setUploadStatus(null);
    setErrorMessage('');
    setUploadedDataset(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="csv-upload-container">
      {/* Success Message */}
      {uploadStatus === 'success' && uploadedDataset && (
        <div className="upload-alert upload-alert-success">
          <CheckCircle className="alert-icon" />
          <div className="alert-content">
            <h4>Upload Successful!</h4>
            <p>
              Dataset <strong>{uploadedDataset.dataset_name}</strong> uploaded successfully.
            </p>
            <p className="text-sm">
              {uploadedDataset.row_count.toLocaleString()} rows × {uploadedDataset.column_count} columns
            </p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {uploadStatus === 'error' && errorMessage && (
        <div className="upload-alert upload-alert-error">
          <AlertCircle className="alert-icon" />
          <div className="alert-content">
            <h4>Upload Failed</h4>
            <p style={{ whiteSpace: 'pre-line' }}>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Drag and Drop Area */}
      <div
        className={`upload-dropzone ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !file && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={handleFileInputChange}
          style={{ display: 'none' }}
          disabled={uploading}
        />

        {!file ? (
          <div className="dropzone-content">
            <Upload className="dropzone-icon" size={48} />
            <h3>Drop your CSV file here</h3>
            <p>or click to browse</p>
            <p className="text-sm text-muted">Maximum file size: 100 MB</p>
          </div>
        ) : (
          <div className="file-info">
            <FileText className="file-icon" size={48} />
            <div className="file-details">
              <h4>{file.name}</h4>
              <p>{formatFileSize(file.size)}</p>
            </div>
            {!uploading && (
              <button
                className="remove-file-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemoveFile();
                }}
                aria-label="Remove file"
              >
                <X size={20} />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Upload Form */}
      {file && uploadStatus !== 'success' && (
        <div className="upload-form">
          <div className="form-group">
            <label htmlFor="dataset-name">
              Dataset Name <span className="required">*</span>
            </label>
            <input
              id="dataset-name"
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="e.g., Sales Data 2024"
              disabled={uploading}
              className="form-input"
            />
          </div>

          {/*<div className="form-group">*/}
          {/*  <label htmlFor="description">Description</label>*/}
          {/*  <textarea*/}
          {/*    id="description"*/}
          {/*    value={description}*/}
          {/*    onChange={(e) => setDescription(e.target.value)}*/}
          {/*    placeholder="Brief description of your dataset..."*/}
          {/*    rows={3}*/}
          {/*    disabled={uploading}*/}
          {/*    className="form-input"*/}
          {/*  />*/}
          {/*</div>*/}

          {/*<div className="form-group">*/}
          {/*  <label htmlFor="tags">Tags</label>*/}
          {/*  <input*/}
          {/*    id="tags"*/}
          {/*    type="text"*/}
          {/*    value={tags}*/}
          {/*    onChange={(e) => setTags(e.target.value)}*/}
          {/*    placeholder="e.g., sales, 2024, quarterly (comma-separated)"*/}
          {/*    disabled={uploading}*/}
          {/*    className="form-input"*/}
          {/*  />*/}
          {/*</div>*/}

          {/* Upload Progress */}
          {uploading && (
            <div className="upload-progress">
              <div className="progress-info">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="form-actions">
            <button
              onClick={handleReset}
              disabled={uploading}
              className="btn btn-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={uploading || !datasetName}
              className="btn btn-primary"
            >
              {uploading ? (
                <>
                  <Loader className="btn-icon spinning" size={18} />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="btn-icon" size={18} />
                  Upload Dataset
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
