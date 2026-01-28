import { useState } from 'react';
import { API_ENDPOINTS } from '../config';
import './DatabaseError.css';

export default function DatabaseError() {
    const [isRetrying, setIsRetrying] = useState(false);
    const [retryFailed, setRetryFailed] = useState(false);

    const handleRetry = async () => {
        setIsRetrying(true);
        setRetryFailed(false);
        try {
            const response = await fetch(API_ENDPOINTS.HEALTH_DB, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
            });

            if (response.ok) {
                // Database is back online - refresh the page for a clean state
                window.location.reload();
            } else {
                // Still not connected
                setRetryFailed(true);
            }
        } catch (error) {
            console.error('Retry failed:', error);
            setRetryFailed(true);
        } finally {
            setIsRetrying(false);
        }
    };

    return (
        <div className="database-error-page">
            <div className="database-error-container">
                <div className="database-error-icon">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="64"
                        height="64"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <ellipse cx="12" cy="5" rx="9" ry="3"/>
                        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                        <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>
                        <line x1="2" y1="2" x2="22" y2="22" stroke="var(--accent-red)" strokeWidth="2"/>
                    </svg>
                </div>

                <h1 className="database-error-title">Database Connection Error</h1>

                <p className="database-error-message">
                    Unable to connect to the database. The service is temporarily unavailable.
                </p>

                <div className="database-error-details">
                    <p>This could be due to:</p>
                    <ul>
                        <li>Database server is down or restarting</li>
                        <li>Network connectivity issues</li>
                        <li>Configuration problems</li>
                    </ul>
                </div>

                <button
                    className="database-error-retry-btn"
                    onClick={handleRetry}
                    disabled={isRetrying}
                >
                    {isRetrying ? (
                        <>
                            <span className="retry-spinner"></span>
                            Checking connection...
                        </>
                    ) : (
                        'Try Again'
                    )}
                </button>

                {retryFailed && (
                    <p className="database-error-retry-failed">
                        Database is still unavailable. Please try again later.
                    </p>
                )}

                <p className="database-error-footer">
                    If the problem persists, please contact your administrator.
                </p>
            </div>
        </div>
    );
}
