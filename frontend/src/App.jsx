//src/App.jsx
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import Signin from './components/Signin';
import Signup from './components/Signup';

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                {/* Background */}
                <div className="gradient-overlay" />

                {/* Main app UI on top */}
                <div style={{ position: 'relative', zIndex: 1 }}>
                    <Routes>
                        {/* Auth routes WITHOUT Layout */}
                        <Route path="/signin" element={<Signin />} />
                        <Route path="/signup" element={<Signup />} />

                        {/* Protected routes WITH Layout */}
                        <Route path="/*" element={<Layout />} />
                    </Routes>
                </div>
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;
