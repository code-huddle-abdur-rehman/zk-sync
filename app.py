# app.py
import webview
import webbrowser
import threading
from zk import ZK
from flask import Flask, request, jsonify, render_template
from zk_utils import fetch_attendance
from datetime import datetime, timedelta
import requests
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect', methods=['POST'])
def connect():
    data = request.json
    ip = data.get('ip')
    if not ip:
        return jsonify({'error': 'IP address is required'}), 400

    parts = ip.split(':')
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 4370

    zk = ZK(host, port=port, timeout=10)
    conn = None
    try:
        conn = zk.connect()
        users = []
        for user in conn.get_users():
            users.append({
                'uid': user.uid,
                'user_id': user.user_id,
                'name': user.name,
                'privilege': user.privilege,
                'password': user.password,
                'group_id': user.group_id,
                # add more fields as needed
            })
        return jsonify({
            'message': 'Successfully connected to device',
            'users': users
        })
    except Exception as e:
        return jsonify({'error': str(e) or 'Failed to connect to ZKTeco device'}), 500
    finally:
        if conn:
            conn.disconnect()

@app.route('/attendance', methods=['POST'])
def attendance():
    data = request.json
    ip = data.get('ip')
    start_date = data.get('startDate')
    end_date = data.get('endDate')
    if not ip:
        return jsonify({'error': 'IP address is required'}), 400

    parts = ip.split(':')
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 4370

    zk = ZK(host, port=port, timeout=10)
    conn = None
    try:
        conn = zk.connect()
        users = conn.get_users()
        user_map = {str(user.user_id): user.name for user in users}
        attendance = conn.get_attendance()
    except Exception as e:
        return jsonify({'error': str(e) or 'Failed to connect to ZKTeco device'}), 500
    finally:
        try:
            if conn:
                conn.disconnect()
        except Exception:
            pass

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(milliseconds=1)

    logs = []
    for a in attendance:
        if start <= a.timestamp <= end:
            # punch: 0 = check in, 1 = check out (typical for ZKTeco)
            status = 'Check In' if getattr(a, 'punch', 0) == 0 else 'Check Out'
            logs.append({
                'user_id': a.user_id,
                'name': user_map.get(str(a.user_id), f'User {a.user_id}'),
                'number': str(a.user_id),
                'dateTime': a.timestamp.isoformat(),
                'status': status
            })

    # Prepare data for forwarding (remove user_id, keep only required fields)
    upload_data = [
        {
            'dateTime': log['dateTime'],
            'name': log['name'],
            'status': log['status'],
            'number': log['number']
        }
        for log in logs
    ]

    # Forward to external backend
    try:
        upload_response = requests.post(
            'http://localhost:3002/attendance/upload',
            json=upload_data,
            timeout=10
        )
        upload_response.raise_for_status()
        upload_result = upload_response.json() if upload_response.content else {'success': True}
    except Exception as e:
        return jsonify({
            'attendance': {
                'logs': logs,
                'userMap': user_map,
            },
            'upload': {
                'success': False,
                'error': str(e)
            }
        }), 200

    return jsonify({
        'attendance': {
            'logs': logs,
            'userMap': user_map,
        },
        'upload': {
            'success': True,
            'result': upload_result
        }
    })

@app.route('/exit', methods=['POST'])
def exit_app():
    import threading
    import time
    
    def delayed_exit():
        time.sleep(0.5)  # Small delay to allow browser to close
        os._exit(0)
    
    # Start delayed exit in a separate thread
    threading.Thread(target=delayed_exit, daemon=True).start()
    
    # Return success response to browser
    return jsonify({"status": "exiting"}), 200

def start_flask():
    app.run(debug=False, port=5000)


if __name__ == '__main__':
    threading.Thread(target=start_flask, daemon=True).start()
    webbrowser.open("http://localhost:5000")
    # Keep the script running so the server stays alive
    import time
    while True:
        time.sleep(1)
