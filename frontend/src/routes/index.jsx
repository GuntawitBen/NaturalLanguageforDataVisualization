import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Header from '../components/Header';
import Home from '../pages/Home';
import Datasets from '../pages/Datasets';
import DatasetDetails from '../pages/DatasetDetails';
import DataCleaning from '../pages/DataCleaning';
import History from '../pages/History';


export default function AppRoutes() {
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
                    <Route path="/datasets/:datasetId" element={<DatasetDetails />} />
                    {/* Redirect /upload to /data-cleaning for unified workflow */}
                    <Route path="/upload" element={<Navigate to="/data-cleaning" replace />} />
                    <Route path="/data-cleaning" element={<DataCleaning />} />
                    <Route path="/history" element={<History />} />
                </Routes>
            </main>
        </div>
    );
}
