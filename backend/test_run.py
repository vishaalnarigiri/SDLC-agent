import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TestRun")

from orchestrator import AgileOrchestrator, ACTIVE_PROJECTS

def run_test():
    logger.info("Initializing Agile Orchestrator...")
    orchestrator = AgileOrchestrator()
    
    test_query = "Build a lightweight key-value database using SQLite"
    logger.info(f"Triggering test sprint run with query: '{test_query}'")
    
    project_id = orchestrator.run_sprint(test_query)
    
    logger.info(f"Sprint completed. Project ID generated: '{project_id}'")
    
    if project_id not in ACTIVE_PROJECTS:
        logger.error("Project ID not found in memory ACTIVE_PROJECTS state!")
        sys.exit(1)
        
    proj = ACTIVE_PROJECTS[project_id]
    logger.info(f"Project Final Status: {proj['status']}")
    
    # Check generated files on disk
    project_dir = proj["dir"]
    expected_files = [
        "docs/requirements.md",
        "docs/architecture.md",
        "release_notes.md"
    ]
    
    logger.info(f"Verifying generated files in directory: {project_dir}")
    missing_files = []
    for rel_path in expected_files:
        full_path = os.path.join(project_dir, rel_path)
        if os.path.exists(full_path):
            logger.info(f"  [OK] Found generated file: {rel_path}")
        else:
            logger.error(f"  [ERROR] Missing generated file: {rel_path}")
            missing_files.append(rel_path)
            
    if missing_files:
        logger.error(f"Test failed. Missing {len(missing_files)} expected output files.")
        sys.exit(1)
        
    logger.info("--- Test Log Feed Summary ---")
    for log_entry in proj["logs"]:
        logger.info(f"[{log_entry['sender']}] {log_entry['message']}")
        
    logger.info("SUCCESS: Multi-agent SDLC pipeline test passed successfully!")

if __name__ == "__main__":
    run_test()
