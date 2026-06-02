
import math
import pandas as pd

TRACK_COLS = {
    "name": "Name", "downforce": "Downforce", "overtaking": "Overtaking", "suspension": "Suspension",
    "fuel_label": "Fuel (5)", "tyre_label": "Tyre Wear", "lap_length": "Lap Length", "laps": "Laps",
    "distance": "Distance", "power": "P (10)", "handling": "H", "acceleration": "A",
    "avg_speed": "Avg. Speed", "corners": "Corners (15)", "pit_io": "Pit I/O", "grip": "Grip",
    "base_wings": "Wings (19)", "base_engine": "Engine", "base_brakes": "Brakes", "base_gear": "Gear",
    "base_suspension": "Suspension.1", "wing_split": "WS (25)", "lpkm_dry": "L/km (27)",
    "lpkm_wet": "L/km (wet)", "tyre_wear_base": "Wear (30)",
    "parts_cha": "Cha (32)", "parts_eng": "Eng", "parts_fw": "FW", "parts_rw": "RW",
    "parts_und": "UndB", "parts_sid": "SidP", "parts_coo": "Coo", "parts_gea": "GeaB",
    "parts_bra": "Bra", "parts_sus": "Sus", "parts_ele": "Ele",
}

TYRE_TYPE_INDEX = {"Extra Soft": 0, "Soft": 1, "Medium": 2, "Hard": 3, "Rain": 5}
TYRE_TYPE_BASE = {"Extra Soft": 0.7330345587439847, "Soft": 0.9934771303435207, "Medium": 1.3464533107508094, "Hard": 1.8248397096015139, "Rain": 3.351903998622584}
TYRE_CT_FACTOR = {"Extra Soft": 0.998163750229071, "Soft": 0.997064844817654, "Medium": 0.996380346554349, "Hard": 0.995862526048112, "Rain": 0.996087854384523}
TYRE_BRAND_DURABILITY = {"Pipirelli": 1, "Avonn": 8, "Yokomama": 3, "Dunnolop": 4, "Contimental": 8, "Badyear": 7}

# Tabla del Excel: Tyre Wear Calculation, rows 74-79
WEAR_BASE = 129.776458172062
WEAR_FACTORS = {
    "trk_wear": 0.896416176238624,
    "avg_temp": 0.988463622,
    "tyre_durability": 1.048876356,
    "tyre_type": 1.355293715,
    "suspension_lvl": 1.009339294,
    "aggressiveness": 0.999670155,
    "experience": 1.00022936,
    "weight": 0.999858329,
}

FUEL_FACTORS = {
    "concentration": -0.000101165457155397,
    "aggressiveness": 0.0000706080613787091,
    "experience": -0.0000866455021527332,
    "technical": -0.000163915452803369,
    "engine_level": -0.0126912680856842,
    "electronics_level": -0.0083557977071091,
}

PIT = {
    "fuel_tanked": 0.0355393906609645,
    "staff_concentration": -0.0797977676868435,
    "staff_stress": 0,
    "td_experience": 0,
    "td_pit_coordination": 0,
    "base": 24.26,
}

PART_RISK_FACTOR_BY_LEVEL = {1:1.01932679359883,2:1.00995581572653,3:1.00732616184961,4:1.00531414480549,5:1.00432686358572,6:1.00366691368852,7:1.00430482472465,8:1.00969001182737,9:1.00515195539175}
PART_DRIVER_FACTOR_BASE = {"concentration":0.998789138,"talent":0.998751839,"experience":0.998707677}

SETUP_WEATHER_DRY = {"wings": 6, "engine": -3, "brakes": 6, "gear": -4, "suspension": -6}
SETUP_WEATHER_WET = {
    "wings": (1, 263), "engine": (0.7, -190), "brakes": (3.9883754414027, 105.532592432347),
    "gear": (-8.01996418151657, -4.74271170354302), "suspension": (-1, -257),
}
CAR_LEVEL_COEFF = {
    "wings": {"chassis": -19.74, "front_wing": 30.03, "rear_wing": 30.03, "underbody": -15.07},
    "engine": {"engine": 16.04, "cooling": 4.9, "electronics": 3.34},
    "brakes": {"chassis": 6.04, "brakes": -29.14, "electronics": 6.11},
    "gear": {"gearbox": -41, "electronics": 9},
    "suspension": {"chassis": -15.27, "underbody": -10.72, "sidepods": 6.03, "suspension": 31},
}
CAR_WEAR_COEFF = {
    "wings": {"chassis": 0.47, "front_wing": -0.59, "rear_wing": -0.59, "underbody": 0.32},
    "engine": {"engine": -0.51, "cooling": -0.09, "electronics": -0.04},
    "brakes": {"chassis": -0.14, "brakes": 0.71, "electronics": -0.09},
    "gear": {"gearbox": 1.09, "electronics": -0.14},
    "suspension": {"chassis": 0.34, "underbody": 0.23, "sidepods": -0.12, "suspension": -0.7},
}

def _num(v, default=0.0):
    try:
        if pd.isna(v): return default
        return float(v)
    except Exception:
        return default

def clamp(value, low=1, high=999):
    return max(low, min(high, value))

def get_track(df, name):
    m = df[df["Name"].astype(str).str.lower() == str(name).lower()]
    if m.empty:
        m = df[df["Name"].astype(str).str.contains(str(name), case=False, na=False)]
    if m.empty:
        return None
    return m.iloc[0].to_dict()

def track_summary(track):
    return {
        "Circuito": track.get("Name"), "Downforce": track.get("Downforce"), "Overtaking": track.get("Overtaking"),
        "Fuel": track.get("Fuel (5)"), "Tyre wear": track.get("Tyre Wear"), "Lap length": track.get("Lap Length"),
        "Laps": int(_num(track.get("Laps"))), "Distance": track.get("Distance"), "Pit I/O": track.get("Pit I/O"),
        "P/H/A": f'{track.get("P (10)")}/{track.get("H")}/{track.get("A")}', "Grip": track.get("Grip"),
    }

def fuel_lpkm(track, driver, car, weather="Dry"):
    base = _num(track.get("L/km (wet)" if weather == "Wet" else "L/km (27)"))
    adj = (
        FUEL_FACTORS["concentration"] * driver.get("concentration", 0) +
        FUEL_FACTORS["aggressiveness"] * driver.get("aggressiveness", 0) +
        FUEL_FACTORS["experience"] * driver.get("experience", 0) +
        FUEL_FACTORS["technical"] * driver.get("technical", 0) +
        FUEL_FACTORS["engine_level"] * car.get("engine", 1) +
        FUEL_FACTORS["electronics_level"] * car.get("electronics", 1)
    )
    return max(0.1, base + adj)

def fuel_per_lap(track, driver, car, weather="Dry"):
    return fuel_lpkm(track, driver, car, weather) * _num(track.get("Lap Length"))

def tyre_max_km(track, driver, car, brand="Pipirelli", compound="Soft", avg_temp=20, ct_risk=0, weather="Dry"):
    trk_wear = _num(track.get("Wear (30)"), 1)
    tyre_dur = TYRE_BRAND_DURABILITY.get(brand, 1)
    ttype = TYRE_TYPE_INDEX.get(compound, 1)
    # Excel: product(factor^value) * track_wear_base * base_wear * rain_factor
    k79 = (
        WEAR_FACTORS["trk_wear"] ** trk_wear *
        WEAR_FACTORS["avg_temp"] ** avg_temp *
        WEAR_FACTORS["tyre_durability"] ** tyre_dur *
        WEAR_FACTORS["tyre_type"] ** ttype *
        WEAR_FACTORS["suspension_lvl"] ** car.get("suspension", 1) *
        WEAR_FACTORS["aggressiveness"] ** driver.get("aggressiveness", 0) *
        WEAR_FACTORS["experience"] ** driver.get("experience", 0) *
        WEAR_FACTORS["weight"] ** driver.get("weight", 75) *
        TYRE_CT_FACTOR.get(compound, TYRE_CT_FACTOR["Soft"]) ** ct_risk
    )
    rain_factor = 0.73 if compound == "Rain" or weather == "Wet" else 1
    return max(1, k79 * trk_wear * WEAR_BASE * rain_factor)

def tyre_max_laps(track, driver, car, brand, compound, avg_temp, ct_risk, weather="Dry"):
    return tyre_max_km(track, driver, car, brand, compound, avg_temp, ct_risk, weather) / _num(track.get("Lap Length"), 1)

def stint_rows(track, driver, car, stint_laps, brand, compound, avg_temp, ct_risk, weather, margin_l=2, tyre_replace_at=15):
    lap_km = _num(track.get("Lap Length"), 1)
    lpkm = fuel_lpkm(track, driver, car, weather)
    max_km = tyre_max_km(track, driver, car, brand, compound, avg_temp, ct_risk, weather)
    rows=[]
    for i,laps in enumerate(stint_laps, 1):
        if laps <= 0: continue
        km = laps * lap_km
        fuel_base = math.ceil(laps * lpkm * lap_km)
        tyre_used = min(999, km * 100 / max_km)
        tyre_final = 100 - tyre_used
        status = "Seguro" if tyre_final >= tyre_replace_at else ("Riesgoso" if tyre_final > 0 else "No llega")
        pit_time = fuel_base * PIT["fuel_tanked"] + PIT["base"]
        rows.append({
            "Stint": i, "Vueltas": int(laps), "Km": round(km,1), "Combustible base (L)": fuel_base,
            "Margen (L)": margin_l, "Combustible recomendado (L)": math.ceil(fuel_base + margin_l),
            "Neumático usado (%)": round(tyre_used,1), "Neumático final (%)": round(tyre_final,1),
            "Pit refuel est. (s)": round(pit_time,1), "Estado": status
        })
    return rows

def auto_split_laps(total_laps, stops):
    stints = stops + 1
    base = total_laps // stints
    rem = total_laps % stints
    return [base + (1 if i < rem else 0) for i in range(stints)]

def strategy_comparison(track, driver, car, brand, compound, avg_temp, ct_risk, weather, margin_l, tyre_replace_at, max_stops=4):
    total_laps = int(_num(track.get("Laps")))
    res=[]
    for stops in range(max_stops+1):
        laps=auto_split_laps(total_laps, stops)
        rows=stint_rows(track, driver, car, laps, brand, compound, avg_temp, ct_risk, weather, margin_l, tyre_replace_at)
        worst=min([r["Neumático final (%)"] for r in rows]) if rows else 0
        q2=rows[0]["Combustible recomendado (L)"] if rows else 0
        total=sum(r["Combustible recomendado (L)"] for r in rows)
        status="OK" if worst>=tyre_replace_at else ("Riesgoso" if worst>0 else "No llega")
        res.append({"Paradas": stops, "Stints": " + ".join(map(str,laps)), "Q2 / inicial (L)": q2, "Combustible total (L)": total, "Peor neumático final (%)": round(worst,1), "Estado": status})
    return res

def _car_adj(kind, levels, wears):
    total=0
    for part,coef in CAR_LEVEL_COEFF[kind].items(): total += levels.get(part,1) * coef
    for part,coef in CAR_WEAR_COEFF[kind].items(): total += wears.get(part,0) * coef
    return total

def _weather_adj(kind, temp, weather):
    if weather == "Wet":
        mult, off = SETUP_WEATHER_WET[kind]
        return mult * temp + off
    return SETUP_WEATHER_DRY[kind] * temp

def setup_calc(track, driver, levels, wears, temp=18, hum=25, weather="Dry"):
    oval = 0.39 if str(track.get("Name")) == "Indianapolis Oval" else 1
    base_w = _num(track.get("Wings (19)"))*2
    base_e = _num(track.get("Engine"))
    base_b = _num(track.get("Brakes"))
    base_g = _num(track.get("Gear"))
    base_s = _num(track.get("Suspension.1"))
    xw = _weather_adj("wings", temp, weather)*2 if False else _weather_adj("wings", temp, weather)
    # Excel doubles wings base and weather before averaging.
    w_weather = _weather_adj("wings", temp, weather) * 2
    e_weather = _weather_adj("engine", temp, weather)
    b_weather = _weather_adj("brakes", temp, weather)
    g_weather = _weather_adj("gear", temp, weather)
    s_weather = _weather_adj("suspension", temp, weather)
    talent = driver.get("talent",0)
    exp = driver.get("experience",0)
    conc = driver.get("concentration",0)
    aggr = driver.get("aggressiveness",0)
    weight = driver.get("weight",75)
    drv_w = talent * math.floor(base_w + w_weather) * (-0.001349079032746) * oval
    drv_e = (29.521804804429003 + exp * ((base_e + e_weather)*0.001655723 + 0.0469416263186552)) * oval
    drv_b = -49.8
    drv_g = 50
    drv_s = 275
    adj_w=_car_adj("wings", levels, wears)
    adj_e=_car_adj("engine", levels, wears)
    adj_b=_car_adj("brakes", levels, wears)
    adj_g=_car_adj("gear", levels, wears)
    adj_s=_car_adj("suspension", levels, wears)
    wings_mid=(base_w + w_weather + drv_w + adj_w)/2
    engine=base_e + e_weather + drv_e + adj_e
    brakes=base_b + b_weather + drv_b + adj_b
    gear=base_g + g_weather + drv_g + adj_g
    susp=base_s + s_weather + drv_s + adj_s
    ws = (_num(track.get("WS (25)")) + talent*-0.246534498671854 + 3.69107049712848*(levels.get("front_wing",1)+levels.get("rear_wing",1))/2 + wings_mid*-0.189968386659174 + temp*0.376337780506523 + (58.8818967363256 if weather=="Wet" else 0))
    fw = wings_mid + ws
    rw = wings_mid - ws
    return pd.DataFrame([
        {"Setup": "Alerón delantero", "Valor recomendado": int(round(clamp(fw,1,999)))},
        {"Setup": "Alerón trasero", "Valor recomendado": int(round(clamp(rw,1,999)))},
        {"Setup": "Motor", "Valor recomendado": int(round(clamp(engine,1,999)))},
        {"Setup": "Frenos", "Valor recomendado": int(round(clamp(brakes,1,999)))},
        {"Setup": "Caja", "Valor recomendado": int(round(clamp(gear,1,999)))},
        {"Setup": "Suspensión", "Valor recomendado": int(round(clamp(susp,1,999)))}
    ])

def parts_wear(track, driver, levels, current_wear, ct_risk):
    base_key={"chassis":"Cha (32)","engine":"Eng","front_wing":"FW","rear_wing":"RW","underbody":"UndB","sidepods":"SidP","cooling":"Coo","gearbox":"GeaB","brakes":"Bra","suspension":"Sus","electronics":"Ele"}
    names={"chassis":"Chasis","engine":"Motor","front_wing":"Alerón delantero","rear_wing":"Alerón trasero","underbody":"Fondo plano","sidepods":"Pontones","cooling":"Refrigeración","gearbox":"Caja","brakes":"Frenos","suspension":"Suspensión","electronics":"Electrónica"}
    driver_factor=(PART_DRIVER_FACTOR_BASE["concentration"]**driver.get("concentration",0))*(PART_DRIVER_FACTOR_BASE["talent"]**driver.get("talent",0))*(PART_DRIVER_FACTOR_BASE["experience"]**driver.get("experience",0))
    rows=[]
    for part,col in base_key.items():
        lvl=int(levels.get(part,1))
        risk_factor=PART_RISK_FACTOR_BY_LEVEL.get(lvl,1.005)**ct_risk
        est=_num(track.get(col))*risk_factor*driver_factor
        start=current_wear.get(part,0)
        end=start+est
        rows.append({"Pieza":names[part],"Nivel":lvl,"Uso actual %":round(start,1),"Desgaste estimado %":round(est,1),"Uso final %":round(end,1),"Estado":"Cambiar pronto" if end>=90 else "OK"})
    return rows
