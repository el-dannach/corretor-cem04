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
st.set_page_config(page_title="Corretor de Redacao CEM 04", page_icon="📝", layout="wide")

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
    
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(190, 10, "Relatorio de Avaliacao de Redacao", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(190, 10, f"Aluno(a): {nome}", ln=True)
    pdf.cell(190, 10, f"Tema: {tema}", ln=True)
    pdf.cell(190, 10, f"Data: {datetime.date.today().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "Desempenho por Competencia:", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for k, v in notas.items():
        pdf.cell(190, 8, f"{k.upper()}: {v} pontos", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(190, 10, f"NOTA TOTAL: {total}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "Justificativa da Correcao:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    
    just_limpa = justificativa.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(190, 7, just_limpa)
    
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, "Texto Transcrito:", ln=True)
    pdf.set_font("Helvetica", "I", 9)
    
    text_limpo = texto_original.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(190, 5, text_limpo)
    
    # A SOLUÇÃO DEFINITIVA: O fpdf2 já entrega os bytes direitinho
    return bytes(pdf.output())

def ler_redacao(imagem):
    prompt = "Transcreva o manuscrito. Se houver recuo de paragrafo, escreva [PARAGRAFO]."
    try:
        response = client.models.generate_content(model='gemini-2.5-pro', contents=[imagem, prompt])
        return response.text.strip()
    except Exception as e: return f"Erro: {str(e)}"

def recalcular_ia(texto, tema, genero, modelo):
    prompt_config = "Padrão ENEM" if modelo == "Padrão ENEM" else "Básica"
    prompt = (
        f"Você é um corretor de Redação {prompt_config}. Retorne APENAS JSON.\n"
        f"Texto: {texto} | Tema: {tema} | Gênero: {genero}\n"
        "Use HTML <span style='background-color: #fce4e4; color: black;'>erro<sup>C1</sup></span> para marcar erros.\n"
        "SEGURANÇA JSON: Use aspas simples (') dentro dos textos.\n"
        'JSON ESPERADO: {"texto_avaliado": "...", "c1": 0, "c2": 0, "c3": 0, "c4": 0, "c5": 0, "justificativa": "..."}'
    )
    try:
        response = client.models.generate_content(model='gemini-2.5-pro', contents=prompt, config={'response_mime_type': 'application/json'})
        return json.loads(response.text)
    except Exception as e: return {"erro": f"Erro tecnico: {str(e)}"}

# ==========================================
# 3. INTERFACE DE COMANDO
# ==========================================
st.title("📝 AVALIADOR DE REDAÇÕES - CEM 04")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Digitalização")
    st.session_state.nome_aluno = st.text_input("Nome do Aluno:", value=st.session_state.nome_aluno)
    imagem_upload = st.file_uploader("Foto da Redação", type=["png", "jpg", "jpeg", "heic", "heif"])
    
    if st.button("LER TEXTO", use_container_width=True):
        if imagem_upload:
            with st.spinner("Lendo..."):
                img = Image.open(imagem_upload)
                st.session_state.texto_aluno = ler_redacao(img)
        else: st.warning("⚠️ Selecione uma imagem!")
    
    st.session_state.texto_aluno = st.text_area("Texto Transcrito:", value=st.session_state.texto_aluno, height=200)
    
    c_a, c_b, c_c = st.columns(3)
    mod = c_a.selectbox("Modelo", ["Padrão ENEM", "Correção Básica"])
    gen = c_b.selectbox("Gênero", ["Dissertação-Argumentativa", "Carta", "Artigo"])
    tem = c_c.text_input("Tema", placeholder="Tema...")

with col2:
    st.subheader("2. Resultado")
    if st.button("✅ AVALIAR AGORA", type="primary", use_container_width=True):
        with st.spinner("Analisando..."):
            dados = recalcular_ia(st.session_state.texto_aluno, tem, gen, mod)
            if "erro" in dados: st.error(dados["erro"])
            else:
                st.session_state.mapa_calor = f"<div style='padding:10px; border:1px solid #ccc; border-radius:5px;'>{dados.get('texto_avaliado','')}</div>"
                for k in ["c1","c2","c3","c4","c5"]: st.session_state.notas[k] = dados.get(k, 0)
                st.session_state.justificativa = dados.get("justificativa", "")

    if st.session_state.mapa_calor:
        st.markdown(st.session_state.mapa_calor, unsafe_allow_html=True)
        total = 0
        for k in ["c1","c2","c3","c4","c5"]:
            passo = 40 if mod == "Padrão ENEM" else 50
            st.session_state.notas[k] = st.slider(k.upper(), 0, 200, st.session_state.notas[k], passo)
            total += st.session_state.notas[k]
        
        st.markdown(f"## **TOTAL: {total}**")
        st.session_state.justificativa = st.text_area("Justificativa:", value=st.session_state.justificativa, height=150)

        # GERAÇÃO DOS BYTES DO PDF
        try:
            pdf_data = gerar_pdf(st.session_state.nome_aluno, tem, st.session_state.notas, total, st.session_state.justificativa, st.session_state.texto_aluno)
            st.download_button(
                label="📩 BAIXAR RELATÓRIO (PDF)",
                data=pdf_data,
                file_name=f"Avaliacao_{st.session_state.nome_aluno}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
