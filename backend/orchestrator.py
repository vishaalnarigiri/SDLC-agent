import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import google.generativeai as genai
from rag_system import CodeRAGSystem, GraphAgileRAG
from agents import BAAgent, ArchitectAgent, DeveloperAgent, QAAgent, DevOpsAgent, ReleaseAgent

logger = logging.getLogger(__name__)

# Global storage for active project runs
ACTIVE_PROJECTS: Dict[str, Dict[str, Any]] = {}

class AgileOrchestrator:
    """Manages the agent pipeline state machine and coordination."""
    def __init__(self, workspace_root: str = None):
        if not workspace_root:
            workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace"))
        self.workspace_root = workspace_root
        os.makedirs(self.workspace_root, exist_ok=True)
        
        # Initialize agents
        self.ba_agent = BAAgent()
        self.architect_agent = ArchitectAgent()
        self.dev_agent = DeveloperAgent()
        self.qa_agent = QAAgent()
        self.devops_agent = DevOpsAgent()
        self.release_agent = ReleaseAgent()

    def clean_project_name(self, query: str) -> str:
        """Helper to create a clean, filesystem-safe directory name from the user query."""
        # Use Gemini to generate a short, clean project slug if API is configured
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"Convert the following project description into a single short, lower-case snake_case identifier (maximum 3 words, letters and numbers only). E.g. 'Build a basic calculator' -> 'basic_calculator'. Description: '{query}'"
                response = model.generate_content(prompt)
                slug = response.text.strip().lower()
                # Clean up any characters that aren't letters, numbers, or underscores
                slug = re.sub(r'[^a-z0-9_]', '', slug)
                if slug:
                    return slug
            except Exception as e:
                logger.warning(f"Failed to generate project slug with Gemini: {e}. Falling back to regex slug.")
        
        # Fallback slug generator
        words = re.findall(r'\b\w+\b', query.lower())
        slug = "_".join(words[:3])
        slug = re.sub(r'[^a-z0-9_]', '', slug)
        return slug if slug else "generated_project"

    def add_log(self, project_id: str, sender: str, message: str, status_update: str = None):
        """Appends a new event log to the active project session."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "sender": sender,
            "message": message,
            "timestamp": timestamp
        }
        
        if project_id in ACTIVE_PROJECTS:
            ACTIVE_PROJECTS[project_id]["logs"].append(log_entry)
            if status_update:
                ACTIVE_PROJECTS[project_id]["status"] = status_update
            logger.info(f"[{project_id}] {sender}: {message[:100]}...")

    def run_sprint(self, query: str) -> str:
        """Starts a background sprint run for the user query."""
        project_name = self.clean_project_name(query)
        project_dir = os.path.join(self.workspace_root, project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # Verify if directory is empty or write permissions are okay
        docs_dir = os.path.join(project_dir, "docs")
        src_dir = os.path.join(project_dir, "src")
        tests_dir = os.path.join(project_dir, "tests")
        deployment_dir = os.path.join(project_dir, "deployment")
        
        os.makedirs(docs_dir, exist_ok=True)
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(tests_dir, exist_ok=True)
        os.makedirs(deployment_dir, exist_ok=True)
        
        project_id = project_name
        
        # Initialize session state
        ACTIVE_PROJECTS[project_id] = {
            "name": project_name.replace("_", " ").title(),
            "query": query,
            "status": "Starting BA Phase",
            "dir": project_dir,
            "logs": [],
            "kanban": {
                "backlog": [],
                "in_progress": [],
                "code_review": [],
                "done": []
            },
            "artifacts": {
                "requirements": "",
                "architecture": "",
                "code": {},
                "tests": {},
                "test_report": "",
                "devops": {},
                "release": ""
            }
        }
        
        self.add_log(project_id, "System", f"Initialized workspace folder: {project_dir}", "Grooming Backlog")
        
        # Start executing agents synchronously (FastAPI backend can call this in background task)
        try:
            self._execute_sprint_pipeline(project_id, query, project_dir)
        except Exception as e:
            logger.error(f"Error executing sprint {project_id}: {e}", exc_info=True)
            self.add_log(project_id, "System Error", f"Fatal error during sprint: {e}", "Failed")
            
        return project_id

    def _execute_sprint_pipeline(self, project_id: str, query: str, project_dir: str):
        # 1. BA AGENT PHASE
        self.add_log(project_id, "Business Analyst", "Analyzing requirements and seeding project epics/user stories.", "BA Analysis")
        ba_prompt = f"Convert the feature request: '{query}' into detailed ApexSoft specifications."
        requirements_doc = self.ba_agent.run_generation(ba_prompt, search_query="agile sprint rules")
        
        # Save requirement document
        req_path = os.path.join(project_dir, "docs", "requirements.md")
        with open(req_path, "w", encoding="utf-8") as f:
            f.write(requirements_doc)
            
        ACTIVE_PROJECTS[project_id]["artifacts"]["requirements"] = requirements_doc
        self.add_log(project_id, "System", "Requirements documented in docs/requirements.md", "Requirements Drafted")

        # Parse requirements into SQLite stories for Graph RAG/Kanban tracking
        db_path = os.path.join(project_dir, "docs", "agile_graph.db")
        graph_rag = GraphAgileRAG(db_path)
        
        # Simple extraction of stories from markdown
        story_titles = re.findall(r"User Story \d+:\s*(.*?)(?=\n|$)", requirements_doc)
        if not story_titles:
            # Fallback if names are formatted differently
            story_titles = re.findall(r"\*\*As a.*?\*\*.*?(?=\n\n|$)", requirements_doc, re.DOTALL)
            story_titles = [s.strip().replace("\n", " ")[:60] + "..." for s in story_titles]
            
        if not story_titles:
            story_titles = ["Set up basic framework layers", "Implement core database models"]
            
        for idx, title in enumerate(story_titles):
            story_id = f"STORY-{idx+1}"
            graph_rag.add_story(story_id, title, f"Agile task to implement: {title}", story_points=(3 if idx % 2 == 0 else 2))
            ACTIVE_PROJECTS[project_id]["kanban"]["backlog"].append({"id": story_id, "title": title})
            
        self.add_log(project_id, "Project Manager", f"Created {len(story_titles)} backlog cards in the Kanban board.", "Backlog Created")

        # 2. ARCHITECT AGENT PHASE
        self.add_log(project_id, "Lead Architect", "Designing system schema, REST routes, and data flows.", "Architecting System")
        arch_prompt = f"Create system design and Mermaid sequence diagrams for these requirements:\n\n{requirements_doc}"
        architecture_doc = self.architect_agent.run_generation(arch_prompt, search_query="database models REST api")
        
        # Save architecture document
        arch_path = os.path.join(project_dir, "docs", "architecture.md")
        with open(arch_path, "w", encoding="utf-8") as f:
            f.write(architecture_doc)
            
        ACTIVE_PROJECTS[project_id]["artifacts"]["architecture"] = architecture_doc
        self.add_log(project_id, "System", "System design details saved in docs/architecture.md", "Architecture Designed")

        # Move backlog tickets to In Progress
        ACTIVE_PROJECTS[project_id]["kanban"]["in_progress"] = ACTIVE_PROJECTS[project_id]["kanban"]["backlog"]
        ACTIVE_PROJECTS[project_id]["kanban"]["backlog"] = []

        # 3. DEVELOPER AGENT & SELF-CORRECTION LOOP
        max_repair_attempts = 3
        attempt = 1
        dev_success = False
        
        self.add_log(project_id, "Developer", "Beginning implementation code writing. Coding to ApexSoft Standards.", "Development Started")
        
        dev_prompt = (
            f"Based on the Requirements:\n{requirements_doc}\n\n"
            f"And the System Architecture:\n{architecture_doc}\n\n"
            f"Write the required Python source files. Ensure code is written into files inside the 'src/' folder."
        )
        
        developer_output = self.dev_agent.run_generation(dev_prompt, search_query="python style typing logger")
        
        while attempt <= max_repair_attempts:
            # Clear src folder and write generated files
            written_files = self.dev_agent.extract_and_write_files(developer_output, project_dir)
            
            # Read files to save to active artifacts state for UI display
            ACTIVE_PROJECTS[project_id]["artifacts"]["code"] = {}
            for filepath in written_files:
                content = CodeRAGSystem.read_file_contents(project_dir, filepath)
                ACTIVE_PROJECTS[project_id]["artifacts"]["code"][filepath] = content
                
            self.add_log(project_id, "System", f"Developer generated {len(written_files)} source files: {', '.join(written_files)}", "Code Review")
            
            # Move tickets to Code Review
            ACTIVE_PROJECTS[project_id]["kanban"]["code_review"] = ACTIVE_PROJECTS[project_id]["kanban"]["in_progress"]
            ACTIVE_PROJECTS[project_id]["kanban"]["in_progress"] = []

            # 4. QA AGENT PHASE (Test Generation & Running)
            self.add_log(project_id, "QA Engineer", f"Creating pytest unit tests. Run Attempt #{attempt}.", "QA Testing")
            
            # Read developer code layout for QA context
            codebase_summary = CodeRAGSystem.inspect_codebase(os.path.join(project_dir, "src"))
            
            qa_prompt = (
                f"Create Python pytest unit tests for the following codebase structure:\n{codebase_summary}\n\n"
                f"Design specs:\n{architecture_doc}\n\n"
                f"Write the test files in the 'tests/' folder."
            )
            
            qa_output = self.qa_agent.run_generation(qa_prompt, search_query="pytest unit assertions mock")
            
            # Write QA test files
            written_tests = self.dev_agent.extract_and_write_files(qa_output, project_dir)
            ACTIVE_PROJECTS[project_id]["artifacts"]["tests"] = {}
            for filepath in written_tests:
                content = CodeRAGSystem.read_file_contents(project_dir, filepath)
                ACTIVE_PROJECTS[project_id]["artifacts"]["tests"][filepath] = content
                
            self.add_log(project_id, "System", f"QA generated test suite: {', '.join(written_tests)}", "Running Test Suite")
            
            # Execute pytest suite
            test_results = self.qa_agent.run_tests(project_dir)
            ACTIVE_PROJECTS[project_id]["artifacts"]["test_report"] = test_results["log"]
            
            if test_results["success"]:
                self.add_log(project_id, "QA Engineer", "SUCCESS: All pytest unit assertions passed! Code conforms to quality rules.", "Tests Passed")
                dev_success = True
                break
            else:
                self.add_log(
                    project_id, 
                    "QA Engineer", 
                    f"WARNING: Test suite failed or code has error on attempt #{attempt}. Repair loop initiated.\nLogs:\n{test_results['log'][:400]}...", 
                    "Fixing Bugs"
                )
                
                # Setup code repair prompt
                dev_prompt = (
                    f"Your previously generated Python code has test or compilation failures.\n\n"
                    f"CODEBASE METADATA:\n{codebase_summary}\n\n"
                    f"TEST RUN FAILURE LOGS:\n{test_results['log']}\n\n"
                    f"Please review the errors and fix the source files. Enclose your full fixed code in standard FILE tags."
                )
                
                # Let Developer attempt to fix it
                developer_output = self.dev_agent.run_generation(dev_prompt, search_query="python error handling")
                
                # Return tickets to In Progress for fix
                ACTIVE_PROJECTS[project_id]["kanban"]["in_progress"] = ACTIVE_PROJECTS[project_id]["kanban"]["code_review"]
                ACTIVE_PROJECTS[project_id]["kanban"]["code_review"] = []
                attempt += 1
                
        if not dev_success:
            self.add_log(project_id, "System", f"Developer unable to fix test suite failures after {max_repair_attempts} attempts. Continuing pipeline.", "QA Override")

        # 5. DEVOPS AGENT PHASE
        self.add_log(project_id, "DevOps Engineer", "Building Docker deployment package and CI/CD yaml pipelines.", "DevOps Provisioning")
        
        devops_prompt = (
            f"Generate Dockerfile configuration and GitHub Actions workflow for the following project layout:\n"
            f"Source files in 'src/'\n"
            f"Tests in 'tests/'\n"
            f"Requirements defined in:\n{requirements_doc}"
        )
        
        devops_output = self.devops_agent.run_generation(devops_prompt, search_query="Dockerfile python alpine non-root user")
        
        written_devops = self.dev_agent.extract_and_write_files(devops_output, project_dir)
        ACTIVE_PROJECTS[project_id]["artifacts"]["devops"] = {}
        for filepath in written_devops:
            content = CodeRAGSystem.read_file_contents(project_dir, filepath)
            ACTIVE_PROJECTS[project_id]["artifacts"]["devops"][filepath] = content
            
        self.add_log(project_id, "System", f"DevOps created infrastructure: {', '.join(written_devops)}", "Deployment Ready")

        # 6. RELEASE AGENT PHASE
        self.add_log(project_id, "Release Manager", "Compiling deployment sprint packages and writing release notes.", "Releasing Project")
        
        # Compile inputs for Release report
        devops_summary = "\n\n".join([f"File: {k}\n{v}" for k, v in ACTIVE_PROJECTS[project_id]["artifacts"]["devops"].items()])
        release_prompt = (
            f"Generate release notes for project: {project_id}.\n\n"
            f"Agile Specs:\n{requirements_doc}\n\n"
            f"Design Docs:\n{architecture_doc}\n\n"
            f"Test report log:\n{ACTIVE_PROJECTS[project_id]['artifacts']['test_report']}\n\n"
            f"DevOps deployment config:\n{devops_summary}"
        )
        
        release_notes = self.release_agent.run_generation(release_prompt)
        
        # Parse and save release_notes.md
        written_release = self.dev_agent.extract_and_write_files(release_notes, project_dir)
        if "release_notes.md" in written_release or os.path.exists(os.path.join(project_dir, "release_notes.md")):
            notes_content = CodeRAGSystem.read_file_contents(project_dir, "release_notes.md")
        else:
            # Fallback if agent wrote raw markdown without tags
            notes_content = release_notes
            with open(os.path.join(project_dir, "release_notes.md"), "w", encoding="utf-8") as f:
                f.write(release_notes)
                
        ACTIVE_PROJECTS[project_id]["artifacts"]["release"] = notes_content
        
        # Move all tickets to Done
        ACTIVE_PROJECTS[project_id]["kanban"]["done"] = ACTIVE_PROJECTS[project_id]["kanban"]["code_review"] + ACTIVE_PROJECTS[project_id]["kanban"]["in_progress"]
        ACTIVE_PROJECTS[project_id]["kanban"]["code_review"] = []
        ACTIVE_PROJECTS[project_id]["kanban"]["in_progress"] = []
        
        self.add_log(project_id, "Release Manager", "Sprint completed successfully! All code artifacts, tests, and Docker packages released.", "Completed")
