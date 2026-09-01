document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const messagesContainer = document.getElementById('messagesContainer');
    const providerSelect = document.getElementById('providerSelect');
    const categorySelect = document.getElementById('categorySelect');
    const sendBtn = document.getElementById('sendBtn');
    
    const fileInput = document.getElementById('fileInput');
    const uploadZone = document.getElementById('uploadZone');
    
    const statChunks = document.getElementById('statChunks');
    const statDocs = document.getElementById('statDocs');

    const geminiKeyInput = document.getElementById('geminiKeyInput');
    const cohereKeyInput = document.getElementById('cohereKeyInput');
    const groqKeyInput = document.getElementById('groqKeyInput');
    const openrouterKeyInput = document.getElementById('openrouterKeyInput');
    const tavilyKeyInput = document.getElementById('tavilyKeyInput');
    const saveKeysBtn = document.getElementById('saveKeysBtn');
    const keyStatusBadge = document.getElementById('keyStatusBadge');
    const toggleGeminiKey = document.getElementById('toggleGeminiKey');
    const toggleCohereKey = document.getElementById('toggleCohereKey');
    const toggleGroqKey = document.getElementById('toggleGroqKey');
    const toggleOpenrouterKey = document.getElementById('toggleOpenrouterKey');
    const toggleTavilyKey = document.getElementById('toggleTavilyKey');

    const toggleApiKeyAccordion = document.getElementById('toggleApiKeyAccordion');
    const apiKeyCollapseContent = document.getElementById('apiKeyCollapseContent');
    const accordionChevron = document.getElementById('accordionChevron');

    // Auth DOM Elements
    const authOverlay = document.getElementById('authOverlay');
    const userBadgeContainer = document.getElementById('userBadgeContainer');
    const authenticatedUserLabel = document.getElementById('authenticatedUserLabel');
    const logoutBtn = document.getElementById('logoutBtn');

    const authForm = document.getElementById('authForm');
    const passphraseInput = document.getElementById('passphraseInput');
    const emailInput = document.getElementById('emailInput');
    const authError = document.getElementById('authError');
    const togglePassphrase = document.getElementById('togglePassphrase');

    // Auth Password Visibility Toggle
    if (togglePassphrase && passphraseInput) {
        togglePassphrase.addEventListener('click', () => {
            passphraseInput.type = passphraseInput.type === 'password' ? 'text' : 'password';
        });
    }

    // Handle Unified Authentication Submit (Email + Passphrase Mandatory)
    if (authForm) {
        authForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (authError) authError.classList.add('hidden');
            const email = emailInput ? emailInput.value.trim() : '';
            const passphrase = passphraseInput ? passphraseInput.value.trim() : '';

            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, passphrase })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    localStorage.setItem('auth_token', data.token);
                    localStorage.setItem('auth_user', data.user || email);
                    hideAuthOverlay();
                    showUserBadge(data.user || email);
                    fetchStats();
                } else {
                    if (authError) {
                        let errorText = 'Authentication failed.';
                        if (data && data.detail) {
                            if (Array.isArray(data.detail)) {
                                errorText = data.detail.map(e => e.msg).join(', ');
                            } else if (typeof data.detail === 'object') {
                                errorText = JSON.stringify(data.detail);
                            } else {
                                errorText = String(data.detail);
                            }
                        } else if (data && data.message) {
                            errorText = String(data.message);
                        } else if (typeof data === 'object') {
                            errorText = JSON.stringify(data);
                        } else if (data) {
                            errorText = String(data);
                        }
                        authError.textContent = errorText;
                        authError.classList.remove('hidden');
                    }
                }
            } catch (err) {
                if (authError) {
                    authError.textContent = 'Network error during authentication.';
                    authError.classList.remove('hidden');
                }
            }
        });
    }

    // Logout Handler
    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        hideUserBadge();
        showAuthOverlay();
    });

    function getAuthHeaders(baseHeaders = {}) {
        const headers = { ...baseHeaders };
        const token = localStorage.getItem('auth_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }

    const appContainer = document.querySelector('.app-container');

    function showAuthOverlay() {
        if (authOverlay) {
            authOverlay.classList.remove('hidden');
            authOverlay.style.setProperty('display', 'flex', 'important');
        }
        if (appContainer) {
            appContainer.classList.add('hidden');
            appContainer.style.setProperty('display', 'none', 'important');
        }
    }

    function hideAuthOverlay() {
        if (authOverlay) {
            authOverlay.classList.add('hidden');
            authOverlay.style.setProperty('display', 'none', 'important');
        }
        if (appContainer) {
            appContainer.classList.remove('hidden');
            appContainer.style.setProperty('display', 'flex', 'important');
        }
    }

    function showUserBadge(userStr) {
        authenticatedUserLabel.textContent = userStr || 'Technician';
        userBadgeContainer.classList.remove('hidden');
    }

    function hideUserBadge() {
        userBadgeContainer.classList.add('hidden');
    }

    // Verify session on page load
    async function checkSession() {
        const token = localStorage.getItem('auth_token');
        const user = localStorage.getItem('auth_user');
        if (!token) {
            showAuthOverlay();
            return;
        }
        try {
            const res = await fetch('/api/auth/verify', {
                headers: getAuthHeaders()
            });
            if (res.ok) {
                hideAuthOverlay();
                showUserBadge(user || 'AMPM Technician');
                fetchStats();
            } else {
                showAuthOverlay();
            }
        } catch (e) {
            showAuthOverlay();
        }
    }

    checkSession();

    // Accordion Toggle
    toggleApiKeyAccordion.addEventListener('click', () => {
        const isHidden = apiKeyCollapseContent.classList.contains('hidden');
        if (isHidden) {
            apiKeyCollapseContent.classList.remove('hidden');
            accordionChevron.classList.add('open');
        } else {
            apiKeyCollapseContent.classList.add('hidden');
            accordionChevron.classList.remove('open');
        }
    });

    // Load saved API keys from localStorage
    loadSavedApiKeys();

    // Toggle Password Visibility
    if (toggleGeminiKey) {
        toggleGeminiKey.addEventListener('click', () => {
            geminiKeyInput.type = geminiKeyInput.type === 'password' ? 'text' : 'password';
        });
    }
    if (toggleCohereKey) {
        toggleCohereKey.addEventListener('click', () => {
            cohereKeyInput.type = cohereKeyInput.type === 'password' ? 'text' : 'password';
        });
    }
    if (toggleGroqKey) {
        toggleGroqKey.addEventListener('click', () => {
            groqKeyInput.type = groqKeyInput.type === 'password' ? 'text' : 'password';
        });
    }
    if (toggleOpenrouterKey) {
        toggleOpenrouterKey.addEventListener('click', () => {
            openrouterKeyInput.type = openrouterKeyInput.type === 'password' ? 'text' : 'password';
        });
    }
    if (toggleTavilyKey) {
        toggleTavilyKey.addEventListener('click', () => {
            tavilyKeyInput.type = tavilyKeyInput.type === 'password' ? 'text' : 'password';
        });
    }

    // Save Keys Button
    if (saveKeysBtn) {
        saveKeysBtn.addEventListener('click', () => {
            const geminiVal = geminiKeyInput ? geminiKeyInput.value.trim() : '';
            const cohereVal = cohereKeyInput ? cohereKeyInput.value.trim() : '';
            const groqVal = groqKeyInput ? groqKeyInput.value.trim() : '';
            const openrouterVal = openrouterKeyInput ? openrouterKeyInput.value.trim() : '';
            const tavilyVal = tavilyKeyInput ? tavilyKeyInput.value.trim() : '';

            if (geminiVal) localStorage.setItem('gemini_api_key', geminiVal);
            else localStorage.removeItem('gemini_api_key');

            if (cohereVal) localStorage.setItem('cohere_api_key', cohereVal);
            else localStorage.removeItem('cohere_api_key');

            if (groqVal) localStorage.setItem('groq_api_key', groqVal);
            else localStorage.removeItem('groq_api_key');

            if (openrouterVal) localStorage.setItem('openrouter_api_key', openrouterVal);
            else localStorage.removeItem('openrouter_api_key');

            if (tavilyVal) localStorage.setItem('tavily_api_key', tavilyVal);
            else localStorage.removeItem('tavily_api_key');

            updateKeyBadgeStatus();
            alert('Local API Keys saved securely in your browser!');
        });
    }

    function loadSavedApiKeys() {
        const savedGemini = localStorage.getItem('gemini_api_key');
        const savedCohere = localStorage.getItem('cohere_api_key');
        const savedGroq = localStorage.getItem('groq_api_key');
        const savedOpenrouter = localStorage.getItem('openrouter_api_key');
        const savedTavily = localStorage.getItem('tavily_api_key');

        if (savedGemini && geminiKeyInput) geminiKeyInput.value = savedGemini;
        if (savedCohere && cohereKeyInput) cohereKeyInput.value = savedCohere;
        if (savedGroq && groqKeyInput) groqKeyInput.value = savedGroq;
        if (savedOpenrouter && openrouterKeyInput) openrouterKeyInput.value = savedOpenrouter;
        if (savedTavily && tavilyKeyInput) tavilyKeyInput.value = savedTavily;

        updateKeyBadgeStatus();
    }

    function updateKeyBadgeStatus() {
        const hasGemini = !!localStorage.getItem('gemini_api_key');
        const hasCohere = !!localStorage.getItem('cohere_api_key');
        const hasGroq = !!localStorage.getItem('groq_api_key');
        const hasOpenrouter = !!localStorage.getItem('openrouter_api_key');
        const hasTavily = !!localStorage.getItem('tavily_api_key');

        if (hasGemini || hasCohere || hasGroq || hasOpenrouter || hasTavily) {
            keyStatusBadge.textContent = 'Custom Key Active ✓';
            keyStatusBadge.classList.add('active');
        } else {
            keyStatusBadge.textContent = 'Server Default';
            keyStatusBadge.classList.remove('active');
        }
    }

    // Fetch initial stats
    fetchStats();

    const attachBtn = document.getElementById('attachBtn');
    const promptFileInput = document.getElementById('promptFileInput');
    const attachmentsPreviewContainer = document.getElementById('attachmentsPreviewContainer');

    let attachedImages = [];
    let attachedTextFiles = [];
    let conversationHistory = [];

    // Attach Paperclip Button Listener
    attachBtn.addEventListener('click', () => promptFileInput.click());

    promptFileInput.addEventListener('change', () => {
        if (promptFileInput.files.length) {
            handlePromptFiles(promptFileInput.files);
            promptFileInput.value = '';
        }
    });

    // Ctrl+V Clipboard Image & File Paste Listener
    document.addEventListener('paste', (e) => {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        if (!items) return;

        let hasImage = false;
        for (let item of items) {
            if (item.type.indexOf('image') !== -1) {
                hasImage = true;
                const blob = item.getAsFile();
                if (blob) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        addAttachedImage(event.target.result, 'Pasted Screenshot.png');
                    };
                    reader.readAsDataURL(blob);
                }
            }
        }
    });

    function handlePromptFiles(files) {
        for (let file of files) {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => addAttachedImage(e.target.result, file.name);
                reader.readAsDataURL(file);
            } else {
                const reader = new FileReader();
                reader.onload = (e) => addAttachedTextFile(e.target.result, file.name);
                reader.readAsText(file);
            }
        }
    }

    function addAttachedImage(dataUrl, name) {
        const id = 'img-' + Date.now() + '-' + Math.random().toString(36).substr(2, 4);
        attachedImages.push({ id, data: dataUrl, name });
        renderAttachmentPreviews();
    }

    function addAttachedTextFile(content, name) {
        const id = 'txt-' + Date.now() + '-' + Math.random().toString(36).substr(2, 4);
        attachedTextFiles.push({ id, content, name });
        renderAttachmentPreviews();
    }

    function renderAttachmentPreviews() {
        if (attachedImages.length === 0 && attachedTextFiles.length === 0) {
            attachmentsPreviewContainer.classList.add('hidden');
            attachmentsPreviewContainer.innerHTML = '';
            return;
        }

        attachmentsPreviewContainer.classList.remove('hidden');
        attachmentsPreviewContainer.innerHTML = '';

        // Render Images
        attachedImages.forEach(img => {
            const chip = document.createElement('div');
            chip.className = 'attachment-chip';
            chip.innerHTML = `
                <img src="${img.data}" class="attachment-chip-thumb" alt="Preview">
                <span>🖼️ ${escapeHtml(img.name)}</span>
                <span class="attachment-chip-remove" data-id="${img.id}" data-type="image">✕</span>
            `;
            attachmentsPreviewContainer.appendChild(chip);
        });

        // Render Text Files
        attachedTextFiles.forEach(txt => {
            const chip = document.createElement('div');
            chip.className = 'attachment-chip';
            chip.innerHTML = `
                <span>📄 ${escapeHtml(txt.name)}</span>
                <span class="attachment-chip-remove" data-id="${txt.id}" data-type="text">✕</span>
            `;
            attachmentsPreviewContainer.appendChild(chip);
        });

        // Add remove handlers
        attachmentsPreviewContainer.querySelectorAll('.attachment-chip-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.getAttribute('data-id');
                const type = e.target.getAttribute('data-type');
                if (type === 'image') {
                    attachedImages = attachedImages.filter(i => i.id !== id);
                } else {
                    attachedTextFiles = attachedTextFiles.filter(t => t.id !== id);
                }
                renderAttachmentPreviews();
            });
        });

        updateSendBtnVisibility();
    }

    // Dynamic Search Input Height and Send Button Visibility
    function updateChatInputHeight() {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 125) + 'px';
    }

    function updateSendBtnVisibility() {
        const text = chatInput.value.trim();
        const hasAttachments = (attachedImages && attachedImages.length > 0) || (attachedTextFiles && attachedTextFiles.length > 0);
        if (text.length > 0 || hasAttachments) {
            sendBtn.classList.remove('hidden');
        } else {
            sendBtn.classList.add('hidden');
        }
    }

    chatInput.addEventListener('input', () => {
        updateChatInputHeight();
        updateSendBtnVisibility();
    });

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled && (chatInput.value.trim() || attachedImages.length || attachedTextFiles.length)) {
                chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        }
    });

    const mainContent = document.getElementById('mainContent');
    const newChatBtn = document.getElementById('newChatBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    let currentChatAbortController = null;
    let currentSubmittedPrompt = '';
    let currentTypingIndicatorId = null;
    let currentUserMsgId = null;
    let isUserCancelledQuery = false;

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            isUserCancelledQuery = true;
            if (currentChatAbortController) {
                currentChatAbortController.abort();
                currentChatAbortController = null;
            }

            if (currentTypingIndicatorId) {
                removeTypingIndicator(currentTypingIndicatorId);
                currentTypingIndicatorId = null;
            }

            if (currentUserMsgId) {
                const userRow = document.getElementById(currentUserMsgId);
                if (userRow) userRow.remove();
                currentUserMsgId = null;
            }

            // Restore prompt text back into input field for editing
            if (currentSubmittedPrompt) {
                chatInput.value = currentSubmittedPrompt;
                updateChatInputHeight();
            }

            cancelBtn.classList.add('hidden');
            sendBtn.disabled = false;
            updateSendBtnVisibility();
            chatInput.focus();
        });
    }

    function activateChatMode() {
        if (mainContent && mainContent.classList.contains('initial-center-mode')) {
            mainContent.classList.remove('initial-center-mode');
            mainContent.classList.add('active-chat-mode');
            if (messagesContainer) {
                messagesContainer.classList.remove('hidden');
            }
        }
    }

    function resetToInitialMode() {
        if (currentChatAbortController) {
            currentChatAbortController.abort();
            currentChatAbortController = null;
        }

        conversationHistory = [];
        attachedImages = [];
        attachedTextFiles = [];
        renderAttachmentPreviews();
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendBtn.disabled = false;
        if (cancelBtn) cancelBtn.classList.add('hidden');
        updateSendBtnVisibility();

        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="message-row assistant">
                  <div class="message-avatar">AI</div>
                  <div class="message-bubble">
                    Hello! I am your <strong>AMPM Service POS Troubleshooting Assistant</strong>.<br><br>
                    Describe a symptom on a register, PIN pad, or server (e.g. <em>"M400 cash-back 10x error"</em> or
                    <em>"Buypass error 91 host timeout"</em>) and I will provide fast, cited instructions pulled directly from
                    internal documentation.
                  </div>
                </div>
            `;
            messagesContainer.classList.add('hidden');
        }

        if (mainContent) {
            mainContent.classList.remove('active-chat-mode');
            mainContent.classList.add('initial-center-mode');
        }

        chatInput.focus();
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', resetToInitialMode);
    }

    // Event listener for chat submission
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = chatInput.value.trim();
        if (!question && attachedImages.length === 0 && attachedTextFiles.length === 0) return;

        isUserCancelledQuery = false;
        currentSubmittedPrompt = question;

        // Abort any existing in-flight request
        if (currentChatAbortController) {
            currentChatAbortController.abort();
        }
        currentChatAbortController = new AbortController();

        // Transition from initial center search mode to bottom active chat mode
        activateChatMode();

        let displayMsg = question;
        if (attachedImages.length > 0) {
            displayMsg += `\n\n*(Attached ${attachedImages.length} Image Screenshot/File)*`;
        }
        if (attachedTextFiles.length > 0) {
            displayMsg += `\n*(Attached ${attachedTextFiles.length} Reference Document/Log)*`;
        }

        // Render user message
        currentUserMsgId = appendMessage('user', displayMsg);
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendBtn.disabled = true;
        sendBtn.classList.add('hidden');
        if (cancelBtn) cancelBtn.classList.remove('hidden');

        const currentImages = attachedImages.map(i => i.data);
        const currentAttachments = attachedTextFiles.map(t => ({ name: t.name, content: t.content }));

        // Clear attachments state
        attachedImages = [];
        attachedTextFiles = [];
        renderAttachmentPreviews();

        // Render typing indicator
        const typingId = appendTypingIndicator();
        currentTypingIndicatorId = typingId;

        // Build Headers
        let headers = { 'Content-Type': 'application/json' };
        headers = getAuthHeaders(headers);

        const savedGemini = localStorage.getItem('gemini_api_key');
        const savedCohere = localStorage.getItem('cohere_api_key');
        const savedGroq = localStorage.getItem('groq_api_key');
        const savedOpenrouter = localStorage.getItem('openrouter_api_key');
        const savedTavily = localStorage.getItem('tavily_api_key');

        if (savedGemini) headers['X-Gemini-Api-Key'] = savedGemini;
        if (savedCohere) headers['X-Cohere-Api-Key'] = savedCohere;
        if (savedGroq) headers['X-Groq-Api-Key'] = savedGroq;
        if (savedOpenrouter) headers['X-Openrouter-Api-Key'] = savedOpenrouter;
        if (savedTavily) headers['X-Tavily-Api-Key'] = savedTavily;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: headers,
                signal: currentChatAbortController.signal,
                body: JSON.stringify({
                    question: question,
                    provider: providerSelect.value,
                    category: categorySelect.value || null,
                    top_k: 5,
                    images: currentImages,
                    attachments: currentAttachments,
                    history: conversationHistory
                })
            });

            removeTypingIndicator(typingId);
            currentTypingIndicatorId = null;

            if (response.status === 401) {
                appendMessage('assistant', '🔒 **Authentication Required**: Session expired or unauthorized. Please log in.');
                showAuthOverlay();
                return;
            }

            if (response.ok) {
                const data = await response.json();
                appendMessage('assistant', data.answer, data.citations, data.provider_used, data.is_web_fallback);
                
                // Add to history
                conversationHistory.push({ role: 'user', content: question });
                conversationHistory.push({ role: 'assistant', content: data.answer });
                
                // Keep only last 6 turns (12 messages)
                if (conversationHistory.length > 12) {
                    conversationHistory = conversationHistory.slice(conversationHistory.length - 12);
                }
            } else {
                const err = await response.json();
                appendMessage('assistant', `⚠️ **Error**: ${err.detail || 'Failed to process request.'}`);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }
            updateSystemStatusBadge(false, 'System Offline');
            removeTypingIndicator(typingId);
            appendMessage('assistant', `⚠️ **Network Error**: Could not connect to API server (${error.message}).`);
        } finally {
            if (cancelBtn) cancelBtn.classList.add('hidden');
            sendBtn.disabled = false;
            updateSendBtnVisibility();
            if (!isUserCancelledQuery) {
                chatInput.focus();
            }
            currentChatAbortController = null;
            currentTypingIndicatorId = null;
            currentUserMsgId = null;
        }
    });

    // Handle PDF Drag and Drop Upload
    uploadZone.addEventListener('click', () => fileInput.click());
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            uploadFiles(e.dataTransfer.files);
        }
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            uploadFiles(fileInput.files);
        }
    });

    // Configure PDF.js Worker if available
    if (typeof pdfjsLib !== 'undefined') {
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }

    async function extractTextFromPDF(file) {
        if (typeof pdfjsLib === 'undefined') return null;
        try {
            const arrayBuffer = await file.arrayBuffer();
            const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
            const pdf = await loadingTask.promise;
            const pages = [];
            const numPages = pdf.numPages;

            for (let i = 1; i <= numPages; i++) {
                const page = await pdf.getPage(i);
                const textContent = await page.getTextContent();
                const pageText = textContent.items.map(item => item.str).join(' ').trim();
                pages.push({
                    page_number: i,
                    total_pages: numPages,
                    text: pageText,
                    topic_title: file.name.replace(/\.[^/.]+$/, "").replace(/_/g, " ")
                });
            }
            return pages;
        } catch (err) {
            console.warn('[PDF.js Warning] Client-side extraction failed, falling back to server upload:', err);
            return null;
        }
    }

    async function uploadFiles(files) {
        const validExts = ['.pdf', '.chm', '.html', '.htm', '.txt', '.log'];
        const validFiles = Array.from(files).filter(file => {
            const fileName = file.name.toLowerCase();
            return validExts.some(ext => fileName.endsWith(ext));
        });

        if (validFiles.length === 0) {
            alert('Please select valid documentation files (.pdf, .chm, .html, .htm, .txt, .log).');
            return;
        }

        // Transition from initial welcome screen to active chat view so progress is immediately visible
        activateChatMode();

        const totalFiles = validFiles.length;
        const statusId = appendMessage('assistant', `📄 *Preparing to upload & ingest ${totalFiles} file(s)...*`);

        let totalChunksAdded = 0;
        let successfulFiles = [];
        let failedFiles = [];

        for (let i = 0; i < totalFiles; i++) {
            const file = validFiles[i];
            const isPdf = file.name.toLowerCase().endsWith('.pdf');
            updateMessageContent(statusId, `📄 *Ingesting file [${i + 1}/${totalFiles}]: ${file.name}...*`);

            try {
                let res;
                let extractedPages = null;

                // For PDF files, extract text in browser to bypass cloud upload limits (4.5MB)
                if (isPdf) {
                    extractedPages = await extractTextFromPDF(file);
                }

                if (extractedPages && extractedPages.length > 0) {
                    // Send lightweight text payload (~50KB instead of 20MB)
                    res = await fetch('/api/ingest_text', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...getAuthHeaders()
                        },
                        body: JSON.stringify({
                            file_name: file.name,
                            pages: extractedPages
                        })
                    });
                } else {
                    // Fallback to standard binary upload
                    const formData = new FormData();
                    formData.append('files', file);
                    res = await fetch('/api/ingest', {
                        method: 'POST',
                        headers: getAuthHeaders(),
                        body: formData
                    });
                }

                if (res.status === 401) {
                    updateMessageContent(statusId, '🔒 **Authentication Required**: Please log in to ingest documents.');
                    showAuthOverlay();
                    return;
                }

                if (res.ok) {
                    const data = await res.json();
                    totalChunksAdded += (data.total_chunks || 0);
                    successfulFiles.push(file.name);
                } else {
                    const rawText = await res.text();
                    let errMsg = 'Ingestion failed.';
                    try {
                        const err = JSON.parse(rawText);
                        errMsg = err.detail || errMsg;
                    } catch (e) {
                        errMsg = `HTTP ${res.status}: ${rawText.substring(0, 80)}`;
                    }
                    failedFiles.push({ file: file.name, reason: errMsg });
                }
            } catch (e) {
                failedFiles.push({ file: file.name, reason: e.message });
            }
        }

        // Build final summary message
        if (failedFiles.length === 0) {
            updateMessageContent(statusId, `✅ **Batch Ingestion Complete!**\nSuccessfully processed **${successfulFiles.length} file(s)** (${totalChunksAdded} vector chunks added).`);
        } else if (successfulFiles.length > 0) {
            let summary = `⚠️ **Batch Ingestion Complete with warnings:**\n- **Success**: ${successfulFiles.length} file(s) (${totalChunksAdded} chunks)\n- **Failed**: ${failedFiles.length} file(s)\n\n**Failed Details:**\n`;
            failedFiles.forEach(f => summary += `- \`${f.file}\`: ${f.reason}\n`);
            updateMessageContent(statusId, summary);
        } else {
            let summary = `❌ **Batch Ingestion Failed for all ${failedFiles.length} file(s):**\n`;
            failedFiles.forEach(f => summary += `- \`${f.file}\`: ${f.reason}\n`);
            updateMessageContent(statusId, summary);
        }

        fetchStats();
    }

    const statusBadge = document.querySelector('.status-badge');

    function updateSystemStatusBadge(isOnline, labelText = null) {
        if (!statusBadge) return;
        if (isOnline) {
            statusBadge.classList.remove('offline');
            statusBadge.innerHTML = `<span class="status-dot"></span>${labelText || 'System Online'}`;
        } else {
            statusBadge.classList.add('offline');
            statusBadge.innerHTML = `<span class="status-dot offline-dot"></span>${labelText || 'System Offline'}`;
        }
    }

    async function fetchStats() {
        try {
            const res = await fetch('/api/stats', {
                headers: getAuthHeaders()
            });
            if (res.status === 401) {
                showAuthOverlay();
                return;
            }
            if (res.ok) {
                const data = await res.json();
                statChunks.textContent = data.total_chunks !== undefined ? data.total_chunks : (data.total_documents || 0);
                statDocs.textContent = data.collection_name || 'documents';
                updateSystemStatusBadge(true, 'System Online');
            } else {
                updateSystemStatusBadge(false, 'Server Error');
            }
        } catch (e) {
            console.warn('Could not fetch stats', e);
            updateSystemStatusBadge(false, 'System Offline');
        }
    }


    function appendMessage(sender, text, citations = [], providerUsed = '', isWebFallback = false) {
        const msgId = 'msg-' + Date.now();
        const row = document.createElement('div');
        row.className = `message-row ${sender}`;
        row.id = msgId;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? 'TECH' : 'AI';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        if (isWebFallback) {
            bubble.classList.add('web-fallback-bubble');
        }
        
        let htmlContent = '';
        
        if (isWebFallback) {
            htmlContent += `
                <div style="background: #FFF3CD; color: #856404; padding: 0.5rem; border-radius: 4px; margin-bottom: 0.8rem; border-left: 4px solid #FFEEBA; font-size: 0.9em;">
                    <strong>🌐 Answer from Web Search — Not verified company documentation.</strong>
                </div>
            `;
        }
        
        htmlContent += formatMarkdown(text);

        if (citations && citations.length > 0) {
            htmlContent += `
                <div class="citations-box">
                    <div class="citations-title">Sources & References (${providerUsed})</div>
                    <div class="citation-chips">
                        ${citations.map(c => {
                            let fileName = escapeHtml(c.file_name || 'Document');
                            let topic = c.topic_title ? escapeHtml(c.topic_title.trim()) : '';
                            let isPdf = (c.file_name || '').toLowerCase().endsWith('.pdf');
                            let chipText = '';

                            if (isWebFallback) {
                                chipText = `🔗 ${fileName}`;
                            } else if (topic && topic !== 'N/A') {
                                chipText = `📄 ${fileName} [Topic: ${topic}]`;
                            } else if (isPdf && c.page_number && c.page_number !== 'N/A') {
                                chipText = `📄 ${fileName} (Page ${c.page_number})`;
                            } else {
                                chipText = `📄 ${fileName}`;
                            }

                            return `<span class="citation-chip">${chipText}</span>`;
                        }).join('')}
                    </div>
                </div>
            `;
        }

        if (sender === 'assistant' && text && !text.includes('📄 *Uploading') && !text.includes('🔒 **Authentication Required')) {
            htmlContent += `
                <div class="feedback-toolbar" id="fb-${msgId}">
                    <button type="button" class="feedback-btn fb-thumbs-up" title="Helpful answer">👍 Helpful</button>
                    <button type="button" class="feedback-btn fb-thumbs-down" title="Not helpful">👎 Not Helpful</button>
                    <button type="button" class="feedback-btn btn-resolved fb-resolved" title="Mark as confirmed fix in knowledge base">⭐ Resolved My Issue</button>
                </div>
                <div class="feedback-toast hidden" id="toast-${msgId}"></div>
            `;
        }

        bubble.innerHTML = htmlContent;
        row.appendChild(avatar);
        row.appendChild(bubble);

        if (sender === 'assistant') {
            const fbToolbar = bubble.querySelector('.feedback-toolbar');
            if (fbToolbar) {
                const btnUp = fbToolbar.querySelector('.fb-thumbs-up');
                const btnDown = fbToolbar.querySelector('.fb-thumbs-down');
                const btnResolved = fbToolbar.querySelector('.fb-resolved');
                const toast = bubble.querySelector('.feedback-toast');

                const sendFeedback = async (type) => {
                    btnUp.disabled = true;
                    btnDown.disabled = true;
                    btnResolved.disabled = true;

                    if (type === 'thumbs_up') btnUp.classList.add('active-thumbs-up');
                    if (type === 'thumbs_down') btnDown.classList.add('active-thumbs-down');
                    if (type === 'resolved') btnResolved.classList.add('active-resolved');

                    try {
                        const userQuestion = conversationHistory.length >= 2 ? conversationHistory[conversationHistory.length - 2].content : "POS Troubleshooting Query";

                        const res = await fetch('/api/feedback', {
                            method: 'POST',
                            headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
                            body: JSON.stringify({
                                question: userQuestion,
                                answer: text,
                                provider: providerUsed || providerSelect.value,
                                feedback_type: type,
                                category: categorySelect.value || "General"
                            })
                        });

                        if (res.ok) {
                            const resData = await res.json();
                            if (toast) {
                                toast.classList.remove('hidden');
                                if (type === 'resolved') {
                                    toast.innerHTML = '✅ <strong>Confirmed Fix Saved!</strong> Solution indexed into knowledge base for future queries.';
                                    fetchStats();
                                } else {
                                    toast.innerHTML = '✨ <strong>Thank you!</strong> Your feedback helps improve troubleshooting accuracy.';
                                }
                            }
                        }
                    } catch (err) {
                        console.warn('Feedback send error', err);
                    }
                };

                btnUp.addEventListener('click', () => sendFeedback('thumbs_up'));
                btnDown.addEventListener('click', () => sendFeedback('thumbs_down'));
                btnResolved.addEventListener('click', () => sendFeedback('resolved'));
            }
        }

        messagesContainer.appendChild(row);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return msgId;
    }


    function updateMessageContent(msgId, text) {
        const msgRow = document.getElementById(msgId);
        if (msgRow) {
            const bubble = msgRow.querySelector('.message-bubble');
            if (bubble) {
                bubble.innerHTML = formatMarkdown(text);
            }
        }
    }

    function appendTypingIndicator() {
        const id = 'typing-' + Date.now();
        const row = document.createElement('div');
        row.className = 'message-row assistant';
        row.id = id;

        row.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="message-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(row);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return id;
    }

    function removeTypingIndicator(id) {
        const elem = document.getElementById(id);
        if (elem) elem.remove();
    }

    function formatMarkdown(text) {
        if (!text) return '';
        
        let lines = text.split('\n');
        let processedLines = [];
        
        for (let line of lines) {
            let trimmed = line.trim();
            
            // Remove horizontal divider lines (e.g. --- or *** or ___)
            if (/^(---|[*]{3,}|_{3,})$/.test(trimmed)) {
                continue;
            }
            
            // Transform headers (### Header, #### Header, etc.) into clean bold section headers
            if (/^#{1,6}\s+(.*)/.test(trimmed)) {
                let headerText = trimmed.replace(/^#{1,6}\s+/, '');
                processedLines.push(`<strong>${escapeHtml(headerText)}</strong>`);
                continue;
            }
            
            processedLines.push(escapeHtml(line));
        }
        
        let formatted = processedLines.join('\n');
        
        // Strip inline citations like (Source: RBSLynk ISO.pdf, p. 5) or (Source #1: ...)
        formatted = formatted.replace(/\s*\(\s*Source(?:\s*#\d+)?\s*:\s*.*?\)/gi, '');
        
        // Bold
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italics
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Inline code
        formatted = formatted.replace(/`(.*?)`/g, '<code>$1</code>');
        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }

    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
