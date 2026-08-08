import os
import shutil
import logging
from typing import Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="ApexSoft Solutions Multi-Agent Agile SDLC System")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow connections from React server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from orchestrator import AgileOrchestrator, ACTIVE_PROJECTS
from bootstrap_rag import bootstrap

# Initialize Orchestrator
orchestrator = AgileOrchestrator()

class ProjectStartRequest(BaseModel):
    query: str

@app.post("/api/project/start")
def start_project(request: ProjectStartRequest, background_tasks: BackgroundTasks):
    """Initiates an Agile sprint in a background thread."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query prompt cannot be empty.")
        
    try:
        # Extract name to pre-check or register
        project_name = orchestrator.clean_project_name(request.query)
        
        # Start sprint as FastAPI background task
        background_tasks.add_task(orchestrator.run_sprint, request.query)
        
        return {
            "status": "success",
            "project_id": project_name,
            "message": f"Sprint task started for project '{project_name}'"
        }
    except Exception as e:
        logger.error(f"Error starting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects")
def list_projects():
    """Lists all projects currently active in memory or present in the workspace."""
    workspace_dir = orchestrator.workspace_root
    disk_projects = []
    if os.path.exists(workspace_dir):
        for name in os.listdir(workspace_dir):
            if os.path.isdir(os.path.join(workspace_dir, name)) and not name.startswith("."):
                disk_projects.append(name)
                
    # Combine active in-memory state with disk list
    result = []
    seen = set()
    
    # Active/Memory first
    for pid, proj in ACTIVE_PROJECTS.items():
        seen.add(pid)
        result.append({
            "id": pid,
            "name": proj["name"],
            "status": proj["status"],
            "query": proj["query"]
        })
        
    # Disk items that might have finished in previous runs
    for pid in disk_projects:
        if pid not in seen:
            result.append({
                "id": pid,
                "name": pid.replace("_", " ").title(),
                "status": "Completed (Disk)",
                "query": "Project restored from file system."
            })
            
    return result

@app.get("/api/project/status/{project_id}")
def get_project_status(project_id: str):
    """Retrieves full real-time status details of a specific project."""
    if project_id not in ACTIVE_PROJECTS:
        # Check if project folder exists on disk but is not in memory
        project_dir = os.path.join(orchestrator.workspace_root, project_id)
        if os.path.exists(project_dir):
            # Load project details dynamically from disk files to restore state
            return load_project_from_disk(project_id, project_dir)
        raise HTTPException(status_code=404, detail="Project not found.")
        
    return ACTIVE_PROJECTS[project_id]

@app.post("/api/project/upload_knowledge")
async def upload_knowledge(agent: str, file: UploadFile = File(...)):
    """Receives custom documents, saves them to the custom RAG index folder, and re-seeds database."""
    valid_agents = ["ba", "architect", "developer", "qa", "devops"]
    if agent not in valid_agents:
        raise HTTPException(status_code=400, detail=f"Invalid agent parameter. Must be one of {valid_agents}")
        
    # Ensure custom directory exists
    custom_dir = os.path.join(os.path.dirname(__file__), "knowledge_base", "custom")
    os.makedirs(custom_dir, exist_ok=True)
    
    # Clean filename
    filename = f"{agent}_custom_{file.filename}"
    file_path = os.path.join(custom_dir, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"Custom knowledge file written: {file_path}. Triggering RAG re-bootstrapping...")
        
        # Trigger RAG re-indexing
        bootstrap()
        
        return {
            "status": "success",
            "message": f"Successfully uploaded {file.filename} and updated the {agent} agent's RAG database."
        }
    except Exception as e:
        logger.error(f"Error handling knowledge upload: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


def load_project_from_disk(project_id: str, project_dir: str) -> Dict[str, Any]:
    """Helper to reconstruct project details from disk files if not present in memory."""
    docs_dir = os.path.join(project_dir, "docs")
    src_dir = os.path.join(project_dir, "src")
    tests_dir = os.path.join(project_dir, "tests")
    deployment_dir = os.path.join(project_dir, "deployment")
    
    req_content = ""
    arch_content = ""
    code_files = {}
    test_files = {}
    test_report = ""
    devops_files = {}
    release_notes = ""
    
    # Read Docs
    req_path = os.path.join(docs_dir, "requirements.md")
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            req_content = f.read()
            
    arch_path = os.path.join(docs_dir, "architecture.md")
    if os.path.exists(arch_path):
        with open(arch_path, "r", encoding="utf-8") as f:
            arch_content = f.read()
            
    # Read Source Code
    if os.path.exists(src_dir):
        for name in os.listdir(src_dir):
            if name.endswith(".py"):
                with open(os.path.join(src_dir, name), "r", encoding="utf-8") as f:
                    code_files[f"src/{name}"] = f.read()
                    
    # Read Tests
    if os.path.exists(tests_dir):
        for name in os.listdir(tests_dir):
            if name.endswith(".py"):
                with open(os.path.join(tests_dir, name), "r", encoding="utf-8") as f:
                    test_files[f"tests/{name}"] = f.read()
                    
    # Read Test Report
    report_path = os.path.join(project_dir, "tests", "test_report.json")
    if os.path.exists(report_path):
         with open(report_path, "r", encoding="utf-8") as f:
             test_report = f.read()
             
    # Read DevOps
    if os.path.exists(deployment_dir):
        for name in os.listdir(deployment_dir):
            if name in ["Dockerfile", "pipeline.yml"]:
                with open(os.path.join(deployment_dir, name), "r", encoding="utf-8") as f:
                    devops_files[f"deployment/{name}"] = f.read()
                    
    # Read Release Notes
    release_path = os.path.join(project_dir, "release_notes.md")
    if os.path.exists(release_path):
        with open(release_path, "r", encoding="utf-8") as f:
            release_notes = f.read()
            
    # Compile a reconstructed structure
    return {
        "name": project_id.replace("_", " ").title(),
        "query": "Restored project.",
        "status": "Completed (Disk)",
        "dir": project_dir,
        "logs": [{"sender": "System", "message": "Sprint project restored from filesystem storage.", "timestamp": "00:00:00"}],
        "kanban": {
            "backlog": [],
            "in_progress": [],
            "code_review": [],
            "done": [{"id": "STORY-ALL", "title": "All requirements deployed successfully"}]
        },
        "artifacts": {
            "requirements": req_content,
            "architecture": arch_content,
            "code": code_files,
            "tests": test_files,
            "test_report": test_report if test_report else "Test run logs unavailable.",
            "devops": devops_files,
            "release": release_notes
        }
    }
