from __future__ import annotations

import re
from typing import Dict, Any

import requests
from bs4 import BeautifulSoup

URL_CALENDARIO = "https://gpro-tools.eu/en/season-calendar"

# Fallback para que la app no quede rota si GPRO Tools cambia o no responde.
CIRCUITOS_FALLBACK = {
    "Silverstone": {
        "circuito": "Silverstone",
        "fecha": "02.06.2026",
        "vueltas": 60,
        "km_vuelta": 5.138,
        "distancia_total": 308.3,
        "pit_time": 22.5,
        "power": 11,
        "handling": 11,
        "acceleration": 16,
        "consumo": "High",
        "desgaste_neumatico": "Low",
    }
}


def _numero(texto: str):
    if texto is None:
        return None
    m = re.search(r"-?\d+(?:[\.,]\d+)?", str(texto))
    if not m:
        return None
    valor = m.group(0).replace(",", ".")
    return float(valor) if "." in valor else int(valor)


def obtener_html_calendario(timeout: int = 15) -> str:
    headers = {"User-Agent": "Mozilla/5.0 GPROMIO/1.0"}
    r = requests.get(URL_CALENDARIO, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


def obtener_texto_calendario() -> str:
    html = obtener_html_calendario()
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)


def buscar_circuito_gprotools(nombre: str = "Silverstone") -> Dict[str, Any]:
    """Intenta leer GPRO Tools. Si no encuentra datos completos usa fallback."""
    nombre = (nombre or "Silverstone").strip()
    fallback = CIRCUITOS_FALLBACK.get(nombre, CIRCUITOS_FALLBACK["Silverstone"]).copy()

    try:
        texto = obtener_texto_calendario()
    except Exception:
        fallback["fuente"] = "Fallback local"
        return fallback

    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    idxs = [i for i, l in enumerate(lineas) if nombre.lower() in l.lower()]
    if not idxs:
        fallback["fuente"] = "Fallback local"
        return fallback

    bloque = lineas[max(0, idxs[0] - 10): idxs[0] + 80]
    unido = " | ".join(bloque)

    datos = fallback.copy()
    datos["fuente"] = "GPRO Tools + fallback"

    # Parser flexible: si encuentra valores los pisa; si no, deja fallback.
    patrones = {
        "vueltas": r"(?:laps|vueltas)\D+(\d+)",
        "km_vuelta": r"(?:lap distance|km/lap|km\/vuelta)\D+(\d+(?:[\.,]\d+)?)",
        "distancia_total": r"(?:race distance|distancia total)\D+(\d+(?:[\.,]\d+)?)",
        "pit_time": r"(?:pit time|pit)\D+(\d+(?:[\.,]\d+)?)",
        "power": r"(?:power)\D+(\d+)",
        "handling": r"(?:handling)\D+(\d+)",
        "acceleration": r"(?:acceleration)\D+(\d+)",
    }
    for campo, patron in patrones.items():
        m = re.search(patron, unido, flags=re.I)
        if m:
            datos[campo] = _numero(m.group(1))

    for campo, etiquetas in {
        "consumo": ["Very high", "High", "Medium", "Low", "Very low"],
        "desgaste_neumatico": ["Very high", "High", "Medium", "Low", "Very low"],
    }.items():
        # Conservador: deja fallback si no puede diferenciar.
        pass

    return datos
