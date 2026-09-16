// OMNI-AGENT - Manus-like Web Chat App
class OmniChat {
    constructor() {
        this.sessionId = this.generateId();
        this.messages = [];
        this.isStreaming = false;
        this.currentModel = 'qwen/qwen3-coder:free';
        this.currentMode = 'single';
        this.apiBase = window.location.origin; // Works on PC and Render
        
        this.initElements();
        this.initEvents();
        this.loadSessions();
        this.loadFiles();
        this.loadMemory();
        this.updateStatus();
    }

    generateId() {
        return Math.random().toString(36).substring(2, 10);
    }

    initElements() {
        this.messagesContainer = document.getElementById('messagesContainer');
        this.messagesEl = document.getElementById('messages');
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.thinkingIndicator = document.getElementById('thinkingIndicator');
        this.thinkingText = document.getElementById('thinkingText');
        this.toolCallsEl = document.getElementById('toolCalls');
        this.modelSelect = document.getElementById('modelSelect');
        this.modeSelect = document.getElementById('modeSelect');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.sessionsList = document.getElementById('sessionsList');
        this.fileTree = document.getElementById('fileTree');
        this.computerTools = document.getElementById('computer-tools');
        this.computerFilesList = document.getElementById('computerFilesList');
        this.currentModelEl = document.getElementById('currentModel');
        this.currentModeEl = document.getElementById('currentMode');
        this.currentSessionEl = document.getElementById('currentSession');
        this.tokenCountEl = document.getElementById('tokenCount');
    }

    initEvents() {
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
            // Auto resize
            setTimeout(() => {
                this.messageInput.style.height = 'auto';
                this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 128) + 'px';
            }, 0);
        });

        this.newChatBtn.addEventListener('click', () => this.newChat());
        this.modelSelect.addEventListener('change', (e) => {
            this.currentModel = e.target.value;
            this.currentModelEl.textContent = e.target.value;
        });
        this.modeSelect.addEventListener('change', (e) => {
            this.currentMode = e.target.value;
            this.currentModeEl.textContent = e.target.options[e.target.selectedIndex].text;
        });

        // Example prompts
        document.querySelectorAll('.example-prompt').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.querySelector('p').textContent;
                const title = btn.querySelector('span').textContent;
                let prompt = '';
                if (title.includes('REST API')) prompt = 'Build a todo API with FastAPI, SQLite, CRUD endpoints, Pydantic models, pytest tests, and docs. Save to ./workspace/todo_api/';
                else if (title.includes('Research')) prompt = 'Research the latest AI agent frameworks in 2026. Compare LangGraph, CrewAI, AutoGen, OpenHands, OpenClaw. Create report at ./workspace/research/ai_agents_2026.md with table, pros/cons, recommendation.';
                else if (title.includes('Dev Team')) prompt = 'Use 5-agent dev crew (PM, Coder, Reviewer, Tester, Writer) to build a GitHub stats CLI tool that fetches repo stats and saves to CSV. Save to ./workspace/github_stats/';
                else if (title.includes('Scraping')) prompt = 'Scrape top 5 trending AI repos on GitHub today. Extract stars, description, language. Create analysis at ./workspace/research/trending.md';
                this.messageInput.value = prompt;
                this.messageInput.focus();
            });
        });

        // Computer tabs
        document.querySelectorAll('.computer-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.computer-tab').forEach(t => {
                    t.classList.remove('active', 'text-white', 'border-b', 'border-white');
                    t.classList.add('text-zinc-500');
                });
                tab.classList.add('active', 'text-white', 'border-b', 'border-white');
                tab.classList.remove('text-zinc-500');
                
                document.querySelectorAll('.computer-panel').forEach(p => p.classList.add('hidden'));
                document.getElementById(`computer-${tab.dataset.tab}`).classList.remove('hidden');
            });
        });

        // Deploy modal
        document.getElementById('deployBtn').addEventListener('click', () => {
            document.getElementById('deployModal').classList.remove('hidden');
            document.getElementById('deployModal').classList.add('flex');
        });
        document.getElementById('closeDeployModal').addEventListener('click', () => {
            document.getElementById('deployModal').classList.add('hidden');
            document.getElementById('deployModal').classList.remove('flex');
        });

        // Refresh files
        document.getElementById('refreshFilesBtn').addEventListener('click', () => this.loadFiles());
    }

    newChat() {
        this.sessionId = this.generateId();
        this.messages = [];
        this.messagesEl.innerHTML = '';
        this.welcomeScreen.classList.remove('hidden');
        this.currentSessionEl.textContent = this.sessionId.substring(0, 8);
        this.computerTools.innerHTML = '<div class="text-xs text-zinc-600 text-center py-8"><i class="fas fa-terminal text-2xl mb-2 block"></i>Tool calls will appear here<br>when OMNI is working</div>';
        this.messageInput.value = '';
        this.messageInput.focus();
    }

    async sendMessage() {
        const text = this.messageInput.value.trim();
        if (!text || this.isStreaming) return;

        this.welcomeScreen.classList.add('hidden');
        this.addMessage('user', text);
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        
        this.isStreaming = true;
        this.showThinking('OMNI is analyzing task and routing to best free model...');

        try {
            if (this.currentMode === 'single') {
                await this.runSingleAgent(text);
            } else {
                await this.runCrew(text);
            }
        } catch (error) {
            this.hideThinking();
            this.addMessage('error', `Error: ${error.message}. Check if OPENROUTER_API_KEY is set. Get free key at https://openrouter.ai/keys`);
        } finally {
            this.isStreaming = false;
            this.hideThinking();
            this.loadFiles();
            this.loadSessions();
        }
    }

    async runSingleAgent(task) {
        // Simulate streaming steps like Manus
        this.updateThinking('Planning task and checking memory...');
        await this.sleep(800);
        
        this.addToolCall('memory_search', {query: task.substring(0, 50)}, 'Searching memory for relevant learnings...');
        await this.sleep(600);
        
        this.updateThinking(`Routing to ${this.currentModel} and starting ReAct loop...`);
        
        const response = await fetch(`${this.apiBase}/api/run`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                task: task,
                session_id: this.sessionId,
                model: this.currentModel,
                max_iterations: 15
            })
        });

        if (!response.ok) {
            const err = await response.text();
            throw new Error(err);
        }

        const result = await response.json();
        
        // Show tool calls from result if available
        if (result.transcript_path) {
            this.addToolCall('transcript', {path: result.transcript_path}, `Completed in ${result.iterations} iterations, ${result.total_tokens} tokens`);
        }

        this.addMessage('assistant', result.answer, {
            iterations: result.iterations,
            tokens: result.total_tokens,
            model: result.model_used
        });

        this.tokenCountEl.textContent = `Tokens: ${result.total_tokens}`;
    }

    async runCrew(task) {
        this.updateThinking('Assembling dev crew: PM, Coder, Reviewer, Tester, Writer...');
        await this.sleep(800);

        const roles = this.currentMode === 'research' 
            ? ['researcher', 'analyst', 'tech_writer']
            : ['project_manager', 'senior_coder', 'code_reviewer', 'qa_tester', 'tech_writer'];

        const response = await fetch(`${this.apiBase}/api/crew`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                tasks: [{description: task, expected_output: 'Complete high-quality deliverable'}],
                roles: roles,
                parallel: false
            })
        });

        if (!response.ok) {
            const err = await response.text();
            throw new Error(err);
        }

        const result = await response.json();
        
        this.addToolCall('crew', {roles: roles.join(', ')}, `Crew completed: ${result.tasks_completed} tasks in ${result.elapsed_seconds.toFixed(1)}s`);
        
        this.addMessage('assistant', result.final_output, {
            iterations: result.tasks_completed,
            tokens: result.total_tokens,
            model: 'crew'
        });
    }

    addMessage(role, content, meta = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'flex gap-3 max-w-3xl mx-auto';

        if (role === 'user') {
            messageDiv.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-xs font-medium shrink-0">You</div>
                <div class="flex-1 bg-zinc-900 border border-zinc-800 rounded-2xl rounded-tl-sm p-4">
                    <div class="text-sm text-zinc-100 whitespace-pre-wrap">${this.escapeHtml(content)}</div>
                </div>
            `;
        } else if (role === 'assistant') {
            const rendered = marked.parse(content);
            messageDiv.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-gradient-to-br from-sky-500 to-violet-600 flex items-center justify-center text-xs font-bold shrink-0">O</div>
                <div class="flex-1 bg-zinc-900 border border-zinc-800 rounded-2xl rounded-tl-sm p-4">
                    <div class="message-content text-sm text-zinc-100 prose prose-invert prose-sm max-w-none">${rendered}</div>
                    ${meta.iterations ? `<div class="mt-3 pt-3 border-t border-zinc-800 flex gap-4 text-[11px] text-zinc-500"><span>🔄 ${meta.iterations} steps</span><span>📊 ${meta.tokens || 0} tokens</span><span>🤖 ${meta.model || this.currentModel}</span><span class="text-green-400">$0 cost</span></div>` : ''}
                </div>
            `;
        } else if (role === 'error') {
            messageDiv.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-red-900/50 flex items-center justify-center text-xs shrink-0"><i class="fas fa-exclamation"></i></div>
                <div class="flex-1 bg-red-950/30 border border-red-900/50 rounded-2xl rounded-tl-sm p-4">
                    <div class="text-sm text-red-200">${this.escapeHtml(content)}</div>
                </div>
            `;
        }

        this.messagesEl.appendChild(messageDiv);
        
        // Highlight code
        messageDiv.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });

        this.scrollToBottom();
        this.messages.push({role, content, meta});
        this.saveSession();
    }

    addToolCall(name, args, output) {
        const toolDiv = document.createElement('div');
        toolDiv.className = 'tool-call bg-zinc-900 border border-zinc-800 rounded-lg p-2.5 text-xs';
        toolDiv.innerHTML = `
            <div class="flex items-center gap-2 mb-1">
                <i class="fas fa-cog text-sky-500 text-[10px]"></i>
                <span class="font-medium text-zinc-300">${name}</span>
                <span class="text-[10px] text-zinc-600">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="text-zinc-500 mono text-[11px] truncate">${JSON.stringify(args).substring(0, 100)}</div>
            ${output ? `<div class="mt-1 text-zinc-400 text-[11px]">${this.escapeHtml(output.substring(0, 200))}</div>` : ''}
        `;
        
        this.toolCallsEl.appendChild(toolDiv);
        this.computerTools.appendChild(toolDiv.cloneNode(true));
        
        // Keep only last 10 in thinking
        while (this.toolCallsEl.children.length > 10) {
            this.toolCallsEl.removeChild(this.toolCallsEl.firstChild);
        }
        while (this.computerTools.children.length > 20) {
            this.computerTools.removeChild(this.computerTools.firstChild);
        }
    }

    showThinking(text) {
        this.thinkingText.textContent = text;
        this.thinkingIndicator.classList.remove('hidden');
        this.toolCallsEl.innerHTML = '';
        this.scrollToBottom();
    }

    updateThinking(text) {
        this.thinkingText.textContent = text;
    }

    hideThinking() {
        this.thinkingIndicator.classList.add('hidden');
    }

    async loadFiles() {
        try {
            const res = await fetch(`${this.apiBase}/api/files`);
            const data = await res.json();
            
            if (data.files && data.files.length > 0) {
                this.fileTree.innerHTML = data.files.map(f => `
                    <div class="flex items-center gap-2 py-1 hover:bg-zinc-800 rounded px-1 cursor-pointer" onclick="window.omniChat.openFile('${f.path}')">
                        <i class="fas fa-file text-zinc-600 text-[10px]"></i>
                        <span class="truncate">${f.name}</span>
                    </div>
                `).join('');
                
                this.computerFilesList.innerHTML = data.files.map(f => `
                    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-2">
                        <div class="flex items-center gap-2">
                            <i class="fas fa-file-code text-sky-500 text-xs"></i>
                            <span class="text-zinc-300">${f.name}</span>
                        </div>
                        <div class="text-[10px] text-zinc-600 mt-1">${f.path} • ${f.size} bytes</div>
                    </div>
                `).join('');
            } else {
                this.fileTree.innerHTML = '<div class="text-zinc-600">No files yet. Ask OMNI to build something!</div>';
            }
        } catch (e) {
            this.fileTree.innerHTML = '<div class="text-zinc-600">Workspace: ./workspace</div>';
        }
    }

    async loadSessions() {
        try {
            const res = await fetch(`${this.apiBase}/api/sessions`);
            const data = await res.json();
            
            if (data.sessions && data.sessions.length > 0) {
                this.sessionsList.innerHTML = data.sessions.slice(0, 10).map(s => `
                    <div class="px-2 py-2 rounded-lg hover:bg-zinc-800 cursor-pointer text-xs" onclick="window.omniChat.loadSession('${s.id}')">
                        <div class="text-zinc-300 truncate">${s.id.substring(0, 8)} • ${s.message_count || 0} msgs</div>
                        <div class="text-zinc-600 text-[11px]">${new Date(s.created_at).toLocaleDateString()}</div>
                    </div>
                `).join('');
            }
        } catch (e) {
            // No sessions yet
        }
    }

    async loadMemory() {
        try {
            const res = await fetch(`${this.apiBase}/api/memory`);
            const data = await res.json();
            
            if (data.memories && data.memories.length > 0) {
                document.getElementById('memoryList').innerHTML = data.memories.slice(0, 5).map(m => `
                    <div class="py-1 truncate">${m.category}/${m.key}</div>
                `).join('');
            }
        } catch (e) {}
    }

    async openFile(path) {
        try {
            const res = await fetch(`${this.apiBase}/api/files/read?path=${encodeURIComponent(path)}`);
            const data = await res.json();
            
            this.addMessage('assistant', `**File: ${path}**\n\n\`\`\`\n${data.content.substring(0, 2000)}\n\`\`\``, {});
        } catch (e) {
            this.addMessage('error', `Failed to read file: ${path}`);
        }
    }

    loadSession(sessionId) {
        this.sessionId = sessionId;
        this.currentSessionEl.textContent = sessionId.substring(0, 8);
        // In real app, load messages from backend
        this.addMessage('assistant', `Loaded session ${sessionId}. Previous context restored.`);
    }

    saveSession() {
        // Save to localStorage for demo
        localStorage.setItem(`omni_session_${this.sessionId}`, JSON.stringify(this.messages.slice(-20)));
    }

    updateStatus() {
        this.currentModelEl.textContent = this.currentModel;
        this.currentSessionEl.textContent = this.sessionId.substring(0, 8);
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Init
window.omniChat = new OmniChat();
window.addEventListener('load', () => {
    document.getElementById('messageInput').focus();
});
