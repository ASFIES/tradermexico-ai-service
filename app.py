from flask import Flask, request, jsonify
from openai import OpenAI
import os
import requests  # <-- Agregado a requirements.txt

app = Flask(__name__)

# Cliente de OpenAI: requiere que OPENAI_API_KEY esté en variables de entorno
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------------------------------------------------
# URL de Sheets (Apps Script) para obtener el ÚLTIMO registro
# ---------------------------------------------------
# NOTA: Asegúrate de configurar esta variable en Render o pegar tu URL aquí
SHEET_LAST_ENTRY_URL = os.environ.get(
    "IKARUS_SHEET_LAST_URL",
    "https://script.google.com/macros/s/TU_SCRIPT/exec"  # <-- REEMPLAZA ESTO SI NO USAS VAR DE ENTORNO
)


# ---------------------------------------------------
# 0) SALUD DEL SERVICIO
# ---------------------------------------------------
@app.route("/")
def health():
    return "Servicio de perfiles de trader activo", 200


# ---------------------------------------------------
# 1) PRIMER CUESTIONARIO (PERFIL INICIAL)
#    /interpretar-perfil
# ---------------------------------------------------
@app.route("/interpretar-perfil", methods=["POST"])
def interpretar_perfil():
    """
    Genera un horóscopo financiero para el participante, PERO
    toma los datos finales (especialmente monto de inversión)
    del ÚLTIMO registro en Google Sheets.
    """

    # 1. Datos que vienen de PHP (respaldo)
    data = request.get_json(force=True)

    nombre = data.get("nombre", "Trader novel")
    perfil_codigo = data.get("perfil_codigo", "buho")
    perfil_nombre = data.get("perfil_nombre", "BÚHO ANALÍTICO")
    nivel = data.get("nivel", "N0")

    # Valores por defecto
    capital_total = float(data.get("capital_total", 1000))
    capital_trader = float(data.get("capital_trader", 100))
    capital_libre = float(data.get("capital_libre", capital_total - capital_trader))

    # 2. Intentar leer el ÚLTIMO registro desde Google Sheets
    try:
        # Solo intentamos si la URL parece válida
        if SHEET_LAST_ENTRY_URL and SHEET_LAST_ENTRY_URL.startswith("http"):
            resp = requests.get(SHEET_LAST_ENTRY_URL, timeout=5)
            
            if resp.status_code == 200:
                row = resp.json()

                # Buscamos campos (Google Sheets suele devolver claves como definas tu JSON en Apps Script)
                nombre_sheet = row.get("Nombre") or row.get("nombre")
                nivel_sheet = row.get("Nivel") or row.get("nivel")
                monto_inv_str = row.get("Monto Inversión") or row.get("MontoInversion") or row.get("monto_inversion")

                if nombre_sheet:
                    nombre = nombre_sheet

                if nivel_sheet:
                    nivel = nivel_sheet

                # Si viene un monto de inversión, lo usamos como capital_total
                if monto_inv_str is not None:
                    try:
                        # Limpiamos posibles símbolos de moneda o comas
                        limpio = str(monto_inv_str).replace("$", "").replace(",", "")
                        capital_total = float(limpio)
                    except (TypeError, ValueError):
                        pass

                # Datos extra útiles
                estatus = row.get("Estatus") or row.get("estatus") or ""
                activo_str = row.get("Activo") or row.get("activo") or "0"
                activo = str(activo_str).strip().lower() in ("1", "true", "sí", "si")
                origen = row.get("Origen") or row.get("origen") or ""
            else:
                estatus, activo, origen = "", False, ""
        else:
            estatus, activo, origen = "", False, ""
    except Exception:
        # Si falla Sheets, continuamos con los datos del request original
        estatus, activo, origen = "", False, ""

    # 3. Recálculo de Capital con lógica de tramos
    if capital_total <= 0:
        capital_total = 1000.0

    # Tramos por monto de inversión:
    if capital_total < 1500:
        porcentaje_operar = 0.05  # 5%
    elif capital_total <= 3000:
        porcentaje_operar = 0.10  # 10%
    else:
        porcentaje_operar = 0.15  # 15%

    capital_trader = round(capital_total * porcentaje_operar, 2)

    # Límites de seguridad (Hard limits)
    if capital_trader < 50:
        capital_trader = 50.0
    if capital_trader > 1000:
        capital_trader = 1000.0

    capital_libre = capital_total - capital_trader
    if capital_libre < 0:
        capital_libre = 0.0

    # 4. Prompt para la IA
    prompt_usuario = f"""
    Actúa como un coach financiero empático para la Sociedad Ikarus de Estrategas de Mercado.

    Datos del participante:
    - Nombre: {nombre}
    - Perfil: {perfil_nombre} ({perfil_codigo})
    - Nivel: {nivel}
    - Capital total: USD {capital_total}
    - Capital con trader: USD {capital_trader}
    - Capital libre: USD {capital_libre}

    Instrucciones:
    - Escribe un horóscopo financiero emocional, profesional y motivador.
    - Usa 2 a 3 párrafos cortos.
    - Termina con dos bullets de “Siguientes pasos”.
    - Responde SOLO en HTML usando <p>, <strong>, <ul>, <li>.
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # CORREGIDO: Era gpt-4.o-mini
        temperature=0.8,
        messages=[
            {"role": "system", "content": "Eres un asesor financiero profesional y cálido."},
            {"role": "user", "content": prompt_usuario}
        ],
    )

    texto_html = completion.choices[0].message.content.strip()
    
    return jsonify({
        "interpretacion_html": texto_html,
        "capital_total": capital_total,
        "capital_trader": capital_trader,
        "capital_libre": capital_libre
    })


# ---------------------------------------------------
# 2) SEGUNDO CUESTIONARIO: TIPO DE OPERADOR
#    /perfil-trader
# ---------------------------------------------------

def clasificar_trader_por_puntaje(puntaje: int):
    if puntaje <= 8:
        return "Operador Conservador", "BÁSICO"
    elif puntaje <= 12:
        return "Operador Balanceado", "INTERMEDIO"
    else:
        return "Operador Dinámico", "AVANZADO"


@app.route("/perfil-trader", methods=["POST"])
def perfil_trader():
    data = request.get_json(force=True)
    puntaje = int(data.get("puntaje", 0))
    respuestas = data.get("respuestas", [])

    perfil, nivel = clasificar_trader_por_puntaje(puntaje)

    prompt_usuario = f"""
    Actúa como un coach financiero empático.
    Datos:
    - Puntaje: {puntaje} (5-15)
    - Perfil: {perfil}
    - Nivel: {nivel}
    - Respuestas: {respuestas}

    Instrucciones:
    - Describe al OPERADOR DE TRADING que necesita esta persona (segunda persona).
    - 2 párrafos cálidos y profesionales.
    - Texto plano (sin HTML).
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini", # CORREGIDO: Era gpt-4.o-mini
        temperature=0.8,
        messages=[
            {"role": "system", "content": "Eres un asesor financiero profesional."},
            {"role": "user", "content": prompt_usuario}
        ],
    )

    descripcion = completion.choices[0].message.content.strip()

    return jsonify({
        "perfil": perfil,
        "nivel": nivel,
        "descripcion": descripcion,
        "puntaje": puntaje,
        "respuestas": respuestas,
    })


# ---------------------------------------------------
# 3) TERCER CUESTIONARIO: APTITUD SOCIEDAD IKARUS
#    /aptitud-ikarus
# ---------------------------------------------------

def clasificar_nivel_ikarus(puntaje: int):
    if puntaje <= 15:
        return "Silver"
    elif puntaje <= 22:
        return "Gold"
    else:
        return "Platinum"


@app.route("/aptitud-ikarus", methods=["POST"])
def aptitud_ikarus():
    data = request.get_json(force=True)

    nombre = data.get("nombre", "Miembro Ikarus")
    email = data.get("email", "")
    telefono = data.get("telefono", "")
    respuestas = data.get("respuestas", {})
    monto_deseado = data.get("monto_deseado_usd", None)
    estado_registro = data.get("estado_registro", "no_registrado")
    activo = data.get("activo", False)

    # Calcular puntaje
    def puntaje_de_opcion(op):
        if op == "a": return 1
        elif op == "b": return 2
        elif op == "c": return 3
        return 0

    puntaje = 0     
    for i in range(1, 11):
        clave = f"q{i}"
        op = respuestas.get(clave, "")
        puntaje += puntaje_de_opcion(op)

    nivel = clasificar_nivel_ikarus(puntaje)

    texto_monto = ""
    if monto_deseado is not None:
        texto_monto = f"El monto que desea invertir inicialmente es de aproximadamente USD {monto_deseado}."

    prompt_usuario = f"""
    Actúa como un mentor financiero Ikarus.
    Datos:
    - Nombre: {nombre}
    - Nivel: {nivel}
    - Puntaje: {puntaje}
    - {texto_monto}

    Instrucciones:
    - Escribe un 'horóscopo financiero' exaltando su personalidad según nivel ({nivel}).
    - 2 a 3 párrafos cortos + 2 bullets de pasos.
    - SOLO HTML (<p>, <strong>, <ul>, <li>).
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini", # CORREGIDO: Era gpt-4.o-mini
        temperature=0.8,
        messages=[
            {"role": "system", "content": "Eres un mentor financiero profesional."},
            {"role": "user", "content": prompt_usuario}
        ],
    )

    interpretacion_html = completion.choices[0].message.content.strip()

    return jsonify({
        "nombre": nombre,
        "nivel": nivel,
        "puntaje": puntaje,
        "monto_deseado_usd": monto_deseado,
        "estado_registro": estado_registro,
        "activo": activo,
        "interpretacion_html": interpretacion_html
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)