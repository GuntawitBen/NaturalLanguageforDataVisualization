import { useState } from 'react';
import './Signin.css';

const API_BASE_URL = "http://localhost:8000";

export default function Signin() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const handleGoogleLogin = () => {
        setSuccess('Redirecting to Google login...');
        window.location.href = `${API_BASE_URL}/auth/google/login`;
    };

    const handleCustomLogin = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                setSuccess('Login successful! Redirecting...');
                sessionStorage.setItem('userEmail', email);
                sessionStorage.setItem('userName', data.name);
                
                setTimeout(() => {
                    window.location.href = `/?email=${email}&name=${data.name}`;
                }, 1000);
            } else {
                setError(data.detail || 'Login failed. Please check your credentials.');
            }
        } catch (err) {
            console.error('Login error:', err);
            setError('Unable to connect to server. Please try again later.');
        }
    };

    const handleForgotPassword = (e) => {
        e.preventDefault();
        alert('Password reset feature coming soon!');
    };

    return (
        <div className="login-page">
            <div className="login-container">
                <div className="logo">
                    <h1>Phebe</h1>
                    <h1>Log in to your account</h1>
                </div>



                {/* Google Login */}
                <button className="btn btn-google" onClick={handleGoogleLogin}>
                    <svg className="google-icon" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
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

                    <div className="forgot-password">
                        <a href="#" onClick={handleForgotPassword}>Forgot password?</a>
                    </div>

                    <button type="submit" className="btn btn-primary">Login</button>
                </form>

                <div className="signup-link">
                    Don't have an account? <a href="/signup">Sign up</a>
                </div>
            </div>

            {/* Right side with gradient */}
            <div className="login-right">
                <div className="animation-container">

                    {/* Animated Charts Scene */}
                    <div className="charts-scene">
                        {/* Floating Bar Chart */}
                        <div className="chart-bars">
                            <div className="bar bar-1"></div>
                            <div className="bar bar-2"></div>
                            <div className="bar bar-3"></div>
                            <div className="bar bar-4"></div>
                        </div>

                        {/* Animated Pie Chart */}
                        <div className="pie-chart">
                            <svg viewBox="0 0 100 100" className="pie-svg">
                                <circle className="pie-segment-1" cx="50" cy="50" r="40" />
                                <circle className="pie-segment-2" cx="50" cy="50" r="40" />
                            </svg>
                        </div>

                        {/* Line Chart */}
                        <svg className="line-chart" viewBox="0 0 200 100">
                            <polyline className="chart-line" points="0,80 50,60 100,40 150,20 200,10" />
                            <circle className="data-point" cx="200" cy="10" r="3" />
                        </svg>

                        {/* Floating Data Particles */}
                        <div className="particles">
                            <div className="particle particle-1"></div>
                            <div className="particle particle-2"></div>
                            <div className="particle particle-3"></div>
                            <div className="particle particle-4"></div>
                            <div className="particle particle-5"></div>
                            <div className="particle particle-6"></div>
                        </div>

                        {/* Cute Robot Character */}
                        <div className="robot-character">
                            <div className="robot-head">
                                <div className="robot-eye robot-eye-left"></div>
                                <div className="robot-eye robot-eye-right"></div>
                                <div className="robot-antenna"></div>
                            </div>
                            <div className="robot-body"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}