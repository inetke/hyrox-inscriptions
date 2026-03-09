import os
import re
import io
import resend
import pandas as pd
import streamlit as st
from supabase import create_client, Client


# ---------------- Page config ----------------
st.set_page_config(page_title="HYROX Inscripciones", page_icon="💥", layout="wide")

col_logo = st.columns([1,2,1])[1]

with col_logo:
    st.image(
        "assets/logo.png",
        use_container_width=True
    )

st.markdown(
    """
    <h1 style='text-align:center; margin-top:10px;'>
        Inscripción Competición HYROX
    </h1>
    <p style='text-align:center; opacity:0.8;'>
        Plazas limitadas. Si un turno se llena, desaparecerá.
    </p>
    """,
    unsafe_allow_html=True
)

# CSS (aplica a toda la app)
st.markdown(
    """
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

/* Reduce top padding a bit */
.block-container { padding-top: 1.5rem; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- Constants ----------------
ADMIN_TITLE = "Panel admin"
PHONE_REGEX = r"^[0-9+() \-]{7,20}$"

# Evento fijo (cambia aquí la fecha)
EVENT_DATE = "2026-04-25"
event_date = EVENT_DATE
WHATSAPP_PHONE = "34600123456"  # sin + ni espacios (España: 34 + número)
INSTAGRAM_URL = "https://www.instagram.com/rfhyroxtrainingclub?igsh=MTJ3Mnh5aDFzMGMxaA=="
MAPS_URL = "https://maps.app.goo.gl/GFaQENB6pXwxRyUL7?g_st=ic"
BIZUM_PHONE = "+34 600 123 456"
BANK_IBAN = "ES12 1234 0000 0000 0000 0000"
PRICE_INDIVIDUAL = "20€"
PRICE_PAIR = "40€ por pareja"


# ---------------- Secrets / Clients ----------------
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

def send_email(to_email: str, subject: str, html_content: str):
    if "resend" not in st.secrets:
        return False

    resend.api_key = st.secrets["resend"]["api_key"]
    from_email = st.secrets["resend"]["from_email"]

    try:
        resend.Emails.send({
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        })
        return True
    except Exception as e:
        print("Error enviando email:", e)
        return False


# ---------------- Data helpers (REST) ----------------
def fetch_sessions(event_date_str):

    resp_s = (
        sb.table("sessions")
        .select("id,activity,start_time,end_time,capacity")
        .eq("event_date", event_date_str)
        .execute()
    )

    sessions = resp_s.data or []

    resp_b = (
        sb.table("bookings")
        .select("session_id, sessions!inner(event_date)")
        .eq("sessions.event_date", event_date_str)
        .execute()
    )

    counts = {}

    for row in (resp_b.data or []):
        sid = row["session_id"]
        counts[sid] = counts.get(sid, 0) + 1

    for s in sessions:
        booked = counts.get(s["id"], 0)
        s["booked"] = booked
        s["remaining"] = int(s["capacity"]) - int(booked)

    sessions.sort(key=lambda x: (x["activity"], x["start_time"]))

    return sessions

    if email_already_registered(selected_session["id"], email):

        st.error("Este email ya está inscrito en este turno.")
        st.stop()

# ---------------- Create booking ----------------
def create_booking_atomic(
    session_id,
    full_name,
    phone,
    email,
    partner_full_name=None,
    partner_phone=None,
    partner_email=None,
):

    payload = {
        "p_session_id": int(session_id),
        "p_full_name": full_name,
        "p_phone": phone,
        "p_email": email,
        "p_partner_full_name": partner_full_name,
        "p_partner_phone": partner_phone,
        "p_partner_email": partner_email,
    }

    try:
        resp = sb.rpc("book_session_v2", payload).execute()

        if not resp.data:
            return False, "Error inesperado."

        result = resp.data[0]

        return bool(result["ok"]), result["message"]

    except Exception as e:
        print("Error RPC:", e)
        return False, "Error en el servidor al crear la reserva."


def fetch_bookings(event_date_str):

    resp = (
        sb.table("bookings")
        .select(
            "id,full_name,phone,email,partner_full_name,partner_phone,partner_email,created_at,paid,sessions!inner(event_date,activity,start_time,end_time)"
        )
        .eq("sessions.event_date", event_date_str)
        .execute()
    )

    rows = []

    for r in (resp.data or []):

        s = r["sessions"]

        rows.append({
            "id": r["id"],
            "event_date": s["event_date"],
            "activity": s["activity"],
            "start_time": s["start_time"],
            "end_time": s["end_time"],
            "full_name": r["full_name"],
            "email": r["email"],
            "partner_email": r["partner_email"],
            "paid": r["paid"],
            "created_at": r["created_at"]
        })

    return rows


# ---------------- Load sessions / activities ----------------
sessions = fetch_sessions(event_date)
if not sessions:
    st.warning("No hay turnos cargados para esta fecha.")
    st.stop()

activities = sorted({s["activity"] for s in sessions})

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("## HYROX")
    st.caption("Selecciona categoría y turno. Plazas limitadas.")
    st.divider()

    st.markdown("**Fecha del evento**")
    st.write(event_date)

    st.divider()
    st.markdown("**📍 Ubicación**")
    st.link_button("Cómo llegar / Google Maps", MAPS_URL, use_container_width=True)

    st.divider()
    st.markdown("**💬 Contacto**")

    # WhatsApp directo (abre chat)
    wa_text = "Hola! Quiero información sobre la inscripción HYROX."
    whatsapp_url = f"https://wa.me/{WHATSAPP_PHONE}?text={wa_text.replace(' ', '%20')}"
    st.link_button("WhatsApp", whatsapp_url, use_container_width=True)

    # Instagram
    st.link_button("Instagram", INSTAGRAM_URL, use_container_width=True)

    st.divider()
    st.markdown("**💶 Precio y pago**")
    st.markdown(
        f"""
- **Individual:** {PRICE_INDIVIDUAL}  
- **Pareja:** {PRICE_PAIR}  

**Bizum:** {BIZUM_PHONE}  
**Transferencia (IBAN):** `{BANK_IBAN}`  

⚠️ *La plaza se confirma tras recibir el pago.*
""".strip()
    )

# ---------------- Main UI ----------------
left, right = st.columns(2)

with left:

    activity = st.selectbox("Categoría", activities)

    is_pair = activity == "Hyrox Pareja"

    filtered = [s for s in sessions
    if s["activity"] == activity and s["remaining"] > 0]

    if not filtered:
        st.warning("Todas las plazas de esta categoría están completas.")
        st.stop()

    option_map = {}

    options = []

    for s in filtered:

        label = f"{s['start_time'][:5]}-{s['end_time'][:5]} · {s['remaining']}/{s['capacity']}"

        options.append(label)

        option_map[label] = s

    selected_label = st.radio("Turno", options)

    selected_session = option_map[selected_label]

    remaining = selected_session["remaining"]

    if remaining <= 3:
        st.warning(f"⚠️ ¡Solo quedan {remaining} plazas!")
    else:
        st.info(f"Plazas disponibles: {remaining}")


with right:

    with st.form("booking_form", clear_on_submit=True):

        full_name = st.text_input("Nombre")
        phone = st.text_input("Teléfono")
        email = st.text_input("Email")

        partner_full_name = ""
        partner_phone = ""
        partner_email = ""

        if is_pair:

            st.markdown("### Segunda persona")

            partner_full_name = st.text_input("Nombre 2")
            partner_phone = st.text_input("Teléfono 2")
            partner_email = st.text_input("Email 2")

        consent = st.checkbox("Acepto el uso de datos")

        submit = st.form_submit_button("Reservar plaza")

    if submit:

        if not full_name.strip():
            st.error("Introduce tu nombre.")
            st.stop()

        if not phone.strip():
            st.error("Introduce tu teléfono.")
            st.stop()

        if not email.strip():
            st.error("Introduce tu email.")
            st.stop()

        if is_pair:
            if not partner_full_name.strip():
                st.error("Introduce el nombre de la segunda persona.")
                st.stop()

        ok, msg = create_booking_atomic(
            selected_session["id"],
            full_name,
            phone,
            email,
            partner_full_name if is_pair else None,
            partner_phone if is_pair else None,
            partner_email if is_pair else None,
        )

        if ok:

            subject = "HYROX - Inscripción recibida (pendiente de pago)"

            html = f"""
            <h2>Inscripción recibida</h2>

            <p>Evento HYROX</p>

            <ul>
            <li>Fecha: {event_date}</li>
            <li>Categoría: {activity}</li>
            <li>Horario: {selected_session['start_time'][:5]}-{selected_session['end_time'][:5]}</li>
            </ul>

            <p>Tu plaza está pendiente de pago.</p>

            <p>Bizum: {BIZUM_PHONE}</p>
            """

            email_sent = send_email(email, subject, html)

            if not email_sent:
                st.warning("Reserva creada pero el email no pudo enviarse.")

            if is_pair:
                send_email(partner_email, subject, html)

            st.success(msg)

            st.rerun()

        else:

            st.error(msg)



# ---------------- Admin ----------------
st.divider()

with st.expander("Panel admin"):

    pw = st.text_input("Password", type="password")

    if pw == get_admin_password():

        rows = fetch_bookings(event_date)
        df = pd.DataFrame(rows)

        st.markdown("### Plazas por turno")

        sessions_df = pd.DataFrame(sessions)

        sessions_df["ocupadas"] = sessions_df["booked"]
        sessions_df["restantes"] = sessions_df["remaining"]

        st.dataframe(
            sessions_df[["activity","start_time","end_time","ocupadas","restantes"]],
            use_container_width=True
        )

        if df.empty:
            st.warning("Aún no hay inscripciones.")
            st.stop()

        # Crear columna visual de estado
        df["estado_pago"] = df["paid"].apply(
            lambda x: "✅ Pagado" if x else "💰 Pendiente"
        )

        # Ordenar pendientes arriba
        df = df.sort_values(by="paid")

        # Contadores
        pendientes = df[df["paid"] == False].shape[0]
        pagados = df[df["paid"] == True].shape[0]

        st.info(f"💰 Pendientes: {pendientes} | ✅ Pagados: {pagados}")

        busqueda = st.text_input("Buscar por nombre o email")

        if busqueda:
            df = df[
                df["full_name"].str.contains(busqueda, case=False, na=False) |
                df["email"].str.contains(busqueda, case=False, na=False)
            ]

        filtro = st.radio(
            "Filtrar inscripciones",
            ["Todas", "Pendientes", "Pagadas"],
            horizontal=True
        )

        if filtro == "Pendientes":
            df = df[df["paid"] == False]

        elif filtro == "Pagadas":
            df = df[df["paid"] == True]

        st.dataframe(df, use_container_width=True)

        st.markdown("### Confirmar pago")

        booking_id = st.selectbox(
            "Seleccionar inscripción",
            df["id"]
        )

        if st.button("Marcar como pagado"):

            sb.table("bookings") \
                .update({"paid": True}) \
                .eq("id", booking_id) \
                .execute()

            row = df[df["id"] == booking_id].iloc[0]

            subject = "HYROX - Inscripción confirmada"

            html = f"""
            <h2>Pago recibido</h2>

            <p>Tu inscripción está confirmada.</p>

            <ul>
            <li><strong>Fecha:</strong> {row['event_date']}</li>
            <li><strong>Categoría:</strong> {row['activity']}</li>
            <li><strong>Horario:</strong> {row['start_time'][:5]}-{row['end_time'][:5]}</li>
            </ul>

            <p>¡Nos vemos en HYROX! 💥</p>
            """

            send_email(row["email"], subject, html)

            if row["partner_email"]:
                send_email(row["partner_email"], subject, html)

            st.success("Pago confirmado y emails enviados.")
            st.rerun()

        st.markdown("### Eliminar inscripción")

        delete_id = st.selectbox(
            "Seleccionar inscripción a eliminar",
            df["id"],
            key="delete_booking"
        )

        if st.button("Eliminar inscripción"):

            sb.table("bookings") \
                .delete() \
                .eq("id", delete_id) \
                .execute()

            st.success("Inscripción eliminada. La plaza vuelve a estar disponible.")
            st.rerun()

        # Descargar CSV
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)

        st.download_button(
            "Descargar CSV",
            csv_buf.getvalue(),
            file_name=f"inscritos_{event_date}.csv"
        )

    elif pw:
        st.error("Contraseña incorrecta")