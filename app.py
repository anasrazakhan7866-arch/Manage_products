from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import date

app = Flask(__name__)
app.secret_key = "pharma_secret"
conn = mysql.connector.connect(
    host=os.environ.get("MYSQLHOST"),
    user=os.environ.get("MYSQLUSER"),
    password=os.environ.get("MYSQLPASSWORD"),
    database=os.environ.get("MYSQLDATABASE"),
    port=os.environ.get("MYSQLPORT")
)

# ---------- DATABASE CONNECTION ----------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",   # 🔴 CHANGE THIS
        database="ppharma_db"
    )


# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("home.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        db = get_db()
        cur = db.cursor(dictionary=True, buffered=True)

        cur.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cur.fetchone()
        cur.close()
        db.close()

        if user:
            session["user"] = user["username"]
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()

        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, password)
        )
        db.commit()

        cur.close()
        db.close()

        return redirect("/login")

    return render_template("register.html")


# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return render_template("dashboard.html")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------- MEDICINES ----------
@app.route("/medicines", methods=["GET", "POST"])
def medicines():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        batch = request.form["batch"]
        price = request.form["price"]
        qty = request.form["quantity"]
        expiry = request.form["expiry"]

        cur.execute(
            """INSERT INTO medicines 
               (name, batch_no, price, quantity, expiry_date) 
               VALUES (%s, %s, %s, %s, %s)""",
            (name, batch, price, qty, expiry)
        )
        db.commit()

    cur.execute("SELECT * FROM medicines")
    meds = cur.fetchall()

    cur.close()
    db.close()

    return render_template("medicines.html", medicines=meds)

#___delete medicine___
@app.route("/delete_medicine/<int:med_id>", methods=["POST"])
def delete_medicine(med_id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    cur.execute("DELETE FROM medicines WHERE id=%s", (med_id,))
    db.commit()

    cur.close()
    db.close()

    return redirect(url_for("medicines"))


# ---------- SALES ----------
@app.route("/sales", methods=["GET", "POST"])
def sales():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "POST":
        med_id = request.form["medicine_id"]
        qty = int(request.form["quantity"])

        cur.execute("SELECT * FROM medicines WHERE id=%s", (med_id,))
        med = cur.fetchone()

        if med and med["quantity"] >= qty:
            total = qty * med["price"]

            cur.execute(
                """INSERT INTO sales 
                   (medicine_id, quantity, total_price, sale_date) 
                   VALUES (%s, %s, %s, CURDATE())""",
                (med_id, qty, total)
            )

            cur.execute(
                "UPDATE medicines SET quantity = quantity - %s WHERE id=%s",
                (qty, med_id)
            )

            db.commit()

    cur.execute("SELECT * FROM medicines")
    meds = cur.fetchall()

    cur.execute("""
        SELECT s.id, m.name, s.quantity, s.total_price, s.sale_date
        FROM sales s
        JOIN medicines m ON s.medicine_id = m.id
    """)
    sales_data = cur.fetchall()

    cur.close()
    db.close()

    return render_template("sales.html", medicines=meds, sales=sales_data)


# ---------- DELETE SALE ----------
@app.route("/delete_sale/<int:sale_id>", methods=["POST"])
def delete_sale(sale_id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM sales WHERE id=%s", (sale_id,))
    sale = cur.fetchone()

    if sale:
        cur.execute(
            "UPDATE medicines SET quantity = quantity + %s WHERE id=%s",
            (sale["quantity"], sale["medicine_id"])
        )

        cur.execute("DELETE FROM sales WHERE id=%s", (sale_id,))
        db.commit()

    cur.close()
    db.close()

    return redirect(url_for("sales"))


# ---------- BILL ----------
@app.route("/bill/<int:sale_id>")
def bill(sale_id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT s.id, m.name, s.quantity, s.total_price, s.sale_date
        FROM sales s
        JOIN medicines m ON s.medicine_id = m.id
        WHERE s.id=%s
    """, (sale_id,))

    bill = cur.fetchone()

    cur.close()
    db.close()

    return render_template("bill.html", bill=bill)


# ---------- EXPIRY ----------
@app.route("/expiry")
def expiry():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT * FROM medicines
        WHERE expiry_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
    """)

    data = cur.fetchall()

    cur.close()
    db.close()

    return render_template("expiry.html", medicines=data)

# ---------- ANALYTICS REPORT ----------
# ---------- ANALYTICS REPORT ----------
@app.route("/analytics")
def analytics():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    # ----- OVERALL SUMMARY -----
    cur.execute("SELECT SUM(total_price) AS total_sales, COUNT(*) AS total_orders FROM sales")
    summary = cur.fetchone()

    total_sales = summary["total_sales"] if summary["total_sales"] else 0
    total_orders = summary["total_orders"]

    # ----- MONTHLY REPORT -----
    cur.execute("""
        SELECT DATE_FORMAT(sale_date, '%Y-%m') AS month,
               SUM(total_price) AS total_sales,
               COUNT(*) AS total_orders
        FROM sales
        GROUP BY month
        ORDER BY month DESC
    """)
    monthly_report = cur.fetchall()

    # ----- YEARLY REPORT -----
    cur.execute("""
        SELECT YEAR(sale_date) AS year,
               SUM(total_price) AS total_sales,
               COUNT(*) AS total_orders
        FROM sales
        GROUP BY year
        ORDER BY year DESC
    """)
    yearly_report = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        "analytics.html",
        total_sales=total_sales,
        total_orders=total_orders,
        monthly_report=monthly_report,
        yearly_report=yearly_report
    )


# ---------- RUN ----------
import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
