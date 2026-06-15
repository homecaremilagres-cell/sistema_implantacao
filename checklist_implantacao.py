import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configuração da página do Streamlit
st.set_page_config(page_title="Sistema de Movimentação Pro", layout="wide")

st.title("📋 Sistema de Movimentação Pro")
st.subheader("Operando em tempo real integrado ao Google Drive da Empresa.")
st.markdown("---")

# ==============================================================================
# ==============================================================================
# ⚠️ CONFIRA SE OS IDs ABAIXO SÃO EXATAMENTE OS DAS SUAS PLANILHAS ORIGINAIS
URL_EQUIPAMENTOS = "1bp351uYvt8gusDbp9ih-JUm45ITyAZbX-tYAo4r54fc"
URL_PACIENTES = "19B6LCQJLN8vAhRQZphiEabotUsnWk5_5tKugc6YWw4"
URL_HISTORICO = "18iMjG81Gq-fVs3Fgx1Qv50aTtYwPeHxB8VM2mSfnFug"

# A URL do Apps Script que você gerou na janela anônima deve vir EXCLUSIVAMENTE aqui:
URL_API_FOTOS = "https://script.google.com/macros/s/AKfycbyeHfTYHgu7H1kgMit_vo-Alf2D-zrPREVhRDtJHGlGTwE7hnvDQ1rZhMT0CXbBAEy6cQ/exec"
# ==============================================================================
# ==============================================================================

# Cria a conexão oficial do Streamlit com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ------------------------------------------------------------------------------
# 1. ENTRADAS DO TOPO
# ------------------------------------------------------------------------------
col_topo1, col_topo2 = st.columns(2)

with col_topo1:
    unidade_selecionada = st.selectbox(
        "Selecione sua Unidade:", 
        ["BRASILIA", "GOIANIA"]
    )

with col_topo2:
    operacao_selecionada = st.selectbox(
        "Tipo de Operação:", 
        ["Implantacao (Entrega)", "Recolhimento (Retirada)", "Substituicao (Troca)"]
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# 2. CARREGAMENTO DOS DADOS (Google Sheets)
# ------------------------------------------------------------------------------
try:
    df_itens = conn.read(spreadsheet=URL_EQUIPAMENTOS, worksheet="cadastro_equipamentos", ttl="5m")
except Exception as e:
    st.error(f"Erro ao conectar com a planilha de Equipamentos: {e}")
    df_itens = pd.DataFrame(columns=["Item", "Tipo de Controle"])

try:
    df_pacientes_raw = conn.read(spreadsheet=URL_PACIENTES, worksheet="pacientes", ttl="1m")
    if not df_pacientes_raw.empty and 'Unidade' in df_pacientes_raw.columns:
        df_pacientes_raw['Unidade'] = df_pacientes_raw['Unidade'].astype(str).str.upper().str.strip()
except Exception as e:
    st.error(f"Erro ao conectar com a planilha de Pacientes: {e}")
    df_pacientes_raw = pd.DataFrame(columns=["Nome", "Equipamentos Previstos", "Unidade"])

if not df_pacientes_raw.empty:
    df_pacientes_filtrados = df_pacientes_raw[df_pacientes_raw['Unidade'] == unidade_selecionada.strip().upper()]
else:
    df_pacientes_filtrados = pd.DataFrame()

# ------------------------------------------------------------------------------
# 3. INTERFACE PRINCIPAL E FLUXO DO CHECKLIST
# ------------------------------------------------------------------------------
opcoes_paciente = ["+ CADASTRAR NOVO PACIENTE (AVULSO)"]
if not df_pacientes_filtrados.empty:
    opcoes_paciente.extend(df_pacientes_filtrados['Nome'].tolist())

paciente_selecionado = st.selectbox("1. Escolha o Paciente:", opcoes_paciente)

equipamentos_para_exibir = []

if paciente_selecionado == "+ CADASTRAR NOVO PACIENTE (AVULSO)":
    novo_paciente_nome = st.text_input("Digite o Nome Completo do Novo Paciente:")
    if not df_itens.empty:
        equipamentos_para_exibir = df_itens['Item'].tolist()
else:
    novo_paciente_nome = ""
    dados_do_paciente = df_pacientes_filtrados[df_pacientes_filtrados['Nome'] == paciente_selecionado]
    
    if not dados_do_paciente.empty:
        previstos_str = dados_do_paciente.iloc[0]['Equipamentos Previstos']
        if pd.notna(previstos_str) and str(previstos_str).strip() != "":
            equipamentos_para_exibir = [item.strip() for item in str(previstos_str).split(",") if item.strip()]
        else:
            if not df_itens.empty:
                equipamentos_para_exibir = df_itens['Item'].tolist()

# ------------------------------------------------------------------------------
# 4. EXIBIÇÃO DINÂMICA COM ENTRADA DE CÂMERA (FOTO PADRONIZADA)
# ------------------------------------------------------------------------------
registros_para_salvar = []

if len(equipamentos_para_exibir) > 0:
    st.markdown("### 2. Conferência por Foto")
    st.info("Marque o equipamento e use a câmera do aparelho para registrar a etiqueta, patrimônio ou lote.")
    
    for equipamento in equipamentos_para_exibir:
        col_check, col_info, col_cam = st.columns([1, 3, 5])
        
        with col_check:
            marcado = st.checkbox("Sim", key=f"check_{equipamento}")
            
        with col_info:
            st.markdown(f"**{equipamento}**")
            
        with col_cam:
            if marcado:
                # Aciona a câmera nativa do dispositivo (Celular ou Computador)
                foto_capturada = st.camera_input(f"Tirar foto do(a) {equipamento}", key=f"cam_{equipamento}")
                if foto_capturada:
                    registros_para_salvar.append({
                        "Equipamento": equipamento,
                        "ArquivoBuffer": foto_capturada
                    })
        st.markdown("---")

    # ------------------------------------------------------------------------------
    # 5. PROCESSAMENTO E GRAVAÇÃO NO GOOGLE SHEETS
    # ------------------------------------------------------------------------------
    if st.button("💾 Finalizar e Salvar Movimentação", type="primary"):
        nome_final_paciente = novo_paciente_nome if paciente_selecionado == "+ CADASTRAR NOVO PACIENTE (AVULSO)" else paciente_selecionado
        
        if not nome_final_paciente or nome_final_paciente.strip() == "":
            st.error("Por favor, preencha o nome do paciente antes de salvar.")
        elif len(registros_para_salvar) == 0:
            st.warning("Nenhuma foto foi capturada para os equipamentos marcados.")
        else:
            sucesso_geral = True
            linhas_novas = []
            data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            # Criamos uma barra de progresso visual para o envio de fotos
            progresso = st.progress(0)
            status_texto = st.empty()
            
            for i, reg in enumerate(registros_para_salvar):
                item_nome = reg["Equipamento"]
                status_texto.text(f"Enviando foto do(a) {item_nome} para o Google Drive...")
                
                try:
                    # Lê os bytes da imagem capturada e converte em Base64
                    bytes_data = reg["ArquivoBuffer"].getvalue()
                    base64_data = base64.b64encode(bytes_data).decode("utf-8")
                    
                    # Nome estruturado do arquivo que será salvo na pasta do Drive
                    nome_arquivo_drive = f"{unidade_selecionada}_{nome_final_paciente}_{item_nome}_{datetime.now().strftime('%d%m%Y_%H%M%S')}.jpg"
                    
                    # Envia os dados estruturados para a API do Apps Script
                    payload = {
                        "fileName": nome_arquivo_drive,
                        "mimeType": "image/jpeg",
                        "base64Data": base64_data
                    }
                    
                    resposta = requests.post(URL_API_FOTOS, json=payload)
                    resultado_json = resposta.json()
                    
                    if resultado_json.get("success"):
                        link_foto_drive = resultado_json.get("url")
                    else:
                        st.error(f"Falha no script do Drive para {item_nome}: {resultado_json.get('error')}")
                        sucesso_geral = False
                        break
                        
                except Exception as e_upload:
                    st.error(f"Erro ao conectar com o servidor de fotos para {item_nome}: {e_upload}")
                    sucesso_geral = False
                    break
                
                # Guarda as referências da linha com o link clicável da imagem
                linhas_novas.append({
                    "Data/Hora": data_hora_atual,
                    "Unidade": unidade_selecionada,
                    "Operação": operacao_selecionada,
                    "Paciente": nome_final_paciente,
                    "Equipamento": item_nome,
                    "Identificação/Qtd": link_foto_drive  # Armazena o link direto da imagem
                })
                
                progresso.progress((i + 1) / len(registros_para_salvar))
            
            if sucesso_geral and len(linhas_novas) > 0:
                try:
                    status_texto.text("Atualizando tabelas do histórico...")
                    df_historico_atual = conn.read(spreadsheet=URL_HISTORICO, ttl="0s")
                    
                    df_novas_linhas = pd.DataFrame(linhas_novas)
                    df_final = pd.concat([df_historico_atual, df_novas_linhas], ignore_index=True)
                    
                    conn.update(spreadsheet=URL_HISTORICO, data=df_final)
                    
                    if paciente_selecionado == "+ CADASTRAR NOVO PACIENTE (AVULSO)":
                        lista_equipamentos_novos = ", ".join([r["Equipamento"] for r in registros_para_salvar])
                        nova_linha_paciente = pd.DataFrame([{
                            "Nome": nome_final_paciente,
                            "Equipamentos Previstos": lista_equipamentos_novos,
                            "Unidade": unidade_selecionada
                        }])
                        df_pac_final = pd.concat([df_pacientes_raw, nova_linha_paciente], ignore_index=True)
                        conn.update(spreadsheet=URL_PACIENTES, worksheet="pacientes", data=df_pac_final)
                    
                    status_texto.empty()
                    progresso.empty()
                    st.success(f"✅ Sucesso completo! Movimentação registrada e fotos salvas no Drive!")
                    st.balloons()
                    
                except Exception as erro_salvar:
                    st.error(f"Erro crítico ao registrar tabelas de histórico: {erro_salvar}")
else:
    if paciente_selecionado != "+ CADASTRAR NOVO PACIENTE (AVULSO)":
        st.info("Selecione um paciente ativo para iniciar a conferência.")
