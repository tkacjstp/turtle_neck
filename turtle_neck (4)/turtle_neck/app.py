r"""
========================================================================
 �źϸ� �Ǻ� ��� ���� (app.py)
========================================================================

[�� ���α׷��� �ϴ� ��]
  �Ǻ���(posture.py)�� ���� ���� ����� DB(turtle_neck.db)�� �����ϰ�,
  �� ������(http://����IP:5050)���� ǥ�� �����ش�.

[�ʿ� ȯ��]
  Python : 3.9 ~ 3.12 (3.11 ����, �Ǻ���� ���� �������� ���߸� ������ ����)
  flask  : ���� ���� ���� (pip install flask)
  �� ���� ��ǻ�Ϳ��� mediapipe��OpenCV����ķ�� �ʿ� ����

[����]
  ������: venv\Scripts\python app.py      ��/���������: python app.py
  ����  : Ctrl+C
  Ȯ��  : ���������� http://127.0.0.1:5050 (���� ��ǻ��) �Ǵ� http://����IP:5050

[üũ����Ʈ]
  �� �Ǻ��⺸�� ���� �Ѱ�, �� â�� ���� ���� �� �� �� (������ ������ ����)
  �� ���� IP Ȯ�� �� �Ǻ��� �� config.json�� server_url�� ����
      ������: ipconfig �� "IPv4 �ּ�" / ��: ipconfig getifaddr en0 / ������: hostname -I
  �� �Ǻ���� ������ ���� ��������/��Ʈ��ũ�� �ִ���
  �� ó�� ���� �� ������ ��ȭ�� â�� �߸� "���" (�ٸ� ��ǻ�Ϳ��� �����Ϸ��� �ʿ�.
    �� ��ǻ�� �ϳ��� �׽�Ʈ�� ���� ����ص� ��)

[���ǻ���]
  - �� �� �����ϸ� "Address already in use" ���� -> ���� �� â�� Ctrl+C�� ���� �ٽ� ����
  - ��Ʈ�� 5050�� (���� 5000���� AirPlay�� ���� ����)
  - ���� ����� ��� ����� ������ ������ ���� turtle_neck.db ������ ���� (�ٽ� �Ѹ� ���� �������)
"""
from flask import Flask, render_template, request, jsonify, Response
import os
from video_stream import FrameStore
import sqlite3
from datetime import datetime

app = Flask(__name__)
video = FrameStore()

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'turtle_neck.db')

# �Ǻ� ���α׷��� ������ �׸� �� ������ �� (�̸�: SQL Ÿ��)
EXTRA_COLUMNS = {
    'user_id': 'TEXT',
    'worse_pct': 'REAL',
    'shoulder_status': 'TEXT',
    'shoulder_tilt': 'REAL',
    'bad_duration': 'REAL',
}
VALID_STATUS = ('����', '���', '����')


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
    # ���� DB ������ �־ �ʿ��� �÷��� �߰� (���� ������ ����)
    existing = {r['name'] for r in conn.execute('PRAGMA table_info(measurements)')}
    for col, typ in EXTRA_COLUMNS.items():
        if col not in existing:
            conn.execute(f'ALTER TABLE measurements ADD COLUMN {col} {typ}')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON measurements(timestamp)')
    conn.commit()
    conn.close()



@app.post('/api/video_frame')
def receive_video_frame():
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
    return '', 204


@app.get('/api/video_status')
def video_status():
    return jsonify(online=video.online())


@app.get('/video_feed')
def video_feed():
    return Response(video.stream(), mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@app.post('/api/status')
def receive_status():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get('status') not in VALID_STATUS:
        return jsonify(result='fail', reason='invalid status'), 400
    return jsonify(result='success', status=data['status'])


@app.route('/api/record', methods=['POST'])
def record_result():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"result": "fail", "reason": "JSON ������ �ƴմϴ�"}), 400

    status = data.get('status')
    if status not in VALID_STATUS:
        return jsonify({"result": "fail", "reason": f"status �� ����: {status}"}), 400

    # �Ǻ� ���α׷��� ���� ���� �ð� �켱 (�и� �����͵� ���� �ð����� ����)
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
                        'WHERE timestamp BETWEEN ? AND ? GROUP BY status',  # �ε��� ���
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


# ���� ���� ��İ� ������� DB �غ�
init_db()

if __name__ == '__main__':
    # ���� �� ���� Ȯ���� �ʿ��ϸ� debug=True, �ÿ������� ���� False
    app.run(host='0.0.0.0', port=5050, debug=False, threaded=True)
