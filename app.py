"""
Flask API server for AutoDB interactive UI.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pipeline import PipelineSession
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Single session store (demo mode — one user at a time)
session_store = {
    "pipeline": None
}


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/connect', methods=['POST'])
def connect():
    """Connect to a PostgreSQL database."""
    data = request.get_json()
    db_name = data.get('db_name', 'grocermind')
    host = data.get('host')
    port = data.get('port')
    user = data.get('user')
    password = data.get('password')

    # Disconnect previous session if any
    if session_store["pipeline"]:
        session_store["pipeline"].disconnect()

    kwargs = {"db_name": db_name}
    if host: kwargs["host"] = host
    if port: kwargs["port"] = port
    if user: kwargs["user"] = user
    if password: kwargs["password"] = password

    pipeline = PipelineSession(**kwargs)
    result = pipeline.connect()

    if result["success"]:
        session_store["pipeline"] = pipeline
    
    return jsonify(result)


@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from the database."""
    if session_store["pipeline"]:
        session_store["pipeline"].disconnect()
        session_store["pipeline"] = None
    return jsonify({"success": True, "message": "Disconnected."})


@app.route('/api/pipeline/start', methods=['POST'])
def pipeline_start():
    """
    Start the pipeline for a new query.
    Runs Step 1 (Intent Ambiguity Detection) and returns ambiguities if found.
    """
    pipeline = session_store.get("pipeline")
    if not pipeline:
        return jsonify({"success": False, "error": "Not connected to a database."}), 400

    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({"success": False, "error": "Query cannot be empty."}), 400

    try:
        result = pipeline.start_ambiguity_detection(query)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pipeline/clarify', methods=['POST'])
def pipeline_clarify():
    """
    Submit user's clarification choices and detect further ambiguities.
    """
    pipeline = session_store.get("pipeline")
    if not pipeline:
        return jsonify({"success": False, "error": "Not connected to a database."}), 400

    data = request.get_json()
    choices = data.get('choices', [])

    try:
        result = pipeline.submit_clarifications(choices)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pipeline/step2', methods=['POST'])
def pipeline_step2():
    pipeline = session_store.get("pipeline")
    if not pipeline: return jsonify({"success": False, "error": "Not connected"}), 400
    return jsonify(pipeline.execute_step2())

@app.route('/api/pipeline/step3', methods=['POST'])
def pipeline_step3():
    pipeline = session_store.get("pipeline")
    if not pipeline: return jsonify({"success": False, "error": "Not connected"}), 400
    return jsonify(pipeline.execute_step3())

@app.route('/api/pipeline/step4', methods=['POST'])
def pipeline_step4():
    pipeline = session_store.get("pipeline")
    if not pipeline: return jsonify({"success": False, "error": "Not connected"}), 400
    return jsonify(pipeline.execute_step4())

@app.route('/api/pipeline/step5', methods=['POST'])
def pipeline_step5():
    pipeline = session_store.get("pipeline")
    if not pipeline: return jsonify({"success": False, "error": "Not connected"}), 400
    return jsonify(pipeline.execute_step5())

@app.route('/api/pipeline/step6', methods=['POST'])
def pipeline_step6():
    pipeline = session_store.get("pipeline")
    if not pipeline: return jsonify({"success": False, "error": "Not connected"}), 400
    return jsonify(pipeline.execute_step6())


@app.route('/api/config', methods=['GET'])
def get_config():
    """Return current session configuration."""
    pipeline = session_store.get("pipeline")
    return jsonify({
        "connected": pipeline is not None,
        "db_name": pipeline.db_name if pipeline else None
    })


if __name__ == '__main__':
    import socket
    try:
        print(f"\n * Server is accessible locally at: http://127.0.0.1:5000")
        
        # Try to find all network IPs (including Tailscale)
        hostname = socket.gethostname()
        all_ips = socket.gethostbyname_ex(hostname)[2]
        
        for ip in all_ips:
            if not ip.startswith("127."):
                label = "Tailscale IP" if ip.startswith("100.") else "Local Network IP"
                print(f" * Server is accessible on your {label} at: http://{ip}:5000")
                
        print(f" * (Note: Use the Tailscale IP (100.x.x.x) for the remote PC)\n")
    except Exception:
        pass
    app.run(host='0.0.0.0', debug=True, port=5000)
