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
            {/* Sidebar with margins */}
            <aside
                className={`bg-white/90 backdrop-blur-md text-gray-800 flex flex-col shadow-2xl transition-all duration-500 ease-in-out ${
                    sidebarOpen ? 'w-72' : 'w-0'
                } m-4 rounded-2xl overflow-hidden`}
            >
                {/* Sidebar Header */}
                <div className="p-4 border-b border-gray-200">
                    <button
                        onClick={() => setChats([...chats, { id: Date.now(), title: 'New Chat', date: 'Just now' }])}
                        className="w-full flex items-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                    >
                        <Plus size={20} />
                        <span>New Chat</span>
                    </button>
                </div>

                {/* Chat History */}
                <div className="flex-1 overflow-y-auto p-4">
                    <div className="text-xs text-gray-500 px-2 py-2 font-semibold">Recent</div>
                    {chats.map((chat) => (
                        <button
                            key={chat.id}
                            className="w-full text-left px-3 py-3 hover:bg-gray-100 rounded-lg transition-colors group"
                        >
                            <div className="flex items-center gap-2">
                                <MessageSquare size={16} className="flex-shrink-0 text-gray-600" />
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm truncate font-medium">{chat.title}</div>
                                    <div className="text-xs text-gray-500">{chat.date}</div>
                                </div>
                            </div>
                        </button>
                    ))}
                </div>

                {/* Sidebar Footer */}
                <div className="border-t border-gray-200 p-4">
                    <button className="w-full flex items-center gap-3 px-3 py-3 hover:bg-gray-100 rounded-lg transition-colors text-gray-700">
                        <User size={20} />
                        <span className="text-sm">Account</span>
                    </button>
                    <button className="w-full flex items-center gap-3 px-3 py-3 hover:bg-gray-100 rounded-lg transition-colors text-gray-700">
                        <Settings size={20} />
                        <span className="text-sm">Settings</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header with toggle button */}
                <header className="bg-white/80  border-b border-gray-200 p-4 rounded-t-2xl flex items-center">
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
                    </button>
                </header>

                {/* Main Content Area */}
                <main className="flex-1 overflow-y-auto p-4 mt-0 bg-white/80 backdrop-blur-md rounded-b-2xl">
                    <div className="max-w-4xl mx-auto p-6">
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