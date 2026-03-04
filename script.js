function scanURL(){

let url = document.getElementById("urlInput").value;

if(url === ""){
alert("Please enter URL");
return;
}

document.getElementById("result").innerHTML = "⏳ Scanning...";

// Connect to your backend API here later
setTimeout(()=>{
document.getElementById("result").innerHTML =
"✅ Result: Connected to Backend (API Integration Required)";
},1500);

}