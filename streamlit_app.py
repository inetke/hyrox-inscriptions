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

st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
        }
        [data-testid="stAppViewContainer"] {
            padding-top: 0rem !important;
        }
    </style>
""", unsafe_allow_html=True)

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
    <h1 style='text-align:center; margin-top:10px;'>
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
EVENT_DATE = "2026-07-11"
event_date = EVENT_DATE
REGISTRATION_OPEN_DATE = datetime(2026, 6, 2)
WHATSAPP_PHONE = "34659092227"  # sin + ni espacios (España: 34 + número)
INSTAGRAM_URL = "https://www.instagram.com/rfhyroxtrainingclub?igsh=MTJ3Mnh5aDFzMGMxaA=="
MAPS_URL = "https://maps.app.goo.gl/GFaQENB6pXwxRyUL7?g_st=ic"
PAGO_EFECTIVO = "https://maps.app.goo.gl/qHpFpn4dkEvpHkt69"
PAGO_EFECTIVO_H = "https://maps.app.goo.gl/GFaQENB6pXwxRyUL7?g_st=ic"
BANK_IBAN = "ES27 2100 6749 2702 0041 0384"
#PAGO_BIZUM = "+34 659 09 22 27"
ENTRADA_GENERAL = "30€ individual · 60€ dobles"
ENTRADA_USUARIOS = "25€ individual · 50€ dobles"

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
    ### Evento: 11 de julio

    Las inscripciones abrirán oficialmente:

    ## 🌴 2 de junio

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
            "id,event_date,full_name,phone,email,partner_full_name,partner_phone,partner_email,created_at,paid,modality,start_time"
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
            "phone": r["phone"],
            "email": r["email"],
            "partner_full_name": r["partner_full_name"],
            "partner_phone": r["partner_phone"],
            "partner_email": r["partner_email"],
            "modality": r["modality"],
            "paid": r["paid"],
            "created_at": r["created_at"],
            "start_time": r["start_time"]
        })

    return rows

def fetch_total_remaining():
    resp = (
        sb.table("bookings")
        .select("partner_full_name")
        .eq("event_date", EVENT_DATE)
        .execute()
    )

    occupied = 0

    for row in (resp.data or []):
        if row["partner_full_name"]:
            occupied += 2
        else:
            occupied += 1

    return 100 - occupied


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("## HYROX")
    st.caption("Selecciona categoría y modalidad. Plazas limitadas. El aforo total es de 100 personas.")
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

    modality = st.selectbox("Modalidad", ["Individual", "Dobles"])

    is_pair = modality == "Dobles"

    # Paso 4 (AQUÍ VA)
    st.markdown(f"**Categoría seleccionada:** {gender} - {modality}")

    activity = f"Hyrox {modality}"

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

            if is_pair:

                st.markdown("### Segunda persona")

                partner_full_name = st.text_input("Nombre y Apellido (segunda persona)")
                partner_phone = st.text_input("Teléfono (segunda persona)")
                partner_email = st.text_input("Email (segunda persona)")
            
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

            if not full_name or not phone or not email:
                st.error("Introduce tus datos.")
                st.stop()
                
            if is_pair:
                if not partner_full_name.strip():
                    st.error("Introduce el nombre de la segunda persona.")
                    st.stop()

            ok, msg = create_booking_atomic(
                full_name=full_name,
                phone=phone,
                email=email,
                modality=modality,
                partner_full_name=partner_full_name if is_pair else None,
                partner_phone=partner_phone if is_pair else None,
                partner_email=partner_email if is_pair else None,
            )

            if ok:

                subject = "HYROX - Inscripción recibida (pendiente de pago)"

                html = f"""
                <h2>Inscripción recibida</h2>

                <p>Evento HYROX</p>

                <ul>
                <li>Fecha: {event_date}</li>
                <li>Categoría: {activity}</li>

                <p>Tu plaza está pendiente de pago.</p>
            
                <hr>

                <h3>Política de cancelación</h3>
                <p>
                Una vez confirmado el pago de la inscripción, no se admitirán devoluciones bajo ningún concepto en caso de cancelación voluntaria del participante.
                En caso de suspensión o cancelación del evento por parte de la organización, se informará de las condiciones específicas aplicables.
                </p>
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
                "modality",
                "paid",
                "created_at",
                "start_time"
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

                subject = "Recordatorio de pago - HYROX"

                html = f"""
                <p>Hola {row['full_name']},</p>

                <p>Te recordamos que tu plaza para el evento HYROX sigue <strong>pendiente de pago</strong>.</p>

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

        # Seleccionar inscripción
        selected_id = st.selectbox(
            "Seleccionar id",
            available_df["id"],
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

            # Guardar hora
            sb.table("bookings") \
                .update({"start_time": selected_time}) \
                .eq("id", selected_id) \
                .execute()

            # Recuperar datos de la reserva
            resp = sb.table("bookings") \
                .select("id, full_name, email, partner_email, partner_full_name, start_time") \
                .eq("id", selected_id) \
                .single() \
                .execute()

            row = resp.data

            if row:

                subject = "HYROX - Hora de salida confirmada"

                html = f"""
                <h2>Tu salida HYROX ya está confirmada 💥</h2>

                <p>Hola <strong>{row['full_name']}</strong>,</p>

                <p>
                Ya tenemos preparada tu salida para el evento HYROX.
                </p>

                <hr>

                <p>
                <strong>🎽 Número de dorsal:</strong> {row['id']}
                </p>

                <p>
                <strong>⏱️ Hora de salida:</strong> {row['start_time']}
                </p>

                <hr>

                <p>
                Te recomendamos llegar <strong>1 hora antes</strong> de tu salida para:
                </p>

                <ul>
                    <li>Recoger tu dorsal</li>
                    <li>Preparar tu mochila</li>
                    <li>Realizar el warm up</li>
                    <li>Disfrutar de un cafecito pre competición ☕</li>
                </ul>

                <p>
                Queremos que vivas la experiencia HYROX completa desde el primer minuto.
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

                # Email pareja con su propio nombre
                if row.get("partner_email") and str(row["partner_email"]).strip():

                    partner_name = (row.get("partner_full_name") or "").strip()

                    partner_html = f"""
                    <h2>Tu salida HYROX ya está confirmada 💥</h2>

                    <p>Hola <strong>{row["partner_full_name"]}</strong>,</p>

                    <p>
                    Ya tenemos preparada tu salida para el evento HYROX.
                    </p>

                    <hr>

                    <p>
                    <strong>🎽 Número de dorsal:</strong> {row['id']}
                    </p>

                    <p>
                    <strong>⏱️ Hora de salida:</strong> {row['start_time']}
                    </p>

                    <hr>

                    <p>
                    Te recomendamos llegar <strong>1 hora antes</strong> de tu salida para:
                    </p>

                    <ul>
                        <li>Recoger tu dorsal</li>
                        <li>Preparar tu mochila</li>
                        <li>Realizar el warm up</li>
                        <li>Disfrutar de un cafecito pre competición ☕</li>
                    </ul>

                    <p>
                    Nos vemos muy pronto 🔥
                    </p>

                    <p><strong>RF HYROX Training Club</strong></p>
                    """

                    send_email(row["partner_email"], subject, partner_html)
    
            st.success("Start time assigned and email sent successfully")
            st.rerun()

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
                .select("email, partner_email, event_date, partner_full_name") \
                .eq("id", booking_id) \
                .single() \
                .execute()

            row = resp.data

            if not row:
                st.error("No se encontró la reserva")
                st.stop()

            modalidad = (
                "Dobles"
                if row.get("partner_full_name")
                and str(row["partner_full_name"]).strip()
                else "Individual"
            )

            subject = "HYROX - Pago recibido y plaza confirmada"

            html = f"""
            <p>Hola,</p>

            <p>Hemos recibido correctamente tu pago y tu plaza para HYROX está confirmada.</p>

            <ul>
                <li><strong>Fecha:</strong> {row['event_date']}</li>
                <li><strong>Modalidad:</strong> {modalidad}</li>
            </ul>

            <p>📢 Una semana antes te comunicaremos la tanda asignada.</p>

            <p>¡Nos vemos en HYROX! 💥</p>
            """

            email_sent = send_email(row["email"], subject, html)

            if not email_sent:
                st.error("No se pudo enviar el email principal")
                st.stop()

            partner_sent = True

            if row.get("partner_email") and str(row["partner_email"]).strip():
                partner_sent = send_email(row["partner_email"], subject, html)

            if not partner_sent:
                st.warning("El correo de la segunda persona no pudo enviarse")

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
            ["Individual", "Dobles"],
            key="admin_modality"
        )

        admin_name = st.text_input("Nombre", key="admin_name")
        admin_phone = st.text_input("Teléfono", key="admin_phone")
        admin_email = st.text_input("Email", key="admin_email")

        partner_name = ""
        partner_phone = ""
        partner_email = ""

        if admin_modality == "Dobles":

            st.markdown("#### Segunda persona")

            partner_name = st.text_input("Nombre (pareja)", key="partner_name")
            partner_phone = st.text_input("Teléfono (pareja)", key="partner_phone")
            partner_email = st.text_input("Email (pareja)", key="partner_email")

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

            if admin_modality == "Dobles":
                if not partner_name.strip():
                    st.error("Nombre de la pareja obligatorio")
                    st.stop()

            # CREAR RESERVA
            ok, msg = create_booking_atomic(
                full_name=admin_name,
                phone=admin_phone,
                email=admin_email,
                modality=admin_modality,
                partner_full_name=partner_name if admin_modality == "Dobles" else None,
                partner_phone=partner_phone if admin_modality == "Dobles" else None,
                partner_email=partner_email if admin_modality == "Dobles" else None,
                force=True   # 👈 clave
            )

            if ok:

                if send_email_admin:

                    subject = "HYROX - Inscripción recibida (pendiente de pago)"

                    html = f"""
                    <h2>Inscripción recibida</h2>

                    <p>Evento HYROX</p>

                    <ul>
                    <li>Fecha: {event_date}</li>
                    <li>Categoría: {activity}</li>

                    <p>Tu plaza está pendiente de pago.</p>
            
                    <hr>

                    <h3>Política de cancelación</h3>
                    <p>
                    Una vez confirmado el pago de la inscripción, no se admitirán devoluciones bajo ningún concepto en caso de cancelación voluntaria del participante.
                    En caso de suspensión o cancelación del evento por parte de la organización, se informará de las condiciones específicas aplicables.
                    </p>
                    """

                    send_email(admin_email, subject, html)

                    if admin_modality == "Dobles" and partner_email:
                        send_email(partner_email, subject, html)

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