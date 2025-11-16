// Heart is here

//src/App.jsx
import './App.css'
import Layout from './components/Layout';


function App() {
    return (
        <>
            {/* Background */}
            <div className="gradient-overlay" />

            {/* Main app UI on top */}
            <div style={{ position: 'relative', zIndex: 1 }}>
                <Layout>
                    {/* Your pages will be rendered here */}
                </Layout>
            </div>
        </>
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

