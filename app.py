from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------------------------------------------------
# SALUD DEL SERVICIO (opcional pero útil)
# ---------------------------------------------------
@app.route("/")
def health():
    return "Servicio de perfiles de trader activo", 200


# ---------------------------------------------------
# 1) PRIMER CUESTIONARIO
#    /interpretar-perfil  (TAL CUAL ME LO MANDASTE)
# ---------------------------------------------------
@app.route("/interpretar-perfil", methods=["POST"])
def interpretar_perfil():
    data = request.get_json(force=True)

    nombre = data.get("nombre", "Trader novel")
    perfil_codigo = data.get("perfil_codigo", "buho")
    perfil_nombre = data.get("perfil_nombre", "BÚHO ANALÍTICO")
    nivel = data.get("nivel", "N0")
    capital_total = data.get("capital_total", 350)
    capital_trader = data.get("capital_trader", 300)
    capital_libre = data.get("capital_libre", 50)

    prompt_usuario = f"""
    Actúa como un coach financiero empático para el reto TraderMexico.mx.

    Datos del participante:
    - Nombre: {nombre}
    - Perfil: {perfil_nombre} ({perfil_codigo})
    - Nivel: {nivel}
    - Capital total: USD {capital_total}
    - Capital con trader: USD {capital_trader}
    - Capital libre: USD {capital_libre}

    Instrucciones:
    - Escribe un horóscopo financiero emocional, profesional y motivador.
    - 2 a 3 párrafos cortos.
    - Termina con dos bullets de “Siguientes pasos”.
    - Responde SOLO en HTML (<p> <strong> <ul> <li>).
    """

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.8,
        messages=[
            {"role": "system", "content": "Eres un asesor financiero profesional y cálido."},
            {"role": "user", "content": prompt_usuario}
        ],
    )

    texto_html = completion.choices[0].message.content.strip()
    return jsonify({"interpretacion_html": texto_html})


# ---------------------------------------------------
# 2) SEGUNDO CUESTIONARIO
#    /perfil-trader  (cuestionario_trading.php)
# ---------------------------------------------------

def clasificar_trader_por_puntaje(puntaje: int):
    """
    Usa el MISMO rango que en PHP:
      5–8  → Básico  → Trader Inicial
      9–12 → Intermedio → Trader Estratégico
      13–15→ Avanzado → Trader Competitivo
    """
    if puntaje <= 8:
        perfil = "Trader Inicial"
        nivel = "BÁSICO"
    elif puntaje <= 12:
        perfil = "Trader Estratégico"
        nivel = "INTERMEDIO"
    else:
        perfil = "Trader Competitivo"
        nivel = "AVANZADO"
    return perfil, nivel


@app.route("/perfil-trader", methods=["POST"])
def perfil_trader():
    """
    Endpoint para el SEGUNDO cuestionario (cuestionario_trading.php).
    - Recibe: puntaje total (5–15) y lista de respuestas [p1..p5]
    - Devuelve: perfil, nivel y descripcion (texto tipo horóscopo, sin HTML)
    """
    data = request.get_json(force=True)

    puntaje = int(data.get("puntaje", 0))
    respuestas = data.get("respuestas", [])

    # 1) Clasificar según el puntaje
    perfil, nivel = clasificar_trader_por_puntaje(puntaje)

    # 2) Pedirle a OpenAI que escriba el “horóscopo” de este perfil
    prompt_usuario = f"""
    Actúa como un coach financiero empático para un mini test de perfil de trader.

    Datos del participante:
    - Puntaje total: {puntaje} (rango 5–15).
    - Perfil asignado: {perfil}.
    - Nivel: {nivel}.
    - Respuestas numéricas (p1..p5): {respuestas}.

    Instrucciones:
    - Escribe un mensaje tipo horóscopo financiero en español, cálido y profesional.
    - Extensión: 2 párrafos cortos.
    - Debe sonar coherente con el perfil y el nivel (básico / intermedio / avanzado).
    - No repitas los datos numéricos literalmente, interprétalos en lenguaje humano.
    - NO uses listas, ni bullets, ni HTML. Solo texto plano.
    """

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.8,
        messages=[
            {"role": "system", "content": "Eres un asesor financiero profesional y cálido."},
            {"role": "user", "content": prompt_usuario}
        ],
    )

    texto_descripcion = completion.choices[0].message.content.strip()

    return jsonify({
        "perfil": perfil,
        "nivel": nivel,
        "descripcion": texto_descripcion,
        "puntaje": puntaje,
        "respuestas": respuestas,
    })


# ---------------------------------------------------
# 3) EJECUCIÓN LOCAL (opcional)
# ---------------------------------------------------
if __name__ == "__main__":
    # Para pruebas locales: python app.py
    app.run(host="0.0.0.0", port=10000, debug=True)
