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
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { login, isAuthenticated, loading } = useAuth();
    const navigate = useNavigate();

    // Redirect if already logged in
    if (!loading && isAuthenticated) {
        return <Navigate to="/" replace />;
    }


    const handleCustomLogin = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setIsSubmitting(true);

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
                setIsSubmitting(false);
            }
        } catch (err) {
            console.error('Login error:', err);
            setError('Unable to connect to server. Please try again later.');
            setIsSubmitting(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-container">
                <div className="logo">
                    <h1>Phebe</h1>
                    <h2>Log in to your account</h2>
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

                    <button type="submit" className={`btn btn-primary ${isSubmitting ? 'loading' : ''}`} disabled={isSubmitting}>
                        {isSubmitting ? (
                            <>
                                <span className="btn-spinner"></span>
                                <span>Signing in...</span>
                            </>
                        ) : (
                            'Login'
                        )}
                    </button>
                </form>

                <div className="signup-link">
                    Don't have an account? <a href="/signup">Sign up</a>
                </div>
            </div>

            {/* Right side - Technical Dashboard */}
            <div className="login-right">
            </div>
        </div>
    );
}