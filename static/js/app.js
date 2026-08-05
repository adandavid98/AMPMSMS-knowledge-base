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
    const saveKeysBtn = document.getElementById('saveKeysBtn');
    const keyStatusBadge = document.getElementById('keyStatusBadge');
    const toggleGeminiKey = document.getElementById('toggleGeminiKey');
    const toggleGroqKey = document.getElementById('toggleGroqKey');

    const toggleApiKeyAccordion = document.getElementById('toggleApiKeyAccordion');
    const apiKeyCollapseContent = document.getElementById('apiKeyCollapseContent');
    const accordionChevron = document.getElementById('accordionChevron');

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

    // Save Keys Button
    saveKeysBtn.addEventListener('click', () => {
        const geminiVal = geminiKeyInput.value.trim();
        const groqVal = groqKeyInput.value.trim();

        if (geminiVal) localStorage.setItem('gemini_api_key', geminiVal);
        else localStorage.removeItem('gemini_api_key');

        if (groqVal) localStorage.setItem('groq_api_key', groqVal);
        else localStorage.removeItem('groq_api_key');

        updateKeyBadgeStatus();
        alert('Local API Keys saved securely in your browser!');
    });

    function loadSavedApiKeys() {
        const savedGemini = localStorage.getItem('gemini_api_key');
        const savedGroq = localStorage.getItem('groq_api_key');

        if (savedGemini) geminiKeyInput.value = savedGemini;
        if (savedGroq) groqKeyInput.value = savedGroq;

        updateKeyBadgeStatus();
    }

    function updateKeyBadgeStatus() {
        const hasGemini = !!localStorage.getItem('gemini_api_key');
        const hasGroq = !!localStorage.getItem('groq_api_key');

        if (hasGemini || hasGroq) {
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
        const headers = { 'Content-Type': 'application/json' };
        const savedGemini = localStorage.getItem('gemini_api_key');
        const savedGroq = localStorage.getItem('groq_api_key');

        if (savedGemini) headers['X-Gemini-Api-Key'] = savedGemini;
        if (savedGroq) headers['X-Groq-Api-Key'] = savedGroq;

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
                    attachments: currentAttachments
                })
            });

            removeTypingIndicator(typingId);

            if (response.ok) {
                const data = await response.json();
                appendMessage('assistant', data.answer, data.citations, data.provider_used);
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
        for (let file of files) {
            if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
                formData.append('files', file);
            }
        }

        if (!formData.has('files')) {
            alert('Please select valid PDF files.');
            return;
        }

        const statusId = appendMessage('assistant', '📄 *Uploading & parsing PDF documentation...*');

        try {
            const res = await fetch('/api/ingest', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                updateMessageContent(statusId, `✅ **Ingestion Complete!**\nProcessed **${data.total_chunks}** vector chunk(s) from uploaded document(s).`);
                fetchStats();
            } else {
                updateMessageContent(statusId, '❌ **Ingestion Failed**. Check server logs.');
            }
        } catch (e) {
            updateMessageContent(statusId, `❌ **Error uploading file**: ${e.message}`);
        }
    }

    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            if (res.ok) {
                const data = await res.json();
                statChunks.textContent = data.total_chunks;
                statDocs.textContent = data.collection_name;
            }
        } catch (e) {
            console.warn('Could not fetch stats', e);
        }
    }

    function appendMessage(sender, text, citations = [], providerUsed = '') {
        const msgId = 'msg-' + Date.now();
        const row = document.createElement('div');
        row.className = `message-row ${sender}`;
        row.id = msgId;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? 'TECH' : 'AI';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        let htmlContent = formatMarkdown(text);

        if (citations && citations.length > 0) {
            htmlContent += `
                <div class="citations-box">
                    <div class="citations-title">Sources & References (${providerUsed})</div>
                    <div class="citation-chips">
                        ${citations.map(c => `
                            <span class="citation-chip">
                                📄 ${escapeHtml(c.file_name)} (Page ${c.page_number})
                            </span>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        bubble.innerHTML = htmlContent;
        row.appendChild(avatar);
        row.appendChild(bubble);

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
        let formatted = escapeHtml(text);
        
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
