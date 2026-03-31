import io
import json
import os

import pandas as pd
import resend
import streamlit as st
from supabase import Client, create_client


# ---------------- Page config ----------------
st.set_page_config(
    page_title="HYROX Inscripciones",
    page_icon="💥",
    layout="wide",
)


# ---------------- Constants ----------------
ADMIN_TITLE = "Panel admin"
EVENT_DATE = "2026-05-16"
TOTAL_CAPACITY = 100
WHATSAPP_PHONE = "34659092227"
INSTAGRAM_URL = "https://www.instagram.com/rfhyroxtrainingclub?igsh=MTJ3Mnh5aDFzMGMxaA=="
MAPS_URL = "https://maps.app.goo.gl/GFaQENB6pXwxRyUL7?g_st=ic"
PAGO_EFECTIVO = "https://maps.app.goo.gl/qHpFpn4dkEvpHkt69"
BANK_IBAN = "ES12 1234 0000 0000 0000 0000"
PRICE_INDIVIDUAL = "20€"
PRICE_PAIR = "40€ por pareja"
ACTIVITY_INDIVIDUAL = "Hyrox Individual"
ACTIVITY_PAIR = "Hyrox Pareja"


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


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    if not to_email:
        return False

    if "resend" not in st.secrets:
        st.error("❌ No hay configuración de Resend en secrets")
        return False

    resend.api_key = st.secrets["resend"]["api_key"]
    from_email = st.secrets["resend"]["from_email"]

    try:
        resend.Emails.send(
            {
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
        )
        return True
    except Exception as exc:
        st.error(f"❌ Error enviando email: {exc}")
        return False


# ---------------- Data helpers ----------------
def get_activity_session_map(event_date_str: str) -> dict[str, dict]:
    resp = (
        sb.table("sessions")
        .select("id,activity")
        .eq("event_date", event_date_str)
        .in_("activity", [ACTIVITY_INDIVIDUAL, ACTIVITY_PAIR])
        .execute()
    )

    session_map = {row["activity"]: row for row in (resp.data or [])}
    return session_map


def fetch_bookings(event_date_str: str) -> list[dict]:
    resp = (
        sb.table("bookings")
        .select(
            """
            id,
            full_name,
            phone,
            email,
            partner_full_name,
            partner_phone,
            partner_email,
            created_at,
            paid,
            sessions!inner(event_date,activity)
            """
        )
        .eq("sessions.event_date", event_date_str)
        .execute()
    )

    rows = []
    for row in resp.data or []:
        session = row["sessions"]
        is_pair = session["activity"] == ACTIVITY_PAIR
        people_count = 2 if is_pair else 1

        rows.append(
            {
                "id": row["id"],
                "event_date": session["event_date"],
                "activity": session["activity"],
                "modality": "Pareja" if is_pair else "Individual",
                "people_count": people_count,
                "full_name": row["full_name"],
                "phone": row["phone"],
                "email": row["email"],
                "partner_full_name": row["partner_full_name"],
                "partner_phone": row["partner_phone"],
                "partner_email": row["partner_email"],
                "paid": row["paid"],
                "created_at": row["created_at"],
            }
        )

    return rows


def get_capacity_status(bookings_rows: list[dict]) -> dict[str, int]:
    used_slots = sum(int(row["people_count"]) for row in bookings_rows)
    remaining_slots = max(TOTAL_CAPACITY - used_slots, 0)
    return {
        "used_slots": used_slots,
        "remaining_slots": remaining_slots,
        "total_capacity": TOTAL_CAPACITY,
    }


def create_booking_atomic(
    session_id: int,
    full_name: str,
    phone: str,
    email: str,
    partner_full_name: str | None = None,
    partner_phone: str | None = None,
    partner_email: str | None = None,
) -> tuple[bool, str]:
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
        if isinstance(result, bytes):
            result = json.loads(result.decode())

        return result["ok"], result["message"]
    except Exception as exc:
        st.error(f"RPC error: {exc}")
        return False, "Error en el servidor al crear la inscripción."


# ---------------- UI helpers ----------------
def render_intro() -> None:
    col_logo = st.columns([1, 2, 1])[1]
    with col_logo:
        st.image("assets/logo.png", use_container_width=True)

    st.markdown(
        """
        <h1 style='text-align:center; margin-top:10px;'>
            Inscripción Competición HYROX
        </h1>
        <p style='text-align:center; opacity:0.8;'>
            Plazas limitadas. El aforo total es de 100 personas.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "Abre el menú lateral (arriba a la izquierda >>) para ver precios, ubicación y contacto."
    )

    st.markdown(
        """
        <style>
        .card {
            padding: 16px;
            border-radius: 16px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            margin-bottom: 12px;
        }
        .small {
            opacity: 0.8;
            font-size: 0.9rem;
        }
        div[data-testid="stForm"] {
            padding: 16px;
            border-radius: 16px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
        }
        .block-container {
            padding-top: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(event_date_str: str) -> None:
    with st.sidebar:
        st.markdown("## HYROX")
        st.caption("Selecciona modalidad y completa tus datos. Plazas limitadas.")
        st.divider()
        st.markdown("**Fecha del evento**")
        st.write(event_date_str)
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

            **Transferencia (IBAN):** {BANK_IBAN}

            ⚠️ *La plaza se confirma tras recibir el pago.*
            """.strip()
        )


def get_confirmation_email_html(
    event_date_str: str,
    modality: str,
) -> str:
    return f"""
    <h2>Inscripción recibida</h2>
    <p>Hemos recibido tu inscripción para el evento HYROX.</p>
    <ul>
        <li><strong>Fecha:</strong> {event_date_str}</li>
        <li><strong>Modalidad:</strong> {modality}</li>
    </ul>
    <p>Tu plaza está pendiente de pago.</p>
    <p>La inscripción quedará confirmada cuando recibamos el pago.</p>
    """


def get_paid_email_html(event_date_str: str, modality: str) -> str:
    return f"""
    <h2>Pago recibido</h2>
    <p>Tu inscripción para HYROX está confirmada.</p>
    <ul>
        <li><strong>Fecha:</strong> {event_date_str}</li>
        <li><strong>Modalidad:</strong> {modality}</li>
    </ul>
    <p>📍 Recuerda llegar con antelación.</p>
    <p>¡Nos vemos en HYROX! 💥</p>
    """


# ---------------- App ----------------
render_intro()
render_sidebar(EVENT_DATE)

session_map = get_activity_session_map(EVENT_DATE)
if ACTIVITY_INDIVIDUAL not in session_map or ACTIVITY_PAIR not in session_map:
    st.error(
        "Debes tener creadas en Supabase las actividades 'Hyrox Individual' y 'Hyrox Pareja' para esta fecha."
    )
    st.stop()

bookings = fetch_bookings(EVENT_DATE)
capacity = get_capacity_status(bookings)

left, right = st.columns(2)

with left:
    modality = st.selectbox("Modalidad", ["Individual", "Pareja"])
    is_pair = modality == "Pareja"
    people_needed = 2 if is_pair else 1
    activity = ACTIVITY_PAIR if is_pair else ACTIVITY_INDIVIDUAL

    st.markdown(f"**Modalidad seleccionada:** {modality}")

    remaining_slots = capacity["remaining_slots"]
    st.info(
        f"Plazas disponibles: {remaining_slots} de {TOTAL_CAPACITY}"
    )

    if remaining_slots <= 3 and remaining_slots > 0:
        st.warning(f"⚠️ ¡Solo quedan {remaining_slots} plazas!")

    if remaining_slots < people_needed:
        if is_pair:
            st.error("No quedan 2 plazas libres para inscribir una pareja.")
        else:
            st.error("No quedan plazas disponibles.")
        st.stop()

with right:
    with st.form("booking_form", clear_on_submit=True):
        st.warning(
            "⚠️ IMPORTANTE: La reserva solo quedará confirmada una vez recibido el pago."
        )

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

            current_bookings = fetch_bookings(EVENT_DATE)
            current_capacity = get_capacity_status(current_bookings)
            current_remaining = current_capacity["remaining_slots"]

            if current_remaining < people_needed:
                if is_pair:
                    st.error("Mientras completabas el formulario se agotaron las 2 plazas necesarias.")
                else:
                    st.error("Mientras completabas el formulario se agotaron las plazas.")
                st.stop()

            ok, msg = create_booking_atomic(
                session_map[activity]["id"],
                full_name=full_name,
                phone=phone,
                email=email,
                partner_full_name=partner_full_name if is_pair else None,
                partner_phone=partner_phone if is_pair else None,
                partner_email=partner_email if is_pair else None,
            )

            if ok:
                subject = "HYROX - Inscripción recibida (pendiente de pago)"
                html = get_confirmation_email_html(EVENT_DATE, modality)

                email_sent = send_email(email, subject, html)
                if not email_sent:
                    st.warning("Inscripción creada pero el email principal no pudo enviarse.")

                if is_pair and partner_email:
                    send_email(partner_email, subject, html)

                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


# ---------------- Admin ----------------
st.divider()
with st.expander(ADMIN_TITLE):
    pw = st.text_input("Password", type="password")

    if pw == get_admin_password():
        rows = fetch_bookings(EVENT_DATE)
        df = pd.DataFrame(rows)
        capacity = get_capacity_status(rows)

        admin_col1, admin_col2, admin_col3 = st.columns(3)
        admin_col1.metric("Aforo total", capacity["total_capacity"])
        admin_col2.metric("Plazas ocupadas", capacity["used_slots"])
        admin_col3.metric("Plazas restantes", capacity["remaining_slots"])

        if df.empty:
            st.warning("Aún no hay inscripciones.")
            st.stop()

        df["estado_pago"] = df["paid"].apply(lambda paid: "✅ Pagado" if paid else "💰 Pendiente")
        df = df.sort_values(by=["paid", "created_at"], ascending=[True, True])

        pendientes = df[df["paid"] == False].shape[0]
        pagados = df[df["paid"] == True].shape[0]

        st.info(f"💰 Pendientes: {pendientes} | ✅ Pagados: {pagados}")

        modality_summary = (
            df.groupby("modality", dropna=False)["people_count"]
            .sum()
            .reset_index()
            .rename(columns={"people_count": "personas_inscritas"})
        )
        st.markdown("### Resumen por modalidad")
        st.dataframe(modality_summary, use_container_width=True)

        busqueda = st.text_input("Buscar por nombre o email")
        if busqueda:
            df = df[
                df["full_name"].str.contains(busqueda, case=False, na=False)
                | df["email"].str.contains(busqueda, case=False, na=False)
            ]

        filtro = st.radio(
            "Filtrar inscripciones",
            ["Todas", "Pendientes", "Pagadas"],
            horizontal=True,
        )
        if filtro == "Pendientes":
            df = df[df["paid"] == False]
        elif filtro == "Pagadas":
            df = df[df["paid"] == True]

        st.dataframe(df, use_container_width=True)

        if df.empty:
            st.warning("No hay inscripciones con los filtros actuales.")
            st.stop()

        st.markdown("### Confirmar pago")
        booking_id = st.selectbox("Seleccionar inscripción", df["id"], key="pay_booking")

        if st.button("Marcar como pagado"):
            (
                sb.table("bookings")
                .update({"paid": True})
                .eq("id", booking_id)
                .execute()
            )

            resp = (
                sb.table("bookings")
                .select("email, partner_email, sessions(event_date, activity)")
                .eq("id", booking_id)
                .single()
                .execute()
            )

            row = resp.data
            session = row["sessions"]
            modality_text = "Pareja" if session["activity"] == ACTIVITY_PAIR else "Individual"
            subject = "HYROX - Inscripción confirmada"
            html = get_paid_email_html(session["event_date"], modality_text)

            send_email(row["email"], subject, html)
            if row["partner_email"]:
                send_email(row["partner_email"], subject, html)

            st.success("Pago confirmado y emails enviados.")
            st.rerun()

        st.markdown("### Eliminar inscripción")
        delete_id = st.selectbox(
            "Seleccionar inscripción a eliminar",
            df["id"],
            key="delete_booking",
        )

        if st.button("Eliminar inscripción"):
            (
                sb.table("bookings")
                .delete()
                .eq("id", delete_id)
                .execute()
            )
            st.success("Inscripción eliminada. Las plazas vuelven a estar disponibles.")
            st.rerun()

        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        st.download_button(
            "Descargar CSV",
            csv_buf.getvalue(),
            file_name=f"inscritos_{EVENT_DATE}.csv",
        )

    elif pw:
        st.error("Contraseña incorrecta")

