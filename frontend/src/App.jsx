// Heart is here

//src/App.jsx
import Layout from './components/Layout';

const App = () => {
    return (
        <Layout>
        </Layout>
    )
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

