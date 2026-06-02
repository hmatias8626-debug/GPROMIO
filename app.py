import streamlit as st
import pandas as pd

from gpro_model import (
    TYRE_TYPES,
    TYRE_BRANDS,
    load_tracks,
    get_track,
    calc_fuel_l_per_km,
    calc_tyre_max_km,
    calc_strategy,
    recommended_strategy_rows,
)

st.set_page_config(page_title="GPROMIO", layout="wide")

st.title("🏎️ GPROMIO - Estrategia GPRO")
st.caption("Motor de cálculo basado en el Excel GPRO Version 6: combustible, stints y desgaste de neumáticos.")

tracks = load_tracks()
track_names = [t["name"] for t in tracks]

with st.sidebar:
    st.header("Circuito")
    default_idx = track_names.index("Silverstone") if "Silverstone" in track_names else 0
    track_name = st.selectbox("Circuito", track_names, index=default_idx)
    track = get_track(track_name, tracks)

    st.markdown("---")
    st.header("Clima")
    weather = st.selectbox("Condición", ["Dry", "Wet"], index=0)
    avg_temp = st.number_input("Temperatura media carrera °C", min_value=0.0, max_value=60.0, value=20.0, step=0.5)
    humidity = st.number_input("Humedad % (informativo)", min_value=0.0, max_value=100.0, value=20.0, step=1.0)

    st.markdown("---")
    st.header("Piloto")
    concentration = st.number_input("Concentración", min_value=0, max_value=250, value=81)
    aggressiveness = st.number_input("Agresividad", min_value=0, max_value=250, value=151)
    experience = st.number_input("Experiencia", min_value=0, max_value=250, value=27)
    technical = st.number_input("Conocimiento técnico", min_value=0, max_value=250, value=134)
    weight = st.number_input("Peso piloto kg", min_value=40, max_value=130, value=77)

    st.markdown("---")
    st.header("Auto")
    engine_level = st.number_input("Nivel motor", min_value=1, max_value=11, value=3)
    electronics_level = st.number_input("Nivel electrónica", min_value=1, max_value=11, value=2)
    suspension_level = st.number_input("Nivel suspensión", min_value=1, max_value=11, value=2)

    st.markdown("---")
    st.header("Riesgos / Neumáticos")
    ct_risk = st.number_input("Riesgo CT", min_value=0, max_value=100, value=0, step=5)
    tyre_brand = st.selectbox("Marca neumáticos", TYRE_BRANDS, index=TYRE_BRANDS.index("Pipirelli"))
    tyre_type = st.selectbox("Compuesto", TYRE_TYPES, index=TYRE_TYPES.index("Soft"))
    target_wear = st.slider("Reemplazar neumático al llegar a % restante", 0, 40, 15)
    fuel_margin = st.number_input("Margen combustible por stint (L)", min_value=0.0, max_value=20.0, value=2.0, step=0.5)

inputs = {
    "weather": weather,
    "avg_temp": avg_temp,
    "humidity": humidity,
    "concentration": concentration,
    "aggressiveness": aggressiveness,
    "experience": experience,
    "technical": technical,
    "weight": weight,
    "engine_level": engine_level,
    "electronics_level": electronics_level,
    "suspension_level": suspension_level,
    "ct_risk": ct_risk,
    "tyre_brand": tyre_brand,
    "tyre_type": tyre_type,
    "target_wear": target_wear,
    "fuel_margin": fuel_margin,
}

fuel_l_km = calc_fuel_l_per_km(track, inputs)
fuel_lap = fuel_l_km * track["lap_length"]
tyre_max_km = calc_tyre_max_km(track, inputs)
tyre_max_laps_0 = tyre_max_km / track["lap_length"]
tyre_max_laps_target = tyre_max_laps_0 * (100 - target_wear) / 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vueltas", int(track["laps"]))
c2.metric("Distancia", f'{track["distance"]:.1f} km')
c3.metric("Consumo estimado", f"{fuel_lap:.2f} L/vuelta")
c4.metric("Durabilidad neumático", f"{tyre_max_laps_target:.1f} vueltas útiles")

with st.expander("Datos del circuito", expanded=True):
    st.write(
        {
            "Circuito": track["name"],
            "Downforce": track["downforce"],
            "Overtaking": track["overtaking"],
            "Fuel": track["fuel_label"],
            "Tyre wear": track["tyre_wear_label"],
            "Lap length": track["lap_length"],
            "Pit I/O": track["pit_io"],
            "P/H/A": f'{track["p"]}/{track["h"]}/{track["a"]}',
            "Grip": track["grip"],
        }
    )

tab1, tab2, tab3 = st.tabs(["Estrategia editable", "Comparador automático", "Modelo usado"])

with tab1:
    st.subheader("Stints editables")
    st.write("Modificá las vueltas de cada stint y GPROMIO recalcula combustible y desgaste al instante.")

    total_laps = int(track["laps"])
    stops = st.selectbox("Cantidad de paradas", [0, 1, 2, 3, 4], index=2)
    stints_count = stops + 1

    suggested = [total_laps // stints_count] * stints_count
    for i in range(total_laps % stints_count):
        suggested[i] += 1

    cols = st.columns(stints_count)
    stint_laps = []
    for i in range(stints_count):
        with cols[i]:
            val = st.number_input(
                f"Stint {i+1} vueltas",
                min_value=0,
                max_value=total_laps,
                value=int(suggested[i]),
                step=1,
                key=f"stint_{i}",
            )
            stint_laps.append(int(val))

    strategy = calc_strategy(track, inputs, stint_laps)

    st.warning(f"Vueltas cargadas: {sum(stint_laps)} / {total_laps}") if sum(stint_laps) != total_laps else st.success("La suma de stints coincide con la carrera.")

    df = pd.DataFrame(strategy["stints"])
    st.dataframe(df, use_container_width=True, hide_index=True)

    q2_fuel = strategy["stints"][0]["Combustible recomendado (L)"] if strategy["stints"] else 0
    total_fuel = strategy["total_fuel"]
    worst_tyre = min([s["Neumático final (%)"] for s in strategy["stints"] if isinstance(s["Neumático final (%)"], (int, float))], default=100)

    k1, k2, k3 = st.columns(3)
    k1.metric("Q2 / combustible inicial", f"{q2_fuel:.0f} L")
    k2.metric("Combustible total carrera", f"{total_fuel:.0f} L")
    k3.metric("Peor neumático final", f"{worst_tyre:.1f}%")

    if worst_tyre < 0:
        st.error("Algún stint supera la vida estimada del neumático. Esa estrategia no conviene.")
    elif worst_tyre < 10:
        st.warning("Estrategia riesgosa: quedás con menos de 10% en al menos un stint.")
    elif worst_tyre < 20:
        st.info("Estrategia posible, pero con margen bajo de neumáticos.")
    else:
        st.success("Estrategia segura por neumáticos según este modelo.")

with tab2:
    st.subheader("Comparador automático")
    rows = recommended_strategy_rows(track, inputs, max_stops=4)
    comp = pd.DataFrame(rows)
    st.dataframe(comp, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Qué está calculando")
    st.markdown(
        f"""
**Combustible**

Se usa la lógica del Excel:

`L/km = Fuel 2 Base del circuito + ajuste piloto/auto`

Ajustes considerados:
- Concentración
- Agresividad
- Experiencia
- Conocimiento técnico
- Nivel de motor
- Nivel de electrónica

**Neumáticos**

Se usa la lógica del Excel:

`Km máximos = BaseWear × TyreBaseCircuito × ProductoDeFactores`

Factores considerados:
- Tyre wear del circuito
- Temperatura media
- Marca de neumático
- Compuesto
- Nivel de suspensión
- Agresividad
- Experiencia
- Peso
- CT risk

**Valores actuales**
- Fuel base circuito: `{track["base_l_km_dry"] if weather == "Dry" else track["base_l_km_wet"]:.4f} L/km`
- Fuel final: `{fuel_l_km:.4f} L/km`
- Fuel por vuelta: `{fuel_lap:.2f} L`
- Tyre max hasta 0%: `{tyre_max_laps_0:.1f} vueltas`
- Tyre útil hasta {target_wear}% restante: `{tyre_max_laps_target:.1f} vueltas`
        """
    )

st.caption("Ojo: esto reproduce la lógica del Excel que pasaste, no una fórmula oficial publicada por GPRO.")
