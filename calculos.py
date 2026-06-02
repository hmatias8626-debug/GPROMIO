def repartir_stints(vueltas: int, paradas: int) -> list[int]:
    """Devuelve vueltas por stint. Paradas 1 => 2 stints."""
    stints = paradas + 1
    base = vueltas // stints
    resto = vueltas % stints
    return [base + (1 if i < resto else 0) for i in range(stints)]


def calcular_estrategia_combustible(vueltas: int, litros_vuelta: float, paradas: int, margen: float) -> dict:
    stints = repartir_stints(vueltas, paradas)
    combustible_total = round((vueltas * litros_vuelta) + margen, 1)
    q2_litros = round((stints[0] * litros_vuelta) + margen, 1)
    return {
        "vueltas": vueltas,
        "paradas": paradas,
        "stints": stints,
        "combustible_total": combustible_total,
        "q2_litros": q2_litros,
    }


def _factor_desgaste_circuito(label: str) -> float:
    mapa = {
        "Very low": 0.55,
        "Low": 0.75,
        "Medium": 1.00,
        "High": 1.25,
        "Very high": 1.55,
        "Muy bajo": 0.55,
        "Bajo": 0.75,
        "Medio": 1.00,
        "Alto": 1.25,
        "Muy alto": 1.55,
    }
    return mapa.get(label, 1.00)


def _factor_compuesto(compuesto: str) -> float:
    mapa = {
        "Blando": 1.25,
        "Medio": 1.00,
        "Duro": 0.78,
        "Lluvia": 1.10,
    }
    return mapa.get(compuesto, 1.00)


def estimar_desgaste_neumatico(tyre_label: str, compuesto: str, temperatura: int, riesgo: int, stints: list[int]) -> list[dict]:
    """
    Modelo inicial aproximado. No copia fórmula de GPRO Tools.
    Sirve para comparar estrategias hasta tener historial real.
    """
    base_por_vuelta = 2.15
    factor_circuito = _factor_desgaste_circuito(tyre_label)
    factor_compuesto = _factor_compuesto(compuesto)
    factor_temp = 1 + max(0, temperatura - 20) * 0.008
    factor_riesgo = 1 + (riesgo / 100) * 0.35

    desgaste_vuelta = base_por_vuelta * factor_circuito * factor_compuesto * factor_temp * factor_riesgo

    resultados = []
    for vueltas in stints:
        desgaste = round(vueltas * desgaste_vuelta, 1)
        restante = max(0, round(100 - desgaste, 1))
        if restante >= 25:
            estado = "Seguro"
        elif restante >= 12:
            estado = "Riesgoso"
        else:
            estado = "Peligro"
        resultados.append({
            "vueltas": vueltas,
            "desgaste_pct": desgaste,
            "restante_pct": restante,
            "estado": estado,
        })
    return resultados
