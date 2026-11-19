from flask import Flask, render_template, request, redirect, session, flash, g
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "pointstrack-secret"
DB = "loyalty.db"

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DB)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT);
    CREATE TABLE IF NOT EXISTS members (id TEXT PRIMARY KEY, name TEXT, phone TEXT UNIQUE, points INTEGER DEFAULT 0, created_at TEXT);
    CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id TEXT, receipt TEXT UNIQUE, amount REAL, points INTEGER, cashier TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id TEXT, type TEXT, points INTEGER, amount REAL, receipt TEXT, description TEXT, cashier TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS disputes (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id TEXT, type TEXT, description TEXT, status TEXT DEFAULT 'Open', created_at TEXT);
    CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, action TEXT, details TEXT, created_at TEXT);
    """)
    cur = db.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        db.execute("INSERT INTO users (username,password,role) VALUES ('admin','admin123','admin')")
    db.commit(); db.close()

def log(username, action, details=""):
    db = get_db()
    db.execute("INSERT INTO activity (username,action,details,created_at) VALUES (?,?,?,?)", (username, action, details, datetime.now().strftime("%Y-%m-%d %H:%M")))
    db.commit()

def need_login():
    return "username" not in session

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE username=? AND password=?", (request.form["username"], request.form["password"])).fetchone()
        if u:
            session["username"] = u["username"]; session["role"] = u["role"]
            log(u["username"], "Login", "Logged in")
            return redirect("/dashboard")
        flash("Wrong username or password")
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        db = get_db()
        try:
            db.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", (request.form["username"], request.form["password"], request.form["role"]))
            db.commit(); flash("Account created! Now login."); return redirect("/")
        except: flash("Username already taken")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect("/")

@app.route("/dashboard")
def dashboard():
    if need_login(): return redirect("/")
    db = get_db()
    total_members = db.execute("SELECT COUNT(*) c FROM members").fetchone()["c"]
    total_purchases = db.execute("SELECT COUNT(*) c FROM purchases").fetchone()["c"]
    total_points = db.execute("SELECT COALESCE(SUM(points),0) s FROM purchases").fetchone()["s"]
    total_redeemed = db.execute("SELECT COALESCE(SUM(ABS(points)),0) s FROM transactions WHERE type='Redeem'").fetchone()["s"]
    open_disputes = db.execute("SELECT COUNT(*) c FROM disputes WHERE status='Open'").fetchone()["c"]
    outstanding = db.execute("SELECT COALESCE(SUM(points),0) s FROM members").fetchone()["s"]
    recent = db.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 5").fetchall()
    return render_template("dashboard.html", total_members=total_members, total_purchases=total_purchases, total_points=total_points, total_points_issued=total_points, total_redeemed=total_redeemed, open_disputes=open_disputes, outstanding=outstanding, recent=recent, recent_activity=recent)

@app.route("/members", methods=["GET","POST"])
def members():
    if need_login(): return redirect("/")
    db = get_db()
    if request.method == "POST":
        name = request.form["name"].strip(); phone = request.form["phone"].strip()
        count = db.execute("SELECT COUNT(*) c FROM members").fetchone()["c"]
        card = f"LC-{count+1:04d}"
        try:
            db.execute("INSERT INTO members (id,name,phone,points,created_at) VALUES (?,?,?,?,?)", (card, name, phone, 0, datetime.now().strftime("%Y-%m-%d")))
            db.commit(); log(session["username"], "Enrol Member", f"{name} {card}"); flash(f"Member enrolled! Card: {card}")
        except: flash("Phone number already exists")
        return redirect("/members")
    q = request.args.get("q","").strip()
    if q:
        like = f"%{q}%"
        members = db.execute("SELECT * FROM members WHERE name LIKE ? OR id LIKE ? OR phone LIKE ? ORDER BY id DESC", (like,like,like)).fetchall()
    else:
        members = db.execute("SELECT * FROM members ORDER BY id DESC").fetchall()
    return render_template("members.html", members=members, q=q)

@app.route("/member-history", methods=["GET","POST"])
def member_history():
    if need_login(): return redirect("/")
    db = get_db()
    mid = request.args.get("id","")
    m = db.execute("SELECT * FROM members WHERE id=?", (mid,)).fetchone()
    if not m: return redirect("/members")
    if request.method == "POST":
        try: pts = int(request.form.get("points",0))
        except: pts = 0
        if pts <= 0: flash("Enter points more than 0")
        elif pts > m["points"]: flash("Cannot redeem more than balance")
        else:
            db.execute("UPDATE members SET points=points-? WHERE id=?", (pts, mid))
            db.execute("INSERT INTO transactions (member_id,type,points,amount,receipt,description,cashier,created_at) VALUES (?,?,?,?,?,?,?,?)", (mid,"Redeem",-pts,pts,"","Redeemed points",session["username"],datetime.now().strftime("%Y-%m-%d %H:%M")))
            db.commit(); log(session["username"], "Redeem", f"{mid} redeemed {pts}"); flash(f"Redeemed {pts} points!")
            return redirect(f"/member-history?id={mid}")
    hist = db.execute("SELECT * FROM transactions WHERE member_id=? ORDER BY id DESC", (mid,)).fetchall()
    return render_template("member-history.html", member=m, m=m, history=hist, transactions=hist)

@app.route("/purchase", methods=["GET","POST"])
def purchase():
    if need_login(): return redirect("/")
    if request.method == "POST":
        db = get_db()
        mid = request.form["member_id"].strip().upper(); receipt = request.form["receipt"].strip()
        try: amount = float(request.form["amount"])
        except: flash("Invalid amount"); return redirect("/purchase")
        m = db.execute("SELECT * FROM members WHERE id=?", (mid,)).fetchone()
        if not m: flash("Member not found"); return redirect("/purchase")
        if db.execute("SELECT * FROM purchases WHERE receipt=?", (receipt,)).fetchone():
            flash("Receipt already rewarded!"); return redirect("/purchase")
        pts = int(amount // 100)
        db.execute("INSERT INTO purchases (member_id,receipt,amount,points,cashier,created_at) VALUES (?,?,?,?,?,?)", (mid,receipt,amount,pts,session["username"],datetime.now().strftime("%Y-%m-%d %H:%M")))
        db.execute("UPDATE members SET points=points+? WHERE id=?", (pts,mid))
        db.execute("INSERT INTO transactions (member_id,type,points,amount,receipt,description,cashier,created_at) VALUES (?,?,?,?,?,?,?,?)", (mid,"Purchase",pts,amount,receipt,f"Purchase {receipt}",session["username"],datetime.now().strftime("%Y-%m-%d %H:%M")))
        db.commit(); log(session["username"], "Purchase", f"{mid} {receipt} {pts} pts"); flash(f"Purchase recorded! {pts} points awarded to {m['name']}")
        return redirect("/purchase")
    return render_template("purchase.html")

@app.route("/disputes", methods=["GET","POST"])
def disputes():
    if need_login(): return redirect("/")
    db = get_db()
    if request.method == "POST":
        db.execute("INSERT INTO disputes (member_id,type,description,status,created_at) VALUES (?,?,?,?,?)", (request.form.get("member_id","").strip().upper(), request.form.get("type",""), request.form.get("description",""), "Open", datetime.now().strftime("%Y-%m-%d")))
        db.commit(); log(session["username"], "Dispute", "New dispute logged"); flash("Dispute logged!")
        return redirect("/disputes")
    rows = db.execute("SELECT * FROM disputes ORDER BY id DESC").fetchall()
    return render_template("disputes.html", disputes=rows)

@app.route("/activity")
def activity():
    if need_login(): return redirect("/")
    db = get_db()
    rows = db.execute("SELECT * FROM activity ORDER BY id DESC").fetchall()
    return render_template("activity.html", activity=rows, logs=rows)

@app.route("/reports")
def reports():
    if need_login(): return redirect("/")
    db = get_db()
    total_purchases = db.execute("SELECT COUNT(*) c FROM purchases").fetchone()["c"]
    total_sales = db.execute("SELECT COALESCE(SUM(amount),0) s FROM purchases").fetchone()["s"]
    total_points = db.execute("SELECT COALESCE(SUM(points),0) s FROM purchases").fetchone()["s"]
    outstanding = db.execute("SELECT COALESCE(SUM(points),0) s FROM members").fetchone()["s"]
    by_cashier = db.execute("SELECT cashier as username, COALESCE(SUM(points),0) points FROM purchases GROUP BY cashier").fetchall()
    return render_template("reports.html", total_purchases=total_purchases, total_sales=total_sales, total_points=total_points, outstanding=outstanding, by_cashier=by_cashier)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)