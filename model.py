from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from datetime import datetime
from bson.objectid import ObjectId

app = Flask(__name__)

# -----------------------------
# MongoDB Configuration
# -----------------------------
app.config["MONGO_URI"] = os.getenv("MONGO_URI")

mongo = PyMongo(app)

# -----------------------------
# 1️⃣ Register User
# -----------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    
    user = {
        "name": data["name"],
        "email": data["email"],
        "password": data["password"],
        "role": "user",
        "created_at": datetime.utcnow()
    }
    
    mongo.db.users.insert_one(user)
    
    return jsonify({"message": "User Registered Successfully"})


# -----------------------------
# 2️⃣ Save Scan History
# -----------------------------
@app.route("/save_scan", methods=["POST"])
def save_scan():
    data = request.json
    
    scan = {
        "user_id": data.get("user_id"),  # optional
        "scan_type": data["scan_type"],  # website / qr
        "input_data": data["input_data"],
        "prediction": data["prediction"],
        "confidence": data.get("confidence"),
        "ip_address": request.remote_addr,
        "scanned_at": datetime.utcnow()
    }
    
    mongo.db.scan_history.insert_one(scan)
    
    return jsonify({"message": "Scan Saved Successfully"})


# -----------------------------
# 3️⃣ Report Threat
# -----------------------------
@app.route("/report", methods=["POST"])
def report_threat():
    data = request.json
    
    report = {
        "url": data["url"],
        "reason": data.get("reason"),
        "reported_by": data.get("reported_by"),
        "reported_at": datetime.utcnow()
    }
    
    mongo.db.reported_threats.insert_one(report)
    
    return jsonify({"message": "Threat Reported Successfully"})


# -----------------------------
# 4️⃣ Get User Scan History
# -----------------------------
@app.route("/history/<user_id>", methods=["GET"])
def get_history(user_id):
    
    scans = list(mongo.db.scan_history.find({"user_id": user_id}))
    
    for scan in scans:
        scan["_id"] = str(scan["_id"])
    
    return jsonify(scans)


if __name__ == "__main__":
    app.run(debug=True)