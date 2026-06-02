import re
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_CALENDARIO = "https://gpro-tools.eu/en/season-calendar"

# Fallback mínimo para que la app no quede con None si GPRO Tools cambia el HTML
# o Streamlit no puede leer toda la página. Lo vamos ampliando con cada carrera.
FALLBACK_CIRCUITOS = {
    "silverstone": {
        "round": 16,
        "track": "Silverstone",
        "country": "United Kingdom",
        "date": "02.06.2026",
        "distance_km": 308.3,
        "laps": 60,
        "lap_km": 5.138,
        "avg_speed": 225.46,
        "corners": 14,
        "pit_time_s": 22.5,
        "power": 11,
        "handling": 11,
        "acceleration": 16,
        "downforce": "Low",
        "overtaking": "Normal",
        "rigidity": "Medium",
        "fuel": "High",
        "tyre": "Low",
        "grip": "Medium",
    },
}


def _normalizar_texto(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    texto = soup.get_text("\n", strip=True)
    # Compacta espacios pero conserva saltos para separar bloques.
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{2,}", "\n", texto)
    return texto.strip()


def _compactar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def _extraer_num(label: str, texto: str, entero: bool = False) -> int | float | None:
    # Soporta: "Distance 308.3", "PIT time 22.5 s", etc.
    patron = rf"{re.escape(label)}\s+(-?\d+(?:[\.,]\d+)?)"
    m = re.search(patron, texto, flags=re.IGNORECASE)
    if not m:
        return None
    valor = float(m.group(1).replace(",", "."))
    return int(valor) if entero else valor


def _extraer_laps(texto: str) -> tuple[int | None, float | None]:
    m = re.search(r"Laps\s+(\d+)\s*x\s*(\d+(?:[\.,]\d+)?)", texto, flags=re.IGNORECASE)
    if not m:
        return None, None
    return int(m.group(1)), float(m.group(2).replace(",", "."))


def _extraer_categoria(label: str, texto: str) -> str | None:
    valores = [
        "Very low", "Low", "Medium", "High", "Very high",
        "Very easy", "Easy", "Normal", "Hard", "Very hard", "Soft",
    ]
    patron = rf"{re.escape(label)}\s+({'|'.join(re.escape(v) for v in valores)})"
    m = re.search(patron, texto, flags=re.IGNORECASE)
    if not m:
        return None
    encontrado = m.group(1).lower()
    for v in valores:
        if v.lower() == encontrado:
            return v
    return m.group(1)


def _extraer_texto_despues(label: str, texto: str) -> str:
    patron = rf"{re.escape(label)}\s+([^\n]+)"
    m = re.search(patron, texto, flags=re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _parsear_bloque(bloque: str) -> dict[str, Any] | None:
    lineas = [x.strip() for x in bloque.splitlines() if x.strip()]
    if not lineas:
        return None

    # Ronda
    m_round = re.match(r"#\s*(\d+|Test)", lineas[0], flags=re.IGNORECASE)
    if not m_round:
        return None
    ronda_txt = m_round.group(1)
    ronda = int(ronda_txt) if ronda_txt.isdigit() else ronda_txt

    # En el calendario de GPRO Tools, el nombre suele venir en la línea siguiente.
    track = lineas[1] if len(lineas) > 1 else ""

    # País: suele aparecer antes de la palabra GPRO.
    country = ""
    for idx, linea in enumerate(lineas):
        if linea.upper() == "GPRO" and idx > 0:
            country = lineas[idx - 1]
            break

    compacto = _compactar(bloque)
    laps, lap_km = _extraer_laps(compacto)

    return {
        "round": ronda,
        "track": track,
        "country": country,
        "date": _extraer_texto_despues("Date", compacto),
        "distance_km": _extraer_num("Distance", compacto),
        "laps": laps,
        "lap_km": lap_km,
        "avg_speed": _extraer_num("Avg speed", compacto),
        "corners": _extraer_num("Corners", compacto, entero=True),
        "pit_time_s": _extraer_num("PIT time", compacto),
        "power": _extraer_num("Power", compacto, entero=True),
        "handling": _extraer_num("Handling", compacto, entero=True),
        "acceleration": _extraer_num("Acceleration", compacto, entero=True),
        "downforce": _extraer_categoria("Downforce", compacto),
        "overtaking": _extraer_categoria("Overtaking", compacto),
        "rigidity": _extraer_categoria("Rigidity", compacto),
        "fuel": _extraer_categoria("Fuel consumption", compacto),
        "tyre": _extraer_categoria("Tyre wear", compacto),
        "grip": _extraer_categoria("Grip", compacto),
    }


def _completar_con_fallback(circuito: dict[str, Any]) -> dict[str, Any]:
    clave = str(circuito.get("track", "")).lower().strip()
    fallback = FALLBACK_CIRCUITOS.get(clave)
    if not fallback:
        return circuito
    completo = dict(fallback)
    for k, v in circuito.items():
        if v not in (None, ""):
            completo[k] = v
    return completo


def obtener_calendario() -> list[dict[str, Any]]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GPROMIO/1.0)"}
    r = requests.get(URL_CALENDARIO, headers=headers, timeout=25)
    r.raise_for_status()

    texto = _normalizar_texto(r.text)

    # Separa desde cada "# 1", "# 2", etc. hasta el próximo #.
    matches = list(re.finditer(r"(?m)^#\s*(?:\d+|Test)\s*$", texto))
    circuitos: list[dict[str, Any]] = []

    for idx, match in enumerate(matches):
        inicio = match.start()
        fin = matches[idx + 1].start() if idx + 1 < len(matches) else len(texto)
        bloque = texto[inicio:fin]
        circuito = _parsear_bloque(bloque)
        if circuito and circuito.get("track"):
            circuitos.append(_completar_con_fallback(circuito))

    # Si por algún cambio de web no salió nada, al menos devolvemos la base local.
    if not circuitos:
        return list(FALLBACK_CIRCUITOS.values())

    return circuitos


def buscar_circuitos(circuitos: list[dict[str, Any]], texto: str) -> list[dict[str, Any]]:
    q = texto.lower().strip()
    if not q:
        return circuitos
    encontrados = [
        c for c in circuitos
        if q in str(c.get("track", "")).lower() or q in str(c.get("country", "")).lower()
    ]
    if not encontrados and q in FALLBACK_CIRCUITOS:
        encontrados = [FALLBACK_CIRCUITOS[q]]
    return encontrados


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
