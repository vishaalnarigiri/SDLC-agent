import os
import glob
import logging
from dotenv import load_dotenv
import chromadb
import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class GeminiEmbeddingFunction:
    """Custom embedding function for ChromaDB utilizing Gemini APIs."""
    def __init__(self, api_key):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
            self.model = "models/text-embedding-004"
            logger.info("Using Gemini text-embedding-004 for RAG indexing.")
        else:
            logger.warning("No GEMINI_API_KEY found! Using mock embeddings for dry-run testing.")
            
    def __call__(self, input):
        # input is a list of documents
        if not self.api_key:
            # Mock embeddings (vector length 768)
            import random
            return [[random.random() for _ in range(768)] for _ in input]
        try:
            response = genai.embed_content(
                model=self.model,
                content=input,
                task_type="retrieval_document"
            )
            # Response['embedding'] contains the list of floats
            embeddings = response.get("embedding", [])
            # Wait, if input is a list of strings, embed_content returns a list of embeddings
            # (or we may have to handle single vs list responses depending on the API version)
            if embeddings and isinstance(embeddings[0], float):
                # Single string was embedded, wrap in a list
                return [embeddings]
            return embeddings
        except Exception as e:
            logger.error(f"Error calling Gemini Embedding API: {e}. Falling back to mock embeddings.")
            import random
            return [[random.random() for _ in range(768)] for _ in input]

def chunk_markdown(file_path):
    """Chunks markdown files by sections (split by headers #)."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    sections = content.split("\n#")
    chunks = []
    for i, sec in enumerate(sections):
        if not sec.strip():
            continue
        # Restore header formatting except for the first one if it didn't start with #
        prefix = "#" if i > 0 or content.startswith("#") else ""
        chunk = prefix + sec
        chunks.append(chunk.strip())
    
    return chunks

def bootstrap():
    # Initialize Chroma client
    # We will use PersistentClient to save files locally in backend/chroma_db
    chroma_dir = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=chroma_dir)
    
    embedding_fn = GeminiEmbeddingFunction(GEMINI_API_KEY)
    
    # We define our agent collections
    collections_map = {
        "ba": "ba_rules",
        "architect": "architect_rules",
        "developer": "developer_rules",
        "qa": "qa_rules",
        "devops": "devops_rules"
    }
    
    base_dir = os.path.dirname(__file__)
    knowledge_base_dir = os.path.join(base_dir, "knowledge_base")
    
    for agent_name, col_name in collections_map.items():
        logger.info(f"Indexing RAG data for agent: {agent_name} -> Collection: {col_name}")
        
        # Reset or create collection
        try:
            client.delete_collection(name=col_name)
            logger.info(f"Cleared existing collection {col_name}")
        except Exception:
            pass # Collection didn't exist yet
            
        collection = client.create_collection(
            name=col_name,
            embedding_function=embedding_fn
        )
        
        # Find all markdown files in the agent's folder
        agent_kb_path = os.path.join(knowledge_base_dir, agent_name)
        kb_files = glob.glob(os.path.join(agent_kb_path, "*.md"))
        
        # Check custom files in custom subdirectory if it exists
        custom_kb_path = os.path.join(knowledge_base_dir, "custom")
        if os.path.exists(custom_kb_path):
            kb_files.extend(glob.glob(os.path.join(custom_kb_path, f"*{agent_name}*.md")))
            kb_files.extend(glob.glob(os.path.join(custom_kb_path, f"*{agent_name}*.txt")))
            
        if not kb_files:
            logger.warning(f"No files found to index for agent {agent_name} in {agent_kb_path}")
            # Add a placeholder document so ChromaDB doesn't throw an error on empty collection query
            collection.add(
                documents=[f"Default placeholder rule for {agent_name} agent."],
                ids=[f"{agent_name}_placeholder"],
                metadatas=[{"source": "default"}]
            )
            continue
            
        for filepath in kb_files:
            filename = os.path.basename(filepath)
            logger.info(f"Processing knowledge source: {filename}")
            
            chunks = chunk_markdown(filepath)
            documents = []
            ids = []
            metadatas = []
            
            for idx, chunk in enumerate(chunks):
                documents.append(chunk)
                ids.append(f"{filename}_chunk_{idx}")
                metadatas.append({"source": filename, "filepath": filepath})
                
            if documents:
                collection.add(
                    documents=documents,
                    ids=ids,
                    metadatas=metadatas
                )
                logger.info(f"Successfully indexed {len(documents)} chunks from {filename}")

    logger.info("RAG bootstrapping complete!")

if __name__ == "__main__":
    bootstrap()
