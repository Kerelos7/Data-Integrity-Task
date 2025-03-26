from flask import Flask
from flask_jwt_extended import JWTManager
from config import Config
from auth import auth_bp
from products import products_bp  

flask_app = Flask(__name__)  
flask_app.config.from_object(Config)

if not flask_app.config.get("JWT_SECRET_KEY"):
    raise RuntimeError("⚠️ Critical: JWT_SECRET_KEY is not set in Config!")

jwt_manager = JWTManager(flask_app)

flask_app.register_blueprint(auth_bp, url_prefix="/auth")
flask_app.register_blueprint(products_bp, url_prefix="/api") 

print("🔍 Available Endpoints:")
for route in flask_app.url_map.iter_rules():
    print(f"→ {route}")

if __name__ == "__main__":
    try:
        flask_app.run(debug=True)
    except Exception as error:
        print(f"❌ Failed to start server: {error}")