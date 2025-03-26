from flask import Blueprint, request, jsonify, send_file
from database import get_db_connection
from flask_bcrypt import Bcrypt
import pyotp
import qrcode
from io import BytesIO
from flask_jwt_extended import create_access_token
from datetime import timedelta

password_hasher = Bcrypt()
auth_endpoints = Blueprint("auth", __name__)

@auth_endpoints.route("/register", methods=["POST"])
def user_registration():
    registration_data = request.json
    user_name = registration_data.get("username")
    user_password = registration_data.get("password")

    if not user_name or not user_password:
        return jsonify({"error": "Username and password required"}), 400

    encrypted_password = password_hasher.generate_password_hash(user_password).decode("utf-8")
    fa_secret = pyotp.random_base32()

    db = get_db_connection()
    cur = db.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password, twofa_secret) VALUES (%s, %s, %s)",
            (user_name, encrypted_password, fa_secret),
        )
        db.commit()
        return jsonify({"message": "Registration successful", "2FA_secret": fa_secret}), 201
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cur.close()
        db.close()

@auth_endpoints.route("/login", methods=["POST"])
def user_login():
    login_data = request.json
    user_name = login_data.get("username")
    user_password = login_data.get("password")

    if not user_name or not user_password:
        return jsonify({"error": "Username and password required"}), 400

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM users WHERE username = %s", (user_name,))
    user_record = cur.fetchone()

    cur.close()
    db.close()

    if not user_record or not password_hasher.check_password_hash(user_record["password"], user_password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "2FA verification needed"}), 200

@auth_endpoints.route("/generate_qr/<username>", methods=["GET"])
def create_qr_code(username):
    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT twofa_secret FROM users WHERE username = %s", (username,))
    user_record = cur.fetchone()

    cur.close()
    db.close()

    if not user_record:
        return jsonify({"error": "User not found"}), 404

    secret_key = user_record["twofa_secret"]
    auth_uri = pyotp.TOTP(secret_key).provisioning_uri(name=username, issuer_name="FlaskAuthApp")

    qr_config = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=2,
    )
    qr_config.add_data(auth_uri)
    qr_config.make(fit=True)

    qr_image = qr_config.make_image(fill="black", back_color="white")

    image_buffer = BytesIO()
    qr_image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    return send_file(image_buffer, mimetype="image/png")

@auth_endpoints.route("/verify_2fa", methods=["POST"])
def verify_two_factor():
    verification_data = request.json
    user_name = verification_data.get("username")
    auth_code = verification_data.get("otp_code")

    if not user_name or not auth_code:
        return jsonify({"error": "Username and 2FA code required"}), 400

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT twofa_secret FROM users WHERE username = %s", (user_name,))
    user_record = cur.fetchone()

    cur.close()
    db.close()

    if not user_record:
        return jsonify({"error": "User not found"}), 404

    secret_key = user_record["twofa_secret"]
    authenticator = pyotp.TOTP(secret_key, interval=30)
    valid_code = authenticator.verify(auth_code, valid_window=2)

    if not valid_code:
        return jsonify({"error": "Invalid 2FA code"}), 401

    return jsonify({"message": "2FA verification passed"}), 200

@auth_endpoints.route("/login_2fa", methods=["POST"])
def complete_login():
    login_data = request.json
    user_name = login_data.get("username")
    auth_code = login_data.get("otp_code")

    if not user_name or not auth_code:
        return jsonify({"error": "Username and 2FA code required"}), 400

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT twofa_secret FROM users WHERE username = %s", (user_name,))
    user_record = cur.fetchone()

    cur.close()
    db.close()

    if not user_record:
        return jsonify({"error": "User not found"}), 404

    secret_key = user_record["twofa_secret"]
    authenticator = pyotp.TOTP(secret_key, interval=30)
    valid_code = authenticator.verify(auth_code, valid_window=2)

    if not valid_code:
        return jsonify({"error": "Invalid 2FA code"}), 401

    auth_token = create_access_token(identity=user_name, expires_delta=timedelta(minutes=10))
    return jsonify({"message": "Login complete", "token": auth_token}), 200