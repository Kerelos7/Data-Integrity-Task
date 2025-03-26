from flask import Blueprint, request, jsonify
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

product_routes = Blueprint("products", __name__)

@product_routes.route("/products", methods=["POST"])
@jwt_required()
def create_product():
    product_data = request.json
    product_name = product_data.get("name")
    product_description = product_data.get("description", "")
    product_price = product_data.get("price")

    if not product_name or product_price is None:
        return jsonify({"error": "Name and price are required fields"}), 400

    db = get_db_connection()
    cur = db.cursor()

    try:
        cur.execute(
            "INSERT INTO products (name, description, price) VALUES (%s, %s, %s)",
            (product_name, product_description, product_price)
        )
        db.commit()
        return jsonify({"message": "Product created successfully"}), 201
    except Exception as error:
        return jsonify({"error": str(error)}), 500
    finally:
        cur.close()
        db.close()

@product_routes.route("/products", methods=["GET"])
@jwt_required()
def list_products():
    search_name = request.args.get("name")
    price_min = request.args.get("min_price")
    price_max = request.args.get("max_price")

    base_query = "SELECT * FROM products"
    conditions = []
    parameters = []

    if search_name:
        conditions.append("name LIKE %s")
        parameters.append(f"%{search_name}%")
    if price_min:
        conditions.append("price >= %s")
        parameters.append(price_min)
    if price_max:
        conditions.append("price <= %s")
        parameters.append(price_max)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute(base_query, tuple(parameters))
    items = cur.fetchall()

    cur.close()
    db.close()

    return jsonify({"products": items}), 200

@product_routes.route("/products/<int:item_id>", methods=["GET"])
@jwt_required()
def fetch_product(item_id):
    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM products WHERE id = %s", (item_id,))
    item = cur.fetchone()

    cur.close()
    db.close()

    if not item:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(item), 200

@product_routes.route("/products/<int:item_id>", methods=["PUT"])
@jwt_required()
def modify_product(item_id):
    update_data = request.json
    new_name = update_data.get("name")
    new_description = update_data.get("description", "")
    new_price = update_data.get("price")

    if not new_name or new_price is None:
        return jsonify({"error": "Name and price are required fields"}), 400

    db = get_db_connection()
    cur = db.cursor()

    cur.execute("SELECT * FROM products WHERE id = %s", (item_id,))
    exists = cur.fetchone()

    if not exists:
        return jsonify({"error": "Product not found"}), 404

    try:
        cur.execute(
            "UPDATE products SET name = %s, description = %s, price = %s WHERE id = %s",
            (new_name, new_description, new_price, item_id)
        )
        db.commit()
        return jsonify({"message": "Product updated successfully"}), 200
    except Exception as error:
        return jsonify({"error": str(error)}), 500
    finally:
        cur.close()
        db.close()

@product_routes.route("/products/<int:item_id>", methods=["DELETE"])
@jwt_required()
def remove_product(item_id):
    db = get_db_connection()
    cur = db.cursor()

    cur.execute("SELECT * FROM products WHERE id = %s", (item_id,))
    exists = cur.fetchone()

    if not exists:
        return jsonify({"error": "Product not found"}), 404

    try:
        cur.execute("DELETE FROM products WHERE id = %s", (item_id,))
        db.commit()
        return jsonify({"message": "Product deleted successfully"}), 200
    except Exception as error:
        return jsonify({"error": str(error)}), 500
    finally:
        cur.close()
        db.close()