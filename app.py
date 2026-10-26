import streamlit as st
import pymupdf
from docx import Document
from io import BytesIO

from requisitos import VAGA
from analise import identificar_competencias
from pontuacao import calcular_compatibilidade


st.title("SkillMatch")
st.subheader("Análise de currículos por competências")

st.write(
    "Sistema experimental de apoio à análise de currículos, "
    "com foco nas competências profissionais."
)

st.header("Vaga em análise")
st.write(VAGA["nome"])

st.write("Competências avaliadas inicialmente:")
for competencia in VAGA["competencias"]:
    st.write(f"- {competencia}")

st.divider()

st.header("Envio de currículos")

arquivos = st.file_uploader(
    "Selecione os currículos",
    type=["pdf", "docx"],
    accept_multiple_files=True,
)

if arquivos:
    for arquivo in arquivos:
        st.divider()
        st.subheader(arquivo.name)

        if arquivo.name.lower().endswith(".pdf"):
            documento = pymupdf.open(
                stream=arquivo.getvalue(),
                filetype="pdf",
            )

            texto = "\n".join(
                pagina.get_text()
                for pagina in documento
            )

            documento.close()

        else:
            documento = Document(
                BytesIO(arquivo.getvalue())
            )

            texto = "\n".join(
                paragrafo.text
                for paragrafo in documento.paragraphs
            )

            # Inclui também o texto das tabelas do Word.
            for tabela in documento.tables:
                for linha in tabela.rows:
                    texto += "\n" + " ".join(
                        celula.text
                        for celula in linha.cells
                    )

        if texto.strip():
            with st.expander("Ver texto extraído"):
                st.text(texto)

            with st.spinner(
                "Analisando competências por palavras-chave "
                "e similaridade semântica..."
            ):
                resultados = identificar_competencias(texto)
                compatibilidade = calcular_compatibilidade(
                    resultados
                )

            # Pontuação geral
            st.header("Compatibilidade com a vaga")

            st.metric(
                label="Compatibilidade estimada",
                value=f"{compatibilidade['percentual']:.1f}%",
                help=(
                    "Indicador experimental baseado nas "
                    "correspondências encontradas. Não representa "
                    "a probabilidade de competência profissional."
                ),
            )

            st.progress(
                compatibilidade["percentual"] / 100
            )

            st.write(
                f"Pontuação total: {compatibilidade['pontos']} "
                f"de {compatibilidade['maximo']} pontos."
            )

            # Pontuação por competência
            st.subheader("Pontuação por competência")

            for competencia, detalhe in (
                compatibilidade["detalhes"].items()
            ):
                st.write(
                    f"**{competencia}:** "
                    f"{detalhe['pontos']}/"
                    f"{detalhe['maximo']} pontos"
                )

                st.caption(detalhe["motivo"])

            st.divider()

            # Análise detalhada
            st.header("Resultados detalhados da análise")

            for competencia, dados in resultados.items():
                st.subheader(competencia)

                if dados["identificada"]:
                    st.success("Competência identificada")
                else:
                    st.warning("Competência não identificada")

                st.write("**Evidências textuais:**")

                termos = dados["termos_encontrados"]

                if termos:
                    st.write(", ".join(termos))
                else:
                    st.write(
                        "Nenhuma palavra-chave encontrada."
                    )

                similaridade = dados["similaridade_semantica"]

                st.metric(
                    label="Maior similaridade semântica",
                    value=f"{similaridade:.1%}",
                )

                evidencias = dados["evidencias_semanticas"]

                if evidencias:
                    with st.expander(
                        "Ver possíveis evidências semânticas"
                    ):
                        for evidencia in evidencias:
                            st.write(
                                f"**Requisito:** "
                                f"{evidencia['requisito']}"
                            )

                            st.write(
                                f"**Trecho do currículo:** "
                                f"{evidencia['trecho']}"
                            )

                            st.write(
                                f"**Similaridade:** "
                                f"{evidencia['similaridade']:.1%}"
                            )

                            st.divider()

                else:
                    st.info(
                        "Nenhum trecho atingiu o limite de "
                        "similaridade definido para exibição "
                        "de evidências."
                    )

                st.caption(
                    "A similaridade representa proximidade "
                    "entre textos, não comprovação de domínio "
                    "da competência."
                )

            st.divider()

            st.caption(
                "O SkillMatch é experimental. A pontuação "
                "não deve ser utilizada isoladamente para "
                "aprovar ou eliminar candidatos."
            )

        else:
            st.warning(
                "Não foi possível extrair texto deste arquivo. "
                "Ele pode estar vazio ou ser um PDF digitalizado."
            )