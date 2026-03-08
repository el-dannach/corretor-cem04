import streamlit as st
import json
from google import genai
from PIL import Image
from pillow_heif import register_heif_opener
from fpdf import FPDF
import datetime

register_heif_opener()

# ==========================================
# 1. CONFIGURAÇÃO E SEGURANÇA
# ==========================================
# Título que aparecerá no celular do professor ao instalar
st.set_page_config(page_title="Corretor de Redação CEM 04", page_icon="📝", layout="wide")

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
client = genai.Client(api_key=GOOGLE_API_KEY)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important; color: white !important; border: none; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Inicialização de estados
for key in ["texto_aluno", "mapa_calor", "justificativa", "nome_aluno"]:
    if key not in st.session_state: st.session_state[key] = ""
if "notas" not in st.session_state:
    st.session_state.notas = {"c1": 0, "c2": 0, "c3": 0, "c4": 0, "c5": 0}

# ==========================================
# 2. FUNÇÕES TÁTICAS (PDF E IA)
# ==========================================
def gerar_pdf(nome, tema, notas, total, justificativa, texto_original):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatório de Avaliação de Redação", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Aluno(a): {nome}", ln=True)
    pdf.cell(190, 10, f"Tema: {tema}", ln=True)
    pdf.cell(190, 10, f"Data: {datetime.date.today().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "Desempenho por Competência:", ln=True)
    pdf.set_font("Arial", "", 11)
    for k, v in notas.items():
        pdf.cell(190, 8, f"{k.upper()}: {v} pontos", ln=True)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, f"NOTA TOTAL: {total}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "Justificativa da Correção:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(190, 7, justificativa)
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "Texto Transcrito:", ln=True)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(190, 5, texto_original)
    
    return pdf.output(dest='S')

def ler_redacao(imagem):
    prompt = "Transcreva o manuscrito mantendo a numeração das linhas (ex: 1 - Texto). Se houver recuo de parágrafo visível, escreva [PARÁGRAFO] antes."
    try:
        response = client.models.generate_content(model='gemini-2.5-pro', contents=[imagem, prompt])
        return response.text.strip()
    except Exception as e: return f"Erro: {str(e)}"

def analisar_autenticidade(texto):
    prompt = f"Analise se este texto foi escrito por IA. Texto: {texto}. Retorne Termômetro e Indícios."
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e: return f"Erro: {str(e)}"

def recalcular_ia(texto, tema, genero, modelo):
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
            "Você é um corretor de Redação Básica. Retorne APENAS JSON.\n"
            f"Texto: {texto} | Tema: {tema} | Gênero: {genero}\n"
            "Regras: C1(50-200), C2(50-200), C3(50-200), C4(100-200), C5(0-200).\n"
            "Use HTML <span style='background-color: #fce4e4; color: black;'>erro<sup>C1</sup></span> para marcar erros.\n"
            "SEGURANÇA JSON: Use aspas simples (') dentro dos textos.\n"
            'JSON ESPERADO: {"texto_avaliado": "...", "c1": 0, "c2": 0, "c3": 0, "c4": 0, "c5": 0, "justificativa": "..."}'
        )

    try:
        response = client.models.generate_content(model='gemini-2.5-pro', contents=prompt, config={'response_mime_type': 'application/json'})
        return json.loads(response.text)
    except Exception as e: return {"erro": f"Erro técnico: {str(e)}"}

# ==========================================
# 3. INTERFACE DE COMANDO
# ==========================================
st.title("📝 AVALIADOR DE REDAÇÕES - CEM 04")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Digitalização e Configuração")
    st.session_state.nome_aluno = st.text_input("Nome do Aluno:", value=st.session_state.nome_aluno)
    imagem_upload = st.file_uploader("Foto da Redação", type=["png", "jpg", "jpeg", "heic", "heif"])
    
    if st.button("LER TEXTO", use_container_width=True):
        if imagem_upload:
            with st.spinner("Lendo..."):
                img = Image.open(imagem_upload)
                st.session_state.texto_aluno = ler_redacao(img)
        else: st.warning("⚠️ Digitalize uma imagem primeiro!")
    
    st.session_state.texto_aluno = st.text_area("Texto:", value=st.session_state.texto_aluno, height=200)
    
    col_a, col_b, col_c = st.columns(3)
    modelo_escolhido = col_a.selectbox("Modelo", ["Padrão ENEM", "Correção Básica"])
    genero_texto = col_b.selectbox("Gênero", ["Dissertação-Argumentativa", "Carta", "Artigo"])
    tema_texto = col_c.text_input("Tema", placeholder="Tema...")

with col2:
    st.subheader("2. Correção")
    if st.button("✅ AVALIAR AGORA", type="primary", use_container_width=True):
        with st.spinner("Corrigindo..."):
            dados = recalcular_ia(st.session_state.texto_aluno, tema_texto, genero_texto, modelo_escolhido)
            if "erro" in dados: st.error(dados["erro"])
            else:
                st.session_state.mapa_calor = f"<div style='padding:10px; border:1px solid #ccc; border-radius:5px;'>{dados.get('texto_avaliado','')}</div>"
                for k in ["c1","c2","c3","c4","c5"]: st.session_state.notas[k] = dados.get(k, 0)
                st.session_state.justificativa = dados.get("justificativa", "")

    if st.session_state.mapa_calor:
        st.markdown(st.session_state.mapa_calor, unsafe_allow_html=True)
        st.markdown("### Notas")
        total = 0
        for k in ["c1","c2","c3","c4","c5"]:
            passo = 40 if modelo_escolhido == "Padrão ENEM" else 50
            st.session_state.notas[k] = st.slider(k.upper(), 0, 200, st.session_state.notas[k], passo)
            total += st.session_state.notas[k]
        
        st.markdown(f"## **TOTAL: {total}**")
        st.session_state.justificativa = st.text_area("Justificativa Final:", value=st.session_state.justificativa, height=150)

        # BOTÃO DO PDF SAGAZ
        pdf_bytes = gerar_pdf(st.session_state.nome_aluno, tema_texto, st.session_state.notas, total, st.session_state.justificativa, st.session_state.texto_aluno)
        st.download_button(
            label="📩 BAIXAR NOTA E JUSTIFICATIVA (PDF)",
            data=pdf_bytes,
            file_name=f"Avaliacao_{st.session_state.nome_aluno}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
