# ApexSoft Solutions - Multi-Agent Agile SDLC Workspace

This is an automated, ticket-free Agile software development lifecycle (SDLC) simulation system using multiple specialized Gemini agents and isolated RAG systems.

## Project Structure

```text
├── backend/
│   ├── main.py                 # FastAPI server entrypoint
│   ├── orchestrator.py         # Agile Orchestrator State Machine
│   ├── agents.py               # BA, Architect, Dev, QA, DevOps, Release Agent prompts
│   ├── rag_system.py           # AST & Vector RAG implementations
│   ├── bootstrap_rag.py        # Seed ApexSoft guidelines into ChromaDB
│   ├── requirements.txt        # Backend dependencies
│   ├── .env                    # Environment configurations (API Keys)
│   └── knowledge_base/         # ApexSoft Solutions Corporate Guidelines
│       ├── ba/
│       ├── architect/
│       ├── developer/
│       ├── qa/
│       └── devops/
├── frontend/                   # React + Vite Dashboard
│   ├── src/
│   │   ├── App.jsx             # Beautiful interactive developer dashboard
│   │   └── index.css           # Premium glassmorphic styling
│   └── package.json            # Node.js dependencies
└── workspace/                  # Dynamic sandboxes created for each project
```

## Getting Started

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Set your Gemini API key in `.env`:
   ```env
   GEMINI_API_KEY=your-gemini-api-key
   ```
4. Seed the RAG databases with ApexSoft guidelines:
   ```bash
   python3 bootstrap_rag.py
   ```
5. Start the backend server:
   ```bash
   python3 -m uvicorn main:app --reload --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
