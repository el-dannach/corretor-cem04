import streamlit as st
import json
from google import genai
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

# ==========================================
# 1. A CHAVE DO IMPÉRIO E CONFIGURAÇÃO
# ==========================================
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
client = genai.Client(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="Corretor IA de Redações", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important; color: white !important; border: none; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

if "texto_aluno" not in st.session_state:
    st.session_state.texto_aluno = ""
if "mapa_calor" not in st.session_state:
    st.session_state.mapa_calor = ""
if "notas" not in st.session_state:
    st.session_state.notas = {"c1": 0, "c2": 0, "c3": 0, "c4": 0, "c5": 0}
if "justificativa" not in st.session_state:
    st.session_state.justificativa = ""

# ==========================================
# 2. O CÉREBRO DA MÁQUINA
# ==========================================
def ler_redacao(imagem):
    prompt = "Transcreva o manuscrito mantendo a numeração das linhas (ex: 1 - Texto). Se houver recuo de parágrafo visível, escreva [PARÁGRAFO] antes."
    try:
        response = client.models.generate_content(model='gemini-2.5-pro', contents=[imagem, prompt])
        return response.text.strip()
    except Exception as e:
        return f"Erro: {str(e)}"

def analisar_autenticidade(texto):
    prompt = f"Analise se este texto foi escrito por IA. Texto: {texto}. Retorne Termômetro e Indícios."
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"Erro: {str(e)}"

def recalcular_ia(texto, tema, genero, modelo):
    # DIVISÃO DE CÉREBROS
    if modelo == "Padrão ENEM":
        prompt = (
            "Você é um corretor ENEM. Retorne APENAS JSON.\n"
            f"Texto: {texto} | Tema: {tema} | Gênero: {genero}\n"
            "Regras: Notas 0, 40, 80, 120, 160, 200. Penalize falta de [PARÁGRAFO] na C2.\n"
            "Use HTML <span style='background-color: #fce4e4; color: black;'>erro<sup>C1</sup></span> para marcar erros.\n"
            "SEGURANÇA JSON: Use aspas simples (') dentro dos textos. NUNCA aspas duplas.\n"
            'JSON ESPERADO: {"texto_avaliado": "...", "c1": 0, "c2": 0, "c3": 0, "c4": 0, "c5": 0, "justificativa": "..."}'
        )
    else:
        prompt = (
            "Você é um corretor da Grade Específica de Correção Básica. Retorne APENAS JSON.\n"
            f"Texto: {texto} | Tema: {tema} | Gênero: {genero}\n"
            "REGRAS (Converta para base 200 para manter o padrão do sistema):\n"
            "- C1 (Gramática): 50 (Precário/1 período), 100 (Mediano/1 período em 1+ parágrafos), 150 (Bom/2+ períodos), 200 (Ótimo/apenas 2 desvios).\n"
            "- C2 (Tema/Repertório): 50 (Tangente/Motivadores), 100 (Completa/Motivadores), 150 (Completa/Além dos motivadores NÃO articulado), 200 (Completa/Além dos motivadores ARTICULADO).\n"
            "- C3 (Projeto de Texto): 50 (Sem articulação/Sem desenvolvimento), 100 (Sem articulação/COM desenvolvimento), 150 (COM alguma articulação/COM desenvolvimento), 200 (COM articulação/COM desenvolvimento).\n"
            "- C4 (Estrutura em parágrafos): 100 (Monobloco/Embrionário), 150 (Dois parágrafos), 200 (Três parágrafos).\n"
            "- C5 (Intervenção): 0 (Tangente/Sem proposta/Fere direitos), 50 (1 elemento válido), 100 (2 elementos válidos), 150 (3 elementos válidos), 200 (4 elementos válidos).\n"
            "- ZERO (Nota 0 geral): Textos com 14 linhas ou menos, cópia, fuga, impropérios.\n"
            "Use HTML <span style='background-color: #fce4e4; color: black;'>erro<sup>C1</sup></span> para marcar erros.\n"
            "SEGURANÇA JSON: Use aspas simples (') dentro dos textos. NUNCA aspas duplas.\n"
            'JSON ESPERADO: {"texto_avaliado": "...", "c1": 0, "c2": 0, "c3": 0, "c4": 0, "c5": 0, "justificativa": "..."}'
        )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro', 
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        return {"erro": f"Erro técnico: {str(e)}"}

# ==========================================
# 3. INTERFACE DE COMANDO
# ==========================================
st.title("📝 AVALIADOR DE REDAÇÕES COM IA")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Digitalização e Configuração")
    imagem_upload = st.file_uploader("Foto da Redação", type=["png", "jpg", "jpeg", "heic", "heif"])
    
    if st.button("LER TEXTO", use_container_width=True):
        if imagem_upload:
            with st.spinner("Lendo..."):
                img = Image.open(imagem_upload)
                st.session_state.texto_aluno = ler_redacao(img)
        else:
            st.warning("⚠️ Digitalize uma imagem primeiro!")
    
    st.session_state.texto_aluno = st.text_area("Texto:", value=st.session_state.texto_aluno, height=250)
    
    col_a, col_b, col_c = st.columns(3)
    # A ALTERAÇÃO EXIGIDA PELA SUA ALIADA
    modelo_escolhido = col_a.selectbox("Modelo", ["Padrão ENEM", "Correção Básica"])
    genero_texto = col_b.selectbox("Gênero", ["Dissertação-Argumentativa", "Carta", "Artigo"])
    tema_texto = col_c.text_input("Tema", placeholder="Tema...")
    
    if st.button("Checar Autenticidade", use_container_width=True):
        st.info(analisar_autenticidade(st.session_state.texto_aluno))

with col2:
    st.subheader("2. Correção")
    if st.button("✅ AVALIAR AGORA", type="primary", use_container_width=True):
        with st.spinner("Corrigindo..."):
            dados = recalcular_ia(st.session_state.texto_aluno, tema_texto, genero_texto, modelo_escolhido)
            if "erro" in dados:
                st.error(dados["erro"])
            else:
                st.session_state.mapa_calor = f"<div style='padding:10px; border:1px solid #ccc; border-radius:5px;'>{dados.get('texto_avaliado','')}</div>"
                for k in ["c1","c2","c3","c4","c5"]: st.session_state.notas[k] = dados.get(k, 0)
                st.session_state.justificativa = dados.get("justificativa", "")

    if st.session_state.mapa_calor:
        st.markdown(st.session_state.mapa_calor, unsafe_allow_html=True)
        st.markdown("### Notas (Convertidas para base 1000)")
        total = 0
        for k in ["c1","c2","c3","c4","c5"]:
            passo = 40 if modelo_escolhido == "Padrão ENEM" else 50
            st.session_state.notas[k] = st.slider(k.upper(), 0, 200, st.session_state.notas[k], passo)
            total += st.session_state.notas[k]
        st.markdown(f"**TOTAL: {total}**")
        st.text_area("Justificativa:", value=st.session_state.justificativa, height=200)
