import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  Layers, 
  Terminal, 
  CheckCircle, 
  Folder, 
  FileCode, 
  Settings, 
  Upload,
  Cpu,
  PlusCircle,
  FileText,
  AlertTriangle
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

function App() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [projectData, setProjectData] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState("requirements");
  const [selectedSubFile, setSelectedSubFile] = useState(null);
  
  // Custom context upload state
  const [uploadAgent, setUploadAgent] = useState("ba");
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");

  const chatEndRef = useRef(null);
  const pollingRef = useRef(null);

  // Fetch all projects on mount
  useEffect(() => {
    fetchProjects();
    return () => stopPolling();
  }, []);

  // Poll project details if selected project is in progress
  useEffect(() => {
    if (!selectedProjectId) {
      setProjectData(null);
      return;
    }
    fetchProjectDetails(selectedProjectId);
    
    // Set up polling
    stopPolling();
    pollingRef.current = setInterval(() => {
      fetchProjectDetails(selectedProjectId, true);
    }, 2000);

    return () => stopPolling();
  }, [selectedProjectId]);

  // Scroll chats to bottom when log updates
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [projectData?.logs]);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      const data = await res.json();
      setProjects(data);
    } catch (e) {
      console.error("Failed to fetch projects list", e);
    }
  };

  const fetchProjectDetails = async (id, isSilent = false) => {
    try {
      const res = await fetch(`${API_BASE}/project/status/${id}`);
      if (!res.ok) throw new Error("Project details not found");
      const data = await res.json();
      setProjectData(data);
      
      // Stop polling if complete or failed
      if (data.status === "Completed" || data.status === "Failed" || data.status.includes("Disk")) {
        stopPolling();
        fetchProjects(); // Update sidebar status
      }
    } catch (e) {
      console.error("Failed to fetch project details", e);
      if (!isSilent) stopPolling();
    }
  };

  const startNewSprint = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/project/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: prompt })
      });
      const data = await res.json();
      if (data.status === "success") {
        setPrompt("");
        setSelectedProjectId(data.project_id);
        fetchProjects();
      }
    } catch (e) {
      console.error("Failed to start project sprint", e);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    
    setUploadStatus("Uploading & Indexing...");
    const formData = new FormData();
    formData.append("file", uploadFile);
    
    try {
      const res = await fetch(`${API_BASE}/project/upload_knowledge?agent=${uploadAgent}`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.status === "success") {
        setUploadStatus("Context successfully indexed!");
        setUploadFile(null);
        // Clear file input
        document.getElementById("file-input").value = "";
      } else {
        setUploadStatus("Upload failed");
      }
    } catch (e) {
      setUploadStatus("Upload error occurred.");
    }
  };

  // Helper to set badge classes based on agent names
  const getBadgeClass = (sender) => {
    const s = sender.toLowerCase();
    if (s.includes("system")) return "system";
    if (s.includes("analyst") || s.includes("ba")) return "ba";
    if (s.includes("architect")) return "architect";
    if (s.includes("developer") || s.includes("dev")) return "developer";
    if (s.includes("qa") || s.includes("engineer")) return "qa";
    if (s.includes("devops")) return "devops";
    if (s.includes("release") || s.includes("manager")) return "release";
    return "system";
  };

  return (
    <div className="app-container">
      {/* HEADER */}
      <header className="app-header glass-panel">
        <div className="brand">
          <span className="logo-icon">🤖</span>
          <div className="brand-text">
            <h1>ApexSoft Solutions</h1>
            <p>Multi-Agent Agile SDLC System</p>
          </div>
        </div>
        <div className="header-meta" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span className="agent-badge release" style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={14} /> ACTIVE MODEL: GEMINI 1.5
          </span>
        </div>
      </header>

      {/* WORKSPACE GRID */}
      <main className="workspace-grid">
        
        {/* COLUMN 1: SIDEBAR (PROJECT LIST & RAG LOADER) */}
        <section className="sidebar-col glass-panel">
          <div className="column-header">
            <Folder size={18} style={{ color: 'var(--accent-secondary)' }} />
            <h2>Projects Workspace</h2>
          </div>
          
          <div className="scroll-content" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div className="projects-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {projects.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '20px 0' }}>
                  No projects generated yet.
                </div>
              ) : (
                projects.map((proj) => (
                  <div 
                    key={proj.id} 
                    onClick={() => setSelectedProjectId(proj.id)}
                    className={`subfile-item ${selectedProjectId === proj.id ? 'active' : ''}`}
                    style={{ 
                      padding: '12px', 
                      borderRadius: '8px', 
                      display: 'flex', 
                      flexDirection: 'column', 
                      gap: '4px',
                      cursor: 'pointer',
                      background: selectedProjectId === proj.id ? 'rgba(2, 132, 199, 0.12)' : 'rgba(255, 255, 255, 0.02)'
                    }}
                  >
                    <span style={{ fontWeight: '600', fontSize: '13px', color: 'var(--text-primary)' }}>{proj.name}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Status: {proj.status}</span>
                  </div>
                ))
              )}
            </div>

            {/* RAG Context Ingest Tool */}
            <div className="glass-panel" style={{ marginTop: 'auto', padding: '16px', border: '1px dashed var(--border-glass)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <Upload size={14} style={{ color: 'var(--accent-primary)' }} />
                <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase' }}>Ingest RAG Context</span>
              </div>
              <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <select 
                  className="text-input" 
                  style={{ padding: '6px', fontSize: '12px' }}
                  value={uploadAgent}
                  onChange={(e) => setUploadAgent(e.target.value)}
                >
                  <option value="ba">BA Agent DB</option>
                  <option value="architect">Architect Agent DB</option>
                  <option value="developer">Developer Agent DB</option>
                  <option value="qa">QA Agent DB</option>
                  <option value="devops">DevOps Agent DB</option>
                </select>
                <input 
                  type="file" 
                  id="file-input"
                  style={{ fontSize: '11px', color: 'var(--text-secondary)' }}
                  onChange={(e) => setUploadFile(e.files ? e.files[0] : e.target.files[0])}
                  required
                />
                <button type="submit" className="btn" style={{ padding: '6px 12px', fontSize: '11px', width: '100%', justifyContent: 'center' }}>
                  Index Document
                </button>
                {uploadStatus && (
                  <span style={{ fontSize: '10px', color: 'var(--accent-cyan)', marginTop: '4px', textAlign: 'center' }}>
                    {uploadStatus}
                  </span>
                )}
              </form>
            </div>
          </div>
        </section>

        {/* COLUMN 2: CENTER (AGILE KANBAN & FEED) */}
        <section className="center-col" style={{ gap: '16px' }}>
          
          {/* New Sprint Input Form */}
          <div className="glass-panel" style={{ padding: '16px' }}>
            <form onSubmit={startNewSprint} style={{ display: 'flex', gap: '10px' }}>
              <input 
                type="text" 
                className="text-input"
                placeholder="Describe your next project feature (e.g. 'Build a user directory API with SQLite')..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={isSubmitting}
              />
              <button type="submit" className="btn" disabled={isSubmitting || !prompt.trim()}>
                <Play size={14} /> Start Sprint
              </button>
            </form>
          </div>

          {/* Kanban Board */}
          <div className="glass-panel" style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '55%' }}>
            <div className="column-header">
              <Layers size={18} style={{ color: 'var(--accent-amber)' }} />
              <h2>Sprint Kanban Board</h2>
              {projectData && (
                <span className="agent-badge system" style={{ marginLeft: 'auto' }}>
                  PIPELINE: {projectData.status}
                </span>
              )}
            </div>
            <div className="scroll-content">
              <div className="kanban-grid">
                {/* Backlog */}
                <div className="kanban-col">
                  <h3>To Do <span className="card-count">{projectData?.kanban?.backlog?.length || 0}</span></h3>
                  <div className="kanban-cards">
                    {projectData?.kanban?.backlog?.map(card => (
                      <div key={card.id} className="kanban-card">
                        <div className="kanban-card-id">{card.id}</div>
                        <div className="kanban-card-title">{card.title}</div>
                      </div>
                    ))}
                  </div>
                </div>
                {/* In Progress */}
                <div className="kanban-col">
                  <h3>In Progress <span className="card-count">{projectData?.kanban?.in_progress?.length || 0}</span></h3>
                  <div className="kanban-cards">
                    {projectData?.kanban?.in_progress?.map(card => (
                      <div key={card.id} className="kanban-card" style={{ borderLeft: '3px solid var(--accent-secondary)' }}>
                        <div className="kanban-card-id">{card.id}</div>
                        <div className="kanban-card-title">{card.title}</div>
                      </div>
                    ))}
                  </div>
                </div>
                {/* Code Review */}
                <div className="kanban-col">
                  <h3>Review <span className="card-count">{projectData?.kanban?.code_review?.length || 0}</span></h3>
                  <div className="kanban-cards">
                    {projectData?.kanban?.code_review?.map(card => (
                      <div key={card.id} className="kanban-card" style={{ borderLeft: '3px solid var(--accent-primary)' }}>
                        <div className="kanban-card-id">{card.id}</div>
                        <div className="kanban-card-title">{card.title}</div>
                      </div>
                    ))}
                  </div>
                </div>
                {/* Done */}
                <div className="kanban-col">
                  <h3>Done <span className="card-count">{projectData?.kanban?.done?.length || 0}</span></h3>
                  <div className="kanban-cards">
                    {projectData?.kanban?.done?.map(card => (
                      <div key={card.id} className="kanban-card" style={{ borderLeft: '3px solid var(--accent-green)', opacity: 0.8 }}>
                        <div className="kanban-card-id">{card.id}</div>
                        <div className="kanban-card-title">{card.title}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Slack-like Agent Conversation stream */}
          <div className="glass-panel" style={{ height: '35%', display: 'flex', flexDirection: 'column' }}>
            <div className="column-header">
              <Terminal size={18} style={{ color: 'var(--accent-primary)' }} />
              <h2>Agent Feed</h2>
            </div>
            <div className="scroll-content" style={{ background: 'rgba(0, 0, 0, 0.1)' }}>
              {!projectData || projectData.logs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '30px 0' }}>
                  No agent conversation streaming yet. Submit a prompt or select a project directory to watch development.
                </div>
              ) : (
                projectData.logs.map((log, i) => (
                  <div key={i} className={`chat-bubble ${getBadgeClass(log.sender)}`}>
                    <div className="chat-header">
                      <span className={`agent-badge ${getBadgeClass(log.sender)}`}>{log.sender}</span>
                      <span className="chat-time">{log.timestamp}</span>
                    </div>
                    <div className="chat-body">{log.message}</div>
                  </div>
                ))
              )}
              <div ref={chatEndRef} />
            </div>
          </div>

        </section>

        {/* COLUMN 3: RIGHT (CODE VIEWER & ARTIFACT VIEW) */}
        <section className="right-col glass-panel" style={{ height: '100%' }}>
          <div className="artifact-tab-bar">
            <button 
              className={`artifact-tab ${activeTab === 'requirements' ? 'active' : ''}`}
              onClick={() => setActiveTab('requirements')}
            >
              <FileText size={14} /> BA
            </button>
            <button 
              className={`artifact-tab ${activeTab === 'architecture' ? 'active' : ''}`}
              onClick={() => setActiveTab('architecture')}
            >
              <Layers size={14} /> Arch
            </button>
            <button 
              className={`artifact-tab ${activeTab === 'code' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('code');
                const fileKeys = Object.keys(projectData?.artifacts?.code || {});
                if (fileKeys.length > 0 && !selectedSubFile) {
                  setSelectedSubFile(fileKeys[0]);
                }
              }}
            >
              <FileCode size={14} /> Code
            </button>
            <button 
              className={`artifact-tab ${activeTab === 'tests' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('tests');
                const testKeys = Object.keys(projectData?.artifacts?.tests || {});
                if (testKeys.length > 0 && !selectedSubFile) {
                  setSelectedSubFile(testKeys[0]);
                }
              }}
            >
              <CheckCircle size={14} /> QA
            </button>
            <button 
              className={`artifact-tab ${activeTab === 'devops' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('devops');
                const devopsKeys = Object.keys(projectData?.artifacts?.devops || {});
                if (devopsKeys.length > 0 && !selectedSubFile) {
                  setSelectedSubFile(devopsKeys[0]);
                }
              }}
            >
              <Settings size={14} /> DevOps
            </button>
            <button 
              className={`artifact-tab ${activeTab === 'release' ? 'active' : ''}`}
              onClick={() => setActiveTab('release')}
            >
              <CheckCircle size={14} /> Release
            </button>
          </div>

          {/* Sub-file browser for code/tests/devops tabs */}
          {projectData && ['code', 'tests', 'devops'].includes(activeTab) && (
            <div className="subfile-list">
              {Object.keys(projectData.artifacts[activeTab] || {}).map((filepath) => (
                <span 
                  key={filepath}
                  className={`subfile-item ${selectedSubFile === filepath ? 'active' : ''}`}
                  onClick={() => setSelectedSubFile(filepath)}
                >
                  {filepath.split('/').pop()}
                </span>
              ))}
            </div>
          )}

          {/* Code Viewer Body */}
          <div className="editor-wrapper">
            {!projectData ? (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '100px' }}>
                Select a project to inspect source code.
              </div>
            ) : (
              activeTab === "requirements" ? (
                <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>
                  {projectData.artifacts.requirements || "BA Agent requirements doc is pending..."}
                </div>
              ) : activeTab === "architecture" ? (
                <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>
                  {projectData.artifacts.architecture || "Architect design doc is pending..."}
                </div>
              ) : activeTab === "release" ? (
                <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>
                  {projectData.artifacts.release || "Release Notes are pending..."}
                </div>
              ) : (
                // For files tab (code, tests, devops)
                projectData.artifacts[activeTab] && selectedSubFile && projectData.artifacts[activeTab][selectedSubFile] ? (
                  <div>
                    <div style={{ paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.05)', marginBottom: '10px', color: 'var(--accent-cyan)' }}>
                      // Location: {selectedSubFile}
                    </div>
                    <pre style={{ color: '#38bdf8', overflowX: 'auto' }}>
                      {projectData.artifacts[activeTab][selectedSubFile]}
                    </pre>
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
                    No generated files yet in this tab.
                  </div>
                )
              )}
            )}
          </div>
        </section>

      </main>
    </div>
  );
}

export default App;
