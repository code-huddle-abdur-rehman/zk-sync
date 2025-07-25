# app.py
import webview
import webbrowser
import threading
from zk import ZK
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from zk_utils import fetch_attendance
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv
import jwt
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Add a secret key for sessions

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For now, we'll use a simple session check
        # In production, you might want to validate JWT tokens
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    # Redirect to login if not authenticated, otherwise to dashboard
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login_post():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    environment = data.get('environment', 'dev')
    
    if not email or not password or not role:
        return jsonify({'error': 'Email, password, and role are required'}), 400
    
        # Determine backend URL based on environment
    if environment == 'prod':
        backend_url = os.getenv('PROD_BACKEND_URL', 'http://localhost:3001')
    else:
        backend_url = os.getenv('DEV_BACKEND_URL', 'http://localhost:3003')
    
    # Ensure proper URL construction by removing trailing slash if present
    backend_url = backend_url.rstrip('/')
    login_url = f"{backend_url}/auth/login"
    
    # Prepare request payload
    payload = {
        'email': email,
        'password': password,
        'role': role
    }
    
    # Call the main backend's login endpoint
    try:
        login_response = requests.post(
            login_url,
            json=payload,
            timeout=10
        )
        if login_response.status_code == 200 or login_response.status_code == 201:
            login_data = login_response.json()
            
            # Convert snake_case tokens to camelCase for frontend
            tokens = login_data.get('tokens', {})
            frontend_tokens = {
                'accessToken': tokens.get('access_token'),
                'refreshToken': tokens.get('refresh_token')
            }
            
            # Store user info in session
            session['user_id'] = login_data.get('user', {}).get('_id')
            session['user_email'] = login_data.get('user', {}).get('email')
            session['user_role'] = login_data.get('user', {}).get('role')
            session['environment'] = environment
            session['access_token'] = frontend_tokens.get('accessToken')
            
            return jsonify({
                'success': True,
                'tokens': frontend_tokens,
                'user': login_data.get('user', {})
            })
        else:
            error_data = login_response.json() if login_response.content else {}
            return jsonify({
                'error': error_data.get('message', 'Login failed')
            }), login_response.status_code
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Failed to connect to {environment} backend: {str(e)}'
        }), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/devices', methods=['GET'])
@require_auth
def get_devices():
    """Get list of available devices from .env file"""
    devices = []
    for i in range(1, 3):  # DEVICE_IP_1 and DEVICE_IP_2
        device_ip = os.getenv(f'DEVICE_IP_{i}')
        if device_ip:
            devices.append(device_ip)
    return jsonify({'devices': devices})

@app.route('/connect', methods=['POST'])
@require_auth
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
@require_auth
def attendance():
    data = request.json
    ip = data.get('ip')
    start_date = data.get('startDate')
    end_date = data.get('endDate')
    environment = data.get('environment', 'dev')  # Default to dev if not specified
    
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

    # Determine backend endpoint based on environment from .env file
    if environment == 'prod':
        backend_url = os.getenv('PROD_BACKEND_URL', 'http://localhost:3001')
    else:
        backend_url = os.getenv('DEV_BACKEND_URL', 'http://localhost:3003')

    backend_url = backend_url.rstrip('/')
    attendance_url = f"{backend_url}/attendance/upload"

    # Get the access token from session
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({
            'attendance': {
                'logs': logs,
                'userMap': user_map,
            },
            'upload': {
                'success': False,
                'error': 'No access token found. Please login again.'
            }
        }), 200

    # Forward to external backend with authentication
    try:
        upload_response = requests.post(
            attendance_url,
            json=upload_data,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
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
                'error': f'Failed to upload to {environment} backend: {str(e)}'
            }
        }), 200

    return jsonify({
        'attendance': {
            'logs': logs,
            'userMap': user_map,
        },
        'upload': {
            'success': True,
            'result': upload_result,
            'environment': environment
        }
    })

@app.route('/exit', methods=['POST'])
@require_auth
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
