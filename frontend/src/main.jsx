import { StrictMode, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { createPortal } from "react-dom";
import "./styles.css";

const API = "/api/v1";

function classesOf(students) {
  return [...new Set(students.map((student) => student.class_section).filter(Boolean))].sort();
}

function ClassOptions({ students }) {
  return (
    <datalist id="class-options">
      {[...new Set(["A", "B", "C", "D", ...classesOf(students)])].sort().map((value) => (
        <option key={value} value={value} />
      ))}
    </datalist>
  );
}
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

function BrandMark() {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path d="M4 11V7a3 3 0 0 1 3-3h4M21 4h4a3 3 0 0 1 3 3v4M28 21v4a3 3 0 0 1-3 3h-4M11 28H7a3 3 0 0 1-3-3v-4" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="16" cy="16" r="4.2" fill="currentColor" />
    </svg>
  );
}

function IconMenu(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...props}><line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="14" y2="17"/></svg>;
}

function IconArrowRight(props) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="5" y1="12" x2="19" y2="12"/><polyline points="13 6 19 12 13 18"/></svg>;
}

const NAV_SECTIONS = [
  { title: "Workspace", links: [{ id: "overview", icon: <IconHome />, label: "Overview" }] },
  {
    title: "Roster",
    links: [
      { id: "students", icon: <IconUsers />, label: "Students" },
      { id: "enroll", icon: <IconUserPlus />, label: "Enroll faces" },
    ],
  },
  {
    title: "Attendance",
    links: [
      { id: "attendance", icon: <IconCheckCircle />, label: "Take attendance" },
      { id: "reports", icon: <IconBarChart />, label: "History" },
    ],
  },
];

function Sidebar({ page, setPage, open, setOpen }) {
  return (
    <>
      <div className={`sidebar-scrim ${open ? "open" : ""}`} onClick={() => setOpen(false)} aria-hidden="true" />
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <a className="brand" href="#overview" onClick={() => { setPage("overview"); setOpen(false); }}>
          <span className="brand-mark"><BrandMark /></span>
          <span className="brand-text">
            <strong>ClassSnap</strong>
            <small>Attendance, verified</small>
          </span>
        </a>
        <nav className="nav" aria-label="Main navigation">
          {NAV_SECTIONS.map((section) => (
            <div className="nav-section" key={section.title}>
              <span className="nav-section-title">{section.title}</span>
              {section.links.map((link) => (
                <a
                  className={`nav-link ${page === link.id ? "active" : ""}`}
                  href={`#${link.id}`}
                  key={link.id}
                  aria-current={page === link.id ? "page" : undefined}
                  onClick={() => { setPage(link.id); setOpen(false); }}
                >
                  {link.icon}
                  <span>{link.label}</span>
                </a>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-note">
          <IconShield />
          <div>
            <strong>Privacy by design</strong>
            <p>Classroom photos are processed in memory. Only face templates and crops are stored.</p>
          </div>
        </div>
      </aside>
    </>
  );
}

function PageHeading({ eyebrow, title, children, description }) {
  return (
    <header className="page-heading">
      <div className="page-heading-info">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p className="lead">{description}</p>}
      </div>
      {children && <div className="page-heading-actions">{children}</div>}
    </header>
  );
}

const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/* Counts a leading number up to its value ("95%" counts 0→95, then keeps the "%"). */
function CountUp({ value, duration = 750 }) {
  const match = typeof value === "number" ? [null, String(value), ""] : String(value ?? "").match(/^(\d+)(.*)$/);
  const target = match ? Number(match[1]) : null;
  const suffix = match ? match[2] : "";
  const shown = useRef(0);
  const [n, setN] = useState(0);

  useEffect(() => {
    if (target == null) return undefined;
    if (reducedMotion()) {
      shown.current = target;
      setN(target);
      return undefined;
    }
    const from = shown.current;
    const start = performance.now();
    let frame;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const next = Math.round(from + (target - from) * eased);
      shown.current = next;
      setN(next);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  if (target == null) return value;
  return `${n}${suffix}`;
}

function Stat({ icon, tone, label, value, foot }) {
  return (
    <article className={`stat-card ${tone || ""}`}>
      <div className="stat-top">
        <span className="stat-label">{label}</span>
        <span className={`stat-icon ${tone || ""}`}>{icon}</span>
      </div>
      <strong className="stat-value"><CountUp value={value} /></strong>
      {foot && <span className="stat-foot">{foot}</span>}
    </article>
  );
}

function Meter({ value, total, tone = "" }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <span className={`meter ${tone}`} role="img" aria-label={`${value} of ${total}`}>
      <i style={{ width: `${pct}%` }} />
    </span>
  );
}

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function Overview({ students, setPage }) {
  const [history, setHistory] = useState(null);

  useEffect(() => {
    request("/attendance/sessions").then(setHistory).catch(() => setHistory([]));
  }, []);

  const enrolled = students.filter((s) => (s.enrolled_templates_count || 0) > 0);
  const notEnrolled = students.filter((s) => !(s.enrolled_templates_count > 0));
  const classes = classesOf(students);
  const unassigned = students.filter((s) => !s.class_section).length;
  const sessions = history || [];
  const confirmed = sessions.filter((s) => s.status === "confirmed");
  const pending = sessions.filter((s) => s.status !== "confirmed");
  const marks = confirmed.reduce((sum, s) => sum + s.present_count, 0);
  const possible = confirmed.reduce((sum, s) => sum + s.total_registered, 0);
  const rate = possible ? Math.round((marks / possible) * 100) : null;

  const classRows = [
    ...classes.map((value) => ({ label: `Class ${value}`, key: value, members: students.filter((s) => s.class_section === value) })),
    ...(unassigned ? [{ label: "No class", key: "-", members: students.filter((s) => !s.class_section) }] : []),
  ];

  const resume = (sessionId) => {
    storageSet(ACTIVE_SESSION_KEY, sessionId);
    setPage("attendance");
  };

  const today = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  return (
    <section className="page-section">
      <PageHeading eyebrow={today} title={greeting()} description="Here is where your roster and attendance stand today.">
        <Button variant="secondary" onClick={() => setPage("students")}>
          <IconUserPlus /> Add student
        </Button>
        <Button onClick={() => setPage("attendance")}>
          <IconCheckCircle /> Take attendance
        </Button>
      </PageHeading>

      <div className="stat-grid four">
        <Stat icon={<IconUsers />} tone="blue" label="Active students" value={students.length} foot={classes.length ? `Across ${classes.length} ${classes.length === 1 ? "class" : "classes"}` : "No classes assigned yet"} />
        <Stat
          icon={<IconShield />}
          tone="green"
          label="Face coverage"
          value={students.length ? `${Math.round((enrolled.length / students.length) * 100)}%` : "—"}
          foot={notEnrolled.length ? `${notEnrolled.length} without a reference photo` : "Every student enrolled"}
        />
        <Stat icon={<IconCheckCircle />} tone="ink" label="Confirmed sessions" value={history ? confirmed.length : "…"} foot={pending.length ? `${pending.length} awaiting confirmation` : "Nothing pending"} />
        <Stat icon={<IconBarChart />} tone="amber" label="Attendance rate" value={rate == null ? "—" : `${rate}%`} foot={possible ? `${marks} of ${possible} marks present` : "Confirm a session to see this"} />
      </div>

      <div className="overview-grid">
        <div className="content-card">
          <div className="card-toolbar">
            <div>
              <h2>Recent sessions</h2>
              <p className="muted">The latest classes, newest first.</p>
            </div>
            <Button variant="ghost" className="sm" onClick={() => setPage("reports")}>
              View all
            </Button>
          </div>
          {!history ? (
            <div className="skeleton-list" aria-label="Loading sessions">
              <span className="skeleton" /><span className="skeleton" /><span className="skeleton" />
            </div>
          ) : !sessions.length ? (
            <div className="empty-state">
              <p>No attendance taken yet.</p>
              <Button className="sm" onClick={() => setPage("attendance")}>Start the first session</Button>
            </div>
          ) : (
            <ul className="session-list">
              {sessions.slice(0, 6).map((item) => {
                const date = new Date(item.class_date);
                const done = item.status === "confirmed";
                return (
                  <li key={item.session_id} className="session-item">
                    <span className="date-chip">
                      <b>{date.getDate()}</b>
                      <small>{date.toLocaleDateString(undefined, { month: "short" })}</small>
                    </span>
                    <span className="session-item-main">
                      <strong>{item.session_name}</strong>
                      <small>
                        {item.class_section ? `Class ${item.class_section}` : "All classes"},{" "}
                        {date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </small>
                    </span>
                    {done ? (
                      <span className="session-item-stat">
                        <span className="mono">{item.present_count}/{item.total_registered}</span>
                        <Meter value={item.present_count} total={item.total_registered} tone="green" />
                      </span>
                    ) : (
                      <Button variant="secondary" className="sm" onClick={() => resume(item.session_id)}>
                        Resume
                      </Button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="overview-side">
          <div className="content-card">
            <div className="card-toolbar">
              <div>
                <h2>Classes</h2>
                <p className="muted">Students and face coverage per class.</p>
              </div>
            </div>
            {classRows.length ? (
              <ul className="class-list">
                {classRows.map((row) => {
                  const withFace = row.members.filter((s) => s.enrolled_templates_count > 0).length;
                  return (
                    <li key={row.key}>
                      <span className={`class-badge ${row.key === "-" ? "none" : ""}`}>{row.key === "-" ? "—" : row.key}</span>
                      <span className="class-list-main">
                        <strong>{row.label}</strong>
                        <Meter value={withFace} total={row.members.length} />
                      </span>
                      <span className="mono muted">{withFace}/{row.members.length}</span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <div className="empty-state">No students yet.</div>
            )}
          </div>

          {(notEnrolled.length > 0 || unassigned > 0 || pending.length > 0) && (
            <div className="content-card attention-card">
              <h2>Needs attention</h2>
              <ul className="attention-list">
                {pending.length > 0 && (
                  <li>
                    <span className="dot amber" />
                    <span>{pending.length} {pending.length === 1 ? "session is" : "sessions are"} waiting for review</span>
                    <button className="link-button" onClick={() => resume(pending[0].session_id)}>Resume</button>
                  </li>
                )}
                {notEnrolled.length > 0 && (
                  <li>
                    <span className="dot red" />
                    <span>{notEnrolled.length} {notEnrolled.length === 1 ? "student has" : "students have"} no face reference</span>
                    <button className="link-button" onClick={() => setPage("enroll", notEnrolled[0].id)}>Enroll</button>
                  </li>
                )}
                {unassigned > 0 && (
                  <li>
                    <span className="dot gray" />
                    <span>{unassigned} {unassigned === 1 ? "student is" : "students are"} not in a class</span>
                    <button className="link-button" onClick={() => setPage("students")}>Assign</button>
                  </li>
                )}
              </ul>
            </div>
          )}
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
    class_section: student.class_section || "",
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
          class_section: form.class_section.trim().toUpperCase() || null,
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
              <span className="eyebrow">Edit student</span>
              <h2 style={{ margin: 0 }}>{student.first_name} {student.last_name}</h2>
              <small className="student-id">{student.student_id}</small>
            </div>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <IconX style={{ width: 18, height: 18 }} />
          </button>
        </div>

        <form className="modal-body" onSubmit={save} noValidate>
          <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr", gap: "14px 20px" }}>
            <label className="full" style={{ gridColumn: "1 / -1" }}>
              USN
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
              First name
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
              Last name
              <input
                name="last_name"
                value={form.last_name}
                onChange={update}
                placeholder="Doe"
                required
              />
            </label>
            <label className="full" style={{ gridColumn: "1 / -1" }}>
              Email
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={update}
                placeholder="jane.doe@university.edu"
              />
            </label>
            <label className="full" style={{ gridColumn: "1 / -1" }}>
              Class
              <input
                name="class_section"
                value={form.class_section}
                onChange={update}
                placeholder="A"
                maxLength="16"
                list="class-options"
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
              Consent notes
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
              {saving ? "Saving…" : "Save changes"}
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
        <td>{student.class_section ? <span className="pill blue">{student.class_section}</span> : <span className="muted">—</span>}</td>
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
              <small>{templates.length ? "View face references" : "Face not enrolled"}</small>
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
          <td colSpan="6">
            <div className="template-detail">
              <div className="template-detail-heading">
                <div>
                                    <h3>{templates.length ? `${templates.length} face ${templates.length === 1 ? "reference" : "references"}` : "No face references"}</h3>
                  <p className="muted">
                    Each preview is the aligned face crop the recognizer compares against.
                  </p>
                </div>
                <Button variant="secondary" className="sm" onClick={() => setPage("enroll", student.id)}>
                  <IconUserPlus style={{ width: 14, height: 14 }} /> Add reference
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
                        <span className="template-number">Reference {index + 1}</span>
                        {template.is_primary && <span className="pill blue">Primary</span>}
                      </div>
                      <dl>
                        <div>
                          <dt>Model</dt>
                          <dd>{template.model_name} {template.model_version}</dd>
                        </div>
                        <div>
                          <dt>Embedding</dt>
                          <dd>{template.embedding_dim} dimensions</dd>
                        </div>
                        <div>
                          <dt>Quality</dt>
                          <dd>
                            {Math.round(template.quality_score * 100)}%
                            <span className="quality-bar">
                              <i style={{ width: `${Math.min(100, Math.max(0, template.quality_score * 100))}%` }} />
                            </span>
                          </dd>
                        </div>
                        <div>
                          <dt>Added</dt>
                          <dd>{new Date(template.created_at).toLocaleDateString()}</dd>
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
                        <IconTrash style={{ width: 13, height: 13 }} /> Delete reference
                      </Button>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="template-empty">
                  No face references yet. Add a portrait so this student can be recognized in class photos.
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
  const [classFilter, setClassFilter] = useState("");
  const classes = classesOf(students);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    student_id: "",
    email: "",
    has_consent: false,
    consent_notes: "",
    class_section: "",
  });

  const filteredStudents = useMemo(() => {
    const inClass = classFilter
      ? students.filter((s) => (classFilter === "-" ? !s.class_section : s.class_section === classFilter))
      : students;
    if (!search.trim()) return inClass;
    const q = search.toLowerCase();
    return inClass.filter(
      (s) =>
        s.first_name.toLowerCase().includes(q) ||
        s.last_name.toLowerCase().includes(q) ||
        s.student_id.toLowerCase().includes(q) ||
        (s.email && s.email.toLowerCase().includes(q))
    );
  }, [students, search, classFilter]);

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
        body: JSON.stringify({ ...form, class_section: form.class_section.trim().toUpperCase() || null }),
      });
      setForm({
        first_name: "",
        last_name: "",
        student_id: "",
        email: "",
        has_consent: false,
        consent_notes: "",
        class_section: "",
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
        title="Students"
        description="Everyone on the roster, their class, consent and face references."
      >
        <Button onClick={() => setPage("enroll")}>
          <IconUserPlus /> Enroll a face
        </Button>
      </PageHeading>

      <div className="content-card">
        <div className="card-toolbar">
          <div>
            <h2>Active students ({filteredStudents.length})</h2>
            <p className="muted">Search by name, USN or email.</p>
          </div>
          <div>
            <input
              type="text"
              className="search-input"
              placeholder="Search students"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select value={classFilter} onChange={(e) => setClassFilter(e.target.value)} aria-label="Filter by class">
              <option value="">All classes</option>
              {classes.map((value) => <option key={value} value={value}>Class {value}</option>)}
              <option value="-">No class</option>
            </select>
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
                <th>USN</th>
                <th>Class</th>
                <th>Consent</th>
                <th>Face references</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {!filteredStudents.length ? (
                <tr>
                  <td colSpan="6" className="empty-state">
                    {search ? "No students match that search." : "No students yet. Add the first one below."}
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
        <div>
          <h2>Add a student</h2>
          <p className="muted">
            Create the record first, then enroll a face so they can be recognized.
          </p>
        </div>
        <form className="form-grid" noValidate onSubmit={submit}>
          <Field label="First name" name="first_name" value={form.first_name} onChange={update} placeholder="Jane" required />
          <Field label="Last name" name="last_name" value={form.last_name} onChange={update} placeholder="Doe" required />
          <Field
            label="USN"
            name="student_id"
            value={form.student_id}
            onChange={update}
            placeholder="ENG24AM0107"
            maxLength="11"
            required
          />
          <Field label="Email (optional)" name="email" type="email" value={form.email} onChange={update} placeholder="jane.doe@university.edu" />
          <Field label="Class" name="class_section" value={form.class_section} onChange={update} placeholder="A" maxLength="16" list="class-options" />
          <ClassOptions students={students} />
          <label className="checkbox-label full">
            <input name="has_consent" type="checkbox" checked={form.has_consent} onChange={update} />
            <span>Biometric consent verified and recorded on file</span>
          </label>
          <Field className="full" label="Consent notes (optional)" name="consent_notes" value={form.consent_notes} onChange={update} placeholder="Parent/student consent signed on registration." />
          <Button className="full" type="submit">
            <IconUserPlus /> Add student
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
        title="Enroll a face"
        description="A clear reference portrait lets ClassSnap recognize this student in classroom photos."
      />

      <div className="split-layout">
        <div className="content-card">
          <h2>Reference photo</h2>
          <p className="muted" style={{ marginBottom: "20px" }}>
            Pick the student, then choose one portrait of them.
          </p>

          <form onSubmit={submit}>
            <label style={{ marginBottom: "16px" }}>
              Student
              <select value={studentId} onChange={(e) => setStudentId(e.target.value)} required>
                <option value="">Choose a student</option>
                {students.map((student) => (
                  <option value={student.id} key={student.id}>
                    {student.first_name} {student.last_name} ({student.student_id}{student.class_section ? ` · ${student.class_section}` : ""})
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
                    style={{ maxHeight: 160, borderRadius: 8, objectFit: "contain", border: "1px solid var(--rule)" }}
                  />
                  <strong>{image?.name}</strong>
                  <small>{(image.size / 1024).toFixed(1)} KB · click to choose another</small>
                </div>
              ) : (
                <>
                  <div className="upload-icon">
                    <IconUpload />
                  </div>
                  <strong>Choose a portrait</strong>
                  <small>JPG or PNG, face clearly visible, up to 10 MB</small>
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
              label="Consent notes (optional)"
              value={consentNotes}
              onChange={(e) => setConsentNotes(e.target.value)}
              placeholder="Signed waiver form ID or reference code"
              style={{ marginBottom: "18px" }}
            />

            <Button className="full" type="submit" disabled={submitting || !image || !studentId}>
              <IconUserPlus /> {submitting ? "Enrolling…" : "Enroll face"}
            </Button>
          </form>
        </div>

        <div className="info-panel">
          <div className="info-icon">
            <IconShield />
          </div>
          <h2>What makes a good reference</h2>
          <ul>
            <li><strong>One face.</strong> Only the student should be in the frame.</li>
            <li><strong>Even light.</strong> Avoid windows behind them and harsh shadows.</li>
            <li><strong>Facing the camera.</strong> Both eyes and the mouth should be visible.</li>
            <li><strong>Several angles help.</strong> Add a second reference for students who are often missed.</li>
          </ul>
        </div>
      </div>
    </section>
  );
}

const ACTIVE_SESSION_KEY = "classsnap.activeSession";
// Mirrors MAX_PHOTOS_PER_SESSION on the server.
const MAX_PHOTOS = 10;
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

function StatusPill({ status, className = "" }) {
  const meta = STATUS_META[status] || { label: status, tone: "gray" };
  return <span className={`pill ${meta.tone} ${className}`}>{meta.label}</span>;
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
          <strong><CountUp value={value ?? 0} /></strong>
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
        re-select the photo in step 2 of a new session to see the annotated view.
      </div>
    );
  }

  return (
    <div className="annotated-image">
      <img src={src} alt="Classroom with detected faces outlined" onLoad={(e) => setNatural({ w: e.target.naturalWidth, h: e.target.naturalHeight })} />
      {detections.map((detection, index) => {
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
              "--i": index,
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
  const previous = useRef(entry.status);
  const changed = previous.current !== entry.status;
  useEffect(() => {
    previous.current = entry.status;
  }, [entry.status]);
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
    <tr className={`roster-row status-${entry.status} ${changed ? "changed" : ""}`}>
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
        <StatusPill key={entry.status} status={entry.status} className={changed ? "changed" : ""} />
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
              {student.first_name} {student.last_name} ({student.student_id}{student.class_section ? ` · ${student.class_section}` : ""})
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
  const [classSection, setClassSection] = useState("");
  const classes = classesOf(students);
  const [reviewer, setReviewer] = useState(() => storageGet(REVIEWER_KEY) || "");
  const [session, setSession] = useState(null);
  // Photos chosen but not yet processed, and previews of processed photos
  // (index = photo_index - 1). Photos are never stored on the server.
  const [images, setImages] = useState([]);
  const [imagePreviews, setImagePreviews] = useState([]);
  const [photoPreviews, setPhotoPreviews] = useState([]);
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
          class_section: classSection || null,
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
    setImages([]);
    setImagePreviews([]);
    setPhotoPreviews([]);
    setConfirmError(null);
    setName("");
    setFilter("all");
  };

  const handleImageSelect = (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length) {
      setImages(files);
      setImagePreviews(files.map((file) => URL.createObjectURL(file)));
    }
    // Let the teacher pick the same file again later.
    event.target.value = "";
  };

  const processImage = async (event) => {
    event.preventDefault();
    setProcessing(true);
    const form = new FormData();
    images.forEach((file) => form.append("images", file));
    const before = session.summary?.proposed_present || 0;
    const addingMore = session.status === "review_required";
    try {
      const detail = await request(`/attendance/sessions/${session.id}/images`, { method: "POST", body: form });
      setSession(detail);
      // Place each processed preview at its photo number so faces line up.
      const firstIndex = detail.photo_count - images.length;
      setPhotoPreviews((previous) => {
        const next = previous.slice(0, firstIndex);
        while (next.length < firstIndex) next.push(null);
        return [...next, ...imagePreviews];
      });
      setImages([]);
      setImagePreviews([]);
      const photos = `${images.length} photo${images.length === 1 ? "" : "s"}`;
      notify(
        addingMore
          ? `${photos} added. ${Math.max(0, detail.summary.proposed_present - before)} more student(s) marked present`
          : `${photos} processed. ${detail.summary.proposed_present} student(s) automatically marked present`
      );
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
  const photoCount = session?.photo_count || 0;
  const canAddPhotos =
    !!session && (session.status === "processing" || session.status === "review_required") && photoCount < MAX_PHOTOS;
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
        title="Take attendance"
        description="Upload one or more classroom photos. Recognized students are marked present; you review the rest and confirm."
      >
        <span className="badge privacy">
          <IconShield /> Photos are processed in memory
        </span>
      </PageHeading>

      <div className="attendance-layout">
        <div className="content-card">
          <div className="card-heading">
            <span className="step">1</span>
            <div>
              <h2>Session</h2>
              <p className="muted">What, when, and who is reviewing.</p>
            </div>
          </div>
          {session ? (
            <div className="session-info">
              <strong>{session.name}</strong>
              <small>
                {session.class_section ? `Class ${session.class_section}` : "All classes"} · {formatDateTime(session.class_at)}
              </small>
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
                label="Subject"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="CS401 Computer Vision, lecture 4"
                required
              />
              <label>
                Class
                <select value={classSection} onChange={(e) => setClassSection(e.target.value)}>
                  <option value="">All active students</option>
                  {classes.map((value) => (
                    <option key={value} value={value}>
                      Class {value} ({students.filter((student) => student.class_section === value).length} students)
                    </option>
                  ))}
                </select>
              </label>
              <div className="date-time-fields">
                <Field label="Date" type="date" value={classDate} onChange={(e) => setClassDate(e.target.value)} required />
                <Field label="Time" type="time" value={classTime} onChange={(e) => setClassTime(e.target.value)} required />
              </div>
              <Button className="full" type="submit">
                <IconCheck /> Start session
              </Button>
            </form>
          )}
          <Field
            label="Reviewer, recorded when you confirm"
            value={reviewer}
            onChange={(e) => updateReviewer(e.target.value)}
            placeholder="e.g. Prof. Rao"
            className="reviewer-field"
          />
        </div>

        <div className="content-card">
          <div className="card-heading">
            <span className="step">2</span>
            <div>
              <h2>Classroom photo</h2>
              <p className="muted">
                Add one or more photos of the class, e.g. front and back of the room. A student recognised in any photo is marked present once.
              </p>
            </div>
          </div>
          <form onSubmit={processImage}>
            <label className={`upload-zone compact ${processing ? "scanning" : ""}`} htmlFor="classroom-image">
              {imagePreviews.length ? (
                <div className="upload-selection">
                  <div className="upload-thumbs">
                    {imagePreviews.map((url, index) => (
                      <img key={url} src={url} alt={`Selected photo ${index + 1}`} />
                    ))}
                  </div>
                  <strong>
                    {images.length === 1 ? images[0].name : `${images.length} photos selected`}
                  </strong>
                  <small>
                    {(images.reduce((total, file) => total + file.size, 0) / (1024 * 1024)).toFixed(2)} MB, ready to process
                  </small>
                </div>
              ) : (
                <>
                  <div className="upload-icon"><IconUpload /></div>
                  <strong>{photoCount ? "Add another photo" : "Choose classroom photos"}</strong>
                  <small>
                    {canAddPhotos
                      ? `JPG or PNG with students’ faces visible. Select several at once (up to ${MAX_PHOTOS} per session).`
                      : confirmed
                        ? "Attendance is confirmed, so no more photos can be added."
                        : "Start a session first."}
                  </small>
                </>
              )}
              <input
                id="classroom-image"
                type="file"
                accept="image/*"
                multiple
                onChange={handleImageSelect}
                disabled={!canAddPhotos || processing}
              />
            </label>
            {photoCount > 0 && (
              <p className="muted photo-count">
                {photoCount} photo{photoCount === 1 ? "" : "s"} processed for this session.
              </p>
            )}
            <Button className="full" type="submit" disabled={!canAddPhotos || !images.length || processing}>
              {processing ? <span className="spinner" aria-hidden="true" /> : <IconUpload />}{" "}
              {processing
                ? "Detecting and matching faces…"
                : !images.length
                  ? confirmed ? "Session confirmed" : photoCount ? "Choose photos to add" : "Process classroom photos"
                  : `${photoCount ? "Add" : "Process"} ${images.length} photo${images.length === 1 ? "" : "s"}`}
            </Button>
          </form>
        </div>
      </div>

      {inReview && (
        <div className="content-card review-card">
          <div className="card-toolbar">
            <div>
              <span className="eyebrow">{confirmed ? "Saved attendance" : "Step 3: review and confirm"}</span>
              <h2 className="review-title">
                {session.name}
                {confirmed && <span className="stamp"><IconCheck /> Confirmed</span>}
              </h2>
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
            <summary>
              Annotated classroom {photoCount > 1 ? `photos (${photoCount} photos, ` : "image ("}
              {session.detections.length} faces)
            </summary>
            {photoPreviews.some(Boolean) ? (
              Array.from({ length: Math.max(photoCount, 1) }, (_, index) => (
                <div className="annotated-photo" key={index}>
                  {photoCount > 1 && <h3 className="annotated-photo-title">Photo {index + 1}</h3>}
                  <AnnotatedImage
                    src={photoPreviews[index] || null}
                    detections={session.detections.filter((detection) => (detection.photo_index || 1) === index + 1)}
                    attendance={attendance}
                  />
                </div>
              ))
            ) : (
              <AnnotatedImage src={null} detections={session.detections} attendance={attendance} />
            )}
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
                    students={session.class_section ? students.filter((student) => student.class_section === session.class_section) : students}
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
                  <th>USN</th>
                  <th>Student</th>
                  <th>Status</th>
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
                    {unresolved > 0 && ` · ${unresolved} unresolved will be saved as unverified, not absent`}
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
                {confirming ? <span className="spinner" aria-hidden="true" /> : <IconCheckCircle />} {confirming ? "Saving…" : "Confirm attendance"}
              </Button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ConfirmDeleteSessionModal({ item, onCancel, onConfirm }) {
  const [deleting, setDeleting] = useState(false);
  const confirmed = item.status === "confirmed";

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape" && !deleting) onCancel(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel, deleting]);

  const remove = async () => {
    setDeleting(true);
    try {
      await onConfirm();
    } finally {
      setDeleting(false);
    }
  };

  return createPortal(
    <div
      className="modal-backdrop"
      onClick={(e) => { if (e.target === e.currentTarget && !deleting) onCancel(); }}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="delete-session-title"
      aria-describedby="delete-session-warning"
    >
      <div className="modal">
        <div className="modal-header">
          <div className="modal-header-left">
            <div>
              <span className="eyebrow">Delete Session</span>
              <h2 id="delete-session-title" style={{ margin: 0 }}>{item.session_name}</h2>
              <small style={{ color: "var(--ink-3)" }}>
                {new Date(item.class_date).toLocaleDateString()} · {confirmed ? "Confirmed" : item.status.replace("_", " ")}
              </small>
            </div>
          </div>
          <button className="modal-close" onClick={onCancel} disabled={deleting} aria-label="Close">
            <IconX style={{ width: 18, height: 18 }} />
          </button>
        </div>
        <div className="modal-body">
          <p id="delete-session-warning" className="modal-warning">
            This permanently removes the session from the history
            {confirmed ? `, including ${item.total_registered} saved attendance record${item.total_registered === 1 ? "" : "s"}` : ""}
            {" "}and its detected face previews. This can't be undone.
          </p>
          <div className="modal-footer">
            <Button type="button" variant="secondary" onClick={onCancel} disabled={deleting} autoFocus>
              Cancel
            </Button>
            <Button type="button" variant="danger" onClick={remove} disabled={deleting}>
              <IconTrash style={{ width: 15, height: 15 }} />
              {deleting ? "Deleting…" : "Delete Session"}
            </Button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}

function SessionHistoryRow({ item, onResume, onDelete }) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
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
        <td>{item.class_section ? <span className="pill blue">{item.class_section}</span> : <span className="muted">All</span>}</td>
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
          <Button
            variant="outline-danger"
            className="sm"
            onClick={() => setConfirmingDelete(true)}
            aria-label={`Delete session ${item.session_name}`}
            title="Delete session"
          >
            <IconTrash /> Delete
          </Button>
          {confirmingDelete && (
            <ConfirmDeleteSessionModal
              item={item}
              onCancel={() => setConfirmingDelete(false)}
              onConfirm={async () => {
                if (await onDelete(item)) setConfirmingDelete(false);
              }}
            />
          )}
        </td>
      </tr>
      {open && detail && (
        <tr className="template-detail-row">
          <td colSpan="10">
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
          <h2>Student history</h2>
          <p className="muted">Confirmed sessions only.</p>
        </div>
        <select value={studentId} onChange={(e) => setStudentId(e.target.value)} aria-label="Select student">
          <option value="">Select a student…</option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>
              {student.first_name} {student.last_name} ({student.student_id}{student.class_section ? ` · ${student.class_section}` : ""})
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
              <span>Rate, excluding unverified</span>
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

  const remove = async (item) => {
    try {
      await request(`/attendance/sessions/${encodeURIComponent(item.session_id)}?actor=web-admin`, {
        method: "DELETE",
      });
    } catch (error) {
      notify(error.message, true);
      return false;
    }
    if (storageGet(ACTIVE_SESSION_KEY) === item.session_id) storageSet(ACTIVE_SESSION_KEY, null);
    setHistory((rows) => rows.filter((row) => row.session_id !== item.session_id));
    notify(`"${item.session_name}" deleted from history`);
    load();
    return true;
  };

  const shown = history.filter(inRange);

  return (
    <section className="page-section">
      <PageHeading
        title="Attendance history"
        description="Every session and its confirmed register. Exports come straight from saved records."
      />

      <div className="content-card report-filters">
        <div>
          <label>
            From
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label>
            To
            <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
        </div>
        <Button onClick={load}>
          Apply dates
        </Button>
      </div>

      <div className="stat-grid">
        <Stat icon={<IconBarChart />} tone="blue" label="Confirmed sessions" value={report.total_sessions} />
        <Stat icon={<IconCheckCircle />} tone="green" label="Present marks" value={report.total_attendance} />
        <Stat
          icon={<IconClock />}
          tone="amber"
          label="Attendance rate"
          value={report.total_possible ? `${Math.round((report.total_attendance / report.total_possible) * 100)}%` : "—"}
        />
      </div>

      <div className="content-card">
        <div className="card-toolbar">
          <div>
            <h2>Sessions ({shown.length})</h2>
            <p className="muted">Unconfirmed sessions can be resumed; confirmed ones are read-only. Deleting a session is permanent.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th><th>Subject</th><th>Class</th><th>Status</th><th>Registered</th><th>Present</th>
                <th>Absent</th><th>Unverified</th><th>Confirmed</th><th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {shown.length ? (
                shown.map((item) => <SessionHistoryRow key={item.session_id} item={item} onResume={resume} onDelete={remove} />)
              ) : (
                <tr><td colSpan="10" className="empty-state">No attendance sessions for the selected period.</td></tr>
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

  const toastTimers = useRef([]);
  const notify = (message, error = false) => {
    toastTimers.current.forEach(window.clearTimeout);
    setToast({ message, error, id: Date.now(), leaving: false });
    toastTimers.current = [
      window.setTimeout(() => setToast((t) => (t ? { ...t, leaving: true } : t)), 3400),
      window.setTimeout(() => setToast(null), 3700),
    ];
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
    window.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" });
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
            <span className="brand-mark"><BrandMark /></span>
            <strong>ClassSnap</strong>
          </a>
          <button className="menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle navigation" aria-expanded={menuOpen}>
            <IconMenu />
          </button>
        </header>
        <div className="page-transition" key={page}>{content}</div>
        {toast && (
          <div key={toast.id} className={`toast ${toast.error ? "error" : ""} ${toast.leaving ? "leaving" : ""}`} role="status">
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
