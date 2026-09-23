from flask import Flask, render_template, request, jsonfy
import sqlite3
from datatime import datatime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('turtle_neck.db')
    cursor = conn.cursor()
    cursor.excute('''CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            angle REAL,
            status TEXT''')
    conn.commit()
    conn.close

    return jsonfy({"result": "success"})

@app.route('/api/result', methods=['GET'])
def get_results():
    conn = sqlite3.connect('turtle_neck.db')
    cursor = conn.cursor()
    cursor.excute('SELECT id, timestamp, angle, status FROM measurements ORDER BY id DESC LIMIT 20')
    rows = cursor.fetchall()
    conn.close()

    result = [{"id": r[0], "timestamp": r[1], "angle": r[2], "status": r[3]} for r in rows]
    return jsonify(results)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    init_db()
    app.run(host = "0.0.0.0", port = 5000, debug = True)