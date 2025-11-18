from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

# Asegúrate de que esta variable de entorno esté configurada en tu servicio Render
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------------------------------------------------
# SALUD DEL SERVICIO (opcional pero útil)
# ---------------------------------------------------
@app.route("/")
def health():
    return "Servicio de perfiles de trader activo y listo para asignar operadores", 200


# ---------------------------------------------------
# 1) PRIMER CUESTIONARIO (SIN CAMBIOS)
#    /interpretar-perfil
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
# 2) SEGUNDO CUESTIONARIO (MODIFICADO)
#    /perfil-trader
# ---------------------------------------------------

def clasificar_trader_por_puntaje(puntaje: int):
    """
    Clasifica el puntaje y retorna el nombre del operador asignado.
    (La lógica debe coincidir con el PHP).
    """
    if puntaje <= 8:
        perfil = "Operador de Crecimiento Constante"
        nivel = "BÁSICO"
    elif puntaje <= 12:
        perfil = "Operador Estratégico Balanceado"
        nivel = "INTERMEDIO"
    else:
        perfil = "Operador de Alto Potencial"
        nivel = "AVANZADO"
    return perfil, nivel


@app.route("/perfil-trader", methods=["POST"])
def perfil_trader():
    """
    Endpoint para el SEGUNDO cuestionario (cuestionario_trading.php).
    Recibe el operador asignado por PHP y genera la descripción IA.
    """
    data = request.get_json(force=True)

    puntaje = int(data.get("puntaje", 0))
    respuestas = data.get("respuestas", [])
    # ⬇️ CAPTURA EL NOMBRE DEL OPERADOR ENVIADO DESDE PHP ⬇️
    operador_asignado = data.get("operador_asignado", "Operador no definido") 

    # Clasificamos para obtener el Nivel (BÁSICO/INTERMEDIO/AVANZADO)
    _, nivel = clasificar_trader_por_puntaje(puntaje)


    # 2) Pedirle a OpenAI que escriba la descripción del operador
    prompt_usuario = f"""
    Actúa como un coach financiero experto que describe las características ideales de un gestor o operador de trading para un cliente.

    Datos del cliente:
    - Puntaje total del test: {puntaje} (rango 5–15).
    - Nivel asignado: {nivel}.
    - Operador asignado: {operador_asignado}.
    - Respuestas numéricas (p1..p5): {respuestas}.

    Instrucciones:
    - Escribe un mensaje tipo "descripción del operador ideal" en español, profesional y motivador.
    - El texto debe describir las **características que el operador {operador_asignado} debe tener** para complementar al usuario, basándose en el {nivel} y el puntaje.
    - Extensión: 2 párrafos cortos.
    - No repitas los datos numéricos literalmente.
    - NO uses listas, ni bullets, ni HTML. Solo texto plano.
    - El tono debe ser de recomendación profesional, enfatizando cómo el operador se ajusta al perfil del cliente.
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
        "perfil": operador_asignado, # Se devuelve el nombre del operador como "perfil"
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
    # Asegúrate de tener configurada la variable de entorno OPENAI_API_KEY
    app.run(host="0.0.0.0", port=10000, debug=True)