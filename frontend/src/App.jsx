// Heart is here

//src/App.jsx
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Signin from './components/Signin';
import Signup from './components/Signup';

function App() {
    return (
        <BrowserRouter>
            {/* Background */}
            <div className="gradient-overlay" />
            
            {/* Main app UI on top */}
            <div style={{ position: 'relative', zIndex: 1 }}>
                <Routes>
                    {/* Auth routes WITHOUT Layout */}
                    <Route path="/signin" element={<Signin />} />
                    <Route path="/signup" element={<Signup />} />
                    
                    {/* Protected routes WITH Layout */}
                    <Route path="/*" element={<Layout />} />
                </Routes>
            </div>
        </BrowserRouter>
    );
}

export default App;

// const Member = ({ name }) => {
//     return (
//         <div className="member-box">
//         <h2>{name}</h2>
//             <button onClick={() => setHasLiked(true)}>
//                 Like
//             </button>
//         </div>
//     )
// }

/*
function App() {
    const [message, setMessage] = useState("")

    useEffect(() => {
        fetch("http://localhost:8000/api/hello")
            .then(res => res.json())
            .then(data => setMessage(data.message))
    }, [])

    return (
        <div>
            <h1>React + Vite + FastAPI</h1>
            <p>{message}</p>
            <Member name="Ben" />
            <Member name="Heart" />
            <Member name="Plub  " />

        </div>
    )
}
*/

