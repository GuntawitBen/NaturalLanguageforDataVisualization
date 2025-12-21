import { useEffect, useState } from 'react';

function Dashboard() {
    const [userName, setUserName] = useState('');
    const [userEmail, setUserEmail] = useState('');

    useEffect(() => {
        const name = sessionStorage.getItem('userName') || 'User';
        const email = sessionStorage.getItem('userEmail') || '';
        setUserName(name);
        setUserEmail(email);
    }, []);

    return (
        <div className="p-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold mb-6">
                    Welcome, {userName}!
                </h1>

                <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-6 shadow-lg mb-6">
                    <h2 className="text-xl font-semibold mb-4">User Information</h2>
                    <div className="space-y-2">
                        <p className="text-gray-700">
                            <span className="font-medium">Name:</span> {userName}
                        </p>
                        <p className="text-gray-700">
                            <span className="font-medium">Email:</span> {userEmail}
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
