"""
Enhanced web dashboard with batch uploads, scheduling, monitoring, and task dependencies.
"""

from flask import Flask, render_template_string, request, jsonify
import requests
import json
from datetime import datetime, timedelta

app = Flask(__name__)

API_URL = "http://127.0.0.1:8000"
API_KEY = "default_key_12345"

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Framework - Advanced Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            border-bottom: 2px solid #ddd;
        }
        
        .tab-button {
            padding: 12px 24px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 16px;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }
        
        .tab-button.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .metric-label {
            font-size: 14px;
            opacity: 0.9;
        }
        
        form {
            display: grid;
            gap: 15px;
        }
        
        .form-group {
            display: grid;
            gap: 5px;
        }
        
        label {
            font-weight: 600;
            color: #333;
        }
        
        input, select, textarea {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .button-group {
            display: flex;
            gap: 10px;
        }
        
        button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .success {
            background: #10b981;
        }
        
        .danger {
            background: #ef4444;
        }
        
        .results {
            background: #f9fafb;
            padding: 15px;
            border-radius: 5px;
            margin-top: 15px;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .result-item {
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
            font-size: 14px;
        }
        
        .result-item:last-child {
            border-bottom: none;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .status-pending {
            background: #fef3c7;
            color: #92400e;
        }
        
        .status-completed {
            background: #d1fae5;
            color: #065f46;
        }
        
        .status-failed {
            background: #fee2e2;
            color: #7f1d1d;
        }
        
        .chart-container {
            background: #f9fafb;
            padding: 20px;
            border-radius: 5px;
            margin-top: 15px;
        }
        
        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        @media (max-width: 768px) {
            .two-column {
                grid-template-columns: 1fr;
            }
        }
        
        .loading {
            display: none;
            text-align: center;
            color: #667eea;
        }
        
        .loading.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 AI Agent Framework - Advanced Control Panel</h1>
            <p>Batch uploads • Task scheduling • Priority management • Dependency tracking • Advanced monitoring</p>
        </header>
        
        <div class="tabs">
            <button class="tab-button active" onclick="switchTab('submit')">Submit Tasks</button>
            <button class="tab-button" onclick="switchTab('batch')">Batch Upload</button>
            <button class="tab-button" onclick="switchTab('schedule')">Schedule Tasks</button>
            <button class="tab-button" onclick="switchTab('monitor')">Monitor & Analytics</button>
        </div>
        
        <!-- Submit Single Task Tab -->
        <div id="submit" class="tab-content active">
            <div class="card">
                <h2>Submit Single Task</h2>
                <form onsubmit="submitTask(event)">
                    <div class="two-column">
                        <div class="form-group">
                            <label>Task Description</label>
                            <textarea id="task-desc" required placeholder="Enter task description..."></textarea>
                        </div>
                        <div class="form-group">
                            <label>Priority</label>
                            <select id="task-priority">
                                <option value="normal">Normal</option>
                                <option value="high">High</option>
                                <option value="low">Low</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Depends On Task ID (optional)</label>
                        <input type="text" id="task-depends" placeholder="Leave empty if no dependencies">
                    </div>
                    <div class="button-group">
                        <button type="submit">Submit Task</button>
                    </div>
                </form>
                <div id="submit-results" class="results" style="display:none;"></div>
            </div>
        </div>
        
        <!-- Batch Upload Tab -->
        <div id="batch" class="tab-content">
            <div class="card">
                <h2>Batch Upload - CSV</h2>
                <form onsubmit="uploadCSV(event)">
                    <div class="form-group">
                        <label>Select CSV File</label>
                        <p style="font-size: 12px; color: #666; margin-top: 5px;">Columns: description, priority (high/normal/low), scheduled_time (ISO), depends_on, max_retries</p>
                        <input type="file" id="csv-file" accept=".csv" required>
                    </div>
                    <div class="button-group">
                        <button type="submit">Upload CSV</button>
                    </div>
                </form>
                <div id="csv-results" class="results" style="display:none;"></div>
            </div>
            
            <div class="card">
                <h2>Batch Upload - JSON</h2>
                <form onsubmit="uploadJSON(event)">
                    <div class="form-group">
                        <label>JSON Tasks (Array)</label>
                        <textarea id="json-tasks" required placeholder='[{"description": "task 1", "priority": "high"}, {"description": "task 2"}]'></textarea>
                    </div>
                    <div class="button-group">
                        <button type="submit">Upload JSON</button>
                    </div>
                </form>
                <div id="json-results" class="results" style="display:none;"></div>
            </div>
        </div>
        
        <!-- Schedule Tasks Tab -->
        <div id="schedule" class="tab-content">
            <div class="card">
                <h2>Schedule Task for Later Execution</h2>
                <form onsubmit="scheduleTask(event)">
                    <div class="two-column">
                        <div class="form-group">
                            <label>Task Description</label>
                            <textarea id="sched-desc" required placeholder="Enter task description..."></textarea>
                        </div>
                        <div>
                            <div class="form-group">
                                <label>Scheduled Date & Time</label>
                                <input type="datetime-local" id="sched-time" required>
                            </div>
                            <div class="form-group">
                                <label>Priority</label>
                                <select id="sched-priority">
                                    <option value="normal">Normal</option>
                                    <option value="high">High</option>
                                    <option value="low">Low</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Depends On Task ID (optional)</label>
                        <input type="text" id="sched-depends" placeholder="Leave empty if no dependencies">
                    </div>
                    <div class="button-group">
                        <button type="submit">Schedule Task</button>
                    </div>
                </form>
                <div id="schedule-results" class="results" style="display:none;"></div>
            </div>
        </div>
        
        <!-- Monitor & Analytics Tab -->
        <div id="monitor" class="tab-content">
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Tasks</div>
                    <div class="metric-value" id="metric-total">-</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Completed</div>
                    <div class="metric-value" id="metric-completed">-</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Failed</div>
                    <div class="metric-value" id="metric-failed">-</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Agents Online</div>
                    <div class="metric-value" id="metric-agents">-</div>
                </div>
            </div>
            
            <div class="two-column">
                <div class="card">
                    <h3>Priority Distribution</h3>
                    <div class="chart-container">
                        <div style="display: flex; gap: 20px; margin: 20px 0;">
                            <div style="text-align: center;">
                                <div style="font-size: 24px; font-weight: bold; color: #ef4444;" id="priority-high">0</div>
                                <div style="font-size: 12px; color: #666;">High Priority</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 24px; font-weight: bold; color: #f59e0b;" id="priority-normal">0</div>
                                <div style="font-size: 12px; color: #666;">Normal Priority</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 24px; font-weight: bold; color: #3b82f6;" id="priority-low">0</div>
                                <div style="font-size: 12px; color: #666;">Low Priority</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Task Status Breakdown</h3>
                    <div class="chart-container">
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-weight: 600; width: 80px;">Pending:</span>
                                <div style="background: #fef3c7; height: 20px; border-radius: 3px; flex: 1;" id="progress-pending"></div>
                                <span id="pending-count">0</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-weight: 600; width: 80px;">Scheduled:</span>
                                <div style="background: #bfdbfe; height: 20px; border-radius: 3px; flex: 1;" id="progress-scheduled"></div>
                                <span id="scheduled-count">0</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-weight: 600; width: 80px;">Completed:</span>
                                <div style="background: #d1fae5; height: 20px; border-radius: 3px; flex: 1;" id="progress-completed"></div>
                                <span id="completed-count">0</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>Quick Actions</h3>
                <div class="button-group">
                    <button onclick="refreshMetrics()">🔄 Refresh Metrics</button>
                    <button onclick="getScheduledTasks()" class="success">📅 View Scheduled Tasks</button>
                </div>
                <div id="actions-results" class="results" style="display:none;"></div>
            </div>
        </div>
    </div>
    
    <script>
        const API_KEY = "{{ api_key }}";
        const API_URL = "{{ api_url }}";
        
        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-button').forEach(el => el.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }
        
        async function submitTask(e) {
            e.preventDefault();
            const desc = document.getElementById('task-desc').value;
            const priority = document.getElementById('task-priority').value;
            const dependsOn = document.getElementById('task-depends').value || null;
            
            try {
                const response = await fetch(`${API_URL}/tasks`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${API_KEY}`
                    },
                    body: JSON.stringify({
                        description: desc,
                        priority: priority,
                        depends_on: dependsOn
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    showResult('submit-results', `✓ Task submitted: ${data.id}`);
                    document.getElementById('task-desc').value = '';
                } else {
                    showResult('submit-results', `✗ Error: ${response.statusText}`);
                }
            } catch (error) {
                showResult('submit-results', `✗ Network error: ${error.message}`);
            }
        }
        
        async function uploadCSV(e) {
            e.preventDefault();
            const file = document.getElementById('csv-file').files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch(`${API_URL}/batch/upload/csv`, {
                    method: 'POST',
                    headers: {'Authorization': `Bearer ${API_KEY}`},
                    body: formData
                });
                
                if (response.ok) {
                    const data = await response.json();
                    showResult('csv-results', `✓ Batch ${data.batch_id}: ${data.created_tasks} tasks created, ${data.failed_tasks} failed`);
                } else {
                    showResult('csv-results', `✗ Error: ${response.statusText}`);
                }
            } catch (error) {
                showResult('csv-results', `✗ Error: ${error.message}`);
            }
        }
        
        async function uploadJSON(e) {
            e.preventDefault();
            const jsonStr = document.getElementById('json-tasks').value;
            
            try {
                const tasks = JSON.parse(jsonStr);
                const response = await fetch(`${API_URL}/batch/upload/json`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${API_KEY}`
                    },
                    body: JSON.stringify(tasks)
                });
                
                if (response.ok) {
                    const data = await response.json();
                    showResult('json-results', `✓ Batch ${data.batch_id}: ${data.created_tasks} tasks created`);
                } else {
                    showResult('json-results', `✗ Error: ${response.statusText}`);
                }
            } catch (error) {
                showResult('json-results', `✗ Error: ${error.message}`);
            }
        }
        
        async function scheduleTask(e) {
            e.preventDefault();
            const desc = document.getElementById('sched-desc').value;
            const datetimeLocal = document.getElementById('sched-time').value;
            const isoString = new Date(datetimeLocal).toISOString();
            const priority = document.getElementById('sched-priority').value;
            
            try {
                const response = await fetch(`${API_URL}/tasks/schedule`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${API_KEY}`
                    },
                    body: JSON.stringify({
                        description: desc,
                        scheduled_time: isoString,
                        priority: priority
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    showResult('schedule-results', `✓ Task scheduled: ${data.task_id} for ${isoString}`);
                    document.getElementById('sched-desc').value = '';
                } else {
                    showResult('schedule-results', `✗ Error: ${response.statusText}`);
                }
            } catch (error) {
                showResult('schedule-results', `✗ Error: ${error.message}`);
            }
        }
        
        async function refreshMetrics() {
            try {
                const response = await fetch(`${API_URL}/metrics/advanced`, {
                    headers: {'Authorization': `Bearer ${API_KEY}`}
                });
                
                if (response.ok) {
                    const data = await response.json();
                    document.getElementById('metric-total').textContent = data.task_summary.total;
                    document.getElementById('metric-completed').textContent = data.task_summary.completed;
                    document.getElementById('metric-failed').textContent = data.task_summary.failed;
                    document.getElementById('metric-agents').textContent = data.agent_stats.online;
                }
            } catch (error) {
                console.error('Error:', error);
            }
        }
        
        function showResult(elementId, message) {
            const el = document.getElementById(elementId);
            el.innerHTML = message;
            el.style.display = 'block';
        }
        
        function getScheduledTasks() {
            showResult('actions-results', '📅 Scheduled tasks will be processed at their scheduled time');
        }
        
        // Auto-refresh metrics every 10 seconds
        setInterval(refreshMetrics, 10000);
        refreshMetrics();
        
        // --- Realtime WebSocket connection ---
        let ws = null;
        function initWebSocket() {
            const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
            const url = `${scheme}://${location.hostname}:8000/ws/updates`;
            try {
                ws = new WebSocket(url);
                ws.onopen = () => console.log('WebSocket connected');
                ws.onmessage = (evt) => {
                    try {
                        const msg = JSON.parse(evt.data);
                        handleRealtimeEvent(msg);
                    } catch (e) { console.error('Invalid WS message', e); }
                };
                ws.onclose = () => {
                    console.log('WebSocket closed, reconnecting in 3s');
                    setTimeout(initWebSocket, 3000);
                };
                ws.onerror = (e) => console.error('WebSocket error', e);
            } catch (err) {
                console.error('Failed to open WebSocket', err);
            }
        }

        function handleRealtimeEvent(msg) {
            // msg: { topic: 'topic_name', payload: {...} }
            const area = document.getElementById('actions-results');
            area.style.display = 'block';
            const ts = new Date().toLocaleTimeString();
            let text = '';
            if (msg.topic && msg.payload) {
                if (msg.topic.endsWith('completed')) {
                    text = `✅ [${ts}] Task ${msg.payload.id} completed (${msg.payload.execution_time || 'n/a'}s)`;
                    // refresh metrics quickly
                    refreshMetrics();
                } else if (msg.topic.endsWith('pending')) {
                    text = `📨 [${ts}] Task ${msg.payload.id} queued`;
                    refreshMetrics();
                } else {
                    text = `🔔 [${ts}] ${msg.topic}: ${JSON.stringify(msg.payload)}`;
                }
            } else {
                text = `🔔 [${ts}] ${JSON.stringify(msg)}`;
            }
            const item = document.createElement('div');
            item.className = 'result-item';
            item.textContent = text;
            area.prepend(item);
        }

        // Start WebSocket
        initWebSocket();
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE, api_url=API_URL, api_key=API_KEY)


@app.route('/api/health')
def health():
    try:
        response = requests.get(f'{API_URL}/health', headers={'Authorization': f'Bearer {API_KEY}'})
        return jsonify(response.json())
    except:
        return jsonify({'status': 'error'}), 500


if __name__ == '__main__':
    print("🚀 Web dashboard starting on http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
