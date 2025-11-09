// src/components/Layout.jsx
import Sidebar from './Sidebar';

export default function Layout({ children }) {
    return (
        <div className="flex h-screen bg-gray-50">
            <Sidebar />
            <div className="flex-1 flex flex-col">
                {children}
            </div>
        </div>
    );
}