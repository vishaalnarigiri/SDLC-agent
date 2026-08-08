import os
import re
import logging
import subprocess
import google.generativeai as genai
from rag_system import VectorRAGSystem

logger = logging.getLogger(__name__)

class ApexSoftAgent:
    """Base agent using Gemini with customizable system instructions."""
    def __init__(self, name: str, system_instruction: str, collection_name: str = None, model_name: str = "gemini-1.5-flash"):
        self.name = name
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.collection_name = collection_name
        self.rag = VectorRAGSystem()
        
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_instruction
            )
        else:
            self.model = None
            logger.warning(f"Gemini API key not found. Agent {self.name} will run in mock mode.")

    def run_generation(self, prompt: str, search_query: str = None) -> str:
        """Retrieves isolated RAG context, compiles the prompt, and runs Gemini."""
        context = ""
        if self.collection_name and search_query:
            context = self.rag.retrieve_context(self.collection_name, search_query)
            
        full_prompt = f"### CORPORATE STANDARDS & CONTEXT:\n{context}\n\n### USER TASK:\n{prompt}"
        
        if not self.model:
            return self.get_mock_output()
            
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config={"temperature": 0.2}
            )
            return response.text
        except Exception as e:
            logger.error(f"Error executing agent {self.name}: {e}")
            return f"Error executing agent {self.name}: {e}\nFalling back to mock output."

    def get_mock_output(self) -> str:
        return f"Mock output from {self.name} agent due to missing API key."


class BAAgent(ApexSoftAgent):
    """Business Analyst Agent that converts user prompts into Epics and User Stories."""
    def __init__(self):
        system_instruction = (
            "You are an expert Business Analyst / Product Owner at ApexSoft Solutions.\n"
            "Your job is to translate user requirements into detailed Agile specifications.\n"
            "You must ensure that:\n"
            "1. The Epic title starts with '[EPIC]'.\n"
            "2. There are at least 2 detailed User Stories using the standard template: 'As a... I want... So that...'.\n"
            "3. Each User Story has exactly 3 bulleted acceptance criteria.\n"
            "4. Each User Story is assigned story points from the Fibonacci sequence (1, 2, 3, 5, 8) with justifications based on complexity."
        )
        super().__init__("Business Analyst", system_instruction, collection_name="ba_rules")


class ArchitectAgent(ApexSoftAgent):
    """Architecture Agent that models database structures and builds Mermaid charts."""
    def __init__(self):
        system_instruction = (
            "You are the Lead Systems Architect at ApexSoft Solutions.\n"
            "Your task is to create high-level design specifications based on requirements.\n"
            "Your output must contain:\n"
            "1. A database schema definition using SQLite syntax.\n"
            "2. RESTful endpoint definitions (routes, verbs, bodies, response status).\n"
            "3. A valid Mermaid.js flowchart or sequence diagram representing data flow.\n"
            "Ensure all Mermaid node labels with spaces are enclosed in double quotes (e.g. A[\"Start DB\"] -> B[\"Init Server\"]) to prevent rendering failures."
        )
        super().__init__("Lead Architect", system_instruction, collection_name="architect_rules")


class DeveloperAgent(ApexSoftAgent):
    """Developer Agent that writes clean, modular Python files conforming to coding rules."""
    def __init__(self):
        system_instruction = (
            "You are a Senior Full-Stack Python Developer at ApexSoft Solutions.\n"
            "Your task is to write clean, operational Python code files matching the architectural design.\n"
            "You must strictly follow ApexSoft Python standards:\n"
            "- Use 4 spaces for indentation.\n"
            "- Include python type hints and docstrings for all functions/methods/classes.\n"
            "- Use structured logging instead of print statements.\n"
            "- Keep functions under 50 lines.\n\n"
            "OUTPUT FORMAT RULES:\n"
            "To generate files, you MUST use the following tag format for each file:\n"
            "=== FILE: filepath ===\n"
            "code contents here\n"
            "=== END FILE ===\n\n"
            "Do not include conversational chatter or markdown backticks outside of the file blocks. "
            "Output only the files required to build the backend logic."
        )
        super().__init__("Developer", system_instruction, collection_name="developer_rules")

    def extract_and_write_files(self, response_text: str, project_dir: str):
        """Parses the Dev Agent's tag-based output and writes code files to disk."""
        pattern = r"=== FILE:\s*([^\s]+)\s*===\n(.*?)\n=== END FILE ==="
        matches = re.findall(pattern, response_text, re.DOTALL)
        
        if not matches:
            logger.warning("No file blocks matched in developer agent output. Checking fallback markdown blocks...")
            # Fallback to parse standard markdown codeblocks if agent slips up
            md_pattern = r"```python\s+#\s*FILE:\s*([^\n]+)\n(.*?)\n```"
            matches = re.findall(md_pattern, response_text, re.DOTALL)
            
        written_files = []
        for filepath, content in matches:
            full_path = os.path.join(project_dir, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")
            written_files.append(filepath)
            logger.info(f"Developer Agent wrote file: {filepath}")
            
        return written_files


class QAAgent(ApexSoftAgent):
    """QA Agent that generates and runs pytest unit tests on the developer's code."""
    def __init__(self):
        system_instruction = (
            "You are a Quality Assurance Automation Engineer at ApexSoft Solutions.\n"
            "Your task is to write thorough unit tests using the pytest framework for the developer's source code.\n"
            "Follow ApexSoft rules:\n"
            "- Save test files under the 'tests/' folder with filenames starting with 'test_'.\n"
            "- Test successful execution, error boundaries, and input validation.\n"
            "- Use in-memory SQLite (sqlite:///:memory:) or separate temp files for testing.\n\n"
            "OUTPUT FORMAT RULES:\n"
            "You MUST use the tag format to output test files:\n"
            "=== FILE: tests/test_filename.py ===\n"
            "test code contents here\n"
            "=== END FILE ===\n\n"
            "Do not output markdown code blocks or text outside these tags."
        )
        super().__init__("QA Engineer", system_instruction, collection_name="qa_rules")

    def run_tests(self, project_dir: str) -> dict:
        """Executes pytest inside the project sandbox directory and returns results."""
        tests_dir = os.path.join(project_dir, "tests")
        if not os.path.exists(tests_dir):
            return {"success": False, "log": "No test directory found."}
            
        try:
            # We run pytest against the project's tests directory
            # We add pythonpath so it finds the src folder containing modules
            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.join(project_dir, "src")
            
            logger.info(f"Running pytest in {project_dir}")
            result = subprocess.run(
                ["python3", "-m", "pytest", "-v"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            success = (result.returncode == 0)
            return {
                "success": success,
                "log": result.stdout + "\n" + result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "log": "Testing process timed out."}
        except Exception as e:
            return {"success": False, "log": f"Failed to execute pytest: {e}"}


class DevOpsAgent(ApexSoftAgent):
    """DevOps Agent that generates Dockerfile configurations and GitHub Actions workflows."""
    def __init__(self):
        system_instruction = (
            "You are the DevOps Engineer at ApexSoft Solutions.\n"
            "Your task is to write containerization and CI/CD pipelines.\n"
            "You must follow ApexSoft corporate standards:\n"
            "- Docker container must not run as root. Always add a user group and user (e.g. appuser) and configure the USER instruction.\n"
            "- Use lightweight, official base images (like python:3.11-slim).\n"
            "- Create a GitHub Actions workflow file that checks out code, installs packages, and runs tests.\n\n"
            "OUTPUT FORMAT:\n"
            "You MUST use the tag format:\n"
            "=== FILE: deployment/Dockerfile ===\n"
            "dockerfile content here\n"
            "=== END FILE ===\n\n"
            "=== FILE: deployment/pipeline.yml ===\n"
            "ci/cd yaml content here\n"
            "=== END FILE ==="
        )
        super().__init__("DevOps Engineer", system_instruction, collection_name="devops_rules")


class ReleaseAgent(ApexSoftAgent):
    """Release Agent that compiles the work of all agents into a final release summary."""
    def __init__(self):
        system_instruction = (
            "You are the Release Manager at ApexSoft Solutions.\n"
            "Your task is to compile a summary report of the Agile Sprint deployment.\n"
            "You will take the output of all other agents (Requirements, Architecture, Developer files, QA Test results, and DevOps files) and write a professional markdown Release Summary containing:\n"
            "1. A clean Project Overview.\n"
            "2. The Agile features delivered (listing epics and stories).\n"
            "3. The testing verdict (indicating if tests passed/failed).\n"
            "4. Deployment configuration details (Docker and CI/CD summary).\n"
            "Ensure the output format is markdown, saving it as release_notes.md using the FILE tags."
        )
        super().__init__("Release Manager", system_instruction)
