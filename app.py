import sqlite3
import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
DB_PATH = 'my_fridge.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 💡 核心升級：在資料庫內加上「room_name」欄位來區分不同的使用者/家庭
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fridge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT,
            food_name TEXT,
            purchase_date TEXT,
            expiry_date TEXT,
            quantity REAL
        )
    ''')
    conn.commit()
    conn.close()

def save_to_fridge(room, name, expiry, qty):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = str(datetime.date.today())
    cursor.execute('INSERT INTO fridge (room_name, food_name, purchase_date, expiry_date, quantity) VALUES (?, ?, ?, ?, ?)', (room, name, today, expiry, float(qty)))
    conn.commit()
    conn.close()

@app.route("/delete/<int:food_id>")
def delete_food(food_id):
    room = request.args.get("room", "public")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fridge WHERE id = ? AND room_name = ?", (food_id, room))
    conn.commit()
    conn.close()
    return redirect(url_for("index", room=room))

@app.route("/minus_custom/<int:food_id>", methods=["POST"])
def minus_custom(food_id):
    room = request.args.get("room", "public")
    minus_qty = float(request.form.get("minus_qty", 0.25))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM fridge WHERE id = ? AND room_name = ?", (food_id, room))
    row = cursor.fetchone()
    if row:
        currently_qty = row[0]
        new_qty = currently_qty - minus_qty
        if new_qty > 0:
            cursor.execute("UPDATE fridge SET quantity = ? WHERE id = ? AND room_name = ?", (round(new_qty, 2), food_id, room))
        else:
            cursor.execute("DELETE FROM fridge WHERE id = ? AND room_name = ?", (food_id, room))
    conn.commit()
    conn.close()
    return redirect(url_for("index", room=room))

@app.route("/manifest.json")
def manifest():
    app_config = {
        "short_name": "智慧冰箱",
        "name": "再不吃就別吃了-智慧冰箱管理App",
        "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/3050/3050186.png", "type": "image/png", "sizes": "512x512", "purpose": "any maskable"}],
        "start_url": "/", "background_color": "#f4f7f6", "theme_color": "#2ec4b6", "display": "standalone", "orientation": "portrait"
    }
    return jsonify(app_config)

@app.route("/", methods=["GET", "POST"])
def index():
    # 💡 取得當前使用者的冰箱房間密碼，沒填的話預設叫公用冰箱(public)
    room = request.args.get("room", "public")

    if request.method == "POST":
        name = request.form.get("food_name")
        expiry = request.form.get("expiry_date")
        qty = request.form.get("quantity")
        if name and expiry and qty:
            save_to_fridge(room, name, expiry, qty)
        return redirect(url_for("index", room=room))

    search_query = request.args.get("search", "")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 💡 核心過濾：只抓出符合當前房間密碼(room_name)的食材！
    if search_query:
        cursor.execute("SELECT id, food_name, expiry_date, quantity FROM fridge WHERE room_name = ? AND food_name LIKE ? ORDER BY expiry_date ASC", (room, '%' + search_query + '%',))
    else:
        cursor.execute("SELECT id, food_name, expiry_date, quantity FROM fridge WHERE room_name = ? ORDER BY expiry_date ASC", (room,))
    all_foods = cursor.fetchall()
    conn.close()

    today = datetime.date.today()
    processed_foods = []
    for food in all_foods:
        fid, name, expiry_str, qty = food
        expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").date()
        days_left = (expiry_date - today).days
        if days_left < 0:
            status = "expired"
        elif days_left <= 7:
            status = "warning"
        else:
            status = "safe"
        processed_foods.append({"id": fid, "name": name, "expiry": expiry_str, "qty": qty, "days_left": days_left, "status": status})

    return render_template("index.html", foods=processed_foods, search_query=search_query, current_room=room)

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
