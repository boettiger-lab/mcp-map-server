import { Client } from '../node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StreamableHTTPClientTransport } from '../node_modules/@modelcontextprotocol/sdk/dist/esm/client/streamableHttp.js';

let mcpClient = null;
let mcpTransport = null;
let mcpSessionId = null;
let availableTools = [];

async function initializeClient() {
    const baseUrl = document.getElementById('serverToggle').value === 'local'
        ? 'http://127.0.0.1:8081'
        : 'https://mcp-map.nrp-nautilus.io';

    try {
        // Use HTTP transport (browser-compatible)
        // Note: Server uses /mcp endpoint for HTTP transport
        const transportOptions = {};
        if (mcpSessionId) {
            transportOptions.sessionId = mcpSessionId;
        }

        mcpTransport = new StreamableHTTPClientTransport(new URL(`${baseUrl}/mcp`), transportOptions);

        mcpClient = new Client({
            name: 'map-web-client',
            version: '1.0.0'
        }, {
            capabilities: {}
        });

        await mcpClient.connect(mcpTransport);

        // Get session ID from transport
        mcpSessionId = mcpTransport.sessionId;
        console.log('Connected with session ID:', mcpSessionId);

        // Get session ID from transport

        // List available tools
        const toolsResult = await mcpClient.listTools();
        availableTools = toolsResult.tools || [];

        document.getElementById('sendButton').disabled = false;
        showStatus('Connected to MCP server', 'success');
        updateMapView();

    } catch (error) {
        showStatus(`Connection failed: ${error.message}`, 'error');
        console.error('Connection error:', error);
    }
}

async function sendMessage() {
    const message = document.getElementById('messageInput').value.trim();
    const apiKey = document.getElementById('apiKey').value;

    if (!message || !mcpClient) return;
    if (!apiKey) {
        showStatus('Please enter your API key first', 'error');
        return;
    }

    document.getElementById('messageInput').value = '';
    document.getElementById('sendButton').disabled = true;

    addMessage('user', message);
    addMessage('assistant', 'Thinking...', true);

    try {
        const endpoint = document.getElementById('llmProvider').value === 'custom'
            ? document.getElementById('customEndpoint').value
            : 'https://api.openai.com/v1/chat/completions';

        const model = document.getElementById('llmModel').value || 'openai/gpt-oss-120b:free';

        // Simple prompt - SDK handles tool schemas
        const systemPrompt = `You are a map assistant. Tools: ${availableTools.map(t => t.name).join(', ')}

Example:
TOOL_CALL: {"name": "add_layer", "arguments": {"id": "satellite", "type": "raster", "source": {"type": "raster", "tiles": ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], "tileSize": 256}, "session_id": "${mcpSessionId}"}}
TOOL_CALL: {"name": "set_map_view", "arguments": {"center": [-119.5, 36.5], "zoom": 6, "session_id": "${mcpSessionId}"}}`;

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model,
                messages: [
                    { role: 'system', content: systemPrompt },
                    { role: 'user', content: message }
                ],
                max_tokens: 1000,
                temperature: 0.7
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`LLM API Error (${response.status}): ${errorData.error?.message || response.statusText}`);
        }

        const result = await response.json();
        const assistantResponse = result.choices[0].message.content;

        // Extract and execute tool calls using MCP SDK
        const toolCallRegex = /TOOL_CALL:\s*(\{.+?\}(?=\s*(?:TOOL_CALL:|$)))/gs;
        let match;
        let toolsExecuted = 0;

        while ((match = toolCallRegex.exec(assistantResponse)) !== null) {
            try {
                const toolCall = JSON.parse(match[1]);
                console.log('Executing tool via SDK:', toolCall);

                // Use MCP SDK to call tool
                const toolResult = await mcpClient.callTool({
                    name: toolCall.name,
                    arguments: toolCall.arguments
                });

                console.log('Tool result:', toolResult);
                toolsExecuted++;
            } catch (error) {
                console.error('Tool execution error:', error);
            }
        }

        const responseText = toolsExecuted > 0
            ? `Executed ${toolsExecuted} tool(s). Check the map view!`
            : 'Map updated! Check the map view.';

        updateLastMessage(responseText);
        updateMapView();

    } catch (error) {
        updateLastMessage(`Error: ${error.message}`);
        console.error('Error:', error);
    }

    document.getElementById('sendButton').disabled = false;
}

function switchServer() {
    mcpClient = null;
    mcpTransport = null;
    mcpSessionId = null;
    showStatus('Server changed. Click Connect to reconnect.', 'error');
}

function updateMapView() {
    const baseUrl = document.getElementById('serverToggle').value === 'local'
        ? 'http://127.0.0.1:8081'
        : 'https://mcp-map.nrp-nautilus.io';
    const mapFrame = document.getElementById('mapFrame');
    mapFrame.src = `${baseUrl}/?session=${mcpSessionId || 'default'}&t=${Date.now()}`;
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
}

function addMessage(role, content, isTemporary = false) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    if (isTemporary) messageDiv.className += ' temporary';
    messageDiv.textContent = content;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function updateLastMessage(content) {
    const messagesDiv = document.getElementById('chatMessages');
    const messages = messagesDiv.querySelectorAll('.message');
    const lastMessage = messages[messages.length - 1];
    if (lastMessage) {
        lastMessage.textContent = content;
        lastMessage.classList.remove('temporary');
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !document.getElementById('sendButton').disabled) {
        sendMessage();
    }
}

function toggleLLMSettings() {
    const config = document.getElementById('llmConfig');
    const icon = document.getElementById('toggleIcon');
    config.classList.toggle('visible');
    icon.classList.toggle('expanded');
}

function updateLLMConfig() {
    const provider = document.getElementById('llmProvider').value;
    const customRow = document.getElementById('customEndpointRow');
    customRow.style.display = provider === 'custom' ? 'flex' : 'none';
}

// Global exports for HTML onclick handlers
window.initializeClient = initializeClient;
window.sendMessage = sendMessage;
window.switchServer = switchServer;
window.handleKeyPress = handleKeyPress;
window.toggleLLMSettings = toggleLLMSettings;
window.updateLLMConfig = updateLLMConfig;
