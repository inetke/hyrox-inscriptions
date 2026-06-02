import os
import re
import io
import resend
import pandas as pd
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta


# ---------------- Page config ----------------
st.set_page_config(page_title="HYROX Inscripciones", page_icon="💥", layout="wide")

col_logo = st.columns([1,2,1])[1]

with col_logo:
    st.image(
        "assets/logo_hybrid.png",
        use_container_width=True
    )

#st.markdown(
    #"""
    #<h1 style='text-align:center; margin-top:10px;'>
    #    Inscripción EVENTO HYROX
    #</h1>
    #<p style='text-align:center; opacity:0.8;'>
    #    OUR SPORT IS HYROX. Plazas limitadas.
    #</p>
    #""",
    #unsafe_allow_html=True
#)

st.markdown(
    """
    <h2 style='text-align:center; margin-top:10px;'>
        HYBRID SUMMER GAMES 🥥
    </h1>
    <p style='text-align:center; opacity:0.8;'>
        Plazas limitadas 
    </p>
    """,
    unsafe_allow_html=True
)

#st.info("Abre el menú lateral (arriba a la izquierda >>) para ver precios, ubicación y contacto.")

# CSS (aplica a toda la app)
st.markdown(
    """
<style>
/* FONDO GENERAL DE LA APP */
[data-testid="stAppViewContainer"] {
  background-color: #3d2200;
}
[data-testid="stHeader"] {
  background-color: #3d2200;
}

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

/* Input de contraseña y todos los inputs */
input[type="password"],
input[type="text"],
div[data-baseweb="input"] {
  background-color: rgba(90, 75, 20, 0.5) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  color: white !important;
  border-radius: 8px !important;
}

/* Contenedor del input */
div[data-baseweb="base-input"] {
  background-color: rgba(255,255,255,0.12) !important;
  border-radius: 8px !important;
}

/* SELECTBOX (Categoría, Modalidad) */
div[data-baseweb="select"] > div {
  background-color: rgba(90, 75, 20, 0.5) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 8px !important;
  color: white !important;
}

/* Texto dentro del select */
div[data-baseweb="select"] span {
  color: white !important;
}

/* Dropdown (cuando abres el select) */
ul {
  background-color: #3d3000 !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
}

/* Opciones dentro del dropdown */
li {
  color: white !important;
}

/* Hover de opciones */
li:hover {
  background-color: rgba(255,255,255,0.08) !important;
}

/* BOTÓN DE RESERVAR PLAZA */
div.stButton > button,
div[data-testid="stForm"] button {
    background-color: #e8871e !important; /* Naranja/Dorado coco */
    color: white !important;
    border-radius: 12px !important;
    border: none !important;
    padding: 0.5rem 2rem !important;
    width: 100% !important; /* Lo hace ancho completo para que luzca más en el formulario */
    transition: all 0.3s ease;
    font-weight: bold !important;
}

/* EFECTO AL PASAR EL RATÓN */
div.stButton > button:hover,
div[data-testid="stForm"] button:hover {
    background-color: #cf7416 !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    transform: scale(1.02);
}

/* CHECKBOX - forzar color del tick */
input[type="checkbox"] {
    accent-color: #a85e10 !important;
    width: 18px !important;
    height: 18px !important;
}

/* El tick del checkbox */
div[data-testid="stCheckbox"] div[role="checkbox"] {
    background-color: #a85e10 !important;
    border-color: #a85e10 !important;
}

/* EXPANDER / PANEL ADMIN - fondo azul */
details {
    background-color: rgba(90, 75, 20, 0.5) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
}

details summary {
    background-color: rgba(90, 75, 20, 0.5) !important;
    color: white !important;
    border-radius: 12px !important;
}

/* Por si el expander usa otro selector */
div[data-testid="stExpander"] > details {
    background-color: rgba(90, 75, 20, 0.5) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
}

div[data-testid="stExpander"] > details > summary {
    background-color: rgba(90, 75, 20, 0.5) !important;
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
EVENT_DATE = "2026-07-11"
event_date = EVENT_DATE
REGISTRATION_OPEN_DATE = datetime(2026, 6, 2, 19, 0)
WHATSAPP_PHONE = "34659092227"  # sin + ni espacios (España: 34 + número)
INSTAGRAM_URL = "https://www.instagram.com/rfhyroxtrainingclub?igsh=MTJ3Mnh5aDFzMGMxaA=="
MAPS_URL = "https://maps.app.goo.gl/GFaQENB6pXwxRyUL7?g_st=ic"
PAGO_EFECTIVO = "https://maps.app.goo.gl/qHpFpn4dkEvpHkt69"
PAGO_EFECTIVO_H = "https://maps.app.goo.gl/GFaQENB6pXwxRyUL7?g_st=ic"
BANK_IBAN = "ES27 2100 6749 2702 0041 0384"
#PAGO_BIZUM = "+34 659 09 22 27"
ENTRADA_GENERAL = "25€ individual · 50€ dobles · 75€ tríos"
ENTRADA_USUARIOS = "20€ individual · 40€ dobles · 60€ tríos"

event_datetime = datetime.strptime("2026-07-11 08:00", "%Y-%m-%d %H:%M")
now = datetime.now()

time_left = event_datetime - now

if time_left.total_seconds() > 0:
    days = time_left.days
    hours = time_left.seconds // 3600
    minutes = (time_left.seconds % 3600) // 60

    st.markdown(
        f"""
        <div style="text-align:center; padding:12px; border-radius:12px; border:1px solid rgba(255,255,255,0.1); margin-bottom:20px;">
            ⏳ <strong>Faltan {days} días, {hours} horas y {minutes} minutos para el evento</strong>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.success("💥 ¡Hoy es el día del evento!")

        
# ---------------- Secrets / Clients ----------------
def get_admin_password() -> str:
    if "admin" in st.secrets and "password" in st.secrets["admin"]:
        return st.secrets["admin"]["password"]
    return os.environ.get("ADMIN_PASSWORD", "")

def get_preview_password() -> str:
    if "preview" in st.secrets and "password" in st.secrets["preview"]:
        return st.secrets["preview"]["password"]
    return os.environ.get("PREVIEW_PASSWORD", "")

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
        st.error("❌ No hay configuración de Resend en secrets")
        return False

    resend.api_key = st.secrets["resend"]["api_key"]
    from_email = st.secrets["resend"]["from_email"]

    try:
        st.write("📤 Enviando email a:", to_email)

        response = resend.Emails.send({
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        })

        st.write("✅ Respuesta Resend:", response)

        return True

    except Exception as e:
        st.error(f"❌ Error enviando email: {e}")
        return False

today = datetime.now()

if today < REGISTRATION_OPEN_DATE:

    st.markdown("""
    #### Evento: 11 de julio

    Las inscripciones abrirán oficialmente:

    #### 🌴 2 de junio

    Estamos preparando una experiencia increíble 🔥
    """)

    st.divider()

    st.caption("Private access")

    preview_password = st.text_input(
        "Password",
        type="password",
        key="preview_password"
    )

    if preview_password != get_preview_password():
        st.stop()

# ---------------- Data helpers (REST) ----------------
def fetch_sessions(event_date_str):

    resp_s = (
        sb.table("sessions")
        .select("id,activity,gender,modality,start_time,end_time,capacity")
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

# ---------------- Create time slots ----------------

def generate_mixed_time_slots(start_time="08:00", total_slots=90):

    slots = []

    current = datetime.strptime(start_time, "%H:%M")

    for i in range(total_slots):
        slots.append(current.strftime("%H:%M"))
        
        current += timedelta(minutes=10)
        
    return slots

# ---------------- Create booking ----------------
import json

def create_booking_atomic(
    full_name,
    phone,
    email,
    modality,
    partner_full_name=None,
    partner_phone=None,
    partner_email=None,
    third_full_name=None,
    third_phone=None,
    third_email=None,
    alias=None,
    force=False
):
    payload = {
        "p_event_date": EVENT_DATE,
        "p_full_name": full_name,
        "p_phone": phone,
        "p_email": email,
        "p_modality": modality,
        "p_partner_full_name": partner_full_name,
        "p_partner_phone": partner_phone,
        "p_partner_email": partner_email,
        "p_third_full_name": third_full_name,
        "p_third_phone": third_phone,
        "p_third_email": third_email,
        "p_alias": alias,
        "p_force": force,
    }

    try:
        resp = sb.rpc("book_hyrox_event", payload).execute()

        if not resp.data:
            return False, "Error inesperado."

        result = resp.data[0]
        return result["ok"], result["message"]

    except Exception as e:
        st.error(f"RPC error: {e}")
        return False, "Error en el servidor."

def fetch_bookings(event_date_str):
    resp = (
        sb.table("bookings")
        .select(
            "id,event_date,full_name,alias,phone,email,partner_full_name,partner_phone,partner_email,third_full_name,third_phone,third_email,created_at,paid,modality,start_time"
        )
        .eq("event_date", event_date_str)
        .execute()
    )

    rows = []

    for r in (resp.data or []):
        rows.append({
            "id": r["id"],
            "event_date": r["event_date"],
            "full_name": r["full_name"],
            "alias": r["alias"],
            "phone": r["phone"],
            "email": r["email"],
            "partner_full_name": r["partner_full_name"],
            "partner_phone": r["partner_phone"],
            "partner_email": r["partner_email"],
            "third_full_name": r["third_full_name"],
            "third_phone": r["third_phone"],
            "third_email": r["third_email"],
            "modality": r["modality"],
            "paid": r["paid"],
            "created_at": r["created_at"],
            "start_time": r["start_time"]
        })

    return rows

def fetch_total_remaining():
    resp = (
        sb.table("bookings")
        .select("modality,partner_full_name,third_full_name")
        .eq("event_date", EVENT_DATE)
        .execute()
    )

    occupied = 0

    for row in (resp.data or []):
        if row.get("modality") == "Tríos":
            occupied += 3
        elif row.get("modality") == "Dobles":
            occupied += 2
        elif row.get("partner_full_name"):
            occupied += 2
        else:
            occupied += 1

    return 100 - occupied


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("## HYBRID SUMMER GAMES")
    st.caption("Selecciona categoría y modalidad. Plazas limitadas.")
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
- **Entrada general:** {ENTRADA_GENERAL}  
- **Entrada usuarios:** {ENTRADA_USUARIOS}  

💵 **Opciones de pago:**
- **Pago en efectivo en nuestros centros**  

**Centro de Entrenamiento Inteligente Roberto Fernández**
  [Ir a la ubicación]({PAGO_EFECTIVO})
  
**Roberto Fernández Hyrox Training Club**
  [Ir a la ubicación]({PAGO_EFECTIVO_H})

- **Transferencia (IBAN):** `{BANK_IBAN}`

⚠️ La plaza se confirma tras recibir el pago.

MUY IMPORTANTE (Referencia/Concepto):
    Escribe obligatoriamente tu Nombre y Apellidos.
""".strip()
    )

# ---------------- Main UI ----------------
left, right = st.columns(2)

with left:

    gender = st.selectbox("Categoría", ["Masculino", "Femenino", "Mixto"])

    modality = st.selectbox("Modalidad", ["Individual", "Dobles", "Tríos"])

    is_pair = modality == "Dobles"
    is_trio = modality == "Tríos"
    is_team = modality in ["Dobles", "Tríos"]
    
    # Paso 4 (AQUÍ VA)
    st.markdown(f"**Categoría seleccionada:** {gender} - {modality}")

    activity = f"{modality}"

    remaining = fetch_total_remaining()
    
    if remaining <= 0:
        st.error("❌ Evento completo")

    elif remaining == 1:
        st.error("🚨 ¡ÚLTIMA PLAZA DISPONIBLE!")

    elif remaining <= 5:
        st.markdown(f"""
        <div style="
            padding:20px;
            border-radius:15px;
            background:#ff4b4b20;
            border:1px solid #ff4b4b;
            text-align:center;
        ">
            <h2>🔥 ÚLTIMAS {remaining} PLAZAS 🔥</h2>
            <p style="font-size:18px;">No te quedes fuera</p>
        </div>
        """, unsafe_allow_html=True)
    
    #elif remaining <= 10:
    #st.warning("⚠️ Quedan pocas plazas")
        
    st.markdown("<br>", unsafe_allow_html=True)

    #st.info(f"🎟️ Plazas disponibles: {remaining}/100")
    st.info("📢 Una semana antes se les comunicará a qué tanda van a pertenecer.")


with right:

    if remaining <= 0:
        st.warning("Las inscripciones están cerradas")
        st.info("Política de cancelación: Una vez confirmado el pago de la inscripción, no se admitirán devoluciones bajo ningún concepto en caso de cancelación voluntaria del participante.")
    else:

        with st.form("booking_form", clear_on_submit=True):
        
            st.warning("⚠️ IMPORTANTE: La reserva solo quedará confirmada una vez recibido el pago.")
            
            full_name = st.text_input("Nombre y Apellido")
            phone = st.text_input("Teléfono")
            email = st.text_input("Email")

            partner_full_name = ""
            partner_phone = ""
            partner_email = ""
            alias = ""
            
            third_full_name = ""
            third_phone = ""
            third_email = ""
            
            # Individual
            if not is_team:
                alias = st.text_input("🥥 Alias")

            # Dobles o tríos
            if is_team:

                st.divider()
                st.markdown("### Segunda persona")

                partner_full_name = st.text_input(
                    "Nombre y Apellido (segunda persona)"
                )

                partner_phone = st.text_input(
                    "Teléfono (segunda persona)"
                )

                partner_email = st.text_input(
                    "Email (segunda persona)"
                )

                if is_trio:

                    st.divider()
                    st.markdown("### Tercera persona")

                    third_full_name = st.text_input(
                        "Nombre y Apellido (tercera persona)"
                    )

                    third_phone = st.text_input(
                        "Teléfono (tercera persona)"
                    )

                    third_email = st.text_input(
                        "Email (tercera persona)"
                    )

                st.divider()

                alias = st.text_input(
                    "🥥 Nombre de equipo"
                )
            

            consent = st.checkbox("Acepto el uso de datos")

            submit = st.form_submit_button("Reservar plaza")
            
            st.warning("Política de cancelación: Una vez confirmado el pago de la inscripción, no se admitirán devoluciones bajo ningún concepto en caso de cancelación voluntaria del participante.")

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
                
            if not alias.strip():
                st.error(
                    "Introduce un alias" if not is_pair
                    else "Introduce nombre de equipo"
                )
                st.stop()

            if not full_name or not phone or not email:
                st.error("Introduce tus datos.")
                st.stop()
                
            if is_pair or is_trio:

                if not partner_full_name.strip():
                    st.error("Introduce el nombre de la segunda persona.")
                    st.stop()

                if not partner_phone.strip():
                    st.error("Introduce el teléfono de la segunda persona.")
                    st.stop()

                if not partner_email.strip():
                    st.error("Introduce el email de la segunda persona.")
                    st.stop()

            if is_trio:

                if not third_full_name.strip():
                    st.error("Introduce el nombre de la tercera persona.")
                    st.stop()

                if not third_phone.strip():
                    st.error("Introduce el teléfono de la tercera persona.")
                    st.stop()

                if not third_email.strip():
                    st.error("Introduce el email de la tercera persona.")
                    st.stop()
                    
            ok, msg = create_booking_atomic(
                full_name=full_name,
                phone=phone,
                email=email,
                modality=modality,
                alias=alias,
                partner_full_name=partner_full_name if is_pair or is_trio else None,
                partner_phone=partner_phone if is_pair or is_trio else None,
                partner_email=partner_email if is_pair or is_trio else None,
                third_full_name=third_full_name if is_trio else None,
                third_phone=third_phone if is_trio else None,
                third_email=third_email if is_trio else None,
            )

            if ok:

                subject = "🥥 HYBRID SUMMER GAMES - Inscripción recibida (pendiente de pago)"

                html = f"""
                <h2>Inscripción recibida 🌴</h2>

                <p>Evento HYBRID SUMMER GAMES</p>

                <ul>
                <li>Fecha: {event_date}</li>
                <li>Categoría: {activity}</li>

                <p>Tu plaza está pendiente de pago.</p>
            
                <hr>
                
                <p><strong>Opciones de pago:</strong></p>
                <p><strong>Pago en efectivo:</strong> Disponible en nuestros centros</p>
                <p><strong>Pago por transferencia bancaria - IBAN:</strong> {BANK_IBAN}</p>

                <p>Referencia: nombre y apellidos</p>

                <h3>Política de cancelación</h3>
                <p>
                Una vez confirmado el pago de la inscripción, no se admitirán devoluciones bajo ningún concepto en caso de cancelación voluntaria del participante.
                En caso de suspensión o cancelación del evento por parte de la organización, se informará de las condiciones específicas aplicables.
                </p>
                """

                email_sent = send_email(email, subject, html)

                if not email_sent:
                    st.warning("Reserva creada pero el email no pudo enviarse.")

                if is_pair or is_trio:
                    send_email(partner_email, subject, html)

                if is_trio:
                    send_email(third_email, subject, html)

                st.success(msg)

                st.rerun()

            else:

                st.error(msg)



# ---------------- Admin ----------------
st.divider()

with st.expander("Panel admin"):

    pw = st.text_input("Password", type="password", key="admin_password")

    if pw == get_admin_password():

        rows = fetch_bookings(event_date)
        df = pd.DataFrame(
            rows,
            columns=[
                "id",
                "event_date",
                "full_name",
                "phone",
                "email",
                "partner_full_name",
                "partner_phone",
                "partner_email",
                "third_full_name",
                "third_phone",
                "third_email",
                "modality",
                "paid",
                "created_at",
                "start_time",
                "alias"
            ]
        )

        def format_phone(phone):

            if not phone:
                return ""

            digits = "".join(
                filter(str.isdigit, str(phone))
            )

            if len(digits) == 9:
                digits = "34" + digits

            return digits


        # Solo crear WhatsApp si hay datos
        if not df.empty:

            df["WhatsApp"] = df["phone"].apply(
                lambda x:
                f"https://wa.me/{format_phone(x)}"
                if x else None
            )

        else:

            st.info("Todavía no hay inscripciones")

        st.markdown("### Aforo del evento")

        remaining = fetch_total_remaining()
        occupied = 100 - remaining

        st.info(f"🎟️ Ocupadas: {occupied} | Disponibles: {remaining}/100")
        

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
        
        if st.button("📩 Enviar recordatorio a pendientes"):

            pendientes_df = df[df["paid"] == False]
        
            enviados = 0
            errores = 0

            for _, row in pendientes_df.iterrows():

                subject = "Recordatorio de pago - HYBRID SUMMER GAMES 🥥"

                html = f"""
                <p>Hola {row['full_name']},</p>

                <p>Te recordamos que tu plaza para el evento HYBRID SUMMER GAMES sigue <strong>pendiente de pago</strong>.</p>

                <p>Para confirmar tu inscripción, realiza el pago lo antes posible.</p>
                
                <p><strong>Opciones de pago:</strong></p>
                <p><strong>Pago en efectivo:</strong> Disponible en nuestros centros</p>
                <p><strong>Pago por transferencia bancaria - IBAN:</strong> {BANK_IBAN}</p>

                <p>Referencia: nombre y apellidos</p>

                <p>⚠️ Las plazas son limitadas y no podremos garantizar la reserva sin pago.</p>
                
                <hr>
                
                <h3>¿No puedes asistir?</h3>
                
                <p>
                
                Si finalmente no puedes participar, te pedimos que nos lo comuniques lo antes posible. Esto nos ayuda a organizar mejor el evento.
                </p>
                
                <hr>

                <h3>Política de cancelación</h3>
                <p>
                Una vez confirmado el pago de la inscripción, no se admitirán devoluciones bajo ningún concepto en caso de cancelación voluntaria del participante.
                En caso de suspensión o cancelación del evento por parte de la organización, se informará de las condiciones específicas aplicables.
                </p>
                """

                enviado = send_email(row["email"], subject, html)

                if enviado:
                    enviados += 1
                else:
                    errores += 1

            st.success(f"Emails enviados: {enviados} | errores: {errores}")

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
            
        df_display = df.copy()
        df_display["start_time"] = df_display["start_time"].fillna("Not assigned")

        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "WhatsApp": st.column_config.LinkColumn(
                "💬 WhatsApp",
                display_text="Abrir"
                )
            }
        )

        
        st.markdown("### 🚀 Asignar tanda")

        # Generar horarios
        time_slots = generate_mixed_time_slots()

        # Solo atletas sin hora
        available_df = df[df["start_time"].isna()]

        if available_df.empty:
            st.info("No hay inscripciones pendientes de asignar tanda.")
        else:

            # Seleccionar inscripción
            selected_id = st.selectbox(
                "Seleccionar id",
                available_df["id"].tolist(),
                key="time_booking"
            )

            # Seleccionar hora
            selected_time = st.selectbox(
                "Seleccionar la hora",
                time_slots,
                key="time_select"
            )

            # Guardar + enviar email
            if st.button("Confirmar la asignación"):

                try:

                    # Guardar hora
                    sb.table("bookings") \
                        .update({"start_time": selected_time}) \
                        .eq("id", int(selected_id)) \
                        .execute()

                    # Recuperar datos de la reserva
                    resp = sb.table("bookings") \
                        .select("*") \
                        .eq("id", int(selected_id)) \
                        .single() \
                        .execute()

                    row = resp.data

                    if row:

                        subject = "🥥 HYBRID SUMMER GAMES - Hora de salida confirmada"

                        html = f"""
                        <h2>Tu salida ya está confirmada 🌴</h2>

                        <p>Hola <strong>{row['full_name']}</strong>,</p>

                        <p>
                        Ya tenemos preparada tu salida para el evento HYBRID SUMMER GAMES.
                        </p>

                        <hr>

                        <p>
                        <strong>Número de dorsal:</strong> {row['id']}
                        </p>

                        <p>
                        <strong>Hora de salida:</strong> {row['start_time']}
                        </p>

                        <hr>

                        <p>
                        Te recomendamos llegar <strong>1 hora antes</strong> de tu salida para:
                        </p>

                        <ul>
                            <li>Hacer el check-in</li>
                            <li>Recoger el regalito del corredor</li>
                            <li>Realizar el warm up</li>
                            <li>Disfrutar de un cafecito pre competición ☕</li>
                        </ul>

                        <p>
                        Queremos que vivas la experiencia HYBRID SUMMER GAMES completa desde el primer minuto.
                        </p>

                        <p>
                        Nos vemos muy pronto 🔥
                        </p>

                        <p>
                        <strong>RF HYROX Training Club</strong>
                        </p>
                        """

                        # Email principal
                        send_email(row["email"], subject, html)

                        # Segunda persona
                        if row.get("partner_email"):

                            partner_html = html.replace(
                                row["full_name"],
                                row.get("partner_full_name", "")
                            )

                            send_email(row["partner_email"], subject, partner_html)

                        # Tercera persona
                        if row.get("third_email"):

                            third_html = html.replace(
                                row["full_name"],
                                row.get("third_full_name", "")
                            )

                            send_email(row["third_email"], subject, third_html)

                    st.success("Start time assigned and email sent successfully")
                    st.rerun()

                except Exception as e:
                    st.error("Error asignando tanda")
                    st.exception(e)

        st.markdown("### 💳 Confirmar pago")

        booking_id = st.selectbox(
            "Seleccionar inscripción",
            df["id"]
        )

        if st.button("Marcar como pagado"):

            # marcar como pagado
            sb.table("bookings") \
                .update({"paid": True}) \
                .eq("id", booking_id) \
                .execute()

            # recuperar datos actualizados
            resp = sb.table("bookings") \
                .select("email, partner_email, third_email, event_date, modality") \
                .eq("id", booking_id) \
                .single() \
                .execute()

            row = resp.data

            if not row:
                st.error("No se encontró la reserva")
                st.stop()

            modalidad = row.get("modality") or "Individual"

            subject = "🥥 HYBRID SUMMER GAMES - Pago recibido y plaza confirmada"

            html = f"""
            <p>Hola,</p>

            <p>Hemos recibido correctamente tu pago y tu plaza para HYBRID SUMMER GAMES está confirmada.</p>

            <ul>
                <li><strong>Fecha:</strong> {row['event_date']}</li>
                <li><strong>Modalidad:</strong> {modalidad}</li>
            </ul>

            <p>⚡ Una semana antes te comunicaremos la tanda asignada.</p>

            <p>¡Nos vemos en HYBRID SUMMER GAMES! 🌴☀️</p>
            """

            email_sent = send_email(row["email"], subject, html)

            if not email_sent:
                st.error("No se pudo enviar el email principal")
                st.stop()

            partner_sent = True
            third_sent = True

            if row.get("partner_email") and str(row["partner_email"]).strip():
                partner_sent = send_email(row["partner_email"], subject, html)

            if row.get("third_email") and str(row["third_email"]).strip():
                third_sent = send_email(row["third_email"], subject, html)

            if not partner_sent:
                st.warning("El correo de la segunda persona no pudo enviarse")

            if not third_sent:
                st.warning("El correo de la tercera persona no pudo enviarse")

            st.success("Pago confirmado y emails enviados.")
            st.rerun()
            
        st.markdown("### ❌ Eliminar inscripción")

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
            
        st.markdown("### ➕ Añadir inscripción manual")

        admin_modality = st.selectbox(
            "Modalidad (admin)",
            ["Individual", "Dobles", "Tríos"],
            key="admin_modality"
        )

        admin_name = st.text_input("Nombre", key="admin_name")
        admin_phone = st.text_input("Teléfono", key="admin_phone")
        admin_email = st.text_input("Email", key="admin_email")

        partner_name = ""
        partner_phone = ""
        partner_email = ""
        third_name = ""
        third_phone = ""
        third_email = ""

        if admin_modality in ["Dobles", "Tríos"]:
                             
            st.markdown("#### Segunda persona")

            partner_name = st.text_input("Nombre (segunda persona)", key="partner_name")
            partner_phone = st.text_input("Teléfono (segunda persona)", key="partner_phone")
            partner_email = st.text_input("Email (segunda persona)", key="partner_email")
            
        if admin_modality == "Tríos":

            st.markdown("#### Tercera persona")

            third_name = st.text_input("Nombre (tercera persona)", key="third_name")
            third_phone = st.text_input("Teléfono (tercera persona)", key="third_phone")
            third_email = st.text_input("Email (tercera persona)", key="third_email")
            
        admin_alias = st.text_input(
            "Alias" if admin_modality == "Individual" else "Nombre de equipo",
            key="admin_alias"
        )

        send_email_admin = st.checkbox("Enviar email de confirmación", value=True)

        if st.button("➕ Añadir inscripción manual"):

            # VALIDACIONES
            if not admin_name.strip():
                st.error("Nombre obligatorio")
                st.stop()

            if not admin_phone.strip():
                st.error("Teléfono obligatorio")
                st.stop()

            if not admin_email.strip():
                st.error("Email obligatorio")
                st.stop()
                
            if not admin_alias.strip():
                st.error(
                    "Alias obligatorio"
                    if admin_modality == "Individual"
                    else "Nombre de equipo obligatorio"
                )
                st.stop()

            if admin_modality in ["Dobles", "Tríos"]:
                if not partner_name.strip():
                    st.error("Nombre de la segunda persona obligatorio")
                    st.stop()

                if not partner_phone.strip():
                    st.error("Teléfono de la segunda persona obligatorio")
                    st.stop()

                if not partner_email.strip():
                    st.error("Email de la segunda persona obligatorio")
                    st.stop()

            if admin_modality == "Tríos":
                if not third_name.strip():
                    st.error("Nombre de la tercera persona obligatorio")
                    st.stop()

                if not third_phone.strip():
                    st.error("Teléfono de la tercera persona obligatorio")
                    st.stop()

                if not third_email.strip():
                    st.error("Email de la tercera persona obligatorio")
                    st.stop()

            # CREAR RESERVA
            ok, msg = create_booking_atomic(
                full_name=admin_name,
                phone=admin_phone,
                email=admin_email,
                modality=admin_modality,
                partner_full_name=partner_name if admin_modality in ["Dobles", "Tríos"] else None,
                partner_phone=partner_phone if admin_modality in ["Dobles", "Tríos"] else None,
                partner_email=partner_email if admin_modality in ["Dobles", "Tríos"] else None,
                third_full_name=third_name if admin_modality == "Tríos" else None,
                third_phone=third_phone if admin_modality == "Tríos" else None,
                third_email=third_email if admin_modality == "Tríos" else None,
                alias=admin_alias,
                force=True
            )
            
            if ok:

                if send_email_admin:

                    subject = "🥥 HYBRID SUMMER GAMES - Inscripción recibida (pendiente de pago)"

                    html = f"""
                    <h2>Inscripción recibida</h2>

                    <p>Evento HYBRID SUMMER GAMES</p>

                    <ul>
                    <li>Fecha: {event_date}</li>
                    <li>Modalidad: {admin_modality}</li>

                    <p>Tu plaza está pendiente de pago.</p>
            
                    <hr>

                    <h3>Política de cancelación</h3>
                    <p>
                    Una vez confirmado el pago de la inscripción, no se admitirán devoluciones bajo ningún concepto en caso de cancelación voluntaria del participante.
                    En caso de suspensión o cancelación del evento por parte de la organización, se informará de las condiciones específicas aplicables.
                    </p>
                    """

                    send_email(admin_email, subject, html)

                    if admin_modality in ["Dobles", "Tríos"] and partner_email:
                        send_email(partner_email, subject, html)

                    if admin_modality == "Tríos" and third_email:
                        send_email(third_email, subject, html)

                st.success("Inscripción añadida correctamente (modo admin)")
                st.rerun()

            else:
                st.error(msg)
        

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