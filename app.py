from __future__ import annotations

import pandas as pd
import streamlit as st

from calculos import (
    estimar_consumo_litros_vuelta,
    estimar_desgaste_neumatico_vuelta,
    calcular_estrategia,
    repartir_vueltas,
)
from gpro_public import buscar_circuito_gprotools

st.set_page_config(page_title="GPROMIO", layout="wide")

st.title("GPROMIO - GPRO Manager Tools")
st.caption("Calculadora editable de combustible, stints y desgaste de neumáticos.")

with st.sidebar:
    st.header("Circuito")
    nombre_circuito = st.text_input("Buscar circuito", value="Silverstone")
    cargar = st.button("Cargar datos públicos")

if "circuito" not in st.session_state or cargar:
    st.session_state.circuito = buscar_circuito_gprotools(nombre_circuito)

c = st.session_state.circuito

st.header("1) Datos del circuito")
manual = st.toggle("Usar carga manual / corregir datos", value=False)

col1, col2, col3, col4 = st.columns(4)
with col1:
    circuito = st.text_input("Circuito", value=c.get("circuito", nombre_circuito), disabled=not manual)
    vueltas = st.number_input("Vueltas", min_value=1, max_value=120, value=int(c.get("vueltas") or 60), disabled=not manual)
with col2:
    km_vuelta = st.number_input("Km/vuelta", min_value=0.1, value=float(c.get("km_vuelta") or 5.138), step=0.001, disabled=not manual)
    distancia_total = st.number_input("Distancia total", min_value=1.0, value=float(c.get("distancia_total") or (vueltas * km_vuelta)), step=0.1, disabled=not manual)
with col3:
    pit_time = st.number_input("Pit time", min_value=0.0, value=float(c.get("pit_time") or 22.5), step=0.1, disabled=not manual)
    consumo_circuito = st.selectbox("Consumo circuito", ["Very low", "Low", "Medium", "High", "Very high"], index=["Very low", "Low", "Medium", "High", "Very high"].index(c.get("consumo", "High")))
with col4:
    desgaste_circuito = st.selectbox("Desgaste neumático circuito", ["Very low", "Low", "Medium", "High", "Very high"], index=["Very low", "Low", "Medium", "High", "Very high"].index(c.get("desgaste_neumatico", "Low")))
    st.metric("Fuente", c.get("fuente", "Local"))

with st.expander("Ver datos cargados"):
    st.dataframe(pd.DataFrame([c]).T.rename(columns={0: "Valor"}), use_container_width=True)

st.header("2) Datos editables de carrera")
col1, col2, col3, col4 = st.columns(4)
with col1:
    compuesto = st.selectbox("Neumático", ["Extra blando", "Blando", "Medio", "Duro", "Lluvia"], index=1)
    paradas = st.selectbox("Paradas", [0, 1, 2, 3, 4], index=2)
with col2:
    temp_promedio = st.number_input("Temperatura promedio", value=17.0, step=0.5)
    margen_litros = st.number_input("Margen por stint (L)", value=3.0, step=0.5)
with col3:
    motor_nivel = st.number_input("Nivel motor", min_value=1, max_value=10, value=3)
    electronica_nivel = st.number_input("Nivel electrónica", min_value=1, max_value=10, value=2)
with col4:
    suspension_nivel = st.number_input("Nivel suspensión", min_value=1, max_value=10, value=2)
    experiencia = st.number_input("Experiencia piloto", min_value=0, max_value=250, value=29)

st.subheader("Riesgos")
r1, r2, r3 = st.columns(3)
with r1:
    riesgo_pista_limpia = st.slider("Riesgo pista despejada", 0, 100, 0, 5)
with r2:
    riesgo_adelantar = st.slider("Riesgo adelantar", 0, 100, 0, 5)
with r3:
    riesgo_defender = st.slider("Riesgo defender", 0, 100, 0, 5)

st.header("3) Modelo editable")
a, b, ccol = st.columns(3)
with a:
    ajuste_consumo = st.number_input("Ajuste manual consumo L/vuelta", value=0.00, step=0.05, help="Usalo para calibrar con tus carreras reales.")
with b:
    ajuste_desgaste = st.number_input("Ajuste manual desgaste %/vuelta", value=0.00, step=0.05, help="Usalo para calibrar con tus carreras reales.")
with ccol:
    neumatico_inicial = st.number_input("Neumático inicial %", min_value=1.0, max_value=100.0, value=100.0, step=1.0)

consumo_l_vuelta = estimar_consumo_litros_vuelta(
    consumo_circuito=consumo_circuito,
    motor_nivel=motor_nivel,
    electronica_nivel=electronica_nivel,
    temp_promedio=temp_promedio,
    riesgo_pista_limpia=riesgo_pista_limpia,
    riesgo_adelantar=riesgo_adelantar,
    riesgo_defender=riesgo_defender,
    ajuste_manual=ajuste_consumo,
)

desgaste_pct_vuelta = estimar_desgaste_neumatico_vuelta(
    desgaste_circuito=desgaste_circuito,
    compuesto=compuesto,
    temp_promedio=temp_promedio,
    riesgo_pista_limpia=riesgo_pista_limpia,
    riesgo_adelantar=riesgo_adelantar,
    riesgo_defender=riesgo_defender,
    suspension_nivel=suspension_nivel,
    experiencia_piloto=experiencia,
    ajuste_manual=ajuste_desgaste,
)

m1, m2, m3 = st.columns(3)
m1.metric("Consumo estimado", f"{consumo_l_vuelta:.3f} L/v")
m2.metric("Desgaste estimado", f"{desgaste_pct_vuelta:.3f} %/v")
m3.metric("Vueltas máximas neumático", f"{int(neumatico_inicial / desgaste_pct_vuelta)}")

st.header("4) Stints")
st.write("Podés dejar reparto automático o modificar las vueltas de cada stint. Al cambiar cualquier dato, recalcula solo.")

auto_stints = repartir_vueltas(int(vueltas), int(paradas))
cols = st.columns(len(auto_stints))
vueltas_personalizadas = []
for i, default in enumerate(auto_stints):
    with cols[i]:
        vueltas_personalizadas.append(st.number_input(f"Vueltas stint {i+1}", min_value=0, max_value=int(vueltas), value=int(default), step=1))

suma_stints = sum(vueltas_personalizadas)
if suma_stints != int(vueltas):
    st.warning(f"La suma de stints da {suma_stints} vueltas, pero la carrera tiene {int(vueltas)}. Revisá el reparto.")

resultado = calcular_estrategia(
    vueltas_totales=int(vueltas),
    paradas=int(paradas),
    consumo_l_vuelta=consumo_l_vuelta,
    desgaste_pct_vuelta=desgaste_pct_vuelta,
    margen_litros=float(margen_litros),
    neumatico_inicial_pct=float(neumatico_inicial),
    vueltas_personalizadas=vueltas_personalizadas,
)

df = pd.DataFrame(resultado["filas"])
st.dataframe(df, use_container_width=True, hide_index=True)

q2, total = st.columns(2)
q2.metric("Combustible Q2 recomendado", f"{resultado['q2_litros']} L")
total.metric("Combustible total estimado", f"{resultado['total_litros']} L")

st.info("Esto es un modelo editable/calibrable. La precisión mejora cuando carguemos historial real de tus carreras.")
