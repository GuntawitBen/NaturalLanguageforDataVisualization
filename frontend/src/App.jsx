import { useEffect, useState } from 'react'

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
        </div>
    )
}

export default App
