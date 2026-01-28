//src/App.jsx
import './App.css';
import { BrowserRouter, Routes, Route, useNavigate, useSearchParams } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { NavigationGuardProvider } from './contexts/NavigationGuardContext';
import { DatabaseHealthProvider, useDatabaseHealth } from './contexts/DatabaseHealthContext';
import AppRoutes from './routes';
import Signin from './components/Signin';
import Signup from './components/Signup';
import DatabaseError from './pages/DatabaseError';
import { useEffect } from 'react';

function DatabaseHealthGate({ children }) {
    const { isDbConnected, isChecking } = useDatabaseHealth();

    // Show loading state while checking
    if (isChecking && isDbConnected === null) {
        return (
            <div className="database-loading">
                <div className="loading-terminal">
                    <div className="terminal-header">
                        <span className="terminal-dot red"></span>
                        <span className="terminal-dot yellow"></span>
                        <span className="terminal-dot green"></span>
                        <span className="terminal-title">connection_check.exe</span>
                    </div>
                    <div className="terminal-body">
                        <div className="terminal-line">
                            <span className="prompt">$</span>
                            <span className="command">connecting to server...</span>
                            <span className="cursor"></span>
                        </div>
                        <div className="loading-bar">
                            <div className="loading-progress"></div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Show error page if database is not connected
    if (!isDbConnected) {
        return <DatabaseError />;
    }

    return children;
}

function AppContent() {
    const [searchParams, setSearchParams] = useSearchParams();
    const { login, isAuthenticated } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        // Check for Google OAuth callback parameters
        const email = searchParams.get('email');
        const name = searchParams.get('name');
        const sessionToken = searchParams.get('session_token');
        const error = searchParams.get('error');

        if (error) {
            // Handle OAuth error
            console.error('OAuth error:', error);
            alert('Authentication failed. Please try again.');
            navigate('/signin', { replace: true });
            return;
        }

        if (email && name && sessionToken && !isAuthenticated) {
            // User just logged in via Google OAuth
            console.log('Processing Google OAuth callback...');
            login(email, name, sessionToken);

            // Clean up URL parameters
            searchParams.delete('email');
            searchParams.delete('name');
            searchParams.delete('session_token');
            setSearchParams(searchParams, { replace: true });

            // Navigate to home
            navigate('/', { replace: true });
        }
    }, [searchParams, setSearchParams, login, isAuthenticated, navigate]);

    return (
        <DatabaseHealthGate>
            {/* Background */}
            <div className="gradient-overlay" />

            {/* Main app UI on top */}
            <Routes>
                {/* Auth routes */}
                <Route path="/signin" element={<Signin />} />
                <Route path="/signup" element={<Signup />} />

                {/* Protected routes */}
                <Route path="/*" element={<AppRoutes />} />
            </Routes>
        </DatabaseHealthGate>
    );
}

function App() {
    return (
        <DatabaseHealthProvider>
            <AuthProvider>
                <BrowserRouter>
                    <NavigationGuardProvider>
                        <AppContent />
                    </NavigationGuardProvider>
                </BrowserRouter>
            </AuthProvider>
        </DatabaseHealthProvider>
    );
}

export default App;
