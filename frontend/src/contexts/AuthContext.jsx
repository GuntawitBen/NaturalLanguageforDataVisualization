import { createContext, useContext, useState, useEffect } from 'react';
import { API_ENDPOINTS } from '../config';

const AuthContext = createContext(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [sessionToken, setSessionToken] = useState(null);

    useEffect(() => {
        // Check if user is logged in on mount
        const userEmail = sessionStorage.getItem('userEmail');
        const userName = sessionStorage.getItem('userName');
        const token = sessionStorage.getItem('sessionToken');

        if (userEmail && userName) {
            setUser({
                email: userEmail,
                name: userName
            });
            setSessionToken(token);
        }
        setLoading(false);
    }, []);

    const login = (email, name, token) => {
        setUser({ email, name });
        setSessionToken(token);
        sessionStorage.setItem('userEmail', email);
        sessionStorage.setItem('userName', name);
        if (token) {
            sessionStorage.setItem('sessionToken', token);
        }
    };

    const logout = async () => {
        try {
            // Call backend logout endpoint to invalidate session token
            if (sessionToken) {
                await fetch(API_ENDPOINTS.AUTH.LOGOUT, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${sessionToken}`
                    }
                });
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            // Clear local state regardless of backend response
            setUser(null);
            setSessionToken(null);
            sessionStorage.removeItem('userEmail');
            sessionStorage.removeItem('userName');
            sessionStorage.removeItem('sessionToken');
        }
    };

    const value = {
        user,
        loading,
        sessionToken,
        login,
        logout,
        isAuthenticated: !!user
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
