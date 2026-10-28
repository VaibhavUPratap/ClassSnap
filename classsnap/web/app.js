const state = { sessionId: null };
const $ = (selector) => document.querySelector(selector);

function setStatus(title, message, ready = false) {
  $("#status-title").textContent = title;
  $("#status-message").textContent = message;
  $("#status-dot").classList.toggle("ready", ready);
}

async function loadReview(sessionId) {
  const session = await request(`/api/v1/attendance/sessions/${sessionId}`);
  $("#review-card").hidden = false;
  const list = $("#review-list");
  list.replaceChildren();
  session.detections.forEach((detection) => {
    const row = document.createElement("div");
    row.className = "review-row";
    const meta = document.createElement("span");
    meta.className = "review-meta";
    meta.textContent = `${detection.detection_id} · ${detection.student_id || "No candidate"} · ${detection.status}`;
    const actions = document.createElement("div");
    actions.className = "review-actions";
    const studentInput = document.createElement("input");
    studentInput.placeholder = "Student ID";
    studentInput.value = detection.student_id || "";
    studentInput.setAttribute("aria-label", `Student ID for ${detection.detection_id}`);
    const presentButton = document.createElement("button");
    presentButton.type = "button";
    presentButton.textContent = session.status === "confirmed" ? "Correct present" : "Present";
    const absentButton = document.createElement("button");
    absentButton.type = "button";
    absentButton.textContent = session.status === "confirmed" ? "Correct absent" : "Absent";
    const submitDecision = async (present) => {
      const isCorrection = session.status === "confirmed";
      const url = isCorrection
        ? `/api/v1/attendance/sessions/${sessionId}/detections/${detection.detection_id}/correction`
        : `/api/v1/attendance/sessions/${sessionId}/detections/${detection.detection_id}/review`;
      const body = isCorrection
        ? { present, student_id: present ? studentInput.value.trim() : null, actor: "web-reviewer", reason: "Corrected in review workspace" }
        : { present, student_id: present ? studentInput.value.trim() : null, actor: "web-reviewer", notes: "Reviewed in workspace" };
      await request(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      await loadReview(sessionId);
    };
    presentButton.disabled = session.status !== "confirmed" && detection.reviewed;
    absentButton.disabled = session.status !== "confirmed" && detection.reviewed;
    presentButton.addEventListener("click", () => submitDecision(true).catch((error) => setStatus("Review failed", error.message)));
    absentButton.addEventListener("click", () => submitDecision(false).catch((error) => setStatus("Review failed", error.message)));
    actions.append(studentInput, presentButton, absentButton);
    row.append(meta, actions);
    list.append(row);
  });
  $("#confirm-button").hidden = session.status === "confirmed";
  $("#confirm-button").disabled = !session.detections.length || session.detections.some((item) => !item.reviewed);
}

async function request(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.error?.message || "The request could not be completed.");
  }
  return payload;
}

$("#session-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const name = $("#session-name").value.trim();
    const session = await request("/api/v1/attendance/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, actor: "web-reviewer" }),
    });
    state.sessionId = session.id;
    $("#session-reference").textContent = `Session ${session.id.slice(0, 8)}`;
    $("#process-button").disabled = false;
    setStatus("Session ready", "Choose a classroom image to generate proposals.", true);
    await request(`/api/v1/attendance/sessions/${session.id}/process`, { method: "POST" });
  } catch (error) {
    setStatus("Unable to create session", error.message);
  }
});

$("#image-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.sessionId) return;
  try {
    const file = $("#classroom-image").files[0];
    const form = new FormData();
    form.append("image", file);
    setStatus("Processing image", "Detecting faces and preparing proposals.");
    const session = await request(`/api/v1/attendance/sessions/${state.sessionId}/image`, {
      method: "POST",
      body: form,
    });
    setStatus("Review required", `The image is ready for human review (${session.status}).`, true);
    await loadReview(state.sessionId);
  } catch (error) {
    setStatus("Processing failed", error.message);
  }
});

$("#confirm-button").addEventListener("click", async () => {
  try {
    const session = await request(`/api/v1/attendance/sessions/${state.sessionId}/confirm?actor=web-reviewer`, {
      method: "POST",
    });
    setStatus("Attendance confirmed", `Session ${session.id.slice(0, 8)} is finalized.`, true);
    await loadReview(state.sessionId);
  } catch (error) {
    setStatus("Confirmation blocked", error.message);
  }
});
