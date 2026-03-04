from flask import Flask, render_template, request, jsonify, redirect, session
import numpy as np
import pickle
import os
import re
import cv2
from urllib.parse import urlparse
from sklearn.neural_network import MLPClassifier
from flask_pymongo import PyMongo
import qrcode
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ------------------------------
# MongoDB Configuration
# ------------------------------
app.config["MONGO_URI"] = "mongodb://localhost:27017/securescan"
mongo = PyMongo(app)

# Ensure QR folder exists
if not os.path.exists("static/qrs"):
    os.makedirs("static/qrs")

# ------------------------------
# 1️⃣ Load or Create MLP Model
# ------------------------------
def get_model():
    model_path = 'model.pkl'
    if not os.path.exists(model_path):
        X_train = np.random.randint(0, 2, (200, 16))
        y_train = np.random.randint(0, 2, 200)

        mlp = MLPClassifier(hidden_layer_sizes=(16, 8), max_iter=500)
        mlp.fit(X_train, y_train)

        with open(model_path, 'wb') as f:
            pickle.dump(mlp, f)

    with open(model_path, 'rb') as f:
        return pickle.load(f)

loaded_model = get_model()

# ------------------------------
# 2️⃣ Feature Extraction (16 Features)
# ------------------------------
def extract_features(url):
    features = [
        1 if re.search(r'(([0-9]{1,3}\.){3}[0-9]{1,3})', url) else 0,
        1 if "@" in url else 0,
        1 if len(url) >= 54 else 0,
        len(urlparse(url).path.split('/')) - 1,
        1 if url.rfind('//') > 7 else 0,
        1 if 'https' not in url else 0,
        1 if re.search(r"bit\.ly|goo\.gl|t\.co", url) else 0,
        1 if '-' in urlparse(url).netloc else 0,
    ]

    while len(features) < 16:
        features.append(0)

    return features

# ------------------------------
# 3️⃣ Routes
# ------------------------------

@app.route("/")
def home():
    if "user_id" in session:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        return render_template("index.html", user=user)
    return render_template("index.html", user=None)

# ------------------------------
# Login
# ------------------------------
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    user = mongo.db.users.find_one({"email": email, "password": password})

    if user:
        session["user_id"] = user["_id"]

    return redirect("/")

# ------------------------------
# Register
# ------------------------------
@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    mongo.db.users.insert_one({
        "name": name,
        "email": email,
        "password": password,
        "links": []
    })

    return redirect("/")

# ------------------------------
# Generate QR Code
# ------------------------------
@app.route("/generate_qr", methods=["POST"])
def generate_qr():
    if "user_id" not in session:
        return redirect("/")

    link = request.form["link"]

    # Unique filename using timestamp
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    path = os.path.join("static/qrs", filename)

    img = qrcode.make(link)
    img.save(path)

    mongo.db.users.update_one(
        {"_id": session["user_id"]},
        {"$push": {"links": {
            "originalLink": link,
            "qrPath": path
        }}}
    )

    return redirect("/")

# ------------------------------
# Logout
# ------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ------------------------------
# URL Text Prediction
# ------------------------------
@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        url = data.get('url', '')

        if not url:
            return jsonify({"result": "⚠️ Please enter a URL"}), 400

        features = np.array(extract_features(url)).reshape(1, -1)
        prediction = loaded_model.predict(features)

        status = "🚨 PHISHING ALERT!" if prediction == 1 else "✅ URL IS SAFE"

        return jsonify({
            "result": status,
            "url": url
        })

    except Exception as e:
        return jsonify({"result": f"Error: {str(e)}"}), 500

# ------------------------------
@app.route('/predict_qr', methods=['POST'])
def predict_qr():
    try:
        if 'file' not in request.files:
            return jsonify({"result": "❌ No file uploaded"}), 400

        file = request.files['file']
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"result": "❌ Invalid image file"}), 400

        detector = cv2.QRCodeDetector()

        # Try detecting QR
        data, bbox, _ = detector.detectAndDecode(img)

        if not data:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            data, bbox, _ = detector.detectAndDecode(gray)

        if not data:
            resized = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            data, bbox, _ = detector.detectAndDecode(resized)

        if not data:
            return jsonify({"result": "❌ QR Code Not Detected"}), 400

        # -----------------------------
        # ✅ NEW: Payment QR Detection
        # -----------------------------
        if data.lower().startswith("upi://"):
            return jsonify({
                "result": "💳 SAFE PAYMENT QR CODE",
                "url": data
            })

        # -----------------------------
        # Normal URL phishing check
        # -----------------------------
        features = np.array(extract_features(data)).reshape(1, -1)
        prediction = loaded_model.predict(features)

        status = "🚨 PHISHING ALERT!" if prediction == 1 else "✅ URL IS SAFE"

        return jsonify({
            "result": status,
            "url": data
        })

    except Exception as e:
        return jsonify({"result": f"Error: {str(e)}"}), 500
# Run App
# ------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)