// Heart is here


import { useEffect, useState } from 'react'

const App = () => {
    const [hasLiked, setHasLiked] = useState(false);

    return (
        <div className="member-container">
            <Member name="Ben" />
            <Member name="Plub" />
            <Member name="Heart" />
        </div>
    )
}

const Member = ({ name }) => {
    return (
        <div className="member-box">
        <h2>{name}</h2>
            <button onClick={() => setHasLiked(true)}>
                Like
            </button>
        </div>
    )
}

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

export default App
