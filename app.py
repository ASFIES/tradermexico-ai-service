from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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


