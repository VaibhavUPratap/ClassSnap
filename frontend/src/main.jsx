import { StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "/api/v1";
const USN_PATTERN = /^[A-Z]{3}[0-9]{2}[A-Z]{2}[0-9]{4}$/;

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.error?.message || "The request could not be completed.");
  }
  return payload;
}

function Button({ children, variant = "primary", className = "", ...props }) {
  return <button className={`button ${variant} ${className}`} {...props}>{children}</button>;
}

function Sidebar({ page, setPage, open, setOpen }) {
  const links = [
    ["overview", "⌂", "Overview"],
    ["students", "♙", "Students"],
    ["enroll", "＋", "Enroll face"],
    ["attendance", "✓", "Take attendance"],
  ];
  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <a className="brand" href="#overview" onClick={() => setPage("overview")}>
        <span className="brand-mark">C</span>
        <span><strong>ClassSnap</strong><small>Attendance, simplified</small></span>
      </a>
      <nav className="nav" aria-label="Main navigation">
        {links.map(([id, icon, label]) => (
          <a className={`nav-link ${page === id ? "active" : ""}`} href={`#${id}`} key={id}
            onClick={() => { setPage(id); setOpen(false); }}>
            <span>{icon}</span>{label}
          </a>
        ))}
      </nav>
      <div className="sidebar-note"><span className="privacy-icon">◆</span><strong>Private by design</strong><p>Images are processed locally and are not retained by default.</p></div>
    </aside>
  );
}

function PageHeading({ eyebrow, title, children, description }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lead">{description}</p></div>{children}</div>;
}

function Overview({ students, setPage }) {
  const enrolled = students.reduce((total, student) => total + student.enrolled_templates_count, 0);
  return <section className="page-section">
    <PageHeading eyebrow="Good to see you" title="Attendance overview" description="Manage your classroom roster and run a reviewed attendance session.">
      <Button onClick={() => setPage("attendance")}>Take attendance <span>→</span></Button>
    </PageHeading>
    <div className="stat-grid">
      <Stat icon="♙" tone="blue" label="Active students" value={students.length} />
      <Stat icon="✓" tone="green" label="Enrolled faces" value={enrolled} />
      <Stat icon="◷" tone="amber" label="Last session" value="None yet" />
    </div>
    <div className="welcome-card"><div><p className="eyebrow">Your workflow</p><h2>From roster to reviewed attendance</h2><p> Add students and their consented face images, then process a classroom photo. ClassSnap keeps uncertain matches unassigned until you review them.</p></div><div className="workflow-steps"><span><b>1</b>Add students</span><span><b>2</b>Enroll faces</span><span><b>3</b>Review attendance</span></div></div>
  </section>;
}

function Stat({ icon, tone, label, value }) {
  return <article className="stat-card"><span className={`stat-icon ${tone}`}>{icon}</span><div><span className="stat-label">{label}</span><strong>{value}</strong></div></article>;
}

function Students({ students, refresh, setPage, notify }) {
  const [form, setForm] = useState({ first_name: "", last_name: "", student_id: "", email: "", has_consent: false, consent_notes: "" });
  const update = (event) => {
    const value = event.target.type === "checkbox"
      ? event.target.checked
      : event.target.name === "student_id"
        ? event.target.value.trim().toUpperCase()
        : event.target.value;
    setForm({ ...form, [event.target.name]: value });
  };
  const submit = async (event) => {
    event.preventDefault();
    if (!USN_PATTERN.test(form.student_id)) {
      notify("Enter a valid USN such as ENG24AM0107.", true);
      return;
    }
    try {
      await request("/students?actor=web-admin", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
      setForm({ first_name: "", last_name: "", student_id: "", email: "", has_consent: false, consent_notes: "" });
      await refresh();
      notify("Student added to the roster");
    } catch (error) { notify(error.message, true); }
  };
  return <section className="page-section">
    <PageHeading eyebrow="Roster management" title="Students" description="Keep your classroom roster current and consent-aware."><Button onClick={() => setPage("enroll")}>Enroll a face <span>＋</span></Button></PageHeading>
    <div className="content-card"><div className="card-toolbar"><div><h2>Active roster</h2><p>{students.length} active student{students.length === 1 ? "" : "s"}</p></div><Button variant="secondary" onClick={refresh}>Refresh</Button></div>
      <div className="table-wrap"><table><thead><tr><th>Student</th><th>Student ID</th><th>Consent</th><th>Face templates</th><th /></tr></thead><tbody>
        {!students.length ? <tr><td colSpan="5" className="empty-state">No students yet. Add your first student below.</td></tr> : students.map((student) => <StudentRow key={student.id} student={student} setPage={setPage} />)}
      </tbody></table></div>
    </div>
    <div className="content-card add-card"><div><p className="eyebrow">New record</p><h2>Add a student</h2><p>Create a roster record before enrolling a face.</p></div><form className="form-grid" onSubmit={submit}>
      <Field label="First name" name="first_name" value={form.first_name} onChange={update} required /><Field label="Last name" name="last_name" value={form.last_name} onChange={update} required /><Field label="USN" name="student_id" value={form.student_id} onChange={update} inputMode="text" maxLength="11" title="Use the format ENG24AM0107" placeholder="ENG24AM0107" required /><Field label="Email (optional)" name="email" type="email" value={form.email} onChange={update} />
      <label className="checkbox-label"><input name="has_consent" type="checkbox" checked={form.has_consent} onChange={update} /> Consent is recorded</label><Field className="full" label="Consent notes (optional)" name="consent_notes" value={form.consent_notes} onChange={update} /><Button className="full" type="submit">Add student</Button>
    </form></div>
  </section>;
}

function StudentRow({ student, setPage }) {
  const initials = `${student.first_name[0]}${student.last_name[0]}`.toUpperCase();
  return <tr><td><span className="student-name"><span className="avatar">{initials}</span><strong>{student.first_name} {student.last_name}</strong></span></td><td>{student.student_id}</td><td><span className={`pill ${student.has_consent ? "green" : "gray"}`}>{student.has_consent ? "Recorded" : "Required"}</span></td><td>{student.enrolled_templates_count}</td><td><Button variant="secondary" onClick={() => setPage("enroll")}>Enroll</Button></td></tr>;
}

function Field({ label, className = "", ...props }) {
  return <label className={className}>{label}<input {...props} /></label>;
}

function Enroll({ students, refresh, notify }) {
  const [studentId, setStudentId] = useState("");
  const [image, setImage] = useState(null);
  const [consentNotes, setConsentNotes] = useState("");
  const [consent, setConsent] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    const form = new FormData();
    form.append("image", image);
    form.append("consent_granted", consent);
    form.append("consent_notes", consentNotes);
    try {
      await request(`/students/${encodeURIComponent(studentId)}/enrollment`, { method: "POST", body: form });
      setStudentId(""); setImage(null); setConsent(false); setConsentNotes("");
      event.currentTarget.reset(); await refresh(); notify("Face enrolled successfully");
    } catch (error) { notify(error.message, true); }
  };
  return <section className="page-section"><PageHeading eyebrow="Biometric enrollment" title="Enroll a face" description="Add one clear, consented face image to improve matching." />
    <div className="split-layout"><div className="content-card"><h2>Choose a student</h2><p className="muted">Only active students are shown.</p><form onSubmit={submit}>
      <label>Student<select value={studentId} onChange={(event) => setStudentId(event.target.value)} required><option value="">Select a student</option>{students.map((student) => <option value={student.id} key={student.id}>{student.first_name} {student.last_name} · {student.student_id}</option>)}</select></label>
      <label className="upload-zone" htmlFor="enrollment-image"><span className="upload-icon">↑</span><strong>{image?.name || "Choose a face image"}</strong><small>JPG or PNG · one face · up to 10 MB</small><input id="enrollment-image" type="file" accept="image/*" onChange={(event) => setImage(event.target.files[0])} required /></label>
      <label className="checkbox-label"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} required /> I confirm consent has been recorded</label><Field label="Consent notes (optional)" value={consentNotes} onChange={(event) => setConsentNotes(event.target.value)} /><Button className="full" type="submit">Enroll face</Button>
    </form></div><div className="info-panel"><span className="info-icon">i</span><h2>Good enrollment images</h2><ul><li>Show one person only</li><li>Face the camera in even lighting</li><li>Avoid heavy blur or occlusion</li><li>Use a consented student image</li></ul></div></div>
  </section>;
}

function Attendance({ students, notify }) {
  const [name, setName] = useState("");
  const [session, setSession] = useState(null);
  const [image, setImage] = useState(null);
  const [status, setStatus] = useState({ title: "No session selected", message: "Create a session to begin.", ready: false });
  const [detections, setDetections] = useState([]);
  const [confirmed, setConfirmed] = useState(false);
  const createSession = async (event) => {
    event.preventDefault();
    try {
      const created = await request("/attendance/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, actor: "web-reviewer" }) });
      await request(`/attendance/sessions/${created.id}/process`, { method: "POST" });
      setSession(created); setStatus({ title: "Session ready", message: "Choose a classroom image to generate proposals.", ready: true }); notify("Attendance session created");
    } catch (error) { setStatus({ title: "Unable to create session", message: error.message }); notify(error.message, true); }
  };
  const processImage = async (event) => {
    event.preventDefault();
    const form = new FormData(); form.append("image", image);
    try {
      setStatus({ title: "Processing image", message: "Detecting faces and preparing proposals." });
      const result = await request(`/attendance/sessions/${session.id}/image`, { method: "POST", body: form });
      await loadSession(result.id); setStatus({ title: "Review required", message: "Review every detection before confirmation.", ready: true });
    } catch (error) { setStatus({ title: "Processing failed", message: error.message }); notify(error.message, true); }
  };
  const loadSession = async (id = session?.id) => { if (!id) return; const result = await request(`/attendance/sessions/${id}`); setDetections(result.detections); setConfirmed(result.status === "confirmed"); };
  const review = async (detection, present, studentId) => {
    try {
      const path = confirmed ? `/attendance/sessions/${session.id}/detections/${detection.detection_id}/correction` : `/attendance/sessions/${session.id}/detections/${detection.detection_id}/review`;
      const body = confirmed ? { present, student_id: present ? studentId : null, actor: "web-reviewer", reason: "Corrected in review workspace" } : { present, student_id: present ? studentId : null, actor: "web-reviewer", notes: "Reviewed in workspace" };
      await request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); await loadSession();
    } catch (error) { notify(error.message, true); }
  };
  const confirm = async () => { try { await request(`/attendance/sessions/${session.id}/confirm?actor=web-reviewer`, { method: "POST" }); setConfirmed(true); await loadSession(); setStatus({ title: "Attendance confirmed", message: "The session is finalized.", ready: true }); notify("Attendance confirmed"); } catch (error) { notify(error.message, true); } };
  const allReviewed = detections.length > 0 && detections.every((item) => item.reviewed);
  return <section className="page-section"><PageHeading eyebrow="Human-in-the-loop review" title="Take attendance" description="Process a classroom photo, review every proposal, then confirm."><span className="privacy-badge">Local processing</span></PageHeading>
    <div className="attendance-layout"><div className="content-card"><CardHeading step="01" title="Start a session" text="Name this attendance capture." /><form onSubmit={createSession}><Field label="Session name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Physics 101 · 28 Oct" required /><Button className="full" type="submit">Create session</Button></form><SessionStatus {...status} /></div>
      <div className="content-card"><CardHeading step="02" title="Upload classroom image" text="Images are processed in memory." /><form onSubmit={processImage}><label className="upload-zone compact" htmlFor="classroom-image"><span className="upload-icon">↑</span><strong>{image?.name || "Choose classroom image"}</strong><small>JPG or PNG · up to 10 MB</small><input id="classroom-image" type="file" accept="image/*" onChange={(event) => setImage(event.target.files[0])} required /></label><Button className="full" type="submit" disabled={!session || !image}>Process image</Button></form></div></div>
    {detections.length > 0 && <div className="content-card review-card"><div className="card-toolbar"><div><p className="eyebrow">Step 03</p><h2>Review proposals</h2><p className="muted">Every detection must be reviewed before confirmation.</p></div><Button onClick={confirm} disabled={confirmed || !allReviewed}>Confirm attendance</Button></div>{detections.map((detection) => <ReviewRow key={detection.detection_id} detection={detection} students={students} confirmed={confirmed} onReview={review} />)}</div>}
  </section>;
}

function CardHeading({ step, title, text }) { return <div className="card-heading"><span className="step">{step}</span><div><h2>{title}</h2><p className="muted">{text}</p></div></div>; }
function SessionStatus({ title, message, ready }) { return <div className="session-status"><span className={`status-dot ${ready ? "ready" : ""}`} /><div><strong>{title}</strong><p>{message}</p></div></div>; }
function ReviewRow({ detection, students, confirmed, onReview }) {
  const [studentId, setStudentId] = useState(detection.student_id || "");
  return <div className="review-row"><span className="review-meta">{detection.detection_id} · {detection.student_id ? "Candidate found" : "No candidate"} · {detection.status}</span><div className="review-actions"><select value={studentId} onChange={(event) => setStudentId(event.target.value)} aria-label={`Student for ${detection.detection_id}`}><option value="">Select student</option>{students.map((student) => <option value={student.id} key={student.id}>{student.first_name} {student.last_name}</option>)}</select><Button onClick={() => onReview(detection, true, studentId)} disabled={!confirmed && detection.reviewed}>Present</Button><Button variant="secondary" onClick={() => onReview(detection, false, null)} disabled={!confirmed && detection.reviewed}>Absent</Button></div></div>;
}

function App() {
  const [page, setPage] = useState(window.location.hash.slice(1) || "overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const [students, setStudents] = useState([]);
  const [toast, setToast] = useState(null);
  const notify = (message, error = false) => { setToast({ message, error }); window.setTimeout(() => setToast(null), 3600); };
  const refresh = async () => { try { setStudents(await request("/students?active_only=true")); } catch (error) { notify(error.message, true); } };
  useEffect(() => { refresh(); const onHash = () => setPage(window.location.hash.slice(1) || "overview"); window.addEventListener("hashchange", onHash); return () => window.removeEventListener("hashchange", onHash); }, []);
  const changePage = (next) => { window.location.hash = next; setPage(next); };
  const content = useMemo(() => ({ overview: <Overview students={students} setPage={changePage} />, students: <Students students={students} refresh={refresh} setPage={changePage} notify={notify} />, enroll: <Enroll students={students} refresh={refresh} notify={notify} />, attendance: <Attendance students={students} notify={notify} /> }[page] || <Overview students={students} setPage={changePage} />), [page, students]);
  return <div className="app-shell"><Sidebar page={page} setPage={changePage} open={menuOpen} setOpen={setMenuOpen} /><main className="main-content"><header className="mobile-header"><a className="brand" href="#overview" onClick={() => changePage("overview")}><span className="brand-mark">C</span><strong>ClassSnap</strong></a><button className="menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-label="Open navigation">☰</button></header>{content}{toast && <div className={`toast ${toast.error ? "error" : ""}`} role="status">{toast.message}</div>}</main></div>;
}

createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);
