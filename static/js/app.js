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
    const groqKeyInput = document.getElementById('groqKeyInput');
    const tavilyKeyInput = document.getElementById('tavilyKeyInput');
    const saveKeysBtn = document.getElementById('saveKeysBtn');
    const keyStatusBadge = document.getElementById('keyStatusBadge');
    const toggleGeminiKey = document.getElementById('toggleGeminiKey');
    const toggleGroqKey = document.getElementById('toggleGroqKey');
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
    toggleGeminiKey.addEventListener('click', () => {
        geminiKeyInput.type = geminiKeyInput.type === 'password' ? 'text' : 'password';
    });
    toggleGroqKey.addEventListener('click', () => {
        groqKeyInput.type = groqKeyInput.type === 'password' ? 'text' : 'password';
    });
    toggleTavilyKey.addEventListener('click', () => {
        tavilyKeyInput.type = tavilyKeyInput.type === 'password' ? 'text' : 'password';
    });

    // Save Keys Button
    saveKeysBtn.addEventListener('click', () => {
        const geminiVal = geminiKeyInput.value.trim();
        const groqVal = groqKeyInput.value.trim();
        const tavilyVal = tavilyKeyInput.value.trim();

        if (geminiVal) localStorage.setItem('gemini_api_key', geminiVal);
        else localStorage.removeItem('gemini_api_key');

        if (groqVal) localStorage.setItem('groq_api_key', groqVal);
        else localStorage.removeItem('groq_api_key');

        if (tavilyVal) localStorage.setItem('tavily_api_key', tavilyVal);
        else localStorage.removeItem('tavily_api_key');

        updateKeyBadgeStatus();
        alert('Local API Keys saved securely in your browser!');
    });

    function loadSavedApiKeys() {
        const savedGemini = localStorage.getItem('gemini_api_key');
        const savedGroq = localStorage.getItem('groq_api_key');
        const savedTavily = localStorage.getItem('tavily_api_key');

        if (savedGemini) geminiKeyInput.value = savedGemini;
        if (savedGroq) groqKeyInput.value = savedGroq;
        if (savedTavily) tavilyKeyInput.value = savedTavily;

        updateKeyBadgeStatus();
    }

    function updateKeyBadgeStatus() {
        const hasGemini = !!localStorage.getItem('gemini_api_key');
        const hasGroq = !!localStorage.getItem('groq_api_key');
        const hasTavily = !!localStorage.getItem('tavily_api_key');

        if (hasGemini || hasGroq || hasTavily) {
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
    }

    // Event listener for chat submission
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = chatInput.value.trim();
        if (!question && attachedImages.length === 0 && attachedTextFiles.length === 0) return;

        let displayMsg = question;
        if (attachedImages.length > 0) {
            displayMsg += `\n\n*(Attached ${attachedImages.length} Image Screenshot/File)*`;
        }
        if (attachedTextFiles.length > 0) {
            displayMsg += `\n*(Attached ${attachedTextFiles.length} Reference Document/Log)*`;
        }

        // Render user message
        appendMessage('user', displayMsg);
        chatInput.value = '';
        sendBtn.disabled = true;

        const currentImages = attachedImages.map(i => i.data);
        const currentAttachments = attachedTextFiles.map(t => ({ name: t.name, content: t.content }));

        // Clear attachments state
        attachedImages = [];
        attachedTextFiles = [];
        renderAttachmentPreviews();

        // Render typing indicator
        const typingId = appendTypingIndicator();

        // Build Headers
        let headers = { 'Content-Type': 'application/json' };
        headers = getAuthHeaders(headers);

        const savedGemini = localStorage.getItem('gemini_api_key');
        const savedGroq = localStorage.getItem('groq_api_key');
        const savedTavily = localStorage.getItem('tavily_api_key');

        if (savedGemini) headers['X-Gemini-Api-Key'] = savedGemini;
        if (savedGroq) headers['X-Groq-Api-Key'] = savedGroq;
        if (savedTavily) headers['X-Tavily-Api-Key'] = savedTavily;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: headers,
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
            removeTypingIndicator(typingId);
            appendMessage('assistant', `⚠️ **Network Error**: Could not connect to API server (${error.message}).`);
        } finally {
            sendBtn.disabled = false;
            chatInput.focus();
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

    async function uploadFiles(files) {
        const formData = new FormData();
        const validExts = ['.pdf', '.chm', '.html', '.htm', '.txt', '.log'];
        for (let file of files) {
            const fileName = file.name.toLowerCase();
            if (validExts.some(ext => fileName.endsWith(ext))) {
                formData.append('files', file);
            }
        }

        if (!formData.has('files')) {
            alert('Please select valid documentation files (.pdf, .chm, .html, .htm, .txt, .log).');
            return;
        }

        const statusId = appendMessage('assistant', '📄 *Uploading & parsing documentation...*');

        try {
            const res = await fetch('/api/ingest', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: formData
            });

            if (res.status === 401) {
                updateMessageContent(statusId, '🔒 **Authentication Required**: Please log in to ingest documents.');
                showAuthOverlay();
                return;
            }

            if (res.ok) {
                const data = await res.json();
                updateMessageContent(statusId, `✅ **Ingestion Complete!**\nProcessed **${data.total_chunks}** vector chunk(s) from uploaded document(s).`);
                fetchStats();
            } else {
                const rawText = await res.text();
                let errMsg = 'Ingestion failed.';
                try {
                    const err = JSON.parse(rawText);
                    errMsg = err.detail || errMsg;
                } catch (e) {
                    errMsg = `HTTP ${res.status}: ${rawText.substring(0, 100)}`;
                }
                updateMessageContent(statusId, `❌ **Ingestion Failed**: ${errMsg}`);
            }
        } catch (e) {
            updateMessageContent(statusId, `❌ **Error uploading file**: ${e.message}`);
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
            }
        } catch (e) {
            console.warn('Could not fetch stats', e);
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
