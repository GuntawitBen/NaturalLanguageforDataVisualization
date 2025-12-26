import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, Upload, Database, Settings } from 'lucide-react';

function Sidebar() {
    const location = useLocation();

    const navItems = [
        { path: '/', icon: Home, label: 'Home' },
        { path: '/upload', icon: Upload, label: 'Upload Dataset' },
        { path: '/settings', icon: Settings, label: 'Settings' },
    ];

    return (
        <aside className="w-64 bg-white/40 backdrop-blur-4xl border-r border-white/30 shadow-1xl rounded-3xl ml-5 mt-5 mb-5"
               style={{ height: 'calc(100vh - 2rem)' }}>
            <nav className="p-4">
                <div className="mb-8 px-2">
                    <h2 className="text-xl font-bold text-gray-800">DataViz</h2>
                </div>
                <ul className="space-y-2">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;
                        return (
                            <li key={item.path}>
                                <Link
                                    to={item.path}
                                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                                        isActive
                                            ? 'bg-white/80 text-purple-600 font-semibold shadow-md'
                                            : 'text-gray-700 hover:bg-white/50 hover:text-purple-600'
                                    }`}
                                >
                                    <Icon size={20} />
                                    <span>{item.label}</span>
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>
        </aside>
    );
}

export default Sidebar;