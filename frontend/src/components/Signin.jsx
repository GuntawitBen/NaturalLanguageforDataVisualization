import { useState, useEffect } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import './Signin.css';

export default function Signin() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const { login, isAuthenticated, loading } = useAuth();
    const navigate = useNavigate();

    // Redirect if already logged in
    if (!loading && isAuthenticated) {
        return <Navigate to="/" replace />;
    }

    const handleGoogleLogin = () => {
        setSuccess('Redirecting to Google login...');
        window.location.href = API_ENDPOINTS.AUTH.GOOGLE_LOGIN;
    };

    const handleCustomLogin = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        try {
            const response = await fetch(API_ENDPOINTS.AUTH.LOGIN, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                setSuccess('Login successful! Redirecting...');
                login(data.email, data.name, data.session_token);

                setTimeout(() => {
                    navigate('/');
                }, 1000);
            } else {
                setError(data.detail || 'Login failed. Please check your credentials.');
            }
        } catch (err) {
            console.error('Login error:', err);
            setError('Unable to connect to server. Please try again later.');
        }
    };

    return (
        <div className="login-page">
            <div className="login-container">
                <div className="logo">
                    <h1>Phebe</h1>
                    <h2>Log in to your account</h2>
                </div>



                {/* Google Login */}
                <button className="btn btn-google" onClick={handleGoogleLogin}>
                    <svg className="google-icon" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                    </svg>
                    Google
                </button>

                <div className="divider">
                    <span>OR</span>
                </div>

                {error && <div className="error-message">{error}</div>}
                {success && <div className="success-message">{success}</div>}

                {/* Custom Login Form */}
                <form onSubmit={handleCustomLogin}>
                    <div className="form-group">
                        <label htmlFor="email">Email Address</label>
                        <input
                            type="email"
                            id="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="Enter your email"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            type="password"
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter your password"
                            required
                        />
                    </div>

                    <button type="submit" className="btn btn-primary">Login</button>
                </form>

                <div className="signup-link">
                    Don't have an account? <a href="/signup">Sign up</a>
                </div>
            </div>

            {/* Right side - Technical Dashboard */}
            <div className="login-right">
                <div className="tech-display">
                    {/* Grid background */}
                    <div className="tech-grid"></div>

                    {/* Main Dashboard Container */}
                    <div className="dashboard-frame">
                        {/* Header */}
                        <div className="dash-header">
                            <div className="status-dot"></div>
                            <span className="header-text">PHEBE_ANALYTICS</span>
                            <span className="header-version">v2.4.1</span>
                        </div>

                        {/* Chart Panel */}
                        <div className="chart-panel">
                            <div className="panel-label">REVENUE_METRICS</div>
                            <svg className="area-chart" viewBox="0 0 200 80">
                                <defs>
                                    <linearGradient id="chartGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                                        <stop offset="0%" stopColor="rgba(251,191,36,0.3)" />
                                        <stop offset="100%" stopColor="rgba(251,191,36,0)" />
                                    </linearGradient>
                                </defs>
                                <path className="chart-area" d="M0,60 Q25,55 40,45 T80,35 T120,40 T160,25 T200,30 L200,80 L0,80 Z" fill="url(#chartGrad)" />
                                <path className="chart-line-main" d="M0,60 Q25,55 40,45 T80,35 T120,40 T160,25 T200,30" />
                                <circle className="chart-point" cx="200" cy="30" r="3" />
                            </svg>
                            <div className="chart-labels">
                                <span>Q1</span><span>Q2</span><span>Q3</span><span>Q4</span>
                            </div>
                        </div>

                        {/* Stats Row */}
                        <div className="stats-row">
                            <div className="stat-box">
                                <div className="stat-value">2.4M</div>
                                <div className="stat-label">records</div>
                            </div>
                            <div className="stat-box">
                                <div className="stat-value">847</div>
                                <div className="stat-label">queries</div>
                            </div>
                            <div className="stat-box">
                                <div className="stat-value">99.2%</div>
                                <div className="stat-label">uptime</div>
                            </div>
                        </div>

                        {/* Bar Chart */}
                        <div className="bar-panel">
                            <div className="panel-label">DISTRIBUTION</div>
                            <div className="h-bars">
                                <div className="h-bar-row">
                                    <span className="bar-label">Dataset A</span>
                                    <div className="bar-track"><div className="bar-fill bf-1"></div></div>
                                    <span className="bar-value">78%</span>
                                </div>
                                <div className="h-bar-row">
                                    <span className="bar-label">Dataset B</span>
                                    <div className="bar-track"><div className="bar-fill bf-2"></div></div>
                                    <span className="bar-value">64%</span>
                                </div>
                                <div className="h-bar-row">
                                    <span className="bar-label">Dataset C</span>
                                    <div className="bar-track"><div className="bar-fill bf-3"></div></div>
                                    <span className="bar-value">91%</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Terminal Window */}
                    <div className="terminal-window">
                        <div className="terminal-header">
                            <div className="term-dots">
                                <span></span><span></span><span></span>
                            </div>
                            <span className="term-title">query.sql</span>
                        </div>
                        <div className="terminal-body">
                            <div className="code-line">
                                <span className="line-num">1</span>
                                <span className="kw">SELECT</span> <span className="fn">COUNT</span>(*) <span className="kw">AS</span> total
                            </div>
                            <div className="code-line">
                                <span className="line-num">2</span>
                                <span className="kw">FROM</span> analytics.events
                            </div>
                            <div className="code-line">
                                <span className="line-num">3</span>
                                <span className="kw">WHERE</span> date <span className="op">&gt;=</span> <span className="str">'2024-01'</span>
                            </div>
                            <div className="code-line cursor-line">
                                <span className="line-num">4</span>
                                <span className="kw">GROUP BY</span> category<span className="cursor">|</span>
                            </div>
                        </div>
                    </div>

                    {/* Floating metric badges */}
                    <div className="metric-badge mb-1">
                        <span className="badge-icon">↑</span>
                        <span className="badge-value">+24.5%</span>
                    </div>
                    <div className="metric-badge mb-2">
                        <span className="badge-icon">◆</span>
                        <span className="badge-value">LIVE</span>
                    </div>
                </div>
            </div>
        </div>
    );
}