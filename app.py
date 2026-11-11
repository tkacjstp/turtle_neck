from flask import Flask, render_template, request, jsonify
import os
import threading
import time
from urllib.parse import urlsplit
from video_stream import FrameStore
from flask import Response
import sqlite3
from datetime import datetime

app = Flask(__name__)
video = FrameStore()
command_lock = threading.Lock()
pending_command = None


@app.post('/api/control')
def control_posture():
    global pending_command
    if request.remote_addr not in ('127.0.0.1', '::1'):
        return jsonify(error='local control only'), 403
    origin = request.headers.get('Origin')
    if origin and urlsplit(origin).netloc != request.host:
        return jsonify(error='same origin required'), 403
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get('command') not in ('calibrate', 'quit'):
        return jsonify(error='invalid command'), 400
    if not video.online():
        return jsonify(error='posture offline'), 409
    with command_lock:
        if pending_command and pending_command[1] > time.monotonic():
            return jsonify(error='command pending'), 409
        pending_command = (data['command'], time.monotonic() + 3)
    return jsonify(result='queued'), 202

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'turtle_neck.db')

# 판별 프로그램이 보내는 항목 중 저장할 것 (이름: SQL 타입)
EXTRA_COLUMNS = {
    'user_id': 'TEXT',
    'worse_pct': 'REAL',
    'shoulder_status': 'TEXT',
    'shoulder_tilt': 'REAL',
    'bad_duration': 'REAL',
}
VALID_STATUS = ('정상', '경고', '위험')


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            angle REAL,
            status TEXT
        )
    ''')
    # 예전 DB 파일이 있어도 필요한 컬럼만 추가 (기존 데이터 유지)
    existing = {r['name'] for r in conn.execute('PRAGMA table_info(measurements)')}
    for col, typ in EXTRA_COLUMNS.items():
        if col not in existing:
            conn.execute(f'ALTER TABLE measurements ADD COLUMN {col} {typ}')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON measurements(timestamp)')
    conn.commit()
    conn.close()

@app.post('/api/video_frame')
def receive_video_frame():
    global pending_command
    # Only the local posture process can publish frames.
    if request.remote_addr not in ('127.0.0.1', '::1'):
        return jsonify(error='local publisher only'), 403
    if request.mimetype != 'image/jpeg':
        return jsonify(error='image/jpeg required'), 415
    if request.content_length is None or request.content_length > 2_000_000:
        return jsonify(error='frame too large or missing length'), 413
    frame = request.get_data()
    if not frame.startswith(b'\xff\xd8') or not frame.endswith(b'\xff\xd9'):
        return jsonify(error='invalid JPEG'), 400
    video.publish(frame)
    headers = {}
    with command_lock:
        if pending_command:
            command, expires = pending_command
            pending_command = None
            if expires > time.monotonic():
                headers['X-Posture-Command'] = command
    return '', 204, headers


@app.get('/api/video_status')
def video_status():
    return jsonify(online=video.online())


@app.get('/video_feed')
def video_feed():
    return Response(video.stream(), mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@app.route('/api/status', methods=['POST'])
def receive_status():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "result": "fail",
            "reason": "JSON 형식이 아닙니다"
        }), 400

    status = data.get('status')

    if status not in VALID_STATUS:
        return jsonify({
            "result": "fail",
            "reason": f"status 값 오류: {status}"
        }), 400

    print(f"[상태 알림] 현재 자세 상태: {status}")

    return jsonify({
        "result": "success",
        "status": status
    }), 200

@app.route('/api/record', methods=['POST'])
def record_result():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"result": "fail", "reason": "JSON 형식이 아닙니다"}), 400

    status = data.get('status')
    if status not in VALID_STATUS:
        return jsonify({"result": "fail", "reason": f"status 값 오류: {status}"}), 400

    # 판별 프로그램이 보낸 측정 시각 우선 (밀린 데이터도 원래 시각으로 저장)
    timestamp = data.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    angle = data.get('angle', data.get('worse_pct'))

    cols = ['timestamp', 'angle', 'status'] + list(EXTRA_COLUMNS)
    vals = [timestamp, angle, status] + [data.get(c) for c in EXTRA_COLUMNS]

    conn = get_conn()
    conn.execute(f'INSERT INTO measurements ({",".join(cols)}) '
                 f'VALUES ({",".join("?" * len(cols))})', vals)
    conn.commit()
    conn.close()
    return jsonify({"result": "success"})


@app.route('/api/results', methods=['GET'])
def get_results():
    limit = min(request.args.get('limit', 20, type=int), 500)
    conn = get_conn()
    rows = conn.execute('SELECT * FROM measurements ORDER BY timestamp DESC, id DESC LIMIT ?',
                        (limit,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/stats', methods=['GET'])
def get_stats():
    day = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    conn = get_conn()
    rows = conn.execute('SELECT status, COUNT(*) AS cnt FROM measurements '
                        'WHERE timestamp BETWEEN ? AND ? GROUP BY status',  # 인덱스 사용
                        (day + ' 00:00:00', day + ' 23:59:59')).fetchall()
    conn.close()

    counts = {s: 0 for s in VALID_STATUS}
    for r in rows:
        if r['status'] in counts:
            counts[r['status']] = r['cnt']
    total = sum(counts.values())
    percent = {k: round(v / total * 100, 1) if total else 0 for k, v in counts.items()}
    return jsonify({"date": day, "total": total, "counts": counts, "percent": percent})


@app.route('/')
def index():
    return render_template('index.html')


# 서버 시작 방식과 관계없이 DB 준비
init_db()

if __name__ == '__main__':
    # 개발 중 오류 확인이 필요하면 debug=True, 시연·제출 때는 False
    app.run(host='0.0.0.0', port=5050, debug=False, threaded=True)