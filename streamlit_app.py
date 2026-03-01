import os
import re
import io
import pandas as pd
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="HYROX Inscripciones", page_icon="💥", layout="wide")

st.markdown("""
<style>
/* Cards */
.card {
  padding: 16px;
  border-radius: 16px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  margin-bottom: 12px;
}

/* Smaller labels */
.small { opacity: 0.8; font-size: 0.9rem; }

/* Make form look tighter */
div[data-testid="stForm"] {
  padding: 16px;
  border-radius: 16px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("assets/logo.png", width=180)
    st.markdown("### Competición HYROX")
    st.caption("Selecciona categoría y turno. Plazas limitadas.")

st.markdown("# Inscripción Competición HYROX")
st.caption("Las plazas se asignan por orden de inscripción. Si un turno se llena, desaparecerá.")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("## 1) Elige categoría")
    activity = st.selectbox("Categoría", options=activities)

    st.markdown("## 2) Turnos disponibles")
    # aquí tu radio / listado de horarios

with col2:
    st.markdown("## 3) Datos de inscripción")
    # aquí tu st.form(...)

APP_TITLE = "Inscripción Competición HYROX"
ADMIN_TITLE = "Panel admin"
PHONE_REGEX = r"^[0-9+() \-]{7,20}$"

def get_admin_password() -> str:
    if "admin" in st.secrets and "password" in st.secrets["admin"]:
        return st.secrets["admin"]["password"]
    return os.environ.get("ADMIN_PASSWORD", "")

def get_supabase() -> Client:
    if "supabase" not in st.secrets:
        st.error("Faltan secrets de Supabase.")
        st.stop()
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_role_key"]
    return create_client(url, key)

sb = get_supabase()

# ---- Data helpers (REST) ----
def fetch_event_dates():
    resp = sb.table("sessions").select("event_date").execute()
    dates = sorted({row["event_date"] for row in resp.data})
    return dates

def fetch_sessions(event_date):
    # Trae sesiones del día
    resp_s = sb.table("sessions").select("id,activity,start_time,end_time,capacity").eq("event_date", event_date).execute()
    sessions = resp_s.data

    # Trae bookings del día y cuenta por session_id
    resp_b = (
        sb.table("bookings")
        .select("session_id, sessions!inner(event_date)")
        .eq("sessions.event_date", event_date)
        .execute()
    )
    counts = {}
    for row in resp_b.data:
        sid = row["session_id"]
        counts[sid] = counts.get(sid, 0) + 1

    # Calcula remaining
    for s in sessions:
        booked = counts.get(s["id"], 0)
        s["booked"] = booked
        s["remaining"] = int(s["capacity"]) - int(booked)

    # Orden
    sessions.sort(key=lambda x: (x["activity"], x["start_time"]))
    return sessions

def create_booking_atomic(session_id, full_name, phone, email, partner_full_name=None, partner_phone=None, partner_email=None):
    payload = {
        "p_session_id": int(session_id),
        "p_full_name": full_name,
        "p_phone": phone,
        "p_email": email,
        "p_partner_full_name": partner_full_name,
        "p_partner_phone": partner_phone,
        "p_partner_email": partner_email,
    }
    resp = sb.rpc("book_session_v2", payload).execute()
    if not resp.data:
        return False, "Error inesperado en la reserva."
    return bool(resp.data["ok"]), resp.data["message"]

def fetch_bookings(event_date):
    resp = (
        sb.table("bookings")
        .select("full_name,phone,email,created_at, sessions!inner(event_date,activity,start_time,end_time)")
        .eq("sessions.event_date", event_date)
        .execute()
    )
    rows = []
    for r in resp.data:
        s = r["sessions"]
        rows.append({
            "event_date": s["event_date"],
            "activity": s["activity"],
            "start_time": s["start_time"],
            "end_time": s["end_time"],
            "full_name": r["full_name"],
            "phone": r["phone"],
            "email": r["email"],
            "created_at": r["created_at"],
        })
    rows.sort(key=lambda x: (x["activity"], x["start_time"], x["created_at"]))
    return rows

# ---- UI ----
st.title(APP_TITLE)

dates = fetch_event_dates()
if not dates:
    st.warning("No hay sesiones cargadas en la base de datos todavía.")
    st.stop()

EVENT_DATE = "2026-04-10"

event_date = EVENT_DATE
st.write(f"Fecha del evento: **{event_date}**")

sessions = fetch_sessions(event_date)
activities = sorted(list({s["activity"] for s in sessions}))
activity = st.selectbox("Categoría", options=activities)

is_pair = (activity.strip().lower() == "hyrox pareja")

filtered = [s for s in sessions if s["activity"] == activity]

st.subheader("Turnos disponibles")
options = []
option_map = {}
for s in filtered:
    label = f"{str(s['start_time'])[:5]} - {str(s['end_time'])[:5]}  ·  Plazas: {s['remaining']}/{s['capacity']}"
    options.append(label)
    option_map[label] = s

selected_label = st.radio("Elige tu franja", options=options)
selected_session = option_map[selected_label]

st.divider()
st.subheader("Datos de inscripción")

with st.form("booking_form", clear_on_submit=True):
    # Persona 1
    full_name = st.text_input("Nombre y apellidos", max_chars=80, key="p1_name")
    phone = st.text_input("Teléfono móvil", max_chars=20, help="Ej: +34 600 123 456", key="p1_phone")
    email = st.text_input("Correo electrónico", max_chars=120, key="p1_email")

    # Persona 2 (solo si es pareja)
    partner_full_name = ""
    partner_phone = ""
    partner_email = ""

    if is_pair:
        st.markdown("### Datos de la segunda persona")
        partner_full_name = st.text_input("Nombre y apellidos (segunda persona)", max_chars=80, key="p2_name")
        partner_phone = st.text_input("Teléfono móvil (segunda persona)", max_chars=20, help="Ej: +34 600 123 456", key="p2_phone")
        partner_email = st.text_input("Correo electrónico (segunda persona)", max_chars=120, key="p2_email")

    consent = st.checkbox(
        "Autorizo el uso de mis datos únicamente para gestionar esta inscripción y comunicaciones relacionadas con la competición.",
        key="consent",
    )

    submit = st.form_submit_button("Confirmar inscripción ✅", use_container_width=True)

if submit:
    if selected_session["remaining"] <= 0:
        st.error("Lo sentimos: este turno se acaba de llenar. Elige otro horario.")
        st.stop()

    if not full_name.strip():
        st.error("Falta nombre y apellidos.")
        st.stop()

    if not re.match(PHONE_REGEX, phone.strip()):
        st.error("Teléfono móvil inválido. Revisa el formato.")
        st.stop()

    if "@" not in email or "." not in email:
        st.error("Correo electrónico inválido.")
        st.stop()

    if not consent:
        st.error("Necesitas aceptar el uso de datos para inscribirte.")
        st.stop()

    if is_pair:
        if not partner_full_name.strip():
            st.error("Falta el nombre y apellidos de la segunda persona.")
            st.stop()

        if not re.match(PHONE_REGEX, partner_phone.strip()):
            st.error("Teléfono móvil (segunda persona) inválido. Revisa el formato.")
            st.stop()

        if "@" not in partner_email or "." not in partner_email:
            st.error("Correo electrónico (segunda persona) inválido.")
            st.stop()

    ok, msg = create_booking_atomic(selected_session["id"],
                                    full_name.strip(),
                                    phone.strip(),
                                    email.strip(),
                                    partner_full_name.strip() if is_pair else None,
                                    partner_phone.strip() if is_pair else None,
                                    partner_email.strip() if is_pair else None,)

st.divider()

with st.expander(ADMIN_TITLE):
    admin_pw = st.text_input("Contraseña admin", type="password")

    if admin_pw and admin_pw == get_admin_password():
        st.success("Acceso concedido.")

        rows = fetch_bookings(event_date)
        df = pd.DataFrame(rows)

        if df.empty:
            st.write("Aún no hay inscripciones para esta fecha.")
        else:
            st.dataframe(df, use_container_width=True)

            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)

            st.download_button(
                "Descargar inscritos (CSV)",
                data=csv_buf.getvalue().encode("utf-8"),
                file_name=f"inscritos_{event_date}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    elif admin_pw:
        st.error("Contraseña incorrecta.")