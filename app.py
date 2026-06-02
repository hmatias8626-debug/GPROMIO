import streamlit as st
import pandas as pd

from calculos import (
    calcular_estrategia_combustible,
    estimar_desgaste_neumatico,
    repartir_stints,
)
from gpro_public import obtener_calendario, buscar_circuitos, circuito_a_dataframe

st.set_page_config(page_title="GPROMIO", page_icon="🏎️", layout="wide")

st.title("🏎️ GPROMIO - GPRO Manager Tools")
st.caption("Combustible, neumáticos y estrategia usando datos públicos de GPRO Tools + tus datos manuales.")

with st.sidebar:
    st.header("Datos manuales")
    compuesto = st.selectbox("Neumático", ["Blando", "Medio", "Duro", "Lluvia"], index=0)
    paradas = st.selectbox("Paradas", [1, 2, 3, 4], index=1)
    litros_vuelta_manual = st.number_input("Consumo estimado L/vuelta", min_value=0.5, max_value=6.0, value=2.60, step=0.05)
    margen = st.number_input("Margen seguridad combustible (L)", min_value=0.0, max_value=20.0, value=3.0, step=0.5)
    riesgo = st.slider("Riesgo carrera estimado", 0, 100, 10, 5)
    temp = st.number_input("Temperatura carrera °C", min_value=0, max_value=60, value=18, step=1)

st.header("1) Cargar datos públicos")
col_buscar, col_btn = st.columns([3, 1])
with col_buscar:
    texto_busqueda = st.text_input("Buscar circuito", value="Silverstone")
with col_btn:
    st.write("")
    cargar = st.button("Cargar circuito", use_container_width=True)

if "circuitos" not in st.session_state:
    st.session_state.circuitos = []

if cargar:
    with st.spinner("Leyendo calendario público de GPRO Tools..."):
        circuitos = obtener_calendario()
        encontrados = buscar_circuitos(circuitos, texto_busqueda)
        st.session_state.circuitos = encontrados

if st.session_state.circuitos:
    opciones = [f"{c.get('round', '?')} - {c.get('track', 'Sin nombre')} ({c.get('country', '')})" for c in st.session_state.circuitos]
    elegido_idx = st.selectbox("Resultado encontrado", range(len(opciones)), format_func=lambda i: opciones[i])
    circuito = st.session_state.circuitos[elegido_idx]
else:
    st.info("Cargá un circuito para empezar. Si la web no responde, podés usar carga manual abajo.")
    circuito = {}

st.header("2) Datos del circuito")
manual = st.toggle("Usar carga manual / corregir datos", value=not bool(circuito))

if manual:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        track = st.text_input("Circuito", value=circuito.get("track", "Silverstone"))
        laps = st.number_input("Vueltas", min_value=1, max_value=120, value=int(circuito.get("laps", 60) or 60))
    with col2:
        distance = st.number_input("Distancia total km", min_value=1.0, max_value=600.0, value=float(circuito.get("distance_km", 308.3) or 308.3), step=0.1)
        lap_km = st.number_input("Km por vuelta", min_value=1.0, max_value=10.0, value=float(circuito.get("lap_km", 5.138) or 5.138), step=0.001)
    with col3:
        pit_time = st.number_input("Pit time segundos", min_value=0.0, max_value=60.0, value=float(circuito.get("pit_time_s", 22.5) or 22.5), step=0.5)
        fuel_label = st.selectbox("Consumo circuito", ["Very low", "Low", "Medium", "High", "Very high"], index=["Very low", "Low", "Medium", "High", "Very high"].index(circuito.get("fuel", "High") if circuito.get("fuel", "High") in ["Very low", "Low", "Medium", "High", "Very high"] else "High"))
    with col4:
        tyre_label = st.selectbox("Desgaste neumático", ["Very low", "Low", "Medium", "High", "Very high"], index=["Very low", "Low", "Medium", "High", "Very high"].index(circuito.get("tyre", "Low") if circuito.get("tyre", "Low") in ["Very low", "Low", "Medium", "High", "Very high"] else "Low"))
        grip = st.text_input("Grip", value=circuito.get("grip", "Medium"))

    circuito_final = {
        "track": track, "laps": laps, "distance_km": distance, "lap_km": lap_km,
        "pit_time_s": pit_time, "fuel": fuel_label, "tyre": tyre_label, "grip": grip,
        "power": circuito.get("power"), "handling": circuito.get("handling"), "acceleration": circuito.get("acceleration"),
        "date": circuito.get("date", "")
    }
else:
    circuito_final = circuito

if circuito_final:
    df_c = circuito_a_dataframe(circuito_final)
    st.dataframe(df_c, use_container_width=True, hide_index=True)

st.header("3) Cálculo de estrategia")
if circuito_final:
    vueltas = int(circuito_final.get("laps") or 0)
    estrategia = calcular_estrategia_combustible(vueltas, litros_vuelta_manual, paradas, margen)
    stints = repartir_stints(vueltas, paradas)

    desgaste = estimar_desgaste_neumatico(
        tyre_label=circuito_final.get("tyre", "Medium"),
        compuesto=compuesto,
        temperatura=temp,
        riesgo=riesgo,
        stints=stints,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vueltas", vueltas)
    m2.metric("Combustible total", f"{estrategia['combustible_total']} L")
    m3.metric("Q2 recomendado", f"{estrategia['q2_litros']} L")
    m4.metric("Paradas", paradas)

    filas = []
    for i, v in enumerate(stints, start=1):
        litros_stint = round((v * litros_vuelta_manual) + (margen if i == len(stints) else 1.0), 1)
        filas.append({
            "Stint": i,
            "Vueltas": v,
            "Combustible sugerido": litros_stint,
            "Desgaste estimado": f"{desgaste[i-1]['desgaste_pct']}%",
            "% restante neumático": f"{desgaste[i-1]['restante_pct']}%",
            "Estado": desgaste[i-1]["estado"],
        })

    st.subheader("Stints")
    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    st.warning("El desgaste es una estimación inicial. Lo ideal es corregirlo con tus datos reales de práctica/carrera.")
else:
    st.error("No hay circuito cargado.")

st.header("4) Historial rápido")
st.write("Más adelante esta tabla va a guardar tus carreras reales para ajustar el consumo y desgaste automáticamente.")
