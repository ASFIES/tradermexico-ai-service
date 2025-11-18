from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# ---------------------------------------------------
# SALUD DEL SERVICIO (opcional)
# ---------------------------------------------------
@app.route("/")
def health():
    return "Servicio de perfiles de trader activo", 200


# ---------------------------------------------------
# 1) PRIMER CUESTIONARIO (NO SE TOCA)
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
# 2) SEGUNDO CUESTIONARIO (AQUÍ ES DONDE SE MODIFICA)
# ---------------------------------------------------

def clasificar_trader_por_puntaje(puntaje: int):
    """
    Usa el mismo rango que en PHP:
      5–8  → Operador Conservador  (BÁSICO)
      9–12 → Operador Balanceado   (INTERMEDIO)
      13–15→ Operador Dinámico     (AVANZADO)
    """
    if puntaje <= 8:
        return "Operador Conservador", "BÁSICO"
    elif puntaje <= 12:
        return "Operador Balanceado", "INTERMEDIO"
    else:
        return "Operador Dinámico", "AVANZADO"


@app.route("/perfil-trader", methods=["POST"])
def perfil_trader():
    """
    Endpoint para el cuestionario_trading.php.
    Devuelve:
        - Tipo de operador recomendado
        - Nivel
        - Texto tipo “horóscopo” (humano, cálido, sin HTML)
    """
    data = request.get_json(force=True)

    puntaje = int(data.get("puntaje", 0))
    respuestas = data.get("respuestas", [])

    # Clasificación automática
    perfil, nivel = clasificar_trader_por_puntaje(puntaje)

    # Nuevo prompt enfocado en "el operador que necesitas"
    prompt_usuario = f"""
    Actúa como un coach financiero empático.  
    Este test no describe al usuario: describe EL TIPO DE OPERADOR DE TRADING que necesita.

    Datos:
    - Puntaje: {puntaje} (5–15)
    - Perfil asignado: {perfil}
    - Nivel: {nivel}
    - Respuestas: {respuestas}

    Instrucciones:
    - Escribe 2 párrafos cálidos y profesionales.
    - Describe al operador que la persona necesita trabajar: su estilo, nivel de riesgo, comunicación, disciplina.
    - Habla SIEMPRE en segunda persona: “necesitas un operador que…”.
    - No uses HTML, ni bullets, ni listas.
    - No repitas números; interpreta las respuestas de forma humana.
    """

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.8,
        messages=[
            {"role": "system", "content": "Eres un asesor financiero profesional y cálido."},
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
# 3) EJECUCIÓN LOCAL
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
