# zk_utils.py
from zk import ZK, const
from datetime import datetime

def fetch_attendance(ip, port, start_date, end_date):
    zk = ZK(ip, port=int(port), timeout=5, password=0, force_udp=False, ommit_ping=False)
    conn = None
    try:
        conn = zk.connect()
        conn.disable_device()
        attendance = conn.get_attendance()
        conn.enable_device()
    except Exception as e:
        if conn:
            conn.enable_device()
        raise e
    finally:
        if conn:
            conn.disconnect()

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    return [
        {"user_id": a.user_id, "timestamp": str(a.timestamp)}
        for a in attendance if start <= a.timestamp <= end
    ]
