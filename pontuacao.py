def calcular_compatibilidade(resultados):
    """
    Calcula uma pontuação experimental de compatibilidade.

    Por competência:
    - 2 pontos: termo direto e evidência contextual.
    - 1 ponto: evidência contextual sem termo direto.
    - 0 pontos: não há evidência contextual suficiente.

    A pontuação não representa uma probabilidade de competência.
    """

    pontuacao_total = 0
    pontuacao_maxima = len(resultados) * 2
    detalhes = {}

    for competencia, dados in resultados.items():
        termos_encontrados = dados["termos_encontrados"]
        identificada = dados["identificada"]
        evidencias = dados["evidencias_semanticas"]

        # A menção de uma palavra, sozinha, não concede pontos.
        tem_evidencia_contextual = identificada and bool(evidencias)

        if tem_evidencia_contextual and termos_encontrados:
            pontos = 2
            motivo = (
                "Termo direto e evidência contextual encontrados"
            )

        elif tem_evidencia_contextual:
            pontos = 1
            motivo = "Evidência contextual encontrada"

        else:
            pontos = 0

            if termos_encontrados:
                motivo = (
                    "Competência mencionada, mas sem "
                    "evidência contextual suficiente"
                )
            else:
                motivo = "Evidência insuficiente"

        detalhes[competencia] = {
            "pontos": pontos,
            "maximo": 2,
            "motivo": motivo,
        }

        pontuacao_total += pontos

    percentual = (
        pontuacao_total / pontuacao_maxima * 100
        if pontuacao_maxima > 0
        else 0
    )

    return {
        "pontos": pontuacao_total,
        "maximo": pontuacao_maxima,
        "percentual": round(percentual, 1),
        "detalhes": detalhes,
    }