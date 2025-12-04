from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

# Cliente de OpenAI: requiere que OPENAI_API_KEY esté en variables de entorno
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


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
    - Usa 2 a 3 párrafos cortos.
    - Termina con dos bullets de “Siguientes pasos”.
    - Responde SOLO en HTML usando <p>, <strong>, <ul>, <li>.
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
# 2) SEGUNDO CUESTIONARIO: TIPO DE OPERADOR
#    /perfil-trader
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
        - Tipo de operador recomendado (perfil)
        - Nivel (básico / intermedio / avanzado)
        - Texto tipo “el operador que necesitas”
    """
    data = request.get_json(force=True)

    puntaje = int(data.get("puntaje", 0))
    respuestas = data.get("respuestas", [])

    # Clasificación automática
    perfil, nivel = clasificar_trader_por_puntaje(puntaje)

    # Prompt enfocado en "el operador que necesitas"
    prompt_usuario = f"""
    Actúa como un coach financiero empático.
    Este test no describe al usuario: describe EL TIPO DE OPERADOR DE TRADING que necesita a su lado.

    Datos:
    - Puntaje total: {puntaje} (rango 5–15).
    - Perfil asignado: {perfil}.
    - Nivel: {nivel}.
    - Respuestas numéricas (p1..p5), sobre preferencias de riesgo, comunicación y delegación: {respuestas}.

    Instrucciones:
    - Escribe 2 párrafos en español, cálidos y profesionales.
    - Describe al operador que la persona necesita: su estilo de riesgo, forma de comunicarse, disciplina
      y manera de acompañar al inversionista.
    - Habla SIEMPRE en segunda persona: “necesitas un operador que…”.
    - No repitas números; interpreta las respuestas en lenguaje humano.
    - NO uses HTML, ni bullets, ni listas. Solo texto plano.
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
# 3) TERCER CUESTIONARIO: APTITUD SOCIEDAD IKARUS
#    /aptitud-ikarus
# ---------------------------------------------------

def clasificar_nivel_ikarus(puntaje: int):
    """
    Rango total posible del test: 10 a 30 puntos.

    10–15 puntos → Nivel Silver
    16–22 puntos → Nivel Gold
    23–30 puntos → Nivel Platinum
    """
    if puntaje <= 15:
        return "Silver"
    elif puntaje <= 22:
        return "Gold"
    else:
        return "Platinum"


@app.route("/aptitud-ikarus", methods=["POST"])
def aptitud_ikarus():
    """
    Endpoint para el Cuestionario de Aptitud – Sociedad Ikarus de Estrategas de Mercado.

    Espera un JSON como:
    {
      "nombre": "Wendy",
      "email": "correo@ejemplo.com",
      "telefono": "+52...",
      "respuestas": { "q1": "a", ..., "q10": "c" },
      "monto_deseado_usd": 3000,
      "estado_registro": "no_registrado",
      "activo": false
    }

    Devuelve:
      - nombre
      - nivel (Silver / Gold / Platinum)
      - puntaje total
      - monto_deseado_usd
      - estado_registro
      - activo
      - interpretacion_html (texto tipo horóscopo Ikarus en HTML)
    """
    data = request.get_json(force=True)

    nombre = data.get("nombre", "Miembro Ikarus")
    email = data.get("email", "")
    telefono = data.get("telefono", "")

    respuestas = data.get("respuestas", {})
    monto_deseado = data.get("monto_deseado_usd", None)

    estado_registro = data.get("estado_registro", "no_registrado")
    activo = data.get("activo", False)

    # ------------ 1) Calcular puntaje total (q1..q10) ------------
    def puntaje_de_opcion(op):
        if op == "a":
            return 1
        elif op == "b":
            return 2
        elif op == "c":
            return 3
        return 0

    puntaje = 0
    for i in range(1, 11):
        clave = f"q{i}"
        op = respuestas.get(clave, "")
        puntaje += puntaje_de_opcion(op)

    # ------------ 2) Nivel Ikarus ------------
    nivel = clasificar_nivel_ikarus(puntaje)

    # ------------ 3) Prompt tipo "horóscopo Ikarus" ------------
    texto_monto = ""
    if monto_deseado is not None:
        texto_monto = f"El monto que desea invertir inicialmente es de aproximadamente USD {monto_deseado}."

    prompt_usuario = f"""
Actúa como un mentor financiero y de trading para la Sociedad Ikarus de Estrategas de Mercado.

Datos del participante:
- Nombre: {nombre}
- Nivel asignado: {nivel}
- Puntaje total: {puntaje} (rango de 10 a 30).
- Estado de registro: {estado_registro} (registrado/no_registrado).
- Cuenta activa fondeada: {"sí" if activo else "no"}.
- {texto_monto}

Instrucciones:
- Escribe un texto tipo "horóscopo de perfil Ikarus" en español, cálido, profesional y aspiracional.
- Debe exaltar la personalidad financiera del participante según su nivel:
  * Silver: inicio disciplinado, enfoque en aprendizaje, prudencia inteligente.
  * Gold: operador en crecimiento, con estructura, potencial de consolidar resultados.
  * Platinum: estratega patrimonial, visión de largo plazo, capacidad de manejar complejidad.
- Usa 2 a 3 párrafos cortos.
- Añade luego 2 bullet points de "Siguientes pasos Ikarus" coherentes con el nivel.
- Menciona de forma sutil que puede acceder a beneficios mayores dentro de Ikarus,
  sin sonar vendedor agresivo.
- Responde SOLO en HTML válido usando <p>, <strong>, <ul>, <li>.
"""

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.8,
        messages=[
            {"role": "system", "content": "Eres un mentor financiero profesional, empático y muy claro."},
            {"role": "user", "content": prompt_usuario}
        ],
    )

    interpretacion_html = completion.choices[0].message.content.strip()

    # ------------ 4) Respuesta JSON para PHP / front ------------
    return jsonify({
        "nombre": nombre,
        "nivel": nivel,
        "puntaje": puntaje,
        "monto_deseado_usd": monto_deseado,
        "estado_registro": estado_registro,
        "activo": activo,
        "interpretacion_html": interpretacion_html
    })


# ---------------------------------------------------
# 4) EJECUCIÓN LOCAL
# ---------------------------------------------------
if __name__ == "__main__":
    # En Render normalmente no se usa esto, pero para pruebas locales sí
    app.run(host="0.0.0.0", port=10000, debug=True)
