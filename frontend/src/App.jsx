//src/App.jsx
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import AppRoutes from './components/Routes';
import Signin from './components/Signin';
import Signup from './components/Signup';

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
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
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;
