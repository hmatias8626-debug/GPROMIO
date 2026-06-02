import re
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_CALENDARIO = "https://gpro-tools.eu/en/season-calendar"


def _normalizar_lineas(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    texto = soup.get_text("\n", strip=True)
    return [x.strip() for x in texto.splitlines() if x.strip()]


def _valor_despues(lineas: list[str], etiqueta: str, inicio: int, max_salto: int = 4) -> str | None:
    for j in range(inicio, min(len(lineas), inicio + max_salto + 1)):
        if lineas[j].lower() == etiqueta.lower() and j + 1 < len(lineas):
            return lineas[j + 1]
    return None


def _extraer_float(texto: str | None) -> float | None:
    if not texto:
        return None
    m = re.search(r"\d+(?:\.\d+)?", texto.replace(",", "."))
    return float(m.group()) if m else None


def _extraer_laps(texto: str | None) -> tuple[int | None, float | None]:
    if not texto:
        return None, None
    m = re.search(r"(\d+)\s*x\s*(\d+(?:\.\d+)?)", texto)
    if not m:
        return None, None
    return int(m.group(1)), float(m.group(2))


def obtener_calendario() -> list[dict[str, Any]]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GPROMIO/1.0)"}
    r = requests.get(URL_CALENDARIO, headers=headers, timeout=25)
    r.raise_for_status()
    lineas = _normalizar_lineas(r.text)

    circuitos = []
    i = 0
    while i < len(lineas):
        if re.fullmatch(r"#\s*\d+", lineas[i]):
            ronda = int(lineas[i].replace("#", "").strip())
            bloque = lineas[i:i+45]
            track = bloque[1] if len(bloque) > 1 else ""
            country = bloque[3] if len(bloque) > 3 else ""

            date = _valor_despues(bloque, "Date", 0) or ""
            distance = _extraer_float(_valor_despues(bloque, "Distance", 0))
            laps_text = _valor_despues(bloque, "Laps", 0)
            laps, lap_km = _extraer_laps(laps_text)
            avg_speed = _extraer_float(_valor_despues(bloque, "Avg speed", 0))
            corners = _extraer_float(_valor_despues(bloque, "Corners", 0))
            pit_time = _extraer_float(_valor_despues(bloque, "PIT time", 0))
            power = _extraer_float(_valor_despues(bloque, "Power", 0))
            handling = _extraer_float(_valor_despues(bloque, "Handling", 0))
            acceleration = _extraer_float(_valor_despues(bloque, "Acceleration", 0))

            bloque_texto = " ".join(bloque)
            downforce = _buscar_categoria(bloque_texto, "Downforce")
            overtaking = _buscar_categoria(bloque_texto, "Overtaking")
            rigidity = _buscar_categoria(bloque_texto, "Rigidity")
            fuel = _buscar_categoria(bloque_texto, "Fuel consumption")
            tyre = _buscar_categoria(bloque_texto, "Tyre wear")
            grip = _buscar_categoria(bloque_texto, "Grip")

            circuitos.append({
                "round": ronda,
                "track": track,
                "country": country,
                "date": date,
                "distance_km": distance,
                "laps": laps,
                "lap_km": lap_km,
                "avg_speed": avg_speed,
                "corners": int(corners) if corners is not None else None,
                "pit_time_s": pit_time,
                "power": int(power) if power is not None else None,
                "handling": int(handling) if handling is not None else None,
                "acceleration": int(acceleration) if acceleration is not None else None,
                "downforce": downforce,
                "overtaking": overtaking,
                "rigidity": rigidity,
                "fuel": fuel,
                "tyre": tyre,
                "grip": grip,
            })
            i += 1
        i += 1
    return circuitos


def _buscar_categoria(texto: str, etiqueta: str) -> str | None:
    valores = ["Very low", "Low", "Medium", "High", "Very high", "Very easy", "Easy", "Normal", "Hard", "Very hard", "Soft"]
    patron = etiqueta + r"\s+(" + "|".join(re.escape(v) for v in valores) + r")"
    m = re.search(patron, texto, flags=re.IGNORECASE)
    if not m:
        return None
    val = m.group(1)
    # normaliza capitalización
    for v in valores:
        if val.lower() == v.lower():
            return v
    return val


def buscar_circuitos(circuitos: list[dict[str, Any]], texto: str) -> list[dict[str, Any]]:
    q = texto.lower().strip()
    if not q:
        return circuitos
    return [c for c in circuitos if q in str(c.get("track", "")).lower() or q in str(c.get("country", "")).lower()]


def circuito_a_dataframe(circuito: dict[str, Any]) -> pd.DataFrame:
    campos = [
        ("Circuito", circuito.get("track")),
        ("País", circuito.get("country")),
        ("Fecha", circuito.get("date")),
        ("Vueltas", circuito.get("laps")),
        ("Km/vuelta", circuito.get("lap_km")),
        ("Distancia total", circuito.get("distance_km")),
        ("Pit time", circuito.get("pit_time_s")),
        ("Power", circuito.get("power")),
        ("Handling", circuito.get("handling")),
        ("Acceleration", circuito.get("acceleration")),
        ("Consumo", circuito.get("fuel")),
        ("Desgaste neumático", circuito.get("tyre")),
        ("Grip", circuito.get("grip")),
        ("Downforce", circuito.get("downforce")),
        ("Overtaking", circuito.get("overtaking")),
        ("Rigidity", circuito.get("rigidity")),
    ]
    return pd.DataFrame(campos, columns=["Dato", "Valor"])
