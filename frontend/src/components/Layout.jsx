import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Header from './Header';
import Home from '../pages/Home';
import Upload from '../pages/Upload';
import Datasets from '../pages/Datasets';


export default function Layout() {
    const { isAuthenticated, loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>;
    }

    if (!isAuthenticated) {
        return <Navigate to="/signin" replace />;
    }

    return (
        <div className="layout-container">
            <Header />
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/datasets" element={<Datasets />} />
                    <Route path="/upload" element={<Upload />} />
                </Routes>
            </main>
        </div>
    );
}