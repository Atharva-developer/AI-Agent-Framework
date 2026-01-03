import threading
import json
import time
from flask import Flask, jsonify, render_template_string
from kafka import KafkaConsumer

# --- CONFIGURATION ---
app = Flask(__name__)

# Global memory to store tasks
dashboard_data = {
    "pending": [],
    "completed": []
}

# --- KAFKA BACKGROUND LISTENER ---
def kafka_listener():
    """Reads from Kafka in the background and updates dashboard_data"""
    consumer = KafkaConsumer(
        'pending_tasks', 'completed_tasks',
        bootstrap_servers=['localhost:9092'],
        api_version=(0, 10, 1),  # The Critical Fix
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    for message in consumer:
        data = message.value
        if message.topic == 'pending_tasks':
            # Add to pending
            dashboard_data["pending"].append(data)
        elif message.topic == 'completed_tasks':
            # Add to completed
            dashboard_data["completed"].append(data)
            # Optional: Remove from pending if you want to clean up
            # (Keeping it simple for now)

# Start listener in a separate thread so it doesn't block the website
threading.Thread(target=kafka_listener, daemon=True).start()

# --- THE WEBSITE (HTML + JAVASCRIPT) ---
# We store the HTML here to keep it in one file for you.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Intel AI Agent - Mission Control</title>
    <meta http-equiv="refresh" content="2"> <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', monospace; }
        .card { background-color: #1e1e1e; border: 1px solid #333; margin-bottom: 20px; }
        .card-header { font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
        .status-online { color: #00ff00; font-weight: bold; }
        .table { color: #ccc; }
        .badge-pending { background-color: #ff9800; color: #000; }
        .badge-success { background-color: #00ff00; color: #000; }
    </style>
</head>
<body>

<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>🤖 Intel Agent Framework <span style="font-size:0.5em; color:#888;">Mission Control</span></h1>
        <div>
            <span class="status-online">● SYSTEM ONLINE</span>
        </div>
    </div>

    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header border-bottom border-secondary text-warning">
                    📨 Pending Queue
                </div>
                <div class="card-body p-0">
                    <table class="table table-dark table-striped mb-0">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Task Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for task in data.pending|reverse %}
                            <tr>
                                <td><span class="badge badge-pending">{{ task.id }}</span></td>
                                <td>{{ task.description }}</td>
                            </tr>
                            {% else %}
                            <tr><td colspan="2" class="text-center text-muted">No pending tasks...</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="col-md-6">
            <div class="card">
                <div class="card-header border-bottom border-secondary text-success">
                    ✅ Completed Results
                </div>
                <div class="card-body p-0">
                    <table class="table table-dark table-striped mb-0">
                        <thead>
                            <tr>
                                <th>Task ID</th>
                                <th>Result</th>
                                <th>Agent</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for res in data.completed|reverse %}
                            <tr>
                                <td>{{ res.task_id }}</td>
                                <td class="text-success fw-bold">{{ res.result }}</td>
                                <td><small>{{ res.agent }}</small></td>
                            </tr>
                            {% else %}
                            <tr><td colspan="3" class="text-center text-muted">No results yet...</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

</body>
</html>
"""

# --- FLASK ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, data=dashboard_data)

if __name__ == '__main__':
    print("🚀 Dashboard launching on http://127.0.0.1:5000")
    app.run(port=5000, debug=False)