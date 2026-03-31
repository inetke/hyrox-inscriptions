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
        Plazas limitadas.
    </p>
    """,
    unsafe_allow_html=True
)

st.info("Una semana antes del evento se comunicará a cada participante la tanda en la que competirá.")

st.info("Abre el menú lateral (arriba a la izquierda >>) para ver precios, ubicación y contacto.")

# ---------------- CSS ----------------
st.markdown(
    """
<style>
.card { padding:16px; border-radius:16px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.08); margin-bottom:12px;}
.small { opacity:0.8; font-size:0.9rem; }
div[data-testid="stForm"] { padding:16px; border-radius:16px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);}
.block-container { padding-top:1.5rem; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- Constants ----------------
EVENT_DATE = "2026-05-16"
MAX_CAPACITY = 100

WHATSAPP_PHONE = "34659092227"
INSTAGRAM_URL = "https://www.instagram.com/rfhyroxtrainingclub?igsh=MTJ3Mnh5aDFzMGMxaA=="
MAPS_URL = "https://maps.app.goo.gl/GFaQENB6pXwxRyUL7?g_st=ic"
PAGO_EFECTIVO = "https://maps.app.goo.gl/qHpFpn4dkEvpHkt69"
BANK_IBAN = "ES12 1234 0000 0000 0000 0000"
PRICE_INDIVIDUAL = "20€"
PRICE_PAIR = "40€ por pareja"

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
        st.error(f"Error enviando email: {e}")
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

        return True, "Inscripción creada correctamente."

    except Exception as e:
        return False, str(e)

# ---------------- Sidebar (INTACTO) ----------------
with st.sidebar:
    st.markdown("## HYROX")
    st.caption("Selecciona categoría y modalidad. Plazas limitadas.")
    st.divider()

    st.markdown("**Fecha del evento**")
    st.write(EVENT_DATE)

    st.divider()
    st.markdown("**📍 Ubicación**")
    st.link_button("Cómo llegar / Google Maps", MAPS_URL, use_container_width=True)

    st.divider()
    st.markdown("**💬 Contacto**")

    wa_text = "Hola! Quiero información sobre la inscripción HYROX."
    whatsapp_url = f"https://wa.me/{WHATSAPP_PHONE}?text={wa_text.replace(' ', '%20')}"
    st.link_button("WhatsApp", whatsapp_url, use_container_width=True)

    st.link_button("Instagram", INSTAGRAM_URL, use_container_width=True)

    st.divider()
    st.markdown("**💶 Precio y pago**")
    st.markdown(
        f"""
- **Individual:** {PRICE_INDIVIDUAL}  
- **Pareja:** {PRICE_PAIR}  

💵 **Pago en efectivo en el centro**  

📍 [Ir a la ubicación]({PAGO_EFECTIVO})

**Transferencia (IBAN):** `{BANK_IBAN}`  

⚠️ *La plaza se confirma tras recibir el pago.*
"""
    )

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
        st.warning(f"⚠️ ¡Solo quedan {remaining} plazas!")
    else:
        st.info(f"Plazas disponibles: {remaining}")

with right:

    with st.form("booking_form", clear_on_submit=True):

        st.warning("⚠️ IMPORTANTE: La reserva solo quedará confirmada una vez recibido el pago.")

        full_name = st.text_input("Nombre y Apellido")
        phone = st.text_input("Teléfono")
        email = st.text_input("Email")

        partner_full_name = ""
        partner_phone = ""
        partner_email = ""

        if is_pair:
            st.markdown("### Segunda persona")
            partner_full_name = st.text_input("Nombre y Apellido (segunda persona)")
            partner_phone = st.text_input("Teléfono (segunda persona)")
            partner_email = st.text_input("Email (segunda persona)")

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
            st.error("Introduce el nombre de la segunda persona.")
            st.stop()

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

            <p>Una semana antes del evento se comunicará tu tanda.</p>
            """

            send_email(email, subject, html)

            if is_pair and partner_email:
                send_email(partner_email, subject, html)

            st.success(msg)
            st.rerun()

        else:
            st.error(msg)

# ---------------- Admin (CASI INTACTO) ----------------
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