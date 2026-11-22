import { StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "/api/v1";
const USN_PATTERN = /^[A-Z]{3}[0-9]{2}[A-Z]{2}[0-9]{4}$/;

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const payload = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    throw new Error(payload?.error?.message || "The request could not be completed.");
  }
  return payload;
}

/* ==========================================================================
   SVG Icons (Modern, Clean, Feather/Lucide style)
   ========================================================================== */

function IconHome(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>;
}

function IconUsers(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>;
}

function IconUserPlus(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>;
}

function IconCheckCircle(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>;
}

function IconBarChart(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>;
}

function IconUpload(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>;
}

function IconShield(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>;
}

function IconTrash(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>;
}

function IconRefresh(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>;
}

function IconChevronDown(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="6 9 12 15 18 9"/></svg>;
}

function IconChevronUp(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="18 15 12 9 6 15"/></svg>;
}

function IconSearch(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>;
}

function IconDownload(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>;
}

function IconCheck(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="20 6 9 17 4 12"/></svg>;
}

function IconX(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>;
}

function IconSparkles(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>;
}

function IconClock(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>;
}

function IconEdit(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>;
}

function IconSave(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>;
}

/* ==========================================================================
   UI Components
   ========================================================================== */

function Button({ children, variant = "primary", className = "", ...props }) {
  return <button className={`button ${variant} ${className}`} {...props}>{children}</button>;
}

function Sidebar({ page, setPage, open, setOpen }) {
  const links = [
    { id: "overview", icon: <IconHome />, label: "Overview" },
    { id: "students", icon: <IconUsers />, label: "Students" },
    { id: "enroll", icon: <IconUserPlus />, label: "Enroll Face" },
    { id: "attendance", icon: <IconCheckCircle />, label: "Take Attendance" },
    { id: "reports", icon: <IconBarChart />, label: "Reports" },
  ];

  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <a className="brand" href="#overview" onClick={() => setPage("overview")}>
        <div className="brand-mark">C</div>
        <div>
          <strong>ClassSnap</strong>
          <small>AI Attendance Intelligence</small>
        </div>
      </a>
      <nav className="nav" aria-label="Main navigation">
        {links.map((link) => (
          <a
            className={`nav-link ${page === link.id ? "active" : ""}`}
            href={`#${link.id}`}
            key={link.id}
            onClick={() => { setPage(link.id); setOpen(false); }}
          >
            {link.icon}
            <span>{link.label}</span>
          </a>
        ))}
      </nav>
      <div className="sidebar-note">
        <IconShield />
        <div>
          <strong>Privacy Safeguards Active</strong>
          <p>Biometrics are normalized and stored locally. Raw photos are securely purged.</p>
        </div>
      </div>
    </aside>
  );
}

function PageHeading({ eyebrow, title, children, description }) {
  return (
    <div className="page-heading">
      <div className="page-heading-info">
        {eyebrow && <span className="eyebrow"><IconSparkles style={{ width: 13, height: 13 }} /> {eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p className="lead">{description}</p>}
      </div>
      {children && <div className="page-heading-actions">{children}</div>}
    </div>
  );
}

function Stat({ icon, tone, label, value }) {
  return (
    <article className="stat-card">
      <div className={`stat-icon ${tone}`}>{icon}</div>
      <div>
        <span className="stat-label">{label}</span>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

function Overview({ students, setPage }) {
  const enrolled = students.reduce((total, student) => total + (student.enrolled_templates_count || 0), 0);

  return (
    <section className="page-section">
      <PageHeading
        eyebrow="Dashboard"
        title="Classroom Intelligence"
        description="Monitor active enrollment, verify attendance in real-time, and inspect automated session reports."
      >
        <Button onClick={() => setPage("attendance")}>
          <IconCheckCircle /> Take Attendance
        </Button>
      </PageHeading>

      <div className="stat-grid">
        <Stat icon={<IconUsers />} tone="blue" label="Active Students" value={students.length} />
        <Stat icon={<IconCheckCircle />} tone="green" label="Enrolled Biometrics" value={enrolled} />
        <Stat icon={<IconClock />} tone="amber" label="System Status" value="Online & Ready" />
      </div>

      <div className="welcome-card">
        <div>
          <span className="eyebrow">Quick Workflow</span>
          <h2>Seamless AI Attendance in 3 Steps</h2>
          <p>
            Maintain an active student roster with consented reference portraits. Snap or upload a classroom group photograph to detect all visible faces and review high-confidence identity proposals.
          </p>
        </div>
        <div className="workflow-steps">
          <span><b>1</b> Add student record</span>
          <span><b>2</b> Enroll reference face</span>
          <span><b>3</b> Review & confirm class</span>
        </div>
      </div>
    </section>
  );
}

function TemplatePreview({ src, alt }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <div className="template-preview missing-preview" role="img" aria-label={alt}>Preview unavailable</div>;
  }

  return (
    <img
      className="template-preview"
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  );
}

function EditStudentModal({ student, onClose, refresh, notify }) {
  const [form, setForm] = useState({
    student_id: student.student_id || "",
    first_name: student.first_name || "",
    last_name: student.last_name || "",
    email: student.email || "",
    has_consent: student.has_consent || false,
    consent_notes: student.consent_notes || "",
    is_active: student.is_active !== false,
  });
  const [saving, setSaving] = useState(false);

  const update = (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((prev) => ({ ...prev, [e.target.name]: value }));
  };

  const save = async (e) => {
    e.preventDefault();
    if (!form.first_name.trim() || !form.last_name.trim()) {
      notify("First and last name are required.", true);
      return;
    }
    const normalizedUsn = form.student_id.trim().toUpperCase();
    if (!USN_PATTERN.test(normalizedUsn)) {
      notify("Enter a valid USN such as ENG24AM0107.", true);
      return;
    }
    setSaving(true);
    try {
      await request(`/students/${encodeURIComponent(student.id)}?actor=web-admin`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_id: normalizedUsn,
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          email: form.email.trim() || null,
          has_consent: form.has_consent,
          consent_notes: form.consent_notes.trim() || null,
          is_active: form.is_active,
        }),
      });
      await refresh();
      notify(`${form.first_name} ${form.last_name} updated successfully`);
      onClose();
    } catch (error) {
      notify(error.message, true);
    } finally {
      setSaving(false);
    }
  };

  // Close on backdrop click
  const onBackdrop = (e) => {
    if (e.target === e.currentTarget) onClose();
  };

  // Close on Escape
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const initials = `${student.first_name?.[0] || ""}${student.last_name?.[0] || ""}`.toUpperCase();

  return (
    <div className="modal-backdrop" onClick={onBackdrop} role="dialog" aria-modal="true" aria-label="Edit Student">
      <div className="modal">
        <div className="modal-header">
          <div className="modal-header-left">
            <span className="avatar" style={{ width: 40, height: 40, fontSize: 15, flexShrink: 0 }}>{initials}</span>
            <div>
              <span className="eyebrow">Edit Record</span>
              <h2 style={{ margin: 0 }}>{student.first_name} {student.last_name}</h2>
              <small style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>{student.student_id}</small>
            </div>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <IconX style={{ width: 18, height: 18 }} />
          </button>
        </div>

        <form className="modal-body" onSubmit={save} noValidate>
          <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr", gap: "14px 20px" }}>
            <label className="full" style={{ gridColumn: "1 / -1" }}>
              Student USN
              <input
                name="student_id"
                value={form.student_id}
                onChange={update}
                placeholder="ENG24AM0107"
                maxLength="11"
                required
              />
            </label>
            <label>
              First Name
              <input
                name="first_name"
                value={form.first_name}
                onChange={update}
                placeholder="Jane"
                required
                autoFocus
              />
            </label>
            <label>
              Last Name
              <input
                name="last_name"
                value={form.last_name}
                onChange={update}
                placeholder="Doe"
                required
              />
            </label>
            <label className="full" style={{ gridColumn: "1 / -1" }}>
              Email Address
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={update}
                placeholder="jane.doe@university.edu"
              />
            </label>
            <label className="checkbox-label full" style={{ gridColumn: "1 / -1" }}>
              <input
                name="has_consent"
                type="checkbox"
                checked={form.has_consent}
                onChange={update}
              />
              <span>Biometric consent verified and recorded on file</span>
            </label>
            <label className="full" style={{ gridColumn: "1 / -1" }}>
              Consent Notes
              <input
                name="consent_notes"
                value={form.consent_notes}
                onChange={update}
                placeholder="Signed form ID or reference code"
              />
            </label>
            <label className="checkbox-label full" style={{ gridColumn: "1 / -1" }}>
              <input
                name="is_active"
                type="checkbox"
                checked={form.is_active}
                onChange={update}
              />
              <span>Student is active on the roster</span>
            </label>
          </div>

          <div className="modal-footer">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              <IconSave style={{ width: 15, height: 15 }} />
              {saving ? "Saving…" : "Save Changes"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StudentRow({ student, setPage, refresh, notify }) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const initials = `${student.first_name?.[0] || ""}${student.last_name?.[0] || ""}`.toUpperCase();
  const templates = student.templates || [];

  const remove = async () => {
    if (!window.confirm(`Remove ${student.first_name} ${student.last_name} (${student.student_id}) from the roster?`)) return;
    try {
      await request(`/students/${encodeURIComponent(student.id)}?actor=web-admin`, { method: "DELETE" });
      await refresh();
      notify("Student removed from the roster");
    } catch (error) {
      notify(error.message, true);
    }
  };

  return (
    <>
      {editing && (
        <EditStudentModal
          student={student}
          onClose={() => setEditing(false)}
          refresh={refresh}
          notify={notify}
        />
      )}
      <tr className={expanded ? "student-row expanded" : "student-row"}>
        <td>
          <div className="student-name">
            <span className="avatar">{initials}</span>
            <div>
              <strong>{student.first_name} {student.last_name}</strong>
              <small>{student.email || "No email on record"}</small>
            </div>
          </div>
        </td>
        <td><span className="student-id">{student.student_id}</span></td>
        <td>
          <span className={`pill ${student.has_consent ? "green" : "gray"}`}>
            {student.has_consent ? "Recorded" : "Required"}
          </span>
        </td>
        <td>
          <button
            className={`template-summary ${templates.length ? "enrolled" : "missing"}`}
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            <span className="template-icon">
              {templates.length ? <IconCheck style={{ width: 13, height: 13 }} /> : "!"}
            </span>
            <span>
              <strong>{templates.length} {templates.length === 1 ? "template" : "templates"}</strong>
              <small>{templates.length ? "Inspect biometric crops" : "Face not enrolled"}</small>
            </span>
            <span className="chevron">
              {expanded ? <IconChevronUp style={{ width: 14, height: 14 }} /> : <IconChevronDown style={{ width: 14, height: 14 }} />}
            </span>
          </button>
        </td>
        <td className="row-actions">
          <Button variant="secondary" className="sm" onClick={() => setEditing(true)}>
            <IconEdit style={{ width: 14, height: 14 }} /> Edit
          </Button>
          <Button variant="secondary" className="sm" onClick={() => setPage("enroll", student.id)}>
            <IconUserPlus style={{ width: 14, height: 14 }} /> {templates.length ? "Add face" : "Enroll"}
          </Button>
          <Button variant="outline-danger" className="sm" onClick={remove}>
            <IconTrash style={{ width: 14, height: 14 }} /> Remove
          </Button>
        </td>
      </tr>
      {expanded && (
        <tr className="template-detail-row">
          <td colSpan="5">
            <div className="template-detail">
              <div className="template-detail-heading">
                <div>
                  <span className="eyebrow">Stored Face References</span>
                  <h3>{templates.length ? `${templates.length} Active Biometric ${templates.length === 1 ? "Template" : "Templates"}` : "No face templates"}</h3>
                  <p className="muted">
                    Preview shows the normalized alignment face crop used by the recognition neural network.
                  </p>
                </div>
                <Button variant="secondary" className="sm" onClick={() => setPage("enroll", student.id)}>
                  <IconUserPlus style={{ width: 14, height: 14 }} /> Add Reference
                </Button>
              </div>
              {templates.length ? (
                <div className="template-grid">
                  {templates.map((template, index) => (
                    <article className="template-card" key={template.id}>
                      <TemplatePreview
                        src={template.preview_url}
                        alt={`Face reference ${index + 1} for ${student.first_name} ${student.last_name}`}
                      />
                      <div className="template-card-top">
                        <span className="template-number">REFERENCE #{index + 1}</span>
                        {template.is_primary && <span className="pill blue">Primary</span>}
                      </div>
                      <dl>
                        <div>
                          <dt>Recognition Model</dt>
                          <dd>{template.model_name} · {template.model_version}</dd>
                        </div>
                        <div>
                          <dt>Feature Embedding</dt>
                          <dd>{template.embedding_dim}D Unit Vector</dd>
                        </div>
                        <div>
                          <dt>Quality Confidence</dt>
                          <dd>
                            {Math.round(template.quality_score * 100)}%
                            <span className="quality-bar">
                              <i style={{ width: `${Math.min(100, Math.max(0, template.quality_score * 100))}%` }} />
                            </span>
                          </dd>
                        </div>
                        <div>
                          <dt>Timestamp</dt>
                          <dd>{new Date(template.created_at).toLocaleDateString()} {new Date(template.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</dd>
                        </div>
                      </dl>
                      <Button
                        variant="outline-danger"
                        className="template-remove sm"
                        onClick={async () => {
                          if (!window.confirm("Remove this enrolled face reference?")) return;
                          try {
                            await request(`/students/${student.id}/templates/${template.id}?actor=web-admin`, { method: "DELETE" });
                            await refresh();
                            notify("Face reference removed");
                          } catch (error) {
                            notify(error.message, true);
                          }
                        }}
                      >
                        <IconTrash style={{ width: 13, height: 13 }} /> Delete Face Crop
                      </Button>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="template-empty">
                  No biometric references linked to this student. Click "Add Reference" to enroll a face portrait.
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function Field({ label, className = "", ...props }) {
  return (
    <label className={className}>
      {label}
      <input {...props} />
    </label>
  );
}

function Students({ students, refresh, setPage, notify }) {
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    student_id: "",
    email: "",
    has_consent: false,
    consent_notes: "",
  });

  const filteredStudents = useMemo(() => {
    if (!search.trim()) return students;
    const q = search.toLowerCase();
    return students.filter(
      (s) =>
        s.first_name.toLowerCase().includes(q) ||
        s.last_name.toLowerCase().includes(q) ||
        s.student_id.toLowerCase().includes(q) ||
        (s.email && s.email.toLowerCase().includes(q))
    );
  }, [students, search]);

  const update = (event) => {
    const value =
      event.target.type === "checkbox"
        ? event.target.checked
        : event.target.name === "student_id"
        ? event.target.value.trim().toUpperCase()
        : event.target.value;
    setForm({ ...form, [event.target.name]: value });
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.first_name.trim() || !form.last_name.trim() || !form.student_id.trim()) {
      notify("First name, last name, and USN are required.", true);
      return;
    }
    if (!USN_PATTERN.test(form.student_id)) {
      notify("Enter a valid USN such as ENG24AM0107.", true);
      return;
    }
    try {
      await request("/students?actor=web-admin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setForm({
        first_name: "",
        last_name: "",
        student_id: "",
        email: "",
        has_consent: false,
        consent_notes: "",
      });
      await refresh();
      notify("Student added to the roster");
    } catch (error) {
      notify(error.message, true);
    }
  };

  return (
    <section className="page-section">
      <PageHeading
        eyebrow="Roster Management"
        title="Student Directory"
        description="Maintain authenticated classroom enrollment and consent status."
      >
        <Button onClick={() => setPage("enroll")}>
          <IconUserPlus /> Enroll Face
        </Button>
      </PageHeading>

      <div className="content-card">
        <div className="card-toolbar">
          <div>
            <h2>Active Students ({filteredStudents.length})</h2>
            <p className="muted">Search by name, student ID, or registered email.</p>
          </div>
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <input
              type="text"
              className="search-input"
              placeholder="Search students..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Button variant="secondary" onClick={refresh}>
              <IconRefresh /> Refresh
            </Button>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Student USN</th>
                <th>Consent Status</th>
                <th>Face Biometrics</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {!filteredStudents.length ? (
                <tr>
                  <td colSpan="5" className="empty-state">
                    {search ? "No students matching your search query." : "No students in the roster yet. Add your first student below."}
                  </td>
                </tr>
              ) : (
                filteredStudents.map((student) => (
                  <StudentRow
                    key={student.id}
                    student={student}
                    setPage={setPage}
                    refresh={refresh}
                    notify={notify}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="content-card add-card">
        <div style={{ maxWidth: 300 }}>
          <span className="eyebrow">Roster Registry</span>
          <h2>Register Student</h2>
          <p className="muted">
            Create an active student record before enrolling face biometrics.
          </p>
        </div>
        <form className="form-grid" noValidate onSubmit={submit}>
          <Field label="First Name" name="first_name" value={form.first_name} onChange={update} placeholder="Jane" required />
          <Field label="Last Name" name="last_name" value={form.last_name} onChange={update} placeholder="Doe" required />
          <Field
            label="USN / Student ID"
            name="student_id"
            value={form.student_id}
            onChange={update}
            placeholder="ENG24AM0107"
            maxLength="11"
            required
          />
          <Field label="Email Address (Optional)" name="email" type="email" value={form.email} onChange={update} placeholder="jane.doe@university.edu" />
          <label className="checkbox-label full">
            <input name="has_consent" type="checkbox" checked={form.has_consent} onChange={update} />
            <span>Biometric consent verified and recorded on file</span>
          </label>
          <Field className="full" label="Consent Notes (Optional)" name="consent_notes" value={form.consent_notes} onChange={update} placeholder="Parent/student consent signed on registration." />
          <Button className="full" type="submit">
            <IconUserPlus /> Register Student
          </Button>
        </form>
      </div>
    </section>
  );
}

function Enroll({ students, refresh, notify, preselectedStudentId }) {
  const [studentId, setStudentId] = useState(preselectedStudentId || "");
  useEffect(() => {
    if (preselectedStudentId) setStudentId(preselectedStudentId);
  }, [preselectedStudentId]);

  const [image, setImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [consentNotes, setConsentNotes] = useState("");
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      setImage(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!studentId) {
      notify("Please select a student.", true);
      return;
    }
    if (!image) {
      notify("Please select a portrait image to enroll.", true);
      return;
    }

    setSubmitting(true);
    const formElement = event.currentTarget;
    const form = new FormData();
    form.append("image", image);
    form.append("consent_granted", consent);
    form.append("consent_notes", consentNotes);

    try {
      await request(`/students/${encodeURIComponent(studentId)}/enrollment`, {
        method: "POST",
        body: form,
      });
      setStudentId("");
      setImage(null);
      setPreviewUrl(null);
      setConsent(false);
      setConsentNotes("");
      formElement.reset();
      await refresh();
      notify("Biometric reference enrolled successfully");
    } catch (error) {
      notify(error.message, true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="page-section">
      <PageHeading
        eyebrow="Biometric Registry"
        title="Enroll Student Face"
        description="Add a high-quality facial reference to ensure accurate attendance matching."
      />

      <div className="split-layout">
        <div className="content-card">
          <h2>Enrollment Form</h2>
          <p className="muted" style={{ marginBottom: "20px" }}>
            Select an active student and upload their reference photograph.
          </p>

          <form onSubmit={submit}>
            <label style={{ marginBottom: "16px" }}>
              Target Student
              <select value={studentId} onChange={(e) => setStudentId(e.target.value)} required>
                <option value="">Select a student from roster</option>
                {students.map((student) => (
                  <option value={student.id} key={student.id}>
                    {student.first_name} {student.last_name} ({student.student_id})
                  </option>
                ))}
              </select>
            </label>

            <label className="upload-zone" htmlFor="enrollment-image">
              {previewUrl ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
                  <img
                    src={previewUrl}
                    alt="Preview"
                    style={{ maxHeight: 160, borderRadius: 8, objectFit: "contain", border: "1px solid var(--border)" }}
                  />
                  <strong>{image?.name}</strong>
                  <small>{(image.size / 1024).toFixed(1)} KB · Click to choose different image</small>
                </div>
              ) : (
                <>
                  <div className="upload-icon">
                    <IconUpload />
                  </div>
                  <strong>Upload Reference Portrait</strong>
                  <small>JPG or PNG with clean face visibility · up to 10 MB</small>
                </>
              )}
              <input
                id="enrollment-image"
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                required
              />
            </label>

            <label className="checkbox-label" style={{ margin: "16px 0 12px" }}>
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                required
              />
              <span>I confirm student consent is verified and on file</span>
            </label>

            <Field
              label="Consent Notes (Optional)"
              value={consentNotes}
              onChange={(e) => setConsentNotes(e.target.value)}
              placeholder="Signed waiver form ID or reference code"
              style={{ marginBottom: "18px" }}
            />

            <Button className="full" type="submit" disabled={submitting || !image || !studentId}>
              <IconSparkles /> {submitting ? "Processing & Normalizing..." : "Enroll Face Template"}
            </Button>
          </form>
        </div>

        <div className="info-panel">
          <div className="info-icon">
            <IconShield />
          </div>
          <h2>Best Enrollment Practices</h2>
          <ul>
            <li><strong>Single Face Portrait:</strong> Ensure only one individual appears in the photo.</li>
            <li><strong>Even Lighting:</strong> Avoid heavy backlighting, lens flare, or dark silhouettes.</li>
            <li><strong>Frontal Orientation:</strong> Position eyes and mouth facing the camera directly.</li>
            <li><strong>Clean Backgrounds:</strong> Background-removed cutouts are automatically composited cleanly.</li>
          </ul>
        </div>
      </div>
    </section>
  );
}

const ACTIVE_SESSION_KEY = "classsnap.activeSession";
const REVIEWER_KEY = "classsnap.reviewer";

function storageGet(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function storageSet(key, value) {
  try {
    if (value == null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* storage unavailable: the session can still be reopened from Reports */
  }
}

const STATUS_META = {
  present: { label: "Present", tone: "green" },
  absent: { label: "Absent", tone: "red" },
  needs_review: { label: "Needs review", tone: "amber" },
  not_detected: { label: "Not detected", tone: "gray" },
  unverified: { label: "Unverified", tone: "amber" },
};

const RECOGNITION_LABEL = {
  matched: "Matched",
  ambiguous: "Ambiguous match",
  not_detected: "Not detected",
  manual: "Manually assigned",
};

const METHOD_LABEL = {
  face_recognition: "Face recognition",
  manual_face_review: "Face verified by reviewer",
  manual: "Marked by reviewer",
  unresolved: "Unresolved at confirmation",
  manual_correction: "Corrected after confirmation",
};

const REJECTED_FACE = new Set(["reviewed_absent", "corrected_absent"]);

function StatusPill({ status }) {
  const meta = STATUS_META[status] || { label: status, tone: "gray" };
  return <span className={`pill ${meta.tone}`}>{meta.label}</span>;
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function openExport(sessionId, format) {
  window.open(`${API}/attendance/sessions/${sessionId}/report?format=${format}`, "_blank");
}

function FaceThumb({ src, alt }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) return <span className="face-thumb empty">—</span>;
  return <img className="face-thumb" src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />;
}

function AttendanceSummary({ summary, confirmed }) {
  const items = confirmed
    ? [
        ["Registered", summary.total_registered, ""],
        ["Present", summary.present, "green"],
        ["Absent", summary.absent, "red"],
        ["Unverified", summary.unverified, "amber"],
        ["Auto-identified", summary.auto_identified, "blue"],
        ["Manually decided", summary.manually_corrected, ""],
      ]
    : [
        ["Registered", summary.total_registered, ""],
        ["Auto-identified", summary.auto_identified, "blue"],
        ["Proposed present", summary.proposed_present, "green"],
        ["Needs review", summary.needs_review, "amber"],
        ["Unknown faces", summary.unknown_faces, "red"],
        ["Not detected", summary.not_detected, ""],
        ["Manually corrected", summary.manually_corrected, ""],
      ];
  return (
    <div className="summary-strip">
      {items.map(([label, value, tone]) => (
        <div className={`summary-item ${tone}`} key={label}>
          <strong>{value ?? 0}</strong>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

function AnnotatedImage({ src, detections, attendance }) {
  const [natural, setNatural] = useState(null);
  const names = useMemo(() => {
    const map = {};
    attendance.forEach((entry) => { map[entry.student_id] = entry.student_name; });
    return map;
  }, [attendance]);

  if (!src) {
    return (
      <div className="annotated-empty">
        The classroom photo is not stored on the server for privacy. Face crops are shown below;
        re-select the photo in step 02 of a new session to see the annotated view.
      </div>
    );
  }

  return (
    <div className="annotated-image">
      <img src={src} alt="Classroom with detected faces outlined" onLoad={(e) => setNatural({ w: e.target.naturalWidth, h: e.target.naturalHeight })} />
      {detections.map((detection) => {
        const box = detection.bbox;
        const width = box?.image_width || natural?.w;
        const height = box?.image_height || natural?.h;
        if (!box || !width || !height) return null;
        let tone = "unknown";
        let label = "Unknown";
        if (detection.student_id) {
          tone = "matched";
          label = names[detection.student_id] || detection.student_name || "Assigned";
        } else if (REJECTED_FACE.has(detection.status)) {
          tone = "rejected";
          label = "Not a student";
        } else if (detection.candidate_student_id) {
          tone = "review";
          label = `Review: ${detection.candidate_student_name || "candidate"}?`;
        }
        return (
          <div
            key={detection.detection_id}
            className={`face-box ${tone}`}
            style={{
              left: `${(box.x / width) * 100}%`,
              top: `${(box.y / height) * 100}%`,
              width: `${(box.w / width) * 100}%`,
              height: `${(box.h / height) * 100}%`,
            }}
          >
            <span>{label}</span>
          </div>
        );
      })}
    </div>
  );
}

function RosterRow({ entry, confirmed, busy, onSet, onVerify, onReject }) {
  const isPresent = entry.status === "present";
  const action = confirmed ? null : entry.status === "needs_review" && entry.detection_id ? (
    <>
      <Button variant="success" className="sm" disabled={busy} onClick={() => onVerify(entry)}>
        <IconCheck /> Verify identity
      </Button>
      <Button variant="secondary" className="sm" disabled={busy} onClick={() => onReject(entry)}>
        <IconX /> Not them
      </Button>
    </>
  ) : (
    <div className="segmented" role="group" aria-label={`Attendance for ${entry.student_name}`}>
      <button className={isPresent ? "active present" : ""} disabled={busy} onClick={() => onSet(entry, "present")}>
        Present
      </button>
      <button className={entry.status === "absent" ? "active absent" : ""} disabled={busy} onClick={() => onSet(entry, "absent")}>
        Absent
      </button>
    </div>
  );

  return (
    <tr className={`roster-row status-${entry.status}`}>
      <td className="check-cell">
        <input
          type="checkbox"
          checked={isPresent}
          disabled={confirmed || busy}
          onChange={(e) => onSet(entry, e.target.checked ? "present" : "absent")}
          aria-label={`${entry.student_name} present`}
        />
      </td>
      <td><span className="student-id">{entry.student_usn}</span></td>
      <td>
        <div className="roster-student">
          <FaceThumb src={entry.preview_url} alt={`Detected face for ${entry.student_name}`} />
          <div>
            <strong>{entry.student_name}</strong>
            <small>
              {RECOGNITION_LABEL[entry.recognition_status] || entry.recognition_status}
              {entry.similarity != null && entry.detection_id ? ` · ${Math.round(entry.similarity * 100)}% similarity` : ""}
            </small>
          </div>
        </div>
      </td>
      <td>
        <StatusPill status={entry.status} />
        {entry.manually_set && !confirmed && <span className="edited-flag">edited</span>}
      </td>
      <td>
        <div className="roster-action">
          {confirmed ? (
            <small className="muted">
              {METHOD_LABEL[entry.verification_method] || entry.verification_method || "—"}
              {entry.corrected_by ? ` · corrected by ${entry.corrected_by}` : ""}
            </small>
          ) : action}
        </div>
      </td>
    </tr>
  );
}

function UnknownFace({ detection, students, busy, onAssign, onReject }) {
  const [studentId, setStudentId] = useState(detection.candidate_student_id || "");
  return (
    <article className="unknown-face">
      <FaceThumb src={detection.preview_url} alt="Unidentified face" />
      <div className="unknown-face-body">
        <strong>{detection.candidate_student_id ? "Ambiguous match" : "Unknown face"}</strong>
        <small>
          {detection.candidate_student_name
            ? `Closest: ${detection.candidate_student_name}`
            : detection.status === "low_quality"
            ? "Low quality — could not be identified"
            : "No confident roster match"}
        </small>
        <select value={studentId} onChange={(e) => setStudentId(e.target.value)} aria-label="Assign this face to a student">
          <option value="">Choose student…</option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>
              {student.first_name} {student.last_name} ({student.student_id})
            </option>
          ))}
        </select>
        <div className="unknown-face-actions">
          <Button variant="success" className="sm" disabled={busy || !studentId} onClick={() => onAssign(detection, studentId)}>
            <IconCheck /> Assign
          </Button>
          <Button variant="secondary" className="sm" disabled={busy} onClick={() => onReject(detection)}>
            <IconX /> Not a student
          </Button>
        </div>
      </div>
    </article>
  );
}

function Attendance({ students, notify }) {
  const [name, setName] = useState("");
  const [classDate, setClassDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [classTime, setClassTime] = useState(() => new Date().toTimeString().slice(0, 5));
  const [reviewer, setReviewer] = useState(() => storageGet(REVIEWER_KEY) || "");
  const [session, setSession] = useState(null);
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState(null);
  const [filter, setFilter] = useState("all");

  const load = async (id) => {
    const detail = await request(`/attendance/sessions/${id}`);
    setSession(detail);
    return detail;
  };

  // Resume the active session after a page refresh; the server is the source of truth.
  useEffect(() => {
    const id = storageGet(ACTIVE_SESSION_KEY);
    if (id) load(id).catch(() => storageSet(ACTIVE_SESSION_KEY, null));
  }, []);

  const updateReviewer = (value) => {
    setReviewer(value);
    storageSet(REVIEWER_KEY, value.trim() || null);
  };

  const createSession = async (event) => {
    event.preventDefault();
    try {
      const created = await request("/attendance/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          class_at: `${classDate}T${classTime}:00`,
          actor: reviewer.trim() || "web-reviewer",
        }),
      });
      await request(`/attendance/sessions/${created.id}/process`, { method: "POST" });
      storageSet(ACTIVE_SESSION_KEY, created.id);
      await load(created.id);
      notify("Attendance session created");
    } catch (error) {
      notify(error.message, true);
    }
  };

  const startOver = () => {
    storageSet(ACTIVE_SESSION_KEY, null);
    setSession(null);
    setImage(null);
    setImagePreview(null);
    setConfirmError(null);
    setName("");
    setFilter("all");
  };

  const handleImageSelect = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      setImage(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const processImage = async (event) => {
    event.preventDefault();
    setProcessing(true);
    const form = new FormData();
    form.append("image", image);
    try {
      const detail = await request(`/attendance/sessions/${session.id}/image`, { method: "POST", body: form });
      setSession(detail);
      notify(`${detail.summary.proposed_present} student(s) automatically marked present`);
    } catch (error) {
      notify(error.message, true);
    } finally {
      setProcessing(false);
    }
  };

  const actor = reviewer.trim() || "web-reviewer";

  const run = async (action) => {
    setBusy(true);
    setConfirmError(null);
    try {
      await action();
    } catch (error) {
      notify(error.message, true);
    } finally {
      setBusy(false);
    }
  };

  const setStudentStatus = (entry, status) =>
    run(async () => {
      const detail = await request(
        `/attendance/sessions/${session.id}/attendance/${encodeURIComponent(entry.student_id)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status, actor }),
        }
      );
      setSession(detail);
    });

  const reviewFace = (detectionId, present, studentId, notes) =>
    run(async () => {
      await request(`/attendance/sessions/${session.id}/detections/${encodeURIComponent(detectionId)}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ present, student_id: present ? studentId : null, actor, notes }),
      });
      await load(session.id);
    });

  const confirm = async () => {
    if (!reviewer.trim()) {
      setConfirmError("Enter the reviewer's name before confirming attendance.");
      return;
    }
    setConfirming(true);
    setConfirmError(null);
    try {
      const detail = await request(`/attendance/sessions/${session.id}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: reviewer.trim() }),
      });
      if (detail.status !== "confirmed") throw new Error("The server did not confirm the session.");
      setSession(detail);
      notify("Attendance saved to the database");
    } catch (error) {
      setConfirmError(error.message);
    } finally {
      setConfirming(false);
    }
  };

  const confirmed = session?.status === "confirmed";
  const inReview = session && (session.status === "review_required" || confirmed);
  const attendance = session?.attendance || [];
  const unknownFaces = (session?.detections || []).filter(
    (detection) => !detection.student_id && !REJECTED_FACE.has(detection.status)
  );
  const unresolved = attendance.filter((entry) => entry.status === "needs_review" || entry.status === "not_detected").length;
  const shown = attendance.filter((entry) => filter === "all" || entry.status === filter);
  const filters = confirmed
    ? [["all", "All"], ["present", "Present"], ["absent", "Absent"], ["unverified", "Unverified"]]
    : [["all", "All"], ["present", "Present"], ["needs_review", "Needs review"], ["not_detected", "Not detected"], ["absent", "Absent"]];

  return (
    <section className="page-section">
      <PageHeading
        eyebrow="Verification Workflow"
        title="Classroom Attendance Session"
        description="Upload a classroom photo. Recognized students are marked present automatically; review the rest and confirm to save."
      >
        <span className="badge privacy">
          <IconShield /> In-Memory CV Processing
        </span>
      </PageHeading>

      <div className="attendance-layout">
        <div className="content-card">
          <div className="card-heading">
            <span className="step">01</span>
            <div>
              <h2>Session</h2>
              <p className="muted">Subject, schedule, and reviewer.</p>
            </div>
          </div>
          {session ? (
            <div className="session-info">
              <strong>{session.name}</strong>
              <small>Class: {formatDateTime(session.class_at)}</small>
              <span>
                <StatusPill status={confirmed ? "present" : "needs_review"} />{" "}
                <span className="muted">{confirmed ? "Confirmed" : session.status === "processing" ? "Waiting for photo" : "In review"}</span>
              </span>
              <Button variant="secondary" className="sm" onClick={startOver}>
                <IconRefresh /> Start new session
              </Button>
            </div>
          ) : (
            <form onSubmit={createSession}>
              <Field
                label="Subject / Session Title"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="CS 401 · Computer Vision · Lecture 4"
                required
              />
              <div className="date-time-fields">
                <Field label="Class Date" type="date" value={classDate} onChange={(e) => setClassDate(e.target.value)} required />
                <Field label="Class Time" type="time" value={classTime} onChange={(e) => setClassTime(e.target.value)} required />
              </div>
              <Button className="full" type="submit">
                <IconSparkles /> Initialize Session
              </Button>
            </form>
          )}
          <Field
            label="Reviewer (recorded on confirmation)"
            value={reviewer}
            onChange={(e) => updateReviewer(e.target.value)}
            placeholder="e.g. Prof. Rao"
            className="reviewer-field"
          />
        </div>

        <div className="content-card">
          <div className="card-heading">
            <span className="step">02</span>
            <div>
              <h2>Classroom Snapshot</h2>
              <p className="muted">One photo per session. Faces are detected, matched, and proposed.</p>
            </div>
          </div>
          <form onSubmit={processImage}>
            <label className="upload-zone compact" htmlFor="classroom-image">
              {imagePreview ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                  <img src={imagePreview} alt="Classroom thumbnail" style={{ maxHeight: 110, borderRadius: 6, objectFit: "cover" }} />
                  <strong>{image?.name}</strong>
                  <small>{(image.size / (1024 * 1024)).toFixed(2)} MB · Ready to scan</small>
                </div>
              ) : (
                <>
                  <div className="upload-icon"><IconUpload /></div>
                  <strong>Choose Classroom Photo</strong>
                  <small>JPG / PNG with visible classroom attendees</small>
                </>
              )}
              <input id="classroom-image" type="file" accept="image/*" onChange={handleImageSelect} disabled={session?.status !== "processing"} />
            </label>
            <Button className="full" type="submit" disabled={session?.status !== "processing" || !image || processing}>
              <IconSparkles /> {processing ? "Detecting Faces & Matching..." : inReview ? "Photo Already Processed" : "Process Classroom Image"}
            </Button>
          </form>
        </div>
      </div>

      {inReview && (
        <div className="content-card review-card">
          <div className="card-toolbar">
            <div>
              <span className="eyebrow">Step 03 · {confirmed ? "Saved Attendance" : "Review Proposed Attendance"}</span>
              <h2>{session.name}</h2>
              <p className="muted">
                {confirmed
                  ? `Confirmed by ${session.confirmed_by || "—"} on ${formatDateTime(session.confirmed_at)}. Loaded from the database.`
                  : "Students identified by face recognition are already marked present. Adjust anything that is wrong, then confirm."}
              </p>
            </div>
            {confirmed && (
              <div className="row-actions">
                <Button variant="secondary" className="sm" onClick={() => openExport(session.id, "csv")}>
                  <IconDownload /> CSV
                </Button>
                <Button variant="secondary" className="sm" onClick={() => openExport(session.id, "xlsx")}>
                  <IconDownload /> Excel
                </Button>
              </div>
            )}
          </div>

          <AttendanceSummary summary={session.summary || {}} confirmed={confirmed} />

          <details className="annotated-details" open={!confirmed}>
            <summary>Annotated classroom image ({session.detections.length} faces)</summary>
            <AnnotatedImage src={imagePreview} detections={session.detections} attendance={attendance} />
          </details>

          {!confirmed && unknownFaces.length > 0 && (
            <div className="unknown-faces">
              <h3>Faces needing identification ({unknownFaces.length})</h3>
              <p className="muted">These faces were detected but not matched confidently. No name is assigned until you choose one.</p>
              <div className="unknown-face-grid">
                {unknownFaces.map((detection) => (
                  <UnknownFace
                    key={detection.detection_id}
                    detection={detection}
                    students={students}
                    busy={busy}
                    onAssign={(face, studentId) => reviewFace(face.detection_id, true, studentId, "Identity assigned by reviewer")}
                    onReject={(face) => reviewFace(face.detection_id, false, null, "Not a registered student")}
                  />
                ))}
              </div>
            </div>
          )}

          <div className="roster-filters" role="tablist">
            {filters.map(([key, label]) => (
              <button key={key} className={filter === key ? "active" : ""} onClick={() => setFilter(key)}>
                {label} ({key === "all" ? attendance.length : attendance.filter((entry) => entry.status === key).length})
              </button>
            ))}
          </div>

          <div className="table-wrap">
            <table className="roster-table">
              <thead>
                <tr>
                  <th aria-label="Present" />
                  <th>Student ID</th>
                  <th>Student Name</th>
                  <th>Attendance Status</th>
                  <th>{confirmed ? "Verification" : "Action"}</th>
                </tr>
              </thead>
              <tbody>
                {shown.length ? (
                  shown.map((entry) => (
                    <RosterRow
                      key={entry.student_id}
                      entry={entry}
                      confirmed={confirmed}
                      busy={busy || confirming}
                      onSet={setStudentStatus}
                      onVerify={(row) => reviewFace(row.detection_id, true, row.student_id, "Identity verified by reviewer")}
                      onReject={(row) => reviewFace(row.detection_id, false, null, "Ambiguous match rejected")}
                    />
                  ))
                ) : (
                  <tr><td colSpan="5" className="empty-state">No students in this view.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {!confirmed && (
            <div className="confirm-bar">
              <div>
                {session.confirmation_problems?.length > 0 ? (
                  <div className="confirm-problems">
                    <strong>Fix before confirming:</strong>
                    <ul>{session.confirmation_problems.map((problem) => <li key={problem}>{problem}</li>)}</ul>
                  </div>
                ) : (
                  <p className="muted">
                    {session.summary.proposed_present} present · {session.summary.proposed_absent} absent
                    {unresolved > 0 && ` · ${unresolved} unresolved will be saved as UNVERIFIED (not absent)`}
                  </p>
                )}
                {confirmError && (
                  <div className="confirm-error" role="alert">
                    <strong>Attendance was not saved.</strong> {confirmError}
                    <Button variant="secondary" className="sm" onClick={confirm} disabled={confirming}>
                      <IconRefresh /> Retry
                    </Button>
                  </div>
                )}
              </div>
              <Button
                className="confirm-button"
                onClick={confirm}
                disabled={confirming || busy || session.confirmation_problems?.length > 0}
              >
                <IconCheckCircle /> {confirming ? "Saving…" : "CONFIRM ATTENDANCE"}
              </Button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function SessionHistoryRow({ item, onResume }) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const confirmed = item.status === "confirmed";

  const toggle = async () => {
    if (!open && !detail) {
      try {
        setDetail(await request(`/attendance/sessions/${item.session_id}`));
      } catch {
        setDetail({ attendance: [] });
      }
    }
    setOpen(!open);
  };

  return (
    <>
      <tr>
        <td>{new Date(item.class_date).toLocaleDateString()}</td>
        <td><strong>{item.session_name}</strong></td>
        <td>{confirmed ? <span className="pill green">Confirmed</span> : <span className="pill amber">{item.status.replace("_", " ")}</span>}</td>
        <td>{confirmed ? item.total_registered : "—"}</td>
        <td>{confirmed ? item.present_count : "—"}</td>
        <td>{confirmed ? item.absent_count : "—"}</td>
        <td>{confirmed ? item.unverified_count : "—"}</td>
        <td>
          {confirmed ? (
            <small>{formatDateTime(item.confirmed_at)}<br />{item.confirmed_by || "—"}</small>
          ) : "—"}
        </td>
        <td className="row-actions">
          {confirmed ? (
            <>
              <Button variant="secondary" className="sm" onClick={toggle}>
                {open ? <IconChevronUp /> : <IconChevronDown />} Details
              </Button>
              <Button variant="secondary" className="sm" onClick={() => openExport(item.session_id, "csv")}>CSV</Button>
              <Button variant="secondary" className="sm" onClick={() => openExport(item.session_id, "xlsx")}>Excel</Button>
            </>
          ) : (
            <Button variant="secondary" className="sm" onClick={() => onResume(item.session_id)}>Resume</Button>
          )}
        </td>
      </tr>
      {open && detail && (
        <tr className="template-detail-row">
          <td colSpan="9">
            <div className="history-detail">
              {detail.attendance.map((entry) => (
                <span className="history-chip" key={entry.student_id}>
                  <span className="student-id">{entry.student_usn}</span> {entry.student_name} <StatusPill status={entry.status} />
                </span>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function StudentHistory({ students, notify }) {
  const [studentId, setStudentId] = useState("");
  const [history, setHistory] = useState(null);

  useEffect(() => {
    if (!studentId) {
      setHistory(null);
      return;
    }
    request(`/attendance/students/${encodeURIComponent(studentId)}/history`)
      .then(setHistory)
      .catch((error) => notify(error.message, true));
  }, [studentId]);

  return (
    <div className="content-card">
      <div className="card-toolbar">
        <div>
          <h2>Student Attendance History</h2>
          <p className="muted">Confirmed sessions only.</p>
        </div>
        <select value={studentId} onChange={(e) => setStudentId(e.target.value)} aria-label="Select student">
          <option value="">Select a student…</option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>
              {student.first_name} {student.last_name} ({student.student_id})
            </option>
          ))}
        </select>
      </div>
      {history && (
        <>
          <div className="summary-strip">
            <div className="summary-item"><strong>{history.total_sessions}</strong><span>Sessions</span></div>
            <div className="summary-item green"><strong>{history.sessions_attended}</strong><span>Attended</span></div>
            <div className="summary-item red"><strong>{history.sessions_absent}</strong><span>Absent</span></div>
            <div className="summary-item amber"><strong>{history.sessions_unverified}</strong><span>Unverified</span></div>
            <div className="summary-item blue">
              <strong>{history.attendance_rate == null ? "—" : `${Math.round(history.attendance_rate * 100)}%`}</strong>
              <span>Rate (excl. unverified)</span>
            </div>
          </div>
          {history.sessions.length ? (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Date</th><th>Subject</th><th>Status</th><th>How verified</th></tr></thead>
                <tbody>
                  {history.sessions.map((row) => (
                    <tr key={row.session_id}>
                      <td>{new Date(row.class_date).toLocaleDateString()}</td>
                      <td>{row.session_name}</td>
                      <td><StatusPill status={row.status} /></td>
                      <td><small className="muted">{METHOD_LABEL[row.verification_method] || "—"}</small></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">No confirmed sessions for this student yet.</p>
          )}
        </>
      )}
    </div>
  );
}

function Reports({ students, notify, setPage }) {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [report, setReport] = useState({ total_sessions: 0, total_attendance: 0, total_possible: 0, sessions: [] });
  const [history, setHistory] = useState([]);

  const load = async () => {
    try {
      const params = new URLSearchParams();
      if (from) params.set("date_from", `${from}T00:00:00`);
      if (to) {
        const end = new Date(`${to}T00:00:00`);
        end.setDate(end.getDate() + 1);
        params.set("date_to", end.toISOString());
      }
      const [summary, sessions] = await Promise.all([
        request(`/attendance/sessions/reports/summary?${params}`),
        request("/attendance/sessions"),
      ]);
      setReport(summary);
      setHistory(sessions);
    } catch (error) {
      notify(error.message, true);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const inRange = (item) => {
    const day = new Date(item.class_date).toISOString().slice(0, 10);
    return (!from || day >= from) && (!to || day <= to);
  };

  const resume = (sessionId) => {
    storageSet(ACTIVE_SESSION_KEY, sessionId);
    setPage("attendance");
  };

  const shown = history.filter(inRange);

  return (
    <section className="page-section">
      <PageHeading
        eyebrow="Analytics & Audits"
        title="Attendance History"
        description="Every session, its confirmed attendance, and per-student history. Exports read directly from saved records."
      />

      <div className="content-card report-filters">
        <div>
          <label>
            From Date
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label>
            To Date
            <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
        </div>
        <Button onClick={load}>
          <IconRefresh /> Filter Records
        </Button>
      </div>

      <div className="stat-grid">
        <Stat icon={<IconBarChart />} tone="blue" label="Confirmed Classes" value={report.total_sessions} />
        <Stat icon={<IconCheckCircle />} tone="green" label="Attendance Marks" value={report.total_attendance} />
        <Stat
          icon={<IconClock />}
          tone="amber"
          label="Attendance Rate"
          value={report.total_possible ? `${Math.round((report.total_attendance / report.total_possible) * 100)}%` : "—"}
        />
      </div>

      <div className="content-card">
        <div className="card-toolbar">
          <div>
            <h2>Sessions ({shown.length})</h2>
            <p className="muted">Unconfirmed sessions can be resumed; confirmed ones are read-only.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th><th>Subject</th><th>Status</th><th>Registered</th><th>Present</th>
                <th>Absent</th><th>Unverified</th><th>Confirmed</th><th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {shown.length ? (
                shown.map((item) => <SessionHistoryRow key={item.session_id} item={item} onResume={resume} />)
              ) : (
                <tr><td colSpan="9" className="empty-state">No attendance sessions for the selected period.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <StudentHistory students={students} notify={notify} />
    </section>
  );
}

function App() {
  const [page, setPage] = useState(window.location.hash.slice(1) || "overview");
  const [enrollmentStudentId, setEnrollmentStudentId] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [students, setStudents] = useState([]);
  const [toast, setToast] = useState(null);

  const notify = (message, error = false) => {
    setToast({ message, error });
    window.setTimeout(() => setToast(null), 3600);
  };

  const refresh = async () => {
    try {
      setStudents(await request("/students?active_only=true"));
    } catch (error) {
      notify(error.message, true);
    }
  };

  useEffect(() => {
    refresh();
    const onHash = () => setPage(window.location.hash.slice(1) || "overview");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const changePage = (next, studentId = "") => {
    window.location.hash = next;
    setEnrollmentStudentId(studentId);
    setPage(next);
  };

  const content = useMemo(() => {
    const pages = {
      overview: <Overview students={students} setPage={changePage} />,
      students: <Students students={students} refresh={refresh} setPage={changePage} notify={notify} />,
      enroll: <Enroll students={students} refresh={refresh} notify={notify} preselectedStudentId={enrollmentStudentId} />,
      attendance: <Attendance students={students} notify={notify} />,
      reports: <Reports students={students} notify={notify} setPage={changePage} />,
    };
    return pages[page] || <Overview students={students} setPage={changePage} />;
  }, [page, students, enrollmentStudentId]);

  return (
    <div className="app-shell">
      <Sidebar page={page} setPage={changePage} open={menuOpen} setOpen={setMenuOpen} />
      <main className="main-content">
        <header className="mobile-header">
          <a className="brand" href="#overview" onClick={() => changePage("overview")}>
            <div className="brand-mark">C</div>
            <strong>ClassSnap</strong>
          </a>
          <button className="menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle navigation">
            ☰
          </button>
        </header>
        {content}
        {toast && (
          <div className={`toast ${toast.error ? "error" : ""}`} role="status">
            {toast.error ? <IconX style={{ width: 16, height: 16 }} /> : <IconCheck style={{ width: 16, height: 16 }} />}
            <span>{toast.message}</span>
          </div>
        )}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
