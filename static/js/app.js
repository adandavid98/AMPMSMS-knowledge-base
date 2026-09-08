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
                    loadSharedConversationFromHash();
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
                loadSharedConversationFromHash();
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
        if (sendBtn) sendBtn.disabled = false;
        updateChatInputHeight();
        updateSendBtnVisibility();
    });

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (chatInput.value.trim() || attachedImages.length || attachedTextFiles.length) {
                handleChatSubmit(e);
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
        if (window.location.hash && window.location.hash.includes('#share=')) {
            history.replaceState(null, '', window.location.pathname);
        }
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

    // Dedicated chat submission handler
    async function handleChatSubmit(e) {
        if (e) {
            if (typeof e.preventDefault === 'function') e.preventDefault();
            if (typeof e.stopPropagation === 'function') e.stopPropagation();
        }
        const question = chatInput.value.trim();
        if (!question && attachedImages.length === 0 && attachedTextFiles.length === 0) return;
        if (sendBtn && sendBtn.disabled) return;

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
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.classList.add('hidden');
        }
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
                    provider: providerSelect ? providerSelect.value : 'gemini',
                    category: categorySelect ? (categorySelect.value || null) : null,
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
                let errDetail = '';
                try {
                    const err = await response.json();
                    errDetail = err.detail || err.message || JSON.stringify(err);
                } catch (jsonErr) {
                    try {
                        const rawText = await response.text();
                        // Strip raw HTML tags if Vercel returned an error page
                        errDetail = rawText.replace(/<[^>]*>?/gm, ' ').replace(/\s+/g, ' ').trim().slice(0, 300);
                    } catch (txtErr) {
                        errDetail = response.statusText || 'Server error';
                    }
                }
                appendMessage('assistant', `⚠️ **Error (${response.status})**: ${errDetail || 'Failed to process request.'}`);
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
            if (sendBtn) {
                sendBtn.disabled = false;
                updateSendBtnVisibility();
            }
            if (!isUserCancelledQuery) {
                chatInput.focus();
            }
            currentChatAbortController = null;
            currentTypingIndicatorId = null;
            currentUserMsgId = null;
        }
    }

    // Attach submit listeners to form and send button
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            if (e && e.preventDefault) e.preventDefault();
            handleChatSubmit(e);
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', (e) => {
            if (e && e.preventDefault) e.preventDefault();
            handleChatSubmit(e);
        });
    }

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

    // Global Floating Toast Notification
    function showToast(msg, duration = 2500) {
        let toast = document.getElementById('globalToast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'globalToast';
            toast.className = 'global-toast';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.classList.remove('hidden', 'fade-out');
        toast.classList.add('visible');
        clearTimeout(toast._timeout);
        toast._timeout = setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => {
                toast.classList.remove('visible', 'fade-out');
                toast.classList.add('hidden');
            }, 300);
        }, duration);
    }

    // Robust Clipboard Copy with Fallback
    async function copyToClipboard(text) {
        if (!text) return false;
        if (navigator.clipboard && window.isSecureContext) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch (err) {
                console.warn('navigator.clipboard failed, attempting fallback', err);
            }
        }
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.top = '-9999px';
        textArea.style.left = '-9999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        let success = false;
        try {
            success = document.execCommand('copy');
        } catch (err) {
            success = false;
        }
        document.body.removeChild(textArea);
        return success;
    }

    // Format Entire Conversation as Markdown Text
    function getFormattedConversation() {
        if (!conversationHistory || conversationHistory.length === 0) {
            return 'No conversation history found.';
        }
        return conversationHistory.map(m => {
            const speaker = m.role === 'user' ? 'Technician' : 'AMPM POS Troubleshooting Assistant';
            return `### ${speaker}\n${m.content}\n`;
        }).join('\n---\n\n');
    }

    // Generate Shareable URL Hash (#share=...)
    function generateShareLink() {
        const payload = {
            v: 1,
            ts: Date.now(),
            history: conversationHistory
        };
        const jsonStr = JSON.stringify(payload);
        const encoded = btoa(encodeURIComponent(jsonStr).replace(/%([0-9A-F]{2})/g, (match, p1) => {
            return String.fromCharCode('0x' + p1);
        }));
        return window.location.origin + window.location.pathname + '#share=' + encodeURIComponent(encoded);
    }

    // Load and Render Shared Conversation from URL Hash
    function loadSharedConversationFromHash() {
        const hash = window.location.hash;
        if (!hash || !hash.includes('#share=')) return;
        const encodedPart = hash.split('#share=')[1];
        if (!encodedPart) return;

        try {
            const rawB64 = decodeURIComponent(encodedPart);
            const decodedStr = decodeURIComponent(Array.prototype.map.call(atob(rawB64), (c) => {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            const data = JSON.parse(decodedStr);
            if (data && Array.isArray(data.history) && data.history.length > 0) {
                activateChatMode();
                if (messagesContainer) {
                    messagesContainer.innerHTML = '';
                    
                    // Subtle info banner (NO duplicate "Start New Chat" button, existing header button is used)
                    const banner = document.createElement('div');
                    banner.className = 'shared-chat-notice';
                    banner.innerHTML = '<span>🔗 <strong>Viewing Shared Troubleshooting Session</strong> (Use "+ New Chat" above to start a fresh chat)</span>';
                    messagesContainer.appendChild(banner);

                    conversationHistory = [];
                    data.history.forEach(msg => {
                        conversationHistory.push({ role: msg.role, content: msg.content });
                        appendMessage(msg.role, msg.content, msg.citations || [], msg.provider || '');
                    });

                    messagesContainer.classList.remove('hidden');
                }
                showToast('Shared conversation loaded');
            }
        } catch (err) {
            console.warn('Failed to load shared conversation from hash:', err);
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
                    <button type="button" class="msg-action-btn copy-msg-btn" title="Copy response text" aria-label="Copy response">
                        <svg class="copy-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                    </button>
                    <div class="msg-dropdown-container">
                        <button type="button" class="msg-action-btn dots-msg-btn" title="More options" aria-label="More options">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                                <circle cx="5" cy="12" r="2"></circle>
                                <circle cx="12" cy="12" r="2"></circle>
                                <circle cx="19" cy="12" r="2"></circle>
                            </svg>
                        </button>
                        <div class="msg-dropdown-menu hidden">
                            <button type="button" class="msg-dropdown-item share-chat-btn">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
                                <span>Share Conversation</span>
                            </button>
                            <button type="button" class="msg-dropdown-item copy-all-btn">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
                                <span>Copy Entire Chat</span>
                            </button>
                            <button type="button" class="msg-dropdown-item pdf-chat-btn">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                                <span>Save as PDF / Print</span>
                            </button>
                        </div>
                    </div>
                    <div class="action-divider"></div>
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
            // Copy Message Button Handler
            const copyBtn = bubble.querySelector('.copy-msg-btn');
            if (copyBtn) {
                copyBtn.addEventListener('click', async () => {
                    const ok = await copyToClipboard(text);
                    if (ok) {
                        copyBtn.classList.add('copied');
                        copyBtn.innerHTML = `
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        `;
                        showToast('✓ Response copied to clipboard!');
                        setTimeout(() => {
                            copyBtn.classList.remove('copied');
                            copyBtn.innerHTML = `
                                <svg class="copy-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                </svg>
                            `;
                        }, 2000);
                    }
                });
            }

            // 3-Dots Dropdown Menu Handlers
            const dotsBtn = bubble.querySelector('.dots-msg-btn');
            const dropdownMenu = bubble.querySelector('.msg-dropdown-menu');
            if (dotsBtn && dropdownMenu) {
                dotsBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    document.querySelectorAll('.msg-dropdown-menu').forEach(m => {
                        if (m !== dropdownMenu) m.classList.add('hidden');
                    });
                    dropdownMenu.classList.toggle('hidden');
                });

                const shareBtn = dropdownMenu.querySelector('.share-chat-btn');
                if (shareBtn) {
                    shareBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        dropdownMenu.classList.add('hidden');
                        const shareUrl = generateShareLink();
                        const ok = await copyToClipboard(shareUrl);
                        if (ok) {
                            showToast('🔗 Share link copied to clipboard!');
                        }
                    });
                }

                const copyAllBtn = dropdownMenu.querySelector('.copy-all-btn');
                if (copyAllBtn) {
                    copyAllBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        dropdownMenu.classList.add('hidden');
                        const formattedChat = getFormattedConversation();
                        const ok = await copyToClipboard(formattedChat);
                        if (ok) {
                            showToast('📋 Entire conversation copied to clipboard!');
                        }
                    });
                }

                const pdfBtn = dropdownMenu.querySelector('.pdf-chat-btn');
                if (pdfBtn) {
                    pdfBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        dropdownMenu.classList.add('hidden');
                        window.print();
                    });
                }
            }

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
                                category: categorySelect ? (categorySelect.value || "General") : "General"
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

    // Dismiss 3-dots dropdowns on outside click or Escape
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.msg-dropdown-container')) {
            document.querySelectorAll('.msg-dropdown-menu').forEach(m => m.classList.add('hidden'));
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.msg-dropdown-menu').forEach(m => m.classList.add('hidden'));
        }
    });

    window.addEventListener('hashchange', () => {
        loadSharedConversationFromHash();
    });

    // Check for shared conversation on startup
    loadSharedConversationFromHash();
});
