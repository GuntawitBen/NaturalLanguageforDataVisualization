// src/components/Sidebar.jsx
import { useState } from 'react';
import { Plus, MessageSquare, Settings, User, Menu, X } from 'lucide-react';

export default function App() {
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [chats, setChats] = useState([
        { id: 1, title: 'React Sidebar Tutorial', date: 'Today' },
        { id: 2, title: 'CSS Grid Layout', date: 'Yesterday' },
        { id: 3, title: 'JavaScript Arrays', date: '2 days ago' },
    ]);

    return (
        <div className="flex h-screen w-screen bg-gray-50 overflow-hidden">
            {/* Sidebar - Collapsible */}
            {sidebarOpen && (
                <aside className="w-64 bg-gray-900 text-white flex flex-col">
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
            )}

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0">
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
                    <div className="max-w-4xl mx-auto">
                        <h2 className="text-2xl font-bold text-gray-800 mb-4">
                            Natural Language for Data Visualization
                        </h2>
                        <p className="text-gray-600">
                            Start a new chat to create visualizations using natural language.
                        </p>
                    </div>
                </main>
            </div>
        </div>
    );
}