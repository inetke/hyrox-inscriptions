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
    st.image("assets/logo.png", use_container_width=True)

st.markdown(
    """
    <h1 style='text-align:center; margin-top:10px;'>
        Inscripción Competición HYROX
    </h1>
    <p style='text-align:center; opacity:0.8;'>
        Plazas limitadas. Evento sin turnos.
    </p>
    """,
    unsafe_allow_html=True
)

st.info("Una semana antes del evento se comunicará a cada participante la tanda en la que competirá.")

# ---------------- Constants ----------------
EVENT_DATE = "2026-05-16"
MAX_CAPACITY = 100

# ---------------- Supabase ----------------
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_role_key"]
    return create_client(url, key)

sb = get_supabase()

# ---------------- Email ----------------
def send_email(to_email: str, subject: str, html_content: str):
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
        st.error(f"Error email: {e}")
        return False

# ---------------- Helpers ----------------
def get_total_slots():
    resp = sb.table("bookings") \
        .select("partner_full_name") \
        .eq("event_date", EVENT_DATE) \
        .execute()

    total = 0
    for r in (resp.data or []):
        if r["partner_full_name"]:
            total += 2
        else:
            total += 1

    return total

# ---------------- Create booking ----------------
def create_booking_atomic(
    modality,
    full_name,
    phone,
    email,
    partner_full_name=None,
    partner_phone=None,
    partner_email=None,
):
    try:
        sb.rpc("create_booking_simple", {
            "p_modality": modality,
            "p_full_name": full_name,
            "p_phone": phone,
            "p_email": email,
            "p_partner_full_name": partner_full_name,
            "p_partner_phone": partner_phone,
            "p_partner_email": partner_email,
            "p_event_date": EVENT_DATE
        }).execute()

        return True, "Inscripción registrada correctamente."

    except Exception as e:
        return False, str(e)

# ---------------- Sidebar (NO TOCADO) ----------------
with st.sidebar:
    st.markdown("## HYROX")
    st.caption("Selecciona modalidad y completa tus datos.")
    st.divider()

    st.markdown("**Fecha del evento**")
    st.write(EVENT_DATE)

# ---------------- Main UI ----------------
left, right = st.columns(2)

with left:

    gender = st.selectbox("Categoría", ["Masculino", "Femenino"])
    modality = st.selectbox("Modalidad", ["Individual", "Pareja"])

    is_pair = modality == "Pareja"

    st.markdown(f"**Categoría seleccionada:** {gender} - {modality}")

    total = get_total_slots()
    remaining = MAX_CAPACITY - total

    if remaining <= 0:
        st.error("❌ Evento completo")
        st.stop()

    if remaining <= 10:
        st.warning(f"⚠️ Solo quedan {remaining} plazas")
    else:
        st.info(f"Plazas disponibles: {remaining}")

with right:

    with st.form("booking_form", clear_on_submit=True):

        full_name = st.text_input("Nombre y Apellido")
        phone = st.text_input("Teléfono")
        email = st.text_input("Email")

        partner_full_name = ""
        partner_phone = ""
        partner_email = ""

        if is_pair:
            st.markdown("### Segunda persona")
            partner_full_name = st.text_input("Nombre segunda persona")
            partner_phone = st.text_input("Teléfono segunda persona")
            partner_email = st.text_input("Email segunda persona")

        consent = st.checkbox("Acepto el uso de datos")
        submit = st.form_submit_button("Reservar plaza")

    if submit:

        if not consent:
            st.error("Debes aceptar el uso de datos.")
            st.stop()

        if not full_name.strip():
            st.error("Introduce tu nombre.")
            st.stop()

        if not phone.strip():
            st.error("Introduce tu teléfono.")
            st.stop()

        if not email.strip():
            st.error("Introduce tu email.")
            st.stop()

        if is_pair and not partner_full_name.strip():
            st.error("Introduce la segunda persona.")
            st.stop()

        # 🔥 control capacidad
        slots_needed = 2 if is_pair else 1
        if get_total_slots() + slots_needed > MAX_CAPACITY:
            st.error("No quedan suficientes plazas.")
            st.stop()

        ok, msg = create_booking_atomic(
            modality,
            full_name,
            phone,
            email,
            partner_full_name if is_pair else None,
            partner_phone if is_pair else None,
            partner_email if is_pair else None,
        )

        if ok:

            subject = "HYROX - Inscripción recibida"

            html = f"""
            <h2>Inscripción recibida</h2>

            <ul>
            <li>Fecha: {EVENT_DATE}</li>
            <li>Modalidad: {modality}</li>
            </ul>

            <p>Tu plaza está pendiente de pago.</p>

            <p>Una semana antes del evento recibirás tu tanda de competición.</p>
            """

            send_email(email, subject, html)

            if is_pair and partner_email:
                send_email(partner_email, subject, html)

            st.success(msg)
            st.rerun()

        else:
            st.error(msg)

# ---------------- Admin ----------------
st.divider()

with st.expander("Panel admin"):

    pw = st.text_input("Password", type="password")

    if pw == st.secrets["admin"]["password"]:

        resp = sb.table("bookings") \
            .select("*") \
            .eq("event_date", EVENT_DATE) \
            .execute()

        df = pd.DataFrame(resp.data)

        if df.empty:
            st.warning("Aún no hay inscripciones.")
            st.stop()

        df["estado_pago"] = df["paid"].apply(
            lambda x: "✅ Pagado" if x else "💰 Pendiente"
        )

        st.dataframe(df, use_container_width=True)

        booking_id = st.selectbox("Seleccionar inscripción", df["id"])

        if st.button("Marcar como pagado"):

            sb.table("bookings") \
                .update({"paid": True}) \
                .eq("id", booking_id) \
                .execute()

            st.success("Pago confirmado.")
            st.rerun()

        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)

        st.download_button(
            "Descargar CSV",
            csv_buf.getvalue(),
            file_name=f"inscritos_{EVENT_DATE}.csv"
        )

    elif pw:
        st.error("Contraseña incorrecta")