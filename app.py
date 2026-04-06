from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# -------------------------------
# GLOBAL STATE (NO DATABASE)
# -------------------------------
ride_data = {
    "requested": False,
    "accepted": False,
    "otp": None,
    "verified": False,
    "completed": False,
    "fare": 0,
    "paid": False
}

# -------------------------------
# ROUTES
# -------------------------------

# 🔥 MAIN CLIENT PAGE (NO LOGIN NOW)
@app.route("/")
def home():
    return render_template("client_dashboard.html")


# 🚘 DRIVER PAGE
@app.route("/driver")
def driver():
    return render_template("driver.html")


# -------------------------------
# SOCKET EVENTS
# -------------------------------

@socketio.on("connect")
def connect():
    print("🔌 Client connected")


# 🚕 CLIENT BOOKS RIDE
@socketio.on("book_ride")
def book_ride(data):
    print("🚕 Ride requested:", data)

    ride_data["requested"] = True
    ride_data["accepted"] = False
    ride_data["verified"] = False
    ride_data["completed"] = False
    ride_data["paid"] = False

    emit("new_request", data, broadcast=True)


# ✅ DRIVER ACCEPTS RIDE
@socketio.on("accept_ride")
def accept_ride():
    if not ride_data["requested"]:
        return

    print("✅ Driver accepted ride")

    ride_data["accepted"] = True
    ride_data["otp"] = random.randint(1000, 9999)

    print(f"🔑 OTP: {ride_data['otp']}")

    emit("ride_accepted", {"otp": ride_data["otp"]}, broadcast=True)


# 🔐 DRIVER VERIFIES OTP
@socketio.on("verify_otp")
def verify_otp(data):
    if str(data.get("otp")) == str(ride_data["otp"]):
        print("🔓 OTP Verified → Ride Started")

        ride_data["verified"] = True
        emit("otp_success", broadcast=True)
    else:
        print("❌ Wrong OTP")
        emit("otp_failed")


# 🏁 DRIVER COMPLETES RIDE
@socketio.on("complete_ride")
def complete_ride():
    if not ride_data["verified"]:
        return

    ride_data["completed"] = True
    ride_data["fare"] = random.randint(100, 500)

    print(f"💰 Ride completed. Fare: ₹{ride_data['fare']}")

    emit("ride_completed", {"fare": ride_data["fare"]}, broadcast=True)


# 💳 CLIENT MAKES PAYMENT
@socketio.on("make_payment")
def make_payment(data):
    try:
        amount = int(data.get("amount"))
    except:
        emit("payment_failed")
        return

    if amount == ride_data["fare"]:
        ride_data["paid"] = True

        print("📩 SMS: Payment received successfully")

        emit("payment_success", broadcast=True)
    else:
        print("❌ Incorrect payment")
        emit("payment_failed")


# -------------------------------
# RUN SERVER
# -------------------------------
if __name__ == "__main__":
    socketio.run(app, debug=True)
    #socketio.run(app, host="0.0.0.0", port=5000, debug=True)