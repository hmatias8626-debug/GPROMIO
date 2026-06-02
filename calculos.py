from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


CONSUMO_BASE = {
    "Very low": 1.65,
    "Low": 1.95,
    "Medium": 2.25,
    "High": 2.60,
    "Very high": 2.95,
}

DESGASTE_BASE = {
    "Very low": 0.55,
    "Low": 0.75,
    "Medium": 1.00,
    "High": 1.30,
    "Very high": 1.65,
}

COMPUESTO_FACTOR = {
    "Extra blando": 1.28,
    "Blando": 1.08,
    "Medio": 0.92,
    "Duro": 0.78,
    "Lluvia": 1.00,
}


def clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def estimar_consumo_litros_vuelta(
    consumo_circuito: str,
    motor_nivel: int,
    electronica_nivel: int,
    temp_promedio: float,
    riesgo_pista_limpia: int,
    riesgo_adelantar: int,
    riesgo_defender: int,
    ajuste_manual: float = 0.0,
) -> float:
    """Estimación editable. No replica fórmulas privadas de GPRO Tools.

    La base sale de la categoría pública del circuito y se corrige con inputs del usuario.
    """
    base = CONSUMO_BASE.get(consumo_circuito, 2.25)

    # Motor/electrónica: ajustes suaves para no disparar valores.
    factor_motor = 1 + ((motor_nivel - 1) * 0.015)
    factor_electronica = 1 - ((electronica_nivel - 1) * 0.006)

    # Riesgos: cuanto más agresivo, un poco más de consumo.
    riesgo_total = (riesgo_pista_limpia * 0.0025) + (riesgo_adelantar * 0.0015) + (riesgo_defender * 0.0012)
    factor_riesgo = 1 + riesgo_total

    # Temperatura: efecto leve.
    factor_temp = 1 + ((temp_promedio - 20) * 0.002)

    consumo = base * factor_motor * factor_electronica * factor_riesgo * factor_temp
    consumo += ajuste_manual
    return round(max(0.1, consumo), 3)


def estimar_desgaste_neumatico_vuelta(
    desgaste_circuito: str,
    compuesto: str,
    temp_promedio: float,
    riesgo_pista_limpia: int,
    riesgo_adelantar: int,
    riesgo_defender: int,
    suspension_nivel: int,
    experiencia_piloto: int,
    ajuste_manual: float = 0.0,
) -> float:
    """Devuelve % de neumático gastado por vuelta.

    Es un modelo editable para estrategia, calibrable con historial real.
    """
    base = DESGASTE_BASE.get(desgaste_circuito, 1.0)
    factor_compuesto = COMPUESTO_FACTOR.get(compuesto, 1.0)

    # Más temperatura = más desgaste. Por debajo de 20 baja un poco.
    factor_temp = 1 + ((temp_promedio - 20) * 0.010)
    factor_temp = clamp(factor_temp, 0.75, 1.35)

    riesgo_total = (riesgo_pista_limpia * 0.0045) + (riesgo_adelantar * 0.0020) + (riesgo_defender * 0.0018)
    factor_riesgo = 1 + riesgo_total

    # Suspensión y experiencia corrigen suave.
    factor_susp = 1 - ((suspension_nivel - 1) * 0.018)
    factor_exp = 1 - (min(experiencia_piloto, 250) * 0.00045)

    desgaste = base * factor_compuesto * factor_temp * factor_riesgo * factor_susp * factor_exp
    desgaste += ajuste_manual
    return round(max(0.05, desgaste), 3)


def repartir_vueltas(vueltas_totales: int, paradas: int) -> List[int]:
    stints = paradas + 1
    base = vueltas_totales // stints
    resto = vueltas_totales % stints
    return [base + (1 if i < resto else 0) for i in range(stints)]


def calcular_estrategia(
    vueltas_totales: int,
    paradas: int,
    consumo_l_vuelta: float,
    desgaste_pct_vuelta: float,
    margen_litros: float,
    neumatico_inicial_pct: float = 100.0,
    vueltas_personalizadas: List[int] | None = None,
) -> Dict[str, Any]:
    if vueltas_personalizadas and sum(vueltas_personalizadas) > 0:
        vueltas_stints = [int(v) for v in vueltas_personalizadas if int(v) > 0]
    else:
        vueltas_stints = repartir_vueltas(vueltas_totales, paradas)

    filas = []
    for i, vueltas in enumerate(vueltas_stints, start=1):
        combustible = (vueltas * consumo_l_vuelta) + margen_litros
        desgaste = vueltas * desgaste_pct_vuelta
        restante = neumatico_inicial_pct - desgaste
        restante = round(max(0, restante), 1)

        if restante >= 25:
            estado = "Seguro"
        elif restante >= 12:
            estado = "Riesgoso"
        else:
            estado = "Crítico"

        filas.append({
            "Stint": i,
            "Vueltas": vueltas,
            "Combustible a cargar (L)": round(combustible, 1),
            "Desgaste estimado (%)": round(desgaste, 1),
            "Neumático restante (%)": restante,
            "Estado neumático": estado,
        })

    return {
        "vueltas_stints": vueltas_stints,
        "filas": filas,
        "q2_litros": filas[0]["Combustible a cargar (L)"] if filas else 0,
        "total_litros": round(sum(f["Combustible a cargar (L)"] for f in filas), 1),
    }
