# Phebe

A full-stack application that enables natural language interaction for data visualization using React and FastAPI.

## Tech Stack

### Frontend
- **React 19.1.1** - UI library
- **Vite 7.1.7** - Build tool and dev server
- **Tailwind CSS 3.4.17** - Utility-first CSS framework
- **Lucide React** - Icon library
- **ESLint 9** - Code linting

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server

## Prerequisites

- **Node.js** (v18 or higher)
- **npm** (comes with Node.js)
- **Python 3.8+**
- **pip** (Python package manager)

## Project Structure

```
NaturalLanguageforDataVisualization/
├── backend/              # FastAPI backend
│   ├── main.py          # Main API file
│   └── requirements.txt # Python dependencies
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── App.jsx      # Main App component
│   │   └── main.jsx     # Entry point
│   └── package.json     # Node dependencies
└── README.md
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

   The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

## Running the Application

1. Start the backend server (in one terminal):
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. Start the frontend dev server (in another terminal):
   ```bash
   cd frontend
   npm run dev
   ```

3. Open your browser and navigate to `http://localhost:5173`

## Available API Endpoints

### Backend (http://localhost:8000)

- `GET /api/hello` - Test endpoint that returns a greeting message

## Available Scripts

### Frontend

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Development

### Backend
The FastAPI backend is configured with CORS to allow requests from the Vite dev server (`http://localhost:5173`).

### Frontend
The frontend uses:
- **Vite** for fast development and building
- **Tailwind CSS** for styling with glassmorphism effects
- **ESLint** for code quality

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

