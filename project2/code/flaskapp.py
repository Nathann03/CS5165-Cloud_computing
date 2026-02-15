import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "users.db")

UPLOAD_DIR = os.path.join(APP_DIR, "static", "uploads")
DOWNLOAD_DIR = os.path.join(APP_DIR, "static", "downloads")

app = Flask(__name__)
app.secret_key = "replace-this-with-any-random-string"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            firstname TEXT NOT NULL,
            lastname TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            uploaded_filename TEXT,
            uploaded_word_count INTEGER
        )
    """)
    conn.commit()
    conn.close()

def get_user_by_username(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT username, password, firstname, lastname, email, address, uploaded_filename, uploaded_word_count
        FROM users
        WHERE username = ?
    """, (username,))
    row = c.fetchone()
    conn.close()
    return row

def update_upload_info(username: str, filename: str, word_count: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users
        SET uploaded_filename = ?, uploaded_word_count = ?
        WHERE username = ?
    """, (filename, word_count, username))
    conn.commit()
    conn.close()

@app.route("/", methods=["GET"])
def register_page():
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def register():
    init_db()

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    firstname = request.form.get("firstname", "").strip()
    lastname = request.form.get("lastname", "").strip()
    email = request.form.get("email", "").strip()
    address = request.form.get("address", "").strip()

    if not all([username, password, firstname, lastname, email, address]):
        flash("Please fill out all fields.")
        return redirect(url_for("register_page"))

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (username, password, firstname, lastname, email, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password, firstname, lastname, email, address))
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        flash("Username already exists. Please choose another.")
        return redirect(url_for("register_page"))

    return redirect(url_for("profile", username=username))

@app.route("/profile/<username>", methods=["GET"])
def profile(username):
    init_db()
    user = get_user_by_username(username)
    if not user:
        flash("User not found.")
        return redirect(url_for("login_page"))

    return render_template("profile.html", user=user)

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    init_db()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    user = get_user_by_username(username)
    if not user:
        flash("No such user.")
        return redirect(url_for("login_page"))

    stored_password = user[1]
    if password != stored_password:
        flash("Incorrect password.")
        return redirect(url_for("login_page"))

    return redirect(url_for("profile", username=username))

@app.route("/upload/<username>", methods=["POST"])
def upload(username):
    init_db()
    user = get_user_by_username(username)
    if not user:
        flash("User not found.")
        return redirect(url_for("login_page"))

    if "file" not in request.files:
        flash("No file selected.")
        return redirect(url_for("profile", username=username))

    f = request.files["file"]
    if f.filename == "":
        flash("No file selected.")
        return redirect(url_for("profile", username=username))

    # Enforce Limerick.txt for the assignment (you can relax if desired)
    if f.filename.lower() != "limerick.txt":
        flash("Please upload Limerick.txt")
        return redirect(url_for("profile", username=username))

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    saved_name = f"{username}_Limerick.txt"
    upload_path = os.path.join(UPLOAD_DIR, saved_name)
    f.save(upload_path)

    # Word count
    with open(upload_path, "r", encoding="utf-8", errors="ignore") as fp:
        text = fp.read()
    word_count = len(text.split())

    # Store a copy to downloads folder (so download is easy)
    download_path = os.path.join(DOWNLOAD_DIR, saved_name)
    with open(download_path, "w", encoding="utf-8") as out:
        out.write(text)

    update_upload_info(username, saved_name, word_count)

    return redirect(url_for("profile", username=username))

@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
