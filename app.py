import streamlit as st
import pandas as pd
from calculos import calcular_estrategia, calcular_q2
from circuitos import CIRCUITOS

st.set_page_config(page_title="GPROMIO", layout="wide")

st.title("🏎️ GPROMIO - GPRO Manager Tools")
st.caption("Calculadora inicial de combustible, Q2 y estrategia para GPRO.")

with st.sidebar:
    st.header("Carrera")
    circuito_nombre = st.selectbox("Circuito", list(CIRCUITOS.keys()), index=0)
    circuito = CIRCUITOS[circuito_nombre]
    vueltas = st.number_input("Vueltas", min_value=1, value=int(circuito["vueltas"]), step=1)
    distancia = st.number_input("Distancia total km", min_value=1.0, value=float(circuito["distancia_km"]), step=0.1)

    st.header("Estrategia")
    paradas = st.selectbox("Paradas", [1, 2, 3], index=1)
    litros_vuelta = st.number_input("Consumo estimado L/vuelta", min_value=0.1, value=2.60, step=0.05)
    margen = st.number_input("Margen seguridad total L", min_value=0.0, value=3.0, step=0.5)
    neumatico = st.selectbox("Neumático", ["Extra blando", "Blando", "Medio", "Duro", "Lluvia"], index=1)

col1, col2, col3 = st.columns(3)
col1.metric("Circuito", circuito_nombre)
col2.metric("Vueltas", vueltas)
col3.metric("Distancia", f"{distancia:.1f} km")

st.divider()

st.header("Cálculo de combustible")
resultado = calcular_estrategia(vueltas, litros_vuelta, paradas, margen)
q2 = calcular_q2(resultado)

c1, c2, c3 = st.columns(3)
c1.metric("Combustible total", f"{resultado['combustible_total']} L")
c2.metric("Q2 recomendado", f"{q2} L")
c3.metric("Consumo carrera", f"{litros_vuelta:.2f} L/v")

st.subheader("Stints sugeridos")
df = pd.DataFrame(resultado["stints"])
st.dataframe(df, use_container_width=True, hide_index=True)

st.info("La carga de Q2 corresponde al primer stint. Ajustá litros/vuelta cuando tengas consumo real de práctica o carrera.")

st.divider()

st.header("Datos manuales opcionales")
with st.expander("Piloto"):
    c1, c2, c3 = st.columns(3)
    concentracion = c1.number_input("Concentración", value=81)
    agresividad = c2.number_input("Agresividad", value=151)
    experiencia = c3.number_input("Experiencia", value=29)
    tecnica = c1.number_input("Conocimiento técnico", value=136)
    peso = c2.number_input("Peso kg", value=77)
    energia = c3.number_input("Energía %", value=97)

with st.expander("Auto"):
    c1, c2, c3 = st.columns(3)
    motor = c1.number_input("Motor nivel", value=3)
    electronica = c2.number_input("Electrónica nivel", value=2)
    caja_uso = c3.number_input("Uso caja %", value=31)

with st.expander("Clima"):
    c1, c2, c3 = st.columns(3)
    temp = c1.number_input("Temperatura promedio °C", value=17)
    humedad = c2.number_input("Humedad promedio %", value=28)
    lluvia = c3.number_input("Probabilidad lluvia %", value=0)

st.divider()

st.header("Guardar prueba en historial")
if st.button("Guardar en historial CSV"):
    fila = {
        "circuito": circuito_nombre,
        "vueltas": vueltas,
        "neumatico": neumatico,
        "paradas": paradas,
        "litros_vuelta_estimado": litros_vuelta,
        "margen": margen,
        "q2_recomendado": q2,
        "combustible_total": resultado["combustible_total"],
        "temperatura": temp,
        "humedad": humedad,
        "lluvia": lluvia,
    }
    path = "data/historial.csv"
    try:
        historial = pd.read_csv(path)
        historial = pd.concat([historial, pd.DataFrame([fila])], ignore_index=True)
    except FileNotFoundError:
        historial = pd.DataFrame([fila])
    historial.to_csv(path, index=False)
    st.success("Guardado en data/historial.csv")

try:
    historial = pd.read_csv("data/historial.csv")
    if not historial.empty:
        st.subheader("Historial")
        st.dataframe(historial, use_container_width=True, hide_index=True)
except FileNotFoundError:
    pass
