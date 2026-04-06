from flask import Flask, request, jsonify
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)

ride = {
    "status": "idle",
    "driver": "Driver1",
    "price": 0,
    "ride_otp": None,
    "paid": False
}

@app.route('/book', methods=['POST'])
def book():
    ride["status"] = "requested"
    ride["price"] = random.randint(100, 300)
    ride["ride_otp"] = None   # reset OTP
    ride["paid"] = False
    return jsonify({"price": ride["price"]})

@app.route('/driver/status')
def status():
    return jsonify(ride)

@app.route('/driver/accept', methods=['POST'])
def accept():
    ride["status"] = "accepted"
    ride["ride_otp"] = str(random.randint(1000, 9999))
    return jsonify({"otp": ride["ride_otp"]})

@app.route('/verify-ride-otp', methods=['POST'])
def verify():
    if request.json['otp'] == ride["ride_otp"]:
        ride["status"] = "ongoing"
        return jsonify({"status": "success"})
    return jsonify({"status": "failed"})

@app.route('/complete', methods=['POST'])
def complete():
    ride["status"] = "completed"
    return jsonify({"msg": "done"})

@app.route('/pay', methods=['POST'])
def pay():
    amount = int(request.json['amount'])

    if amount != ride["price"]:
        return jsonify({"status": "failed", "msg": "Wrong amount"})

    ride["paid"] = True
    return jsonify({"status": "success"})

app.run(host="0.0.0.0", port=5000, debug=True)