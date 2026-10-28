const state = { sessionId: null, students: [] };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

function showToast(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.style.background = isError ? "#b83245" : "#172033";
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 3600);
}

function setStatus(title, message, ready = false) {
  $("#status-title").textContent = title;
  $("#status-message").textContent = message;
  $("#session-status .status-dot").classList.toggle("ready", ready);
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload?.error?.message || "The request could not be completed.");
  return payload;
}

function navigate(section) {
  $$(".page-section").forEach((page) => page.classList.toggle("active", page.dataset.page === section));
  $$(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.section === section));
  if (section === "students") loadStudents();
  if (section === "enroll") populateEnrollmentStudents();
  if (window.innerWidth <= 680) $(".sidebar").classList.remove("open");
}

async function loadStudents() {
  const list = $("#student-list");
  try {
    state.students = await request("/api/v1/students?active_only=true");
    $("#student-count").textContent = state.students.length;
    $("#enrolled-count").textContent = state.students.reduce((total, student) => total + student.enrolled_templates_count, 0);
    $("#roster-summary").textContent = `${state.students.length} active student${state.students.length === 1 ? "" : "s"}`;
    list.replaceChildren();
    if (!state.students.length) {
      list.innerHTML = '<tr><td colspan="5" class="empty-state">No students yet. Add your first student below.</td></tr>';
      return;
    }
    state.students.forEach((student) => {
      const row = document.createElement("tr");
      const initials = `${student.first_name[0]}${student.last_name[0]}`.toUpperCase();
      row.innerHTML = `<td><span class="student-name"><span class="avatar"></span><strong></strong></span></td><td class="student-id"></td><td><span class="pill"></span></td><td class="template-count"></td><td><a class="button secondary" href="#enroll" data-navigate="enroll">Enroll</a></td>`;
      row.querySelector(".avatar").textContent = initials;
      row.querySelector("strong").textContent = `${student.first_name} ${student.last_name}`;
      row.querySelector(".student-id").textContent = student.student_id;
      const consent = row.querySelector(".pill");
      consent.classList.add(student.has_consent ? "green" : "gray");
      consent.textContent = student.has_consent ? "Recorded" : "Required";
      row.querySelector(".template-count").textContent = student.enrolled_templates_count;
      list.append(row);
    });
  } catch (error) {
    list.innerHTML = `<tr><td colspan="5" class="empty-state">${error.message}</td></tr>`;
  }
}

function populateEnrollmentStudents() {
  const select = $("#enrollment-student");
  const selected = select.value;
  select.replaceChildren(new Option("Select a student", ""));
  state.students.filter((student) => student.is_active).forEach((student) => {
    select.add(new Option(`${student.first_name} ${student.last_name} · ${student.student_id}`, student.student_id));
  });
  select.value = selected;
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
    meta.textContent = `${detection.detection_id} · ${detection.student_id ? "Candidate found" : "No candidate"} · ${detection.status}`;
    const actions = document.createElement("div");
    actions.className = "review-actions";
    const input = document.createElement("select");
    input.setAttribute("aria-label", `Student for ${detection.detection_id}`);
    input.add(new Option("Select student", ""));
    state.students.forEach((student) => input.add(new Option(`${student.first_name} ${student.last_name} · ${student.student_id}`, student.id)));
    input.value = detection.student_id || "";
    const decision = async (present) => {
      const correction = session.status === "confirmed";
      const url = correction ? `/api/v1/attendance/sessions/${sessionId}/detections/${detection.detection_id}/correction` : `/api/v1/attendance/sessions/${sessionId}/detections/${detection.detection_id}/review`;
      const body = correction ? { present, student_id: present ? input.value.trim() : null, actor: "web-reviewer", reason: "Corrected in review workspace" } : { present, student_id: present ? input.value.trim() : null, actor: "web-reviewer", notes: "Reviewed in workspace" };
      try { await request(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); await loadReview(sessionId); } catch (error) { showToast(error.message, true); }
    };
    ["Present", "Absent"].forEach((label, index) => {
      const button = document.createElement("button");
      button.className = "button primary";
      button.type = "button";
      button.textContent = session.status === "confirmed" ? `Correct ${label.toLowerCase()}` : label;
      button.disabled = session.status !== "confirmed" && detection.reviewed;
      button.addEventListener("click", () => decision(index === 0));
      actions.append(button);
    });
    actions.prepend(input);
    row.append(meta, actions);
    list.append(row);
  });
  $("#confirm-button").hidden = session.status === "confirmed";
  $("#confirm-button").disabled = !session.detections.length || session.detections.some((item) => !item.reviewed);
}

async function refreshDashboard() {
  await loadStudents();
  populateEnrollmentStudents();
}

$$(".nav-link, [data-navigate]").forEach((link) => link.addEventListener("click", (event) => {
  event.preventDefault();
  const section = link.dataset.section || link.dataset.navigate;
  window.history.replaceState(null, "", `#${section}`);
  navigate(section);
}));

$("#menu-button").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
$("#refresh-students").addEventListener("click", () => refreshDashboard().then(() => showToast("Roster refreshed")));

$("#student-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.has_consent = form.get("has_consent") === "on";
  try {
    await request("/api/v1/students?actor=web-admin", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    event.currentTarget.reset();
    await refreshDashboard();
    showToast("Student added to the roster");
  } catch (error) { showToast(error.message, true); }
});

$("#enrollment-image").addEventListener("change", (event) => {
  $("#enrollment-file-label").textContent = event.target.files[0]?.name || "Choose a face image";
});

$("#enrollment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const studentId = form.get("student_id");
  try {
    await request(`/api/v1/students/${encodeURIComponent(studentId)}/enrollment`, { method: "POST", body: form });
    event.currentTarget.reset();
    $("#enrollment-file-label").textContent = "Choose a face image";
    await refreshDashboard();
    showToast("Face enrolled successfully");
  } catch (error) { showToast(error.message, true); }
});

$("#session-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const session = await request("/api/v1/attendance/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: $("#session-name").value.trim(), actor: "web-reviewer" }) });
    state.sessionId = session.id;
    $("#process-button").disabled = false;
    setStatus("Session ready", "Choose a classroom image to generate proposals.", true);
    await request(`/api/v1/attendance/sessions/${session.id}/process`, { method: "POST" });
    showToast("Attendance session created");
  } catch (error) { setStatus("Unable to create session", error.message); showToast(error.message, true); }
});

$("#classroom-image").addEventListener("change", (event) => {
  $("#classroom-file-label").textContent = event.target.files[0]?.name || "Choose classroom image";
});

$("#image-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.sessionId) return;
  try {
    const form = new FormData();
    form.append("image", $("#classroom-image").files[0]);
    setStatus("Processing image", "Detecting faces and preparing proposals.");
    const session = await request(`/api/v1/attendance/sessions/${state.sessionId}/image`, { method: "POST", body: form });
    setStatus("Review required", `The image is ready for human review (${session.status}).`, true);
    await loadReview(state.sessionId);
  } catch (error) { setStatus("Processing failed", error.message); showToast(error.message, true); }
});

$("#confirm-button").addEventListener("click", async () => {
  try {
    const session = await request(`/api/v1/attendance/sessions/${state.sessionId}/confirm?actor=web-reviewer`, { method: "POST" });
    setStatus("Attendance confirmed", `Session ${session.id.slice(0, 8)} is finalized.`, true);
    await loadReview(state.sessionId);
    showToast("Attendance confirmed");
  } catch (error) { setStatus("Confirmation blocked", error.message); showToast(error.message, true); }
});

window.addEventListener("hashchange", () => navigate(window.location.hash.slice(1) || "overview"));
refreshDashboard().catch(() => {});
navigate(window.location.hash.slice(1) || "overview");
