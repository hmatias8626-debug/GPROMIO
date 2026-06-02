import json
import math
from pathlib import Path

TYRE_TYPES = ["Extra Soft", "Soft", "Medium", "Hard", "Rain"]
TYRE_BRANDS = ["Pipirelli", "Avonn", "Yokomama", "Dunnolop", "Contimental", "Badyear"]

# Coeficientes extraídos del Excel GPRO Version 6.
FUEL_FACTORS = {
    "concentration": -0.000101165457155397,
    "aggressiveness": 0.0000706080613787091,
    "experience": -0.0000866455021527332,
    "technical": -0.000163915452803369,
    "engine_level": -0.0126912680856842,
    "electronics_level": -0.0083557977071091,
}

TYRE_BASE_WEAR = 129.776458172062

TRACK_WEAR_VALUES = {
    "Very high": 4,
    "Very High": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
    "Very low": 0,
    "Very Low": 0,
}

TYRE_BRAND_DURABILITY = {
    "Pipirelli": 1,
    "Avonn": 8,
    "Yokomama": 3,
    "Dunnolop": 4,
    "Contimental": 8,
    "Badyear": 7,
}

TYRE_TYPE_VALUES = {
    "Extra Soft": 0,
    "Soft": 1,
    "Medium": 2,
    "Hard": 3,
    "Rain": 5,
}

TYRE_FACTORS = {
    "track_wear": 0.896416176238624,
    "avg_temp": 0.988463622,
    "tyre_durability": 1.048876356,
    "tyre_type": 1.355293715,
    "suspension_level": 1.009339294,
    "aggressiveness": 0.999670155,
    "experience": 1.00022936,
    "weight": 0.999858329,
    "ct_risk": None,  # depende del compuesto
}

TYRE_CT_FACTOR_BY_TYPE = {
    "Extra Soft": 0.998163750229071,
    "Soft": 0.997064844817654,
    "Medium": 0.996380346554349,
    "Hard": 0.995862526048112,
    "Rain": 0.996087854384523,
}

PIT_REFUEL_FACTOR = 0.0355393906609645
BASE_PITSTOP = 24.26


def load_tracks():
    path = Path(__file__).parent / "data" / "tracks.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_track(name, tracks=None):
    tracks = tracks or load_tracks()
    for t in tracks:
        if t["name"] == name:
            return t
    raise ValueError(f"No encontré el circuito: {name}")


def calc_fuel_l_per_km(track, inputs):
    """Fuel method 2 del Excel: track base L/km + ajuste por piloto/auto."""
    base = track["base_l_km_wet"] if inputs.get("weather") == "Wet" and track.get("base_l_km_wet") else track["base_l_km_dry"]

    adjustment = (
        FUEL_FACTORS["concentration"] * inputs["concentration"]
        + FUEL_FACTORS["aggressiveness"] * inputs["aggressiveness"]
        + FUEL_FACTORS["experience"] * inputs["experience"]
        + FUEL_FACTORS["technical"] * inputs["technical"]
        + FUEL_FACTORS["engine_level"] * inputs["engine_level"]
        + FUEL_FACTORS["electronics_level"] * inputs["electronics_level"]
    )

    # Evita valores imposibles si el usuario carga algo extremo.
    return max(0.2, base + adjustment)


def calc_tyre_max_km(track, inputs):
    """Replica la estructura de la hoja Tyre&Fuel/Tables para calcular km máximos de neumático."""
    track_wear_val = TRACK_WEAR_VALUES.get(str(track["tyre_wear_label"]), 2)
    tyre_durability = TYRE_BRAND_DURABILITY.get(inputs["tyre_brand"], 1)
    tyre_type_value = TYRE_TYPE_VALUES.get(inputs["tyre_type"], 1)
    ct_factor = TYRE_CT_FACTOR_BY_TYPE.get(inputs["tyre_type"], TYRE_CT_FACTOR_BY_TYPE["Soft"])

    product = (
        TYRE_FACTORS["track_wear"] ** track_wear_val
        * TYRE_FACTORS["avg_temp"] ** inputs["avg_temp"]
        * TYRE_FACTORS["tyre_durability"] ** tyre_durability
        * TYRE_FACTORS["tyre_type"] ** tyre_type_value
        * TYRE_FACTORS["suspension_level"] ** inputs["suspension_level"]
        * TYRE_FACTORS["aggressiveness"] ** inputs["aggressiveness"]
        * TYRE_FACTORS["experience"] ** inputs["experience"]
        * TYRE_FACTORS["weight"] ** inputs["weight"]
        * ct_factor ** inputs["ct_risk"]
    )

    rain_factor = 0.73 if inputs.get("weather") == "Wet" or inputs["tyre_type"] == "Rain" else 1.0
    return TYRE_BASE_WEAR * track["tyre_base"] * product * rain_factor


def calc_pit_time(fuel_liters):
    return fuel_liters * PIT_REFUEL_FACTOR + BASE_PITSTOP


def calc_strategy(track, inputs, stint_laps):
    fuel_l_km = calc_fuel_l_per_km(track, inputs)
    fuel_lap = fuel_l_km * track["lap_length"]
    tyre_max_km = calc_tyre_max_km(track, inputs)

    stints = []
    total_fuel = 0

    for idx, laps in enumerate(stint_laps, start=1):
        km = laps * track["lap_length"]
        fuel_needed = laps * fuel_lap
        fuel_rec = math.ceil(fuel_needed + inputs.get("fuel_margin", 0))
        tyre_used = (km / tyre_max_km) * 100 if tyre_max_km > 0 else 999
        tyre_final = 100 - tyre_used
        pit_time = calc_pit_time(fuel_rec)

        total_fuel += fuel_rec

        if tyre_final < 0:
            estado = "No recomendable"
        elif tyre_final < 10:
            estado = "Riesgoso"
        elif tyre_final < 20:
            estado = "Ajustado"
        else:
            estado = "Seguro"

        stints.append(
            {
                "Stint": idx,
                "Vueltas": laps,
                "Km": round(km, 1),
                "Combustible base (L)": round(fuel_needed, 1),
                "Margen (L)": inputs.get("fuel_margin", 0),
                "Combustible recomendado (L)": fuel_rec,
                "Neumático usado (%)": round(tyre_used, 1),
                "Neumático final (%)": round(tyre_final, 1),
                "Pit refuel est. (s)": round(pit_time, 1),
                "Estado": estado,
            }
        )

    return {
        "stints": stints,
        "total_fuel": total_fuel,
        "fuel_lap": fuel_lap,
        "tyre_max_km": tyre_max_km,
    }


def split_laps(total_laps, parts):
    base = total_laps // parts
    result = [base] * parts
    for i in range(total_laps % parts):
        result[i] += 1
    return result


def recommended_strategy_rows(track, inputs, max_stops=4):
    rows = []
    total_laps = int(track["laps"])

    for stops in range(0, max_stops + 1):
        stints = split_laps(total_laps, stops + 1)
        strat = calc_strategy(track, inputs, stints)
        tyre_finals = [s["Neumático final (%)"] for s in strat["stints"]]
        min_tyre = min(tyre_finals) if tyre_finals else 0
        q2_fuel = strat["stints"][0]["Combustible recomendado (L)"]

        if min_tyre < 0:
            estado = "No recomendable"
        elif min_tyre < 10:
            estado = "Riesgoso"
        elif min_tyre < 20:
            estado = "Ajustado"
        else:
            estado = "Seguro"

        rows.append(
            {
                "Paradas": stops,
                "Stints": " + ".join(str(x) for x in stints),
                "Q2 / salida (L)": q2_fuel,
                "Fuel total (L)": strat["total_fuel"],
                "Peor final neumático (%)": round(min_tyre, 1),
                "Estado": estado,
            }
        )

    return rows
