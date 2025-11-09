// src/App.js

import { useState } from 'react';
import { Menu, X, Plus, MessageSquare, Settings, User } from 'lucide-react';

export default function App() {
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [chats, setChats] = useState([
        { id: 1, title: 'React Sidebar Tutorial', date: 'Today' },
        { id: 2, title: 'CSS Grid Layout', date: 'Yesterday' },
        { id: 3, title: 'JavaScript Arrays', date: '2 days ago' },
    ]);

    return (
        <div className="flex h-screen bg-gray-50">
            {/* Sidebar */}
            <aside
                className={`${
                    sidebarOpen ? 'translate-x-0' : '-translate-x-full'
                } fixed lg:static inset-y-0 left-0 z-50 w-64 bg-gray-900 text-white transition-transform duration-300 ease-in-out flex flex-col`}
            >
                {/* Sidebar Header */}
                <div className="p-4 border-b border-gray-700">
                    <button
                        onClick={() => setChats([...chats, { id: Date.now(), title: 'New Chat', date: 'Just now' }])}
                        className="w-full flex items-center gap-2 px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <Plus size={20} />
                        <span>New Chat</span>
                    </button>
                </div>

                {/* Chat History */}
                <div className="flex-1 overflow-y-auto p-2">
                    <div className="text-xs text-gray-400 px-2 py-2 font-semibold">Recent</div>
                    {chats.map((chat) => (
                        <button
                            key={chat.id}
                            className="w-full text-left px-3 py-3 hover:bg-gray-800 rounded-lg transition-colors group"
                        >
                            <div className="flex items-center gap-2">
                                <MessageSquare size={16} className="flex-shrink-0" />
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm truncate">{chat.title}</div>
                                    <div className="text-xs text-gray-400">{chat.date}</div>
                                </div>
                            </div>
                        </button>
                    ))}
                </div>

                {/* Sidebar Footer */}
                <div className="border-t border-gray-700 p-2">
                    <button className="w-full flex items-center gap-3 px-3 py-3 hover:bg-gray-800 rounded-lg transition-colors">
                        <User size={20} />
                        <span className="text-sm">Account</span>
                    </button>
                    <button className="w-full flex items-center gap-3 px-3 py-3 hover:bg-gray-800 rounded-lg transition-colors">
                        <Settings size={20} />
                        <span className="text-sm">Settings</span>
                    </button>
                </div>
            </aside>

            {/* Overlay for mobile */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Main Content */}
            <div className="flex-1 flex flex-col">
                {/* Header */}
                <header className="bg-white border-b border-gray-200 p-4 flex items-center gap-4">
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
                    </button>
                    <h1 className="text-xl font-semibold text-gray-800">Chat Interface</h1>
                </header>

                {/* Main Content Area */}
                <main className="flex-1 overflow-y-auto p-6">
                    <div className="max-w-3xl mx-auto">
                        <div className="bg-white rounded-lg shadow-sm p-6 mb-4">
                            <h2 className="text-2xl font-bold text-gray-800 mb-4">
                                Welcome to Your AI Assistant
                            </h2>
                            <p className="text-gray-600 mb-4">
                                This is a ChatGPT-style sidebar layout with:
                            </p>
                            <ul className="space-y-2 text-gray-700">
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-500 mt-1">•</span>
                                    <span>Responsive design - sidebar collapses on mobile</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-500 mt-1">•</span>
                                    <span>Always visible on desktop (lg breakpoint)</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-500 mt-1">•</span>
                                    <span>Smooth transitions and hover effects</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-500 mt-1">•</span>
                                    <span>Chat history with scroll</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-blue-500 mt-1">•</span>
                                    <span>Dark themed sidebar</span>
                                </li>
                            </ul>
                        </div>

                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <p className="text-blue-800">
                                <strong>Try it:</strong> Resize your browser window to see the responsive behavior.
                                On mobile, the sidebar slides in from the left with an overlay.
                            </p>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}