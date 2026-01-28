import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API_ENDPOINTS } from '../config';

const DatabaseHealthContext = createContext(null);

// Health check interval in milliseconds (30 seconds)
const HEALTH_CHECK_INTERVAL = 30000;

export function DatabaseHealthProvider({ children }) {
    const [isDbConnected, setIsDbConnected] = useState(null); // null = checking, true = connected, false = disconnected
    const [isChecking, setIsChecking] = useState(true);

    const checkDatabaseHealth = useCallback(async () => {
        try {
            const response = await fetch(API_ENDPOINTS.HEALTH_DB, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
            });

            if (response.ok) {
                setIsDbConnected(true);
                return true;
            } else {
                // 503 means database is unavailable
                setIsDbConnected(false);
                return false;
            }
        } catch (error) {
            // Network error or backend is completely down
            console.error('Database health check failed:', error);
            setIsDbConnected(false);
            return false;
        } finally {
            setIsChecking(false);
        }
    }, []);

    // Initial health check
    useEffect(() => {
        checkDatabaseHealth();
    }, [checkDatabaseHealth]);

    // Periodic health check when connected
    useEffect(() => {
        if (isDbConnected) {
            const interval = setInterval(checkDatabaseHealth, HEALTH_CHECK_INTERVAL);
            return () => clearInterval(interval);
        }
    }, [isDbConnected, checkDatabaseHealth]);

    return (
        <DatabaseHealthContext.Provider
            value={{
                isDbConnected,
                isChecking
            }}
        >
            {children}
        </DatabaseHealthContext.Provider>
    );
}

export function useDatabaseHealth() {
    const context = useContext(DatabaseHealthContext);
    if (!context) {
        throw new Error('useDatabaseHealth must be used within a DatabaseHealthProvider');
    }
    return context;
}
