
import streamlit as st
import pandas as pd
from calculos import (
    get_track, track_summary, fuel_per_lap, tyre_max_laps, stint_rows,
    auto_split_laps, strategy_comparison, setup_calc, parts_wear
)

st.set_page_config(page_title="GPROMIO", page_icon="🏎️", layout="wide")

@st.cache_data
def load_tracks():
    return pd.read_csv("data/tracks.csv")

tracks_df = load_tracks()
track_names = tracks_df["Name"].dropna().astype(str).tolist()

st.sidebar.title("GPROMIO")
track_name = st.sidebar.selectbox("Circuito", track_names, index=track_names.index("Silverstone") if "Silverstone" in track_names else 0)
track = get_track(tracks_df, track_name)

st.sidebar.header("Piloto")
driver = {
    "concentration": st.sidebar.number_input("Concentración", 0, 250, 81),
    "talent": st.sidebar.number_input("Talento", 0, 250, 27),
    "aggressiveness": st.sidebar.number_input("Agresividad", 0, 250, 151),
    "experience": st.sidebar.number_input("Experiencia", 0, 250, 29),
    "technical": st.sidebar.number_input("Conocimiento técnico", 0, 250, 136),
    "weight": st.sidebar.number_input("Peso", 40, 120, 77),
}

st.sidebar.header("Auto")
parts = ["chassis","engine","front_wing","rear_wing","underbody","sidepods","cooling","gearbox","brakes","suspension","electronics"]
labels = {"chassis":"Chasis","engine":"Motor","front_wing":"Alerón delantero","rear_wing":"Alerón trasero","underbody":"Fondo plano","sidepods":"Pontones","cooling":"Refrigeración","gearbox":"Caja","brakes":"Frenos","suspension":"Suspensión","electronics":"Electrónica"}
levels = {}
wears = {}
with st.sidebar.expander("Niveles y uso de piezas", expanded=False):
    for p in parts:
        c1,c2=st.columns(2)
        levels[p] = c1.number_input(f"Nivel {labels[p]}",1,9,3 if p=="engine" else 2,key=f"lvl_{p}")
        wears[p] = c2.number_input(f"Uso % {labels[p]}",0,99,31 if p=="gearbox" else 0,key=f"wear_{p}")
car = {"engine":levels["engine"],"electronics":levels["electronics"],"suspension":levels["suspension"]}

st.sidebar.header("Clima / Riesgos")
weather = st.sidebar.selectbox("Clima", ["Dry", "Wet"], index=0)
avg_temp = st.sidebar.number_input("Temperatura media", -20, 60, 17)
humidity = st.sidebar.number_input("Humedad media", 0, 100, 25)
ct_risk = st.sidebar.number_input("Riesgo CT", 0, 100, 0)
tyre_replace_at = st.sidebar.slider("Cambiar neumático al llegar a % restante",0,60,15)
margin_l = st.sidebar.number_input("Margen combustible por stint (L)",0.0,20.0,2.0,0.5)

st.sidebar.header("Neumáticos")
brand = st.sidebar.selectbox("Marca", ["Pipirelli","Avonn","Yokomama","Dunnolop","Contimental","Badyear"])
compound = st.sidebar.selectbox("Compuesto", ["Extra Soft","Soft","Medium","Hard","Rain"], index=1)

st.title("🏎️ GPROMIO - Estrategia GPRO")
st.caption("Basado en las fórmulas/tablas del Excel GPRO Version 6 que pasaste. No es fórmula oficial publicada por GPRO.")

col1,col2,col3,col4=st.columns(4)
col1.metric("Vueltas", int(track.get("Laps")))
col2.metric("Distancia", f'{float(track.get("Distance")):.1f} km')
col3.metric("Consumo", f'{fuel_per_lap(track, driver, car, weather):.2f} L/vuelta')
col4.metric("Durabilidad neumático", f'{tyre_max_laps(track, driver, car, brand, compound, avg_temp, ct_risk, weather):.1f} vueltas útiles')

menu = st.tabs(["🏁 Circuito", "🔧 Setup", "⛽ Estrategia", "🛞 Neumáticos", "🧩 Piezas", "📊 Comparador", "📚 Modelo"])

with menu[0]:
    st.subheader("Datos del circuito")
    st.dataframe(pd.DataFrame(track_summary(track).items(), columns=["Dato","Valor"]), use_container_width=True, hide_index=True)
    with st.expander("Ver fila completa del circuito"):
        st.json({k:(None if pd.isna(v) else v) for k,v in track.items()})

with menu[1]:
    st.subheader("Setup recomendado")
    st.write("Calculado desde bases del circuito + temperatura + piloto + niveles/uso del auto.")
    setup_df=setup_calc(track, driver, levels, wears, avg_temp, humidity, weather)
    st.dataframe(setup_df, use_container_width=True, hide_index=True)
    st.info("Usalo como punto de partida. En práctica ajustá con los comentarios del piloto.")

with menu[2]:
    st.subheader("Stints editables")
    total_laps=int(track.get("Laps"))
    stops=st.selectbox("Cantidad de paradas", [0,1,2,3,4], index=2)
    default_laps=auto_split_laps(total_laps, stops)
    cols=st.columns(5)
    stint_laps=[]
    for i in range(5):
        default=default_laps[i] if i < len(default_laps) else 0
        stint_laps.append(cols[i].number_input(f"Stint {i+1} vueltas",0,total_laps,default,key=f"stint_{i}"))
    loaded=sum(stint_laps)
    if loaded == total_laps:
        st.success("La suma de stints coincide con la carrera.")
    else:
        st.warning(f"Vueltas cargadas: {loaded} / {total_laps}")
    rows=stint_rows(track, driver, car, stint_laps, brand, compound, avg_temp, ct_risk, weather, margin_l, tyre_replace_at)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if rows:
        c1,c2,c3=st.columns(3)
        c1.metric("Q2 / combustible inicial", f'{rows[0]["Combustible recomendado (L)"]} L')
        c2.metric("Combustible total carrera", f'{sum(r["Combustible recomendado (L)"] for r in rows)} L')
        c3.metric("Peor neumático final", f'{min(r["Neumático final (%)"] for r in rows):.1f}%')

with menu[3]:
    st.subheader("Cálculo de neumáticos")
    max_laps=tyre_max_laps(track, driver, car, brand, compound, avg_temp, ct_risk, weather)
    max_km=max_laps*float(track.get("Lap Length"))
    st.metric("Durabilidad estimada", f"{max_laps:.1f} vueltas / {max_km:.1f} km")
    test_laps=st.slider("Probar stint de vueltas",1,int(track.get("Laps")),min(20,int(track.get("Laps"))))
    rows=stint_rows(track, driver, car, [test_laps], brand, compound, avg_temp, ct_risk, weather, margin_l, tyre_replace_at)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with menu[4]:
    st.subheader("Desgaste estimado de piezas")
    pw=parts_wear(track, driver, levels, wears, ct_risk)
    st.dataframe(pd.DataFrame(pw), use_container_width=True, hide_index=True)

with menu[5]:
    st.subheader("Comparador automático de estrategias")
    comp=strategy_comparison(track, driver, car, brand, compound, avg_temp, ct_risk, weather, margin_l, tyre_replace_at, 4)
    st.dataframe(pd.DataFrame(comp), use_container_width=True, hide_index=True)

with menu[6]:
    st.subheader("Qué replica esta versión")
    st.markdown("""
    - **Tracks:** datos completos del circuito desde la hoja `Tracks`.
    - **Fuel:** usa `L/km` + ajuste por concentración, agresividad, experiencia, técnica, motor y electrónica.
    - **Tyres:** usa `Wear Base`, compuesto, marca, temperatura, suspensión, agresividad, experiencia, peso y riesgo CT.
    - **Setup:** usa bases de pista, clima, piloto, niveles y desgaste del auto.
    - **Parts wear:** usa base de desgaste de pista, nivel de pieza, riesgo CT y factores del piloto.

    Si algo no coincide con el Excel, lo ajustamos celda por celda, pero esta versión ya no tiene el bug que imprimía objetos internos de Streamlit.
    """)
