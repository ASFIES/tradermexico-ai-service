from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import os
import requests
import json

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN GENERAL (VARIABLES DE ENTORNO)
# ==========================================

# 1. API KEY DE OPENAI
# Al dejarlo así, toma automáticamente la variable 'OPENAI_API_KEY' de Render.
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 2. URL DE GOOGLE SHEETS (APPS SCRIPT)
# Asegúrate de agregar SHEET_API_URL en las Environment Variables de Render
# Si prefieres dejarla fija aquí, cambia os.environ... por "TU_URL_LARGA"
SHEET_API_URL = os.environ.get("SHEET_API_URL")

# 3. CREDENCIALES DE TWILIO
# También agrégalos en Render: TWILIO_SID, TWILIO_TOKEN, TWILIO_NUMBER
# Opcional: ID de plantilla (TWILIO_TEMPLATE_ID)
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER") 
TWILIO_TEMPLATE_ID = os.environ.get("TWILIO_TEMPLATE_ID")

# 4. MEMORIA Y CONTEXTO
user_interactions = {} # Memoria temporal

def cargar_contexto():
    try:
        if os.path.exists('contexto.txt'):
            with open('contexto.txt', 'r', encoding='utf-8') as f:
                return f.read()
    except:
        pass
    return "Información de Ikarus no disponible por el momento."

CONTEXTO_IKARUS = cargar_contexto()


# ==========================================
# RUTAS DEL SERVIDOR
# ==========================================

# 0. SALUD DEL SERVICIO
@app.route("/")
def health():
    return "Servicio Ikarus AI (Cuestionarios + Chatbot) Activo", 200


# 1. CUESTIONARIO: INTERPRETAR PERFIL
@app.route("/interpretar-perfil", methods=["POST"])
def interpretar_perfil():
    data = request.get_json(force=True)
    nombre = data.get("nombre", "Trader")
    perfil_nombre = data.get("perfil_nombre", "Perfil")
    nivel = data.get("nivel", "N0")
    capital_total = data.get("capital_total", 1000)

    prompt_usuario = f"""
    Actúa como un coach financiero empático para la Sociedad Ikarus.
    Datos: Nombre: {nombre}, Perfil: {perfil_nombre}, Nivel: {nivel}, Capital: {capital_total}.
    Instrucciones: Escribe un horóscopo financiero motivador (2-3 párrafos) + 2 bullets de pasos. SOLO HTML.
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini", temperature=0.8,
        messages=[{"role": "system", "content": "Coach financiero."}, {"role": "user", "content": prompt_usuario}]
    )
    return jsonify({"interpretacion_html": completion.choices[0].message.content.strip()})


# 2. CUESTIONARIO: TIPO DE OPERADOR
@app.route("/perfil-trader", methods=["POST"])
def perfil_trader():
    data = request.get_json(force=True)
    puntaje = int(data.get("puntaje", 0))
    
    if puntaje <= 8: perfil, nivel = "Operador Conservador", "BÁSICO"
    elif puntaje <= 12: perfil, nivel = "Operador Balanceado", "INTERMEDIO"
    else: perfil, nivel = "Operador Dinámico", "AVANZADO"

    prompt_usuario = f"""
    Describe el OPERADOR DE TRADING ideal para: Puntaje {puntaje}, Perfil {perfil}.
    Instrucciones: 2 párrafos cálidos en 2ª persona ("Necesitas un operador..."). Texto plano.
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini", temperature=0.8,
        messages=[{"role": "system", "content": "Asesor experto."}, {"role": "user", "content": prompt_usuario}]
    )
    return jsonify({"perfil": perfil, "nivel": nivel, "descripcion": completion.choices[0].message.content.strip()})


# 3. CUESTIONARIO: APTITUD IKARUS
@app.route("/aptitud-ikarus", methods=["POST"])
def aptitud_ikarus():
    data = request.get_json(force=True)
    nombre = data.get("nombre", "Miembro")
    respuestas = data.get("respuestas", {})
    
    puntos = 0
    for i in range(1, 11):
        op = respuestas.get(f"q{i}", "")
        if op == 'a': puntos += 1
        elif op == 'b': puntos += 2
        elif op == 'c': puntos += 3
    
    if puntos <= 15: nivel = "Silver"
    elif puntos <= 22: nivel = "Gold"
    else: nivel = "Platinum"
    
    prompt_usuario = f"""
    Mentor Ikarus. Diagnóstico para: {nombre}, Nivel {nivel}.
    Instrucciones: Exalta su personalidad financiera. 2-3 párrafos + 2 bullets. SOLO HTML.
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini", temperature=0.8,
        messages=[{"role": "system", "content": "Mentor financiero."}, {"role": "user", "content": prompt_usuario}]
    )
    return jsonify({"nombre": nombre, "nivel": nivel, "puntaje": puntos, "interpretacion_html": completion.choices[0].message.content.strip()})


# ==========================================
# 4. CHATBOT INTELIGENTE (WHATSAPP)
# ==========================================

# Funciones de ayuda
def limpiar_numero(numero):
    """Limpia formato de whatsapp:+521... a 55... para buscar en sheet"""
    if not numero: return ""
    return numero.replace("whatsapp:", "").replace("+", "").strip()

def obtener_usuario_sheet(telefono_whatsapp):
    try:
        # Si no hay URL configurada, devolvemos None
        if not SHEET_API_URL: 
            print("Error: SHEET_API_URL no configurada en Render")
            return None

        resp = requests.get(SHEET_API_URL)
        if resp.status_code != 200: return None
        usuarios = resp.json()
        
        tel_limpio = limpiar_numero(telefono_whatsapp)
        
        for u in usuarios:
            # Limpiar número del sheet para comparar
            sheet_tel = str(u.get('telefono', '')).replace("+", "").replace(" ", "").strip()
            
            # Comparación flexible (si uno contiene al otro)
            if (tel_limpio in sheet_tel and len(tel_limpio) > 6) or (sheet_tel in tel_limpio and len(sheet_tel) > 6):
                return u
        return None
    except Exception as e:
        print(f"Error Sheets: {e}")
        return None

def consultar_gpt_chat(mensaje, sistema):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{sistema}\n\nContexto Base:\n{CONTEXTO_IKARUS}"},
                {"role": "user", "content": mensaje}
            ],
            temperature=0.7
        )
        return completion.choices[0].message.content
    except:
        return "En este momento estoy actualizando mi base de datos. Por favor intenta en unos minutos."

# Ruta del Webhook
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    # Datos que envía Twilio automáticamente
    msg_recibido = request.values.get('Body', '').strip()
    remitente = request.values.get('From', '') 
    
    # Objeto para responder (TwiML)
    resp = MessagingResponse()
    
    # Buscar usuario en Sheets
    usuario = obtener_usuario_sheet(remitente)
    
    # --- LOGICA DE NIVELES ---
    
    # 1. NO REGISTRADO (No está en el Excel)
    if not usuario:
        intentos = user_interactions.get(remitente, 0)
        if intentos >= 3:
            resp.message("He respondido tus dudas iniciales. Para unirte a la Sociedad Ikarus, por favor regístrate en nuestro sitio web o espera a que un asesor te contacte.")
        else:
            user_interactions[remitente] = intentos + 1
            sys_prompt = "Eres un asistente de pre-venta de Sociedad Ikarus. Responde dudas sobre registro y qué es la sociedad. Sé breve y persuasivo."
            resp.message(consultar_gpt_chat(msg_recibido, sys_prompt))
            
    # 2. REGISTRADO PERO NO ACTIVO
    # Verifica si la columna 'activo' es falsa, 0 o vacía
    elif str(usuario.get('activo')).lower() in ['false', '0', 'no', '', 'none']:
        nombre = usuario.get('nombre', 'Futuro Socio')
        sys_prompt = f"Eres soporte de onboarding. El usuario {nombre} ya se registró pero le falta validar su cuenta (KYC/Fondeo). Resuelve dudas de registro y anímalo a activarse."
        resp.message(consultar_gpt_chat(msg_recibido, sys_prompt))

    # 3. ACTIVO / SOCIO
    else:
        nombre = usuario.get('nombre', 'Socio')
        nivel = usuario.get('nivel', 'Silver')
        msg_lower = msg_recibido.lower()
        
        # Menú simple si saluda
        if any(x in msg_lower for x in ["hola", "menu", "opciones", "inicio"]):
            menu = f"¡Hola {nombre}! Bienvenido a tu Concierge {nivel}.\n\n" \
                   "1. 📅 Agendar Mentoría\n" \
                   "2. ☕ Coffee Trader\n" \
                   "3. 📈 Dudas de Trading"
            resp.message(menu)
        
        elif "1" in msg_lower or "agendar" in msg_lower or "cita" in msg_lower:
            link = "https://calendly.com/ikarus/silver"
            if "gold" in str(nivel).lower(): link = "https://calendly.com/ikarus/gold"
            if "platinum" in str(nivel).lower(): link = "https://calendly.com/ikarus/platinum"
            resp.message(f"Accede a la agenda exclusiva {nivel}: {link}")
            
        elif "2" in msg_lower or "coffee" in msg_lower:
            resp.message("Reserva tu lugar en el próximo evento aquí: https://asfieswm.com/coffee-trader")
            
        else:
            sys_prompt = f"Eres un mentor de trading nivel {nivel}. Responde la duda técnica del usuario con profesionalismo."
            resp.message(consultar_gpt_chat(msg_recibido, sys_prompt))

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)