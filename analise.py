import re
import unicodedata
from functools import lru_cache

from requisitos import VAGA
from sentence_transformers import SentenceTransformer, util


NOME_MODELO = "paraphrase-multilingual-MiniLM-L12-v2"

TITULOS_GENERICOS = {
    "habilidades tecnicas",
    "habilidades",
    "competencias",
    "competencias tecnicas",
    "experiencia profissional",
    "formacao academica",
    "objetivo profissional",
    "conhecimentos",
}


@lru_cache(maxsize=1)
def carregar_modelo():
    """Carrega o modelo apenas uma vez por execução."""
    return SentenceTransformer(NOME_MODELO)


def normalizar(texto):
    """Padroniza letras e remove acentos."""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)

    return "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )


def contem_termo(texto, termo):
    """Verifica se um termo aparece como palavra ou expressão completa."""
    padrao = r"(?<!\w)" + re.escape(termo.lower()) + r"(?!\w)"
    return re.search(padrao, texto.lower()) is not None


def tem_contexto_pratico(trecho):
    """
    Verifica se o trecho descreve uma atividade ou experiência,
    em vez de apenas listar uma competência.
    """

    palavras = normalizar(trecho).split()

    if len(palavras) < 6:
        return False

    indicadores_atividade = {
        "desenvolvi", "desenvolveu", "desenvolvimento",
        "utilizei", "utilizou", "utilizacao", "uso",
        "criei", "criou", "criacao",
        "implementei", "implementou", "implementacao",
        "automatizei", "automatizou", "automatizacao",
        "elaborei", "elaborou", "elaboracao",
        "construi", "construiu", "construcao",
        "analisei", "analisou", "analise",
        "interpretei", "interpretou", "interpretacao",
        "consultei", "consultou", "consultas",
        "extraí", "extraiu", "extracao",
        "filtrei", "filtrou", "filtragem",
        "transformei", "transformou", "transformacao",
        "processei", "processou", "processamento",
        "limpei", "limpou", "limpeza",
        "comparei", "comparou", "comparacao",
        "identifiquei", "identificou", "identificacao",
        "criar", "desenvolver", "utilizar", "automatizar",
        "elaborar", "construir", "comparar", "interpretar",
        "experiencia", "projeto", "projetos",
        "relatorios", "indicadores", "registros",
    }

    return any(
        palavra.strip(".,;:()[]{}")
        in indicadores_atividade
        for palavra in palavras
    )


def remover_secao_objetivo(texto):
    """Retira o objetivo profissional da busca por termos diretos."""

    cabecalhos = {
        "objetivo",
        "objetivo profissional",
        "experiencia",
        "experiencia profissional",
        "formacao",
        "formacao academica",
        "habilidades",
        "habilidades tecnicas",
        "competencias",
        "competencias tecnicas",
        "projetos",
        "projetos academicos",
        "cursos",
        "certificacoes",
        "idiomas",
        "resumo profissional",
        "perfil profissional",
    }

    linhas_filtradas = []
    dentro_objetivo = False

    for linha in texto.splitlines():
        cabecalho = normalizar(linha).strip().rstrip(":")

        if cabecalho in cabecalhos:
            dentro_objetivo = cabecalho in {
                "objetivo",
                "objetivo profissional",
            }

            if dentro_objetivo:
                continue

        if not dentro_objetivo:
            linhas_filtradas.append(linha)

    return "\n".join(linhas_filtradas)


def separar_trechos(texto):
    """Divide o currículo em trechos aproveitáveis."""
    partes = re.split(r"[\n.!?;]+", texto)
    trechos = []

    todos_os_termos = [
        termo
        for dados in VAGA["competencias"].values()
        for termo in dados["termos"]
    ]

    for parte in partes:
        trecho = parte.strip()

        if not trecho:
            continue

        if normalizar(trecho) in TITULOS_GENERICOS:
            continue

        menciona_termo = any(
            contem_termo(trecho, termo)
            for termo in todos_os_termos
        )

        if len(trecho.split()) >= 4 or menciona_termo:
            trechos.append(trecho)

    return trechos


def identificar_competencias(texto):
    resultados = {}

    if not texto.strip():
        return {
            competencia: {
                "identificada": False,
                "termos_encontrados": [],
                "similaridade_semantica": 0.0,
                "evidencias_semanticas": [],
            }
            for competencia in VAGA["competencias"]
        }

    modelo = carregar_modelo()
    trechos = separar_trechos(texto)

    for competencia, dados in VAGA["competencias"].items():
        termos = dados["termos"]
        contextos_relevantes = dados["contextos_relevantes"]
        contextos_insuficientes = dados["contextos_insuficientes"]

        texto_para_termos = remover_secao_objetivo(texto)

        encontrados = [
            termo
            for termo in termos
            if contem_termo(texto_para_termos, termo)
        ]

        # Comparamos os trechos com os termos e os contextos relevantes.
        referencias = (
            [f"Conhecimento ou experiência prática em {termo}."
             for termo in termos]
            + contextos_relevantes
        )

        similaridade_maxima = 0.0
        evidencias_semanticas = []

        if trechos and referencias:
            embeddings_referencias = modelo.encode(
                referencias,
                convert_to_tensor=True,
                normalize_embeddings=True,
            )

            embeddings_trechos = modelo.encode(
                trechos,
                convert_to_tensor=True,
                normalize_embeddings=True,
            )

            similaridades = util.cos_sim(
                embeddings_referencias,
                embeddings_trechos,
            )

            # Para cada referência, guardamos o trecho mais semelhante.
            melhores = {}

            for i, referencia in enumerate(referencias):
                indice = int(similaridades[i].argmax().item())
                pontuacao = float(similaridades[i][indice].item())
                trecho = trechos[indice]

                if pontuacao > similaridade_maxima:
                    similaridade_maxima = pontuacao

                melhores[trecho] = max(
                    melhores.get(trecho, 0.0),
                    pontuacao,
                )

                # Contextos insuficientes não comprovam a competência
                # quando aparecem isoladamente.
                trecho_normalizado = normalizar(trecho)

                contexto_fraco = any(
                    normalizar(contexto) in trecho_normalizado
                    for contexto in contextos_insuficientes
                )

                if (
                    pontuacao >= 0.65
                    and not contexto_fraco
                    and tem_contexto_pratico(trecho)
                ):
                    evidencias_semanticas.append({
                        "requisito": referencia,
                        "trecho": trecho,
                        "similaridade": round(pontuacao, 4),
                    })

        identificada_semantica = (
            similaridade_maxima >= 0.70
            and len(evidencias_semanticas) > 0
        )

        resultados[competencia] = {
            "identificada": identificada_semantica,
            "termos_encontrados": encontrados,
            "similaridade_semantica": round(
                similaridade_maxima, 4
            ),
            "evidencias_semanticas": evidencias_semanticas,
        }

    return resultados