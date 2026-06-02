def repartir_vueltas(vueltas: int, paradas: int):
    """Devuelve la cantidad de vueltas por stint."""
    stints = paradas + 1
    base = vueltas // stints
    resto = vueltas % stints
    return [base + (1 if i < resto else 0) for i in range(stints)]


def calcular_estrategia(vueltas: int, litros_vuelta: float, paradas: int, margen: float):
    vueltas_stint = repartir_vueltas(int(vueltas), int(paradas))
    margen_por_stint = margen / len(vueltas_stint) if vueltas_stint else 0

    stints = []
    total = 0
    vuelta_inicio = 1
    for i, v in enumerate(vueltas_stint, start=1):
        litros = round((v * litros_vuelta) + margen_por_stint, 1)
        total += litros
        vuelta_fin = vuelta_inicio + v - 1
        stints.append({
            "Stint": i,
            "Vueltas": v,
            "Desde": vuelta_inicio,
            "Hasta": vuelta_fin,
            "Combustible L": litros,
            "Parar al final de vuelta": "Meta" if i == len(vueltas_stint) else vuelta_fin,
        })
        vuelta_inicio = vuelta_fin + 1

    return {
        "combustible_total": round(total, 1),
        "stints": stints,
    }


def calcular_q2(resultado_estrategia: dict):
    return resultado_estrategia["stints"][0]["Combustible L"]
