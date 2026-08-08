import os
import ast
import sqlite3
import logging
import chromadb
from bootstrap_rag import GeminiEmbeddingFunction

logger = logging.getLogger(__name__)

class VectorRAGSystem:
    """Interface to query the isolated ChromaDB vector databases."""
    def __init__(self, chroma_dir=None):
        if not chroma_dir:
            chroma_dir = os.path.join(os.path.dirname(__file__), "chroma_db")
        
        self.client = chromadb.PersistentClient(path=chroma_dir)
        api_key = os.getenv("GEMINI_API_KEY")
        self.embedding_fn = GeminiEmbeddingFunction(api_key)

    def retrieve_context(self, collection_name: str, query: str, n_results: int = 2) -> str:
        """Queries ChromaDB and returns a formatted block of context text."""
        try:
            # Check if collection exists
            collection = self.client.get_collection(
                name=collection_name, 
                embedding_function=self.embedding_fn
            )
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            
            if not documents:
                return "No company standards or templates found for this search query."
            
            context_blocks = []
            for doc, meta in zip(documents, metadatas):
                source = meta.get("source", "unknown")
                context_blocks.append(f"--- Context from {source} ---\n{doc}")
                
            return "\n\n".join(context_blocks)
        except Exception as e:
            logger.error(f"Error querying ChromaDB collection '{collection_name}': {e}")
            return f"Error retrieving context: {e}"


class CodeRAGSystem:
    """Parses and indexes generated Python codebase files dynamically."""
    
    @staticmethod
    def inspect_codebase(src_dir: str) -> str:
        """Performs AST analysis on all Python files in the source directory."""
        if not os.path.exists(src_dir):
            return "Codebase is currently empty. No source files exist yet."
            
        summary_blocks = []
        
        for root, _, files in os.walk(src_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, src_dir)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                        
                    parsed_ast = ast.parse(file_content)
                    
                    file_summary = [f"File: {rel_path}"]
                    
                    # Search classes and functions
                    for node in parsed_ast.body:
                        if isinstance(node, ast.ClassDef):
                            class_doc = ast.get_docstring(node)
                            doc_str = f" - Docstring: '{class_doc.strip()}'" if class_doc else ""
                            file_summary.append(f"  - Class: {node.name}{doc_str}")
                            
                            for sub_node in node.body:
                                if isinstance(sub_node, ast.FunctionDef):
                                    args = [arg.arg for arg in sub_node.args.args]
                                    file_summary.append(f"    - Method: {sub_node.name}({', '.join(args)})")
                                    
                        elif isinstance(node, ast.FunctionDef):
                            func_doc = ast.get_docstring(node)
                            doc_str = f" - Docstring: '{func_doc.strip()}'" if func_doc else ""
                            args = [arg.arg for arg in node.args.args]
                            file_summary.append(f"  - Function: {node.name}({', '.join(args)}){doc_str}")
                            
                    summary_blocks.append("\n".join(file_summary))
                except Exception as e:
                    logger.warning(f"Failed to perform AST parsing on {rel_path}: {e}")
                    summary_blocks.append(f"File: {rel_path} (could not parse AST structure)")
                    
        return "\n\n".join(summary_blocks) if summary_blocks else "Codebase is currently empty. No source files exist yet."

    @staticmethod
    def read_file_contents(src_dir: str, rel_path: str) -> str:
        """Reads raw contents of a specific file inside source directory for deep context."""
        file_path = os.path.join(src_dir, rel_path)
        if not os.path.exists(file_path):
            return f"File {rel_path} does not exist."
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file {rel_path}: {e}"


class GraphAgileRAG:
    """Manages project ticket/story dependency mapping in a local SQLite file."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create stories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                story_points INTEGER,
                status TEXT,
                assigned_agent TEXT
            )
        """)
        
        # Create dependencies table (blocks mapping)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dependencies (
                story_id TEXT,
                blocks_story_id TEXT,
                PRIMARY KEY (story_id, blocks_story_id)
            )
        """)
        conn.commit()
        conn.close()

    def add_story(self, story_id: str, title: str, description: str, story_points: int, status: str = "Backlog"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO stories VALUES (?, ?, ?, ?, ?, NULL)",
            (story_id, title, description, story_points, status)
        )
        conn.commit()
        conn.close()

    def add_dependency(self, story_id: str, blocks_story_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO dependencies VALUES (?, ?)", (story_id, blocks_story_id))
        conn.commit()
        conn.close()

    def get_backlog_graph(self) -> str:
        """Outputs a clean relational map of user stories and their dependencies."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, title, story_points, status FROM stories")
        stories = cursor.fetchall()
        
        cursor.execute("SELECT story_id, blocks_story_id FROM dependencies")
        dependencies = cursor.fetchall()
        
        conn.close()
        
        output = ["Agile Sprint Dependency Map:"]
        
        for s in stories:
            output.append(f"- Story [{s[0]}]: '{s[1]}' ({s[2]} Story Points) - Status: {s[3]}")
            
        if dependencies:
            output.append("\nDependencies:")
            for d in dependencies:
                output.append(f"  - Story {d[0]} blocks Story {d[1]}")
        else:
            output.append("\nNo strict story dependencies defined.")
            
        return "\n".join(output)
