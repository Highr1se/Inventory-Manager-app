import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "secret-key"

DATA_PATH = os.path.join("data", "inventory.json")

def read_data():
    if not os.path.exists(DATA_PATH):
        os.makedirs("data", exist_ok=True)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump({"products": []}, f, indent=2)
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def write_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def next_id(products):
    return max([p["id"] for p in products], default=0) + 1

@app.route("/")
def index():
    data = read_data()
    products = data["products"]
    total_products = len(products)
    total_units = sum(p["quantity"] for p in products)
    inventory_value = sum(p["price"] * p["quantity"] for p in products)
    low_stock = [p for p in products if p["quantity"] <= p["reorder_level"]]
    return render_template(
        "index.html",
        total_products=total_products,
        total_units=total_units,
        inventory_value=inventory_value,
        low_stock=low_stock,
        recent=products[-5:][::-1]
    )

@app.route("/page1", methods=["GET", "POST"])
def page1():
    data = read_data()
    products = data["products"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        sku = request.form.get("sku", "").strip().upper()
        category = request.form.get("category", "").strip()
        price_raw = request.form.get("price", "").strip()
        qty_raw = request.form.get("quantity", "").strip()
        reorder_raw = request.form.get("reorder_level", "").strip()

        if not name or not sku:
            flash("Name and SKU are required.", "error")
            return redirect(url_for("page1"))

        if any(p["sku"] == sku for p in products):
            flash("That SKU already exists. Please use a unique SKU.", "error")
            return redirect(url_for("page1"))

        try:
            price = float(price_raw)
            quantity = int(qty_raw)
            reorder_level = int(reorder_raw)
            if price < 0 or quantity < 0 or reorder_level < 0:
                raise ValueError
        except ValueError:
            flash("Price must be a number; Quantity/Reorder must be whole numbers (0 or more).", "error")
            return redirect(url_for("page1"))

        products.append({
            "id": next_id(products),
            "name": name,
            "sku": sku,
            "category": category if category else "Uncategorized",
            "price": round(price, 2),
            "quantity": quantity,
            "reorder_level": reorder_level
        })
        write_data(data)
        flash("Product added.", "success")
        return redirect(url_for("page2"))

    return render_template("page1.html")

@app.route("/page2")
def page2():
    data = read_data()
    products = data["products"]

    q = request.args.get("q", "").strip().lower()
    cat = request.args.get("category", "").strip().lower()
    low = request.args.get("low", "").strip()

    filtered = products
    if q:
        filtered = [p for p in filtered if q in p["name"].lower() or q in p["sku"].lower()]
    if cat:
        filtered = [p for p in filtered if cat in p["category"].lower()]
    if low == "1":
        filtered = [p for p in filtered if p["quantity"] <= p["reorder_level"]]

    categories = sorted(set(p["category"] for p in products))
    return render_template("page2.html", products=filtered, categories=categories, q=q, category=cat, low=low)

@app.route("/update/<int:pid>", methods=["POST"])
def update(pid):
    data = read_data()
    products = data["products"]
    change_raw = request.form.get("change", "").strip()

    try:
        change = int(change_raw)
    except ValueError:
        flash("Adjustment must be a whole number (example: 5 or -2).", "error")
        return redirect(url_for("page2"))

    for p in products:
        if p["id"] == pid:
            new_qty = p["quantity"] + change
            if new_qty < 0:
                flash("Quantity cannot go below 0.", "error")
                return redirect(url_for("page2"))
            p["quantity"] = new_qty
            write_data(data)
            flash("Quantity updated.", "success")
            return redirect(url_for("page2"))

    flash("Product not found.", "error")
    return redirect(url_for("page2"))

@app.route("/delete/<int:pid>", methods=["POST"])
def delete(pid):
    data = read_data()
    before = len(data["products"])
    data["products"] = [p for p in data["products"] if p["id"] != pid]
    write_data(data)
    if len(data["products"]) < before:
        flash("Product deleted.", "success")
    else:
        flash("Product not found.", "error")
    return redirect(url_for("page2"))

if __name__ == "__main__":
    app.run(debug=True)