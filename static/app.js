async function reviewCode() {
  const code = document.getElementById("code").value;
  const language = document.getElementById("language").value;
  const filename = document.getElementById("filename").value;

  if (!code.trim()) {
    alert("Please paste some code first.");
    return;
  }

  document.getElementById("result").textContent = "Reviewing code...";

  const res = await fetch("/api/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, language, filename })
  });

  const data = await res.json();
  document.getElementById("result").textContent = JSON.stringify(data, null, 2);
}

document.getElementById("reviewBtn").addEventListener("click", reviewCode);
