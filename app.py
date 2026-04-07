from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# -------------------------------
# GLOBAL STATE (NO DATABASE)
# -------------------------------

# Pending ride requests from clients (not yet accepted by a driver)
# Structure: { ride_id: { source, dest, client_sid, ride_id } }
pending_rides = {}

# Active rides (accepted by a driver)
# Structure: { ride_id: { source, dest, client_sid, driver_sid, otp, verified, completed, fare, paid } }
active_rides = {}

# Map socket IDs to ride IDs for quick lookup
# client_sid -> ride_id
client_to_ride = {}

# driver_sid -> ride_id
driver_to_ride = {}


# -------------------------------
# ROUTES
# -------------------------------

@app.route("/")
def home():
    return render_template("landing.html")


@app.route("/client")
def client():
    return render_template("client.html")


@app.route("/driver")
def driver():
    return render_template("driver.html")


# -------------------------------
# HELPERS
# -------------------------------

def broadcast_pending_rides(driver_sid=None):
    """Send the current pending ride list to all drivers (or a specific driver)."""
    rides_list = [
        {
            "ride_id": r["ride_id"],
            "source": r["source"],
            "dest": r["dest"],
        }
        for r in pending_rides.values()
    ]

    if driver_sid:
        # Send only to a specific driver (e.g., on connect)
        emit("pending_rides_update", rides_list, to=driver_sid)
    else:
        # Broadcast to all connected drivers
        socketio.emit("pending_rides_update", rides_list)


# -------------------------------
# SOCKET EVENTS
# -------------------------------

@socketio.on("connect")
def on_connect():
    sid = socketio.server.environ.get("socketio") 
    print(f"🔌 Client connected: {_sid()}")


@socketio.on("disconnect")
def on_disconnect():
    sid = _sid()
    print(f"🔌 Client disconnected: {sid}")

    # If a client disconnects, remove their pending ride
    if sid in client_to_ride:
        ride_id = client_to_ride.pop(sid)
        if ride_id in pending_rides:
            del pending_rides[ride_id]
            broadcast_pending_rides()
            print(f"🗑️ Removed pending ride {ride_id} (client disconnected)")

        # If the ride was active, notify the driver
        if ride_id in active_rides:
            driver_sid = active_rides[ride_id].get("driver_sid")
            if driver_sid:
                emit("client_disconnected", {"ride_id": ride_id}, to=driver_sid)
            del active_rides[ride_id]

    # If a driver disconnects mid-ride, notify the client
    if sid in driver_to_ride:
        ride_id = driver_to_ride.pop(sid)
        if ride_id in active_rides:
            client_sid = active_rides[ride_id].get("client_sid")
            if client_sid:
                emit("driver_disconnected", {"ride_id": ride_id}, to=client_sid)
            del active_rides[ride_id]


def _sid():
    """Get current socket session ID."""
    from flask import request
    return request.sid


# -------------------------------
# CLIENT: BOOK RIDE
# -------------------------------

@socketio.on("book_ride")
def book_ride(data):
    from flask import request
    sid = request.sid

    # Remove any old pending ride for this client
    if sid in client_to_ride:
        old_ride_id = client_to_ride[sid]
        pending_rides.pop(old_ride_id, None)

    ride_id = str(uuid.uuid4())[:8]  # Short unique ID
    ride = {
        "ride_id": ride_id,
        "source": data.get("source", "Unknown"),
        "dest": data.get("dest", "Unknown"),
        "client_sid": sid,
    }

    pending_rides[ride_id] = ride
    client_to_ride[sid] = ride_id

    print(f"🚕 New ride request [{ride_id}]: {ride['source']} → {ride['dest']}")

    # Notify the client their request is live
    emit("ride_requested", {"ride_id": ride_id})

    # Broadcast updated pending list to all drivers
    broadcast_pending_rides()


# -------------------------------
# DRIVER: ACCEPT A SPECIFIC RIDE
# -------------------------------

@socketio.on("accept_ride")
def accept_ride(data):
    from flask import request
    driver_sid = request.sid

    ride_id = data.get("ride_id")

    if ride_id not in pending_rides:
        emit("ride_not_available", {"ride_id": ride_id})
        return

    # Check driver isn't already in an active ride
    if driver_sid in driver_to_ride:
        emit("already_on_ride")
        return

    ride = pending_rides.pop(ride_id)  # Remove from pending queue
    otp = random.randint(1000, 9999)

    active_rides[ride_id] = {
        **ride,
        "driver_sid": driver_sid,
        "otp": otp,
        "verified": False,
        "completed": False,
        "fare": 0,
        "paid": False,
    }

    driver_to_ride[driver_sid] = ride_id

    print(f"✅ Driver [{driver_sid}] accepted ride [{ride_id}] | OTP: {otp}")

    # Tell the specific client their ride was accepted + OTP
    emit("ride_accepted", {"otp": otp, "ride_id": ride_id}, to=ride["client_sid"])

    # Tell the driver acceptance confirmed
    emit("ride_accepted_ack", {
        "ride_id": ride_id,
        "source": ride["source"],
        "dest": ride["dest"],
        "otp": otp,
    })

    # Remove this ride from all other drivers' queues
    broadcast_pending_rides()


# -------------------------------
# DRIVER: VERIFY OTP
# -------------------------------

@socketio.on("verify_otp")
def verify_otp(data):
    from flask import request
    driver_sid = request.sid

    ride_id = driver_to_ride.get(driver_sid)
    if not ride_id or ride_id not in active_rides:
        emit("otp_failed", {"reason": "No active ride"})
        return

    ride = active_rides[ride_id]
    entered_otp = str(data.get("otp", ""))

    if entered_otp == str(ride["otp"]):
        ride["verified"] = True
        print(f"🔓 OTP Verified for ride [{ride_id}]")

        # Notify both client and driver
        emit("otp_success", {"ride_id": ride_id}, to=ride["client_sid"])
        emit("otp_success", {"ride_id": ride_id})
    else:
        print(f"❌ Wrong OTP for ride [{ride_id}]")
        emit("otp_failed", {"reason": "Wrong OTP"})


# -------------------------------
# DRIVER: COMPLETE RIDE
# -------------------------------

@socketio.on("complete_ride")
def complete_ride():
    from flask import request
    driver_sid = request.sid

    ride_id = driver_to_ride.get(driver_sid)
    if not ride_id or ride_id not in active_rides:
        return

    ride = active_rides[ride_id]
    if not ride["verified"]:
        emit("error", {"message": "OTP not verified yet"})
        return

    fare = random.randint(100, 500)
    ride["completed"] = True
    ride["fare"] = fare

    print(f"🏁 Ride [{ride_id}] completed. Fare: ₹{fare}")

    # Tell client to show payment screen
    emit("ride_completed", {"fare": fare, "ride_id": ride_id}, to=ride["client_sid"])

    # Tell driver to wait for payment
    emit("waiting_for_payment", {"fare": fare, "ride_id": ride_id})


# -------------------------------
# CLIENT: MAKE PAYMENT
# -------------------------------

@socketio.on("make_payment")
def make_payment(data):
    from flask import request
    client_sid = request.sid

    ride_id = client_to_ride.get(client_sid)
    if not ride_id or ride_id not in active_rides:
        emit("payment_failed", {"reason": "No active ride found"})
        return

    ride = active_rides[ride_id]

    try:
        amount = int(data.get("amount"))
    except (TypeError, ValueError):
        emit("payment_failed", {"reason": "Invalid amount"})
        return

    if amount == ride["fare"]:
        ride["paid"] = True
        driver_sid = ride["driver_sid"]

        print(f"💰 Payment received for ride [{ride_id}]: ₹{amount}")

        # Notify client
        emit("payment_success", {"ride_id": ride_id})

        # Notify driver
        emit("payment_received", {"fare": amount, "ride_id": ride_id}, to=driver_sid)

        # Cleanup
        client_to_ride.pop(client_sid, None)
        driver_to_ride.pop(driver_sid, None)
        del active_rides[ride_id]

    else:
        print(f"❌ Wrong payment for ride [{ride_id}]: expected ₹{ride['fare']}, got ₹{amount}")
        emit("payment_failed", {"reason": "Incorrect amount"})


# -------------------------------
# DRIVER: REQUEST CURRENT PENDING LIST
# -------------------------------

@socketio.on("get_pending_rides")
def get_pending_rides():
    from flask import request
    broadcast_pending_rides(driver_sid=request.sid)


# -------------------------------
# RUN SERVER
# -------------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)