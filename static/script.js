const socket = io();
// const socket = io(window.location.origin);

// CLIENT EVENTS

function bookRide(source, destination) {
    socket.emit("book_ride", { source, dest: destination });
}

function sendPayment(amount) {
    socket.emit("make_payment", { amount: amount });
}

// DRIVER EVENTS

function acceptRide() {
    socket.emit("accept_ride");
}

function verifyOTP(otp) {
    socket.emit("verify_otp", { otp: otp });
}

function completeRide() {
    socket.emit("complete_ride");
}

// LISTENERS

socket.on("ride_accepted", (data) => {
    if (document.getElementById("otpDisplay")) {
        document.getElementById("otpDisplay").innerText = data.otp;
    }
});

socket.on("otp_success", () => {
    if (document.getElementById("rideStatus")) {
        document.getElementById("rideStatus").innerText = "Ride Started 🚕";
    }
});

socket.on("ride_completed", (data) => {
    window.location.href = "/payment.html?fare=" + data.fare;
});

socket.on("payment_success", () => {
    alert("Payment Successful!");
});

socket.on("payment_failed", () => {
    alert("Incorrect amount!");
});