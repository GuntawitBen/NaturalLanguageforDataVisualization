import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './Sidebar';


export default function Layout() {

    const userEmail = sessionStorage.getItem('userEmail');
    if (!userEmail) {
        return <Navigate to="/signin" replace />;
    }

    return (
        <div className="layout-container">
            <Sidebar />
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                  
                </Routes>
            </main>
        </div>
    );
}