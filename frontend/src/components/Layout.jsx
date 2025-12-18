// src/components/Layout.jsx
import Sidebar from './Sidebar';

export default function Layout({ children }) {
    return (
        <div className="flex h-screen gap-4 items-end">
            <Sidebar />
            <div className="flex-1 bg-white/40 backdrop-blur-3xl rounded-3xl border border-white/30 shadow-1xl mr-5 mb-5"
                 style={{ height: '75vh' }}>
                {children}
            </div>
        </div>
    );
}
