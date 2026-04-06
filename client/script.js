const SERVER = "http://localhost:5000";

async function bookRide() {
    const res = await fetch(`${SERVER}/book`, {method:"POST"});
    const data = await res.json();

    document.getElementById("price").innerText = "Price: ₹" + data.price;
    document.getElementById("status").innerText = "Waiting for driver...";

    trackDriver();
}

function trackDriver(){
    const interval = setInterval(async ()=>{
        const res = await fetch(`${SERVER}/driver/status`);
        const data = await res.json();

        // ✅ OTP FIX: now always updates
        if(data.status === "accepted" && data.ride_otp){
            document.getElementById("driver").innerText = "🚗 Driver Assigned";
            document.getElementById("otp").innerText = "🔐 OTP: " + data.ride_otp;
            document.getElementById("status").innerText = "Driver arriving...";
        }

        if(data.status === "ongoing"){
            document.getElementById("status").innerText = "Ride Started";
        }

        if(data.status === "completed"){
            document.getElementById("status").innerText = "Ride Completed";
            clearInterval(interval);
        }

    },2000);
}

async function payNow(){
    const amount = document.getElementById("amount").value;

    const res = await fetch(`${SERVER}/pay`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({amount})
    });

    const data = await res.json();

    if(data.status==="success"){
        alert("✅ Payment Successful");
    } else {
        alert("❌ Enter exact amount");
    }
}