import os
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
    <h1 style='text-align:center;'>Inscripción Competición HYROX</h1>
    <p style='text-align:center;'>Plazas limitadas</p>
    """,
    unsafe_allow_html=True
)

st.info("📢 Una semana antes del evento se comunicará a cada participante la tanda en la que competirá.")

# ---------------- Constants ----------------
EVENT_DATE = "2026-05-16"

MAX_INDIVIDUAL = 60
MAX_PAIR = 30  # número de parejas

# ---------------- Supabase ----------------
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_role_key"]
    return create_client(url, key)

sb = get_supabase()

# ---------------- Helpers ----------------
def send_email(to_email, subject, html):
    resend.api_key = st.secrets["resend"]["api_key"]
    resend.Emails.send({
        "from": st.secrets["resend"]["from_email"],
        "to": [to_email],
        "subject": subject,
        "html": html,
    })


def get_counts():
    resp = sb.table("bookings") \
        .select("modality") \
        .eq("event_date", EVENT_DATE) \
        .execute()

    data = resp.data or []

    individual = sum(1 for r in data if r["modality"] == "Individual")
    pair = sum(1 for r in data if r["modality"] == "Pareja")

    return individual, pair


def create_booking(modality, full_name, phone, email,
                   partner_full_name=None,
                   partner_phone=None,
                   partner_email=None):

    try:
        resp = sb.rpc("create_booking_simple", {
            "p_modality": modality,
            "p_full_name": full_name,
            "p_phone": phone,
            "p_email": email,
            "p_partner_full_name": partner_full_name,
            "p_partner_phone": partner_phone,
            "p_partner_email": partner_email,
            "p_event_date": EVENT_DATE
        }).execute()

        result = resp.data[0]
        return result["ok"], result["message"]

    except Exception as e:
        return False, str(e)

# ---------------- UI ----------------
left, right = st.columns(2)

with left:

    gender = st.selectbox("Categoría", ["Masculino", "Femenino"])
    modality = st.selectbox("Modalidad", ["Individual", "Pareja"])

    st.markdown(f"**Selección:** {gender} - {modality}")

    individual_count, pair_count = get_counts()

    if modality == "Individual":
        remaining = MAX_INDIVIDUAL - individual_count
    else:
        remaining = MAX_PAIR - pair_count

    if remaining <= 0:
        st.error("❌ Plazas agotadas")
        st.stop()

    if remaining <= 5:
        st.warning(f"⚠️ Quedan solo {remaining} plazas")
    else:
        st.info(f"Plazas disponibles: {remaining}")

with right:

    with st.form("form", clear_on_submit=True):

        full_name = st.text_input("Nombre y Apellido")
        phone = st.text_input("Teléfono")
        email = st.text_input("Email")

        partner_full_name = ""
        partner_phone = ""
        partner_email = ""

        if modality == "Pareja":
            st.markdown("### Segunda persona")
            partner_full_name = st.text_input("Nombre pareja")
            partner_phone = st.text_input("Teléfono pareja")
            partner_email = st.text_input("Email pareja")

        consent = st.checkbox("Acepto el uso de datos")

        submit = st.form_submit_button("Reservar plaza")

    if submit:

        if not consent:
            st.error("Debes aceptar el uso de datos.")
            st.stop()

        if not full_name:
            st.error("Introduce tu nombre.")
            st.stop()

        if modality == "Pareja" and not partner_full_name:
            st.error("Introduce la segunda persona.")
            st.stop()

        ok, msg = create_booking(
            modality,
            full_name,
            phone,
            email,
            partner_full_name if modality == "Pareja" else None,
            partner_phone if modality == "Pareja" else None,
            partner_email if modality == "Pareja" else None,
        )

        if ok:

            html = f"""
            <h2>Inscripción HYROX</h2>

            <ul>
            <li>Fecha: {EVENT_DATE}</li>
            <li>Modalidad: {modality}</li>
            </ul>

            <p>Pendiente de pago</p>
            """

            send_email(email, "HYROX inscripción", html)

            if partner_email:
                send_email(partner_email, "HYROX inscripción", html)

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
            st.warning("Sin inscripciones")
            st.stop()

        df["estado"] = df["paid"].apply(
            lambda x: "Pagado" if x else "Pendiente"
        )

        st.dataframe(df)

        booking_id = st.selectbox("Seleccionar inscripción", df["id"])

        if st.button("Marcar como pagado"):

            sb.table("bookings") \
                .update({"paid": True}) \
                .eq("id", booking_id) \
                .execute()

            st.success("Pago confirmado")
            st.rerun()

        csv = io.StringIO()
        df.to_csv(csv, index=False)

        st.download_button(
            "Descargar CSV",
            csv.getvalue(),
            file_name="inscritos.csv"
        )

    elif pw:
        st.error("Contraseña incorrecta")