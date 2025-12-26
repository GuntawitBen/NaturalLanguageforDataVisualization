import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CSVUpload from '../components/CSVUpload';
import { Database, ArrowLeft } from 'lucide-react';
import './Upload.css';

export default function Upload() {
  const navigate = useNavigate();
  const [recentUploads, setRecentUploads] = useState([]);

  const handleUploadSuccess = (dataset) => {
    console.log('Upload successful:', dataset);

    // Add to recent uploads
    setRecentUploads(prev => [dataset, ...prev].slice(0, 5));

    // Show notification (optional - you could use a toast library)
    // toast.success(`Dataset "${dataset.dataset_name}" uploaded successfully!`);
  };

  const handleUploadError = (error) => {
    console.error('Upload error:', error);

    // Show error notification (optional)
    // toast.error(`Upload failed: ${error}`);
  };

  return (
    <div className="upload-page">
      {/* Header */}
      <div className="upload-header">
        <button
          onClick={() => navigate('/')}
          className="back-button"
          aria-label="Go back to dashboard"
        >
          <ArrowLeft size={20} />
          Back to Dashboard
        </button>

        <div className="header-content">
          <div className="header-icon">
            <Database size={32} />
          </div>
          <div>
            <h1>Upload Dataset</h1>
            <p>Upload CSV files to create datasets for analysis and visualization</p>
          </div>
        </div>
      </div>

      {/* Upload Component */}
      <div className="upload-content">
        <CSVUpload
          onUploadSuccess={handleUploadSuccess}
          onUploadError={handleUploadError}
        />

        {/* Recent Uploads */}
        {recentUploads.length > 0 && (
          <div className="recent-uploads">
            <h2>Recent Uploads</h2>
            <div className="uploads-list">
              {recentUploads.map((dataset) => (
                <div key={dataset.dataset_id} className="upload-item">
                  <div className="upload-item-icon">
                    <Database size={24} />
                  </div>
                  <div className="upload-item-details">
                    <h3>{dataset.dataset_name}</h3>
                    <p>
                      {dataset.row_count.toLocaleString()} rows × {dataset.column_count} columns
                    </p>
                    <p className="upload-item-meta">
                      {new Date(dataset.upload_date).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => navigate(`/datasets/${dataset.dataset_id}`)}
                    className="view-button"
                  >
                    View Dataset
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Help Section */}
      <div className="upload-help">
        <h3>CSV File Requirements</h3>
        <ul>
          <li>
            <strong>File Format:</strong> CSV (.csv extension)
          </li>
          <li>
            <strong>File Size:</strong> Maximum 100 MB
          </li>
          <li>
            <strong>Encoding:</strong> UTF-8 (recommended), ASCII, ISO-8859-1, or Windows-1252
          </li>
          <li>
            <strong>Headers:</strong> First row must contain column names
          </li>
          <li>
            <strong>Delimiters:</strong> Comma (,), semicolon (;), tab, or pipe (|)
          </li>
          <li>
            <strong>Rows:</strong> Minimum 1 row, maximum 1,000,000 rows
          </li>
          <li>
            <strong>Columns:</strong> Minimum 1 column, maximum 100 columns
          </li>
        </ul>

        <div className="help-note">
          <strong>Note:</strong> Files are validated before upload. Any issues will be reported with clear error messages.
        </div>
      </div>
    </div>
  );
}
