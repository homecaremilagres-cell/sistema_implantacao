import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Gestão de Equipamentos Home Care", layout="centered")

# --- CONEXÃO NATIVA COM GOOGLE SHEETS ---
# O Streamlit busca automaticamente as credenciais que você colou no menu 'Secrets'
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO DOS ARQUIVOS E PASTAS ---
# Links ou nomes das planilhas correspondentes no seu Google Drive
# Você pode colar o Link de compartilhamento direto da planilha se preferir
URL_EQUIPAMENTOS = "https://docs.google.com/spreadsheets/d/1bp351uYvt8gusDbp9ih-JUm45ITyAZbX-tYAo4r54fc/edit" 
URL_PACIENTES = "https://docs.google.com/spreadsheets/d/19B6LCQJLN8vAhRQZphiEabotUsnWk5_5tKugc6sYWs4/edit"
URL_HISTORICO = "https://docs.google.com/spreadsheets/d/18iMjG81Gq-fVs3FgxlQv50aTtYwPeHxB8VM2mSfnFug/edit"

PASTA_FOTOS = "fotos_patrimonio"               
if not os.path.exists(PASTA_FOTOS):
    os.makedirs(PASTA_FOTOS)

# Visuais CSS
st.markdown("""
    <style>
        .titulo-principal { color: #FF4B4B; font-size: 2.2rem; font-weight: bold; margin-bottom: 0.5rem; }
        .subtitulo-descricao { color: #555; font-size: 1.0rem; margin-bottom: 2rem; }
        div[data-testid="stCameraInput"] { margin-top: -15px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="titulo-principal">📋 Sistema de Movimentação Pro</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo-descricao">Operando em tempo real integrado ao Google Drive da Empresa.</p>', unsafe_allow_html=True)

# Filtros iniciais
col_unid, col_oper = st.columns(2)
with col_unid:
    unidade_selecionada = st.selectbox("Selecione sua Unidade:", ["BRASÍLIA", "GOIÂNIA"])
with col_oper:
    operacao_selecionada = st.selectbox("Tipo de Operação:", ["Implantação (Entrega)", "Explantação (Retirada)"])

# --- LEITURA EM TEMPO REAL DO GOOGLE SHEETS ---
try:
    # Lê a aba de equipamentos
    # Mude a linha 47 para este formato exatamente:
    df_itens = conn.read(spreadsheet=URL_EQUIPAMENTOS, worksheet="cadastro_equipamentos", ttl="5m")
    df_itens.columns = ["Item", "Tipo de Controle"] + list(df_itens.columns[2:])
except Exception as e:
    st.error(f"Erro ao conectar com a planilha de Equipamentos: {e}")
    st.stop()

dicionario_pre_implantacao = {}
lista_pacientes = ["Selecione um paciente...", "➕ CADASTRAR NOVO PACIENTE (AVULSO)"]

try:
    # Lê a planilha de pacientes ativos
    df_pacientes_raw = conn.read(spreadsheet=URL_PACIENTES, worksheet="Página1", ttl="1m")

# Logo abaixo da leitura, adicione ou verifique se existe esta linha para normalizar o texto:
if not df_pacientes_raw.empty and 'Unidade' in df_pacientes_raw.columns:
    df_pacientes_raw['Unidade'] = df_pacientes_raw['Unidade'].astype(str).str.upper().str.strip()
    df_pacientes_raw.columns = ["Nome", "Equipamentos Previstos", "Unidade"] + list(df_pacientes_raw.columns[3:])
    
    df_filtrado = df_pacientes_raw[df_pacientes_raw["Unidade"].astype(str).str.upper() == unidade_selecionada]
    lista_pacientes_unidade = df_filtrado["Nome"].dropna().tolist()
    lista_pacientes.extend(lista_pacientes_unidade)
    
    for index, linha in df_filtrado.iterrows():
        nome_pac = str(linha["Nome"]).strip()
        itens_previstos = str(linha["Equipamentos Previstos"])
        if itens_previstos and itens_previstos != "nan":
            lista_itens = [i.strip() for i in itens_previstos.split(",")]
        else:
            lista_itens = []
        dicionario_pre_implantacao[nome_pac] = lista_itens
except Exception as e:
    st.warning("Aguardando configuração ou dados na lista de pacientes do Google Sheets.")

paciente_selecionado = st.selectbox("1. Escolha o Paciente:", lista_pacientes)

nome_paciente_final = ""
if paciente_selecionado == "➕ CADASTRAR NOVO PACIENTE (AVULSO)":
    nome_avulso = st.text_input("Digite o nome completo do novo paciente:")
    if nome_avulso.strip() != "":
        nome_paciente_final = nome_avulso.strip().upper()
else:
    if paciente_selecionado != "Selecione um paciente...":
        nome_paciente_final = paciente_selecionado

if nome_paciente_final != "":
    st.markdown("---")
    st.markdown(f"### 2. Checklist de {operacao_selecionada}")
    
    if "Explantação" in operacao_selecionada:
        itens_planejados_paciente = []
    else:
        itens_planejados_paciente = dicionario_pre_implantacao.get(nome_paciente_final, [])
    
    respostas_tecnico = {}
    
    for index, linha in df_itens.iterrows():
        nome_item = str(linha["Item"])
        tipo_controle = str(linha["Tipo de Controle"])
        
        ja_planejado = nome_item in itens_planejados_paciente
        item_movimentado = st.checkbox(nome_item, value=ja_planejado, key=f"chk_{index}")
        
        if item_movimentado:
            col1, col2 = st.columns([2, 3])
            with col1:
                id_registro = st.text_input(f"Digite o {tipo_controle}:", key=f"txt_{index}")
                respostas_tecnico[f"{nome_item} ({tipo_controle})"] = id_registro
            with col2:
                if tipo_controle == "Patrimônio":
                    foto_individual = st.camera_input(f"📸 Foto {nome_item}", key=f"cam_{index}")
                    respostas_tecnico[f"Foto_{nome_item}"] = foto_individual

        respostas_tecnico[nome_item] = "Sim" if item_movimentado else "Não"

    st.markdown("---")
    
    if st.button(f"Finalizar e Salvar {operacao_selecionada.split(' ')[0]}", use_container_width=True):
        if "Sim" not in respostas_tecnico.values():
            st.error("Atenção: Você precisa marcar pelo menos um item para salvar!")
        else:
            agora = datetime.now()
            data_registro = agora.strftime("%Y-%m-%d %H:%M:%S")
            data_nome_foto_base = agora.strftime("%Y%m%d_%H%M%S")
            
            nome_pac_limpo = nome_paciente_final.replace(" ", "_")
            tipo_acao_limpa = "ENTREGA" if "Implantação" in operacao_selecionada else "RETIRADA"
            
            dados_linha = {
                "Data/Hora": data_registro,
                "Unidade": unidade_selecionada,
                "Operação": tipo_acao_limpa,
                "Paciente": nome_paciente_final
            }
            
            # Processamento local de fotos (Podem ser enviadas para um Google Drive Folder futuramente)
            for key_resposta, valor_resposta in respostas_tecnico.items():
                if key_resposta.startswith("Foto_") and valor_resposta is not None:
                    nome_equipamento = key_resposta.replace("Foto_", "").replace(" ", "_")
                    nome_arquivo_foto = f"{unidade_selecionada}_{tipo_acao_limpa}_{nome_pac_limpo}_{data_nome_foto_base}_{nome_equipamento}.jpg"
                    caminho_completo_foto = os.path.join(PASTA_FOTOS, nome_arquivo_foto)
                    with open(caminho_completo_foto, "wb") as f:
                        f.write(valor_resposta.getbuffer())
                    dados_linha[key_resposta] = nome_arquivo_foto
                elif not key_resposta.startswith("Foto_"):
                    dados_linha[key_resposta] = valor_resposta
            
            # --- ESCREVE DIRETAMENTE NA PLANILHA DO GOOGLE SHEETS ---
            try:
                df_nova_linha = pd.DataFrame([dados_linha])
                # Puxa o histórico atual da nuvem, junta a nova linha e salva de volta
                df_historico_atual = conn.read(spreadsheet=URL_HISTORICO, worksheet="Página1", ttl="0s")
                df_final = pd.concat([df_historico_atual, df_nova_linha], ignore_index=True)
                
                conn.update(spreadsheet=URL_HISTORICO, worksheet="Página1", data=df_final)
                conn.update(spreadsheet=URL_PACIENTES, worksheet="Página1", data=df_pac_final)
                
                # Se for avulso, adiciona também na planilha de pacientes ativos da nuvem
                if paciente_selecionado == "➕ CADASTRAR NOVO PACIENTE (AVULSO)":
                    df_pac_atual = conn.read(worksheet="Página1", spreadsheet=URL_PACIENTES, ttl="0s")
                    if nome_paciente_final not in df_pac_atual.iloc[:,0].astype(str).values:
                        df_novo_pac = pd.DataFrame([{"Nome": nome_paciente_final, "Equipamentos Previstos": "", "Unidade": unidade_selecionada}])
                        df_pac_final = pd.concat([df_pac_atual, df_novo_pac], ignore_index=True)
                        conn.update(worksheet="Página1", spreadsheet=URL_PACIENTES, data=df_pac_final)
                
                st.success(f"Registrado com sucesso diretamente no Google Sheets!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao salvar os dados no Google Sheets: {e}")
