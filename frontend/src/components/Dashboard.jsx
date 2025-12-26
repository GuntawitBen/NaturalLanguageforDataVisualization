import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { LogOut } from 'lucide-react';

function Dashboard() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/signin');
    };

    return (
        <div className="p-8">
            <div className="max-w-4xl mx-auto">
                <div className="flex justify-between items-center mb-6">
                    <h1 className="text-3xl font-bold">
                        Welcome, {user?.name || 'User'}!
                    </h1>
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg"
                    >
                        <LogOut size={18} />
                        Logout
                    </button>
                </div>

                <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-6 shadow-lg mb-6">
                    <h2 className="text-xl font-semibold mb-4">User Information</h2>
                    <div className="space-y-2">
                        <p className="text-gray-700">
                            <span className="font-medium">Name:</span> {user?.name}
                        </p>
                        <p className="text-gray-700">
                            <span className="font-medium">Email:</span> {user?.email}
                        </p>
                    </div>
                </div>

                <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-6 shadow-lg">
                    <h2 className="text-xl font-semibold mb-4">Data Visualization</h2>
                    <p className="text-gray-600">
                        Start creating natural language queries for data visualization here.
                    </p>
                </div>
            </div>
        </div>
    );
}

export default Dashboard;
