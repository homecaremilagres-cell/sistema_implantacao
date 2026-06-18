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
# ⚠️ COORDENADAS OFICIAIS COM OS IDs PUROS
URL_EQUIPAMENTOS = "https://docs.google.com/spreadsheets/d/1bp351uYvt8gusDbp9ih-JUm45ITyAZbX-tYAo4r54fc/edit"
URL_PACIENTES = "https://docs.google.com/spreadsheets/d/19B6LCQJLN8vAhRQZphiEabotUsnWk5_5tKugc6sYWs4/edit"
URL_HISTORICO = "https://docs.google.com/spreadsheets/d/18iMjG81Gq-fVs3FgxlQv50aTtYwPeHxB8VM2mSfnFug/edit"
# Cole aqui a sua URL do Apps Script (a que termina em /exec):
URL_API_FOTOS = "https://script.google.com/macros/s/AKfycbz8KA5UVROkQFVk9QEi69mxgfeiBr-uOMRTgCaoTxYwqDCjhM6PCitR1kuIIB5cynsZMg/exec"
# ==============================================================================

# Controladores de reset de tela para o celular
if "versao_tela" not in st.session_state:
    st.session_state["versao_tela"] = 0

v = st.session_state["versao_tela"]

conn = st.connection("gsheets", type=GSheetsConnection)

# ------------------------------------------------------------------------------
# 1. ENTRADAS DO TOPO
# ------------------------------------------------------------------------------
col_topo1, col_topo2 = st.columns(2)

with col_topo1:
    unidade_selecionada = st.selectbox(
        "Selecione sua Unidade:", 
        ["BRASILIA", "GOIANIA"],
        key=f"unidade_{v}"
    )

with col_topo2:
    operacao_selecionada = st.selectbox(
        "Tipo de Operação:", 
        ["Implantacao (Entrega)", "Recolhimento (Retirada)", "Substituicao (Troca)", "Inventario (Conferencia)"],
        key=f"operacao_{v}"
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# 2. CARREGAMENTO DOS DADOS
# ------------------------------------------------------------------------------
try:
    df_itens = conn.read(spreadsheet=URL_EQUIPAMENTOS, ttl="5m")
except Exception as e:
    st.error(f"Erro ao conectar com a planilha de Equipamentos: {e}")
    df_itens = pd.DataFrame(columns=["Item", "Tipo de Controle"])

try:
    df_pacientes_raw = conn.read(spreadsheet=URL_PACIENTES, ttl="1m")
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

paciente_selecionado = st.selectbox("1. Escolha o Paciente:", opcoes_paciente, key=f"paciente_{v}")

equipamentos_para_exibir = []

if paciente_selecionado == "+ CADASTRAR NOVO PACIENTE (AVULSO)":
    novo_paciente_nome = st.text_input("Digite o Nome Completo do Novo Paciente:", key=f"novo_pac_{v}")
    if not df_itens.empty and 'Item' in df_itens.columns:
        equipamentos_para_exibir = df_itens['Item'].tolist()
else:
    novo_paciente_nome = ""
    dados_do_paciente = df_pacientes_filtrados[df_pacientes_filtrados['Nome'] == paciente_selecionado]
    
    if not dados_do_paciente.empty:
        previstos_str = dados_do_paciente.iloc[0]['Equipamentos Previstos']
        if pd.notna(previstos_str) and str(previstos_str).strip() != "":
            equipamentos_para_exibir = [item.strip() for item in str(previstos_str).split(",") if item.strip()]
        else:
            if not df_itens.empty and 'Item' in df_itens.columns:
                equipamentos_para_exibir = df_itens['Item'].tolist()

# ------------------------------------------------------------------------------
# 4. EXIBIÇÃO DINÂMICA COM PASSO A PASSO DE CÂMERA (Evita travar o celular)
# ------------------------------------------------------------------------------
registros_para_salvar = []

if len(equipamentos_para_exibir) > 0:
    st.markdown("### 2. Conferência por Foto")
    
    if operacao_selecionada == "Substituicao (Troca)":
        st.warning("🔄 Modo Substituição ativo: Registre primeiro quem sai, depois quem entra.")
    else:
        st.info("Marque o equipamento e use a câmera para registrar a foto de controle.")
    
    for equipamento in equipamentos_para_exibir:
        col_check, col_info, col_cam = st.columns([1, 3, 8])
        
        with col_check:
            marcado = st.checkbox("Sim", key=f"check_{equipamento}_{v}")
            
        with col_info:
            st.markdown(f"**{equipamento}**")
            
        if marcado:
            with col_cam:
                if operacao_selecionada == "Substituicao (Troca)":
                    foto_retirada = st.camera_input(f"📸 1. Foto do Equipamento que SAI ({equipamento})", key=f"cam_ret_{equipamento}_{v}")
                    
                    if foto_retirada:
                        st.markdown("---")
                        foto_entrega = st.camera_input(f"📸 2. Foto do Equipamento que ENTRA ({equipamento})", key=f"cam_ent_{equipamento}_{v}")
                        
                        if foto_entrega:
                            registros_para_salvar.append({
                                "Equipamento": equipamento,
                                "BufferRetirada": foto_retirada,
                                "BufferEntrega": foto_entrega,
                                "Tipo": "Troca"
                            })
                else:
                    foto_unica = st.camera_input(f"📸 Tirar foto do(a) {equipamento}", key=f"cam_uni_{equipamento}_{v}")
                    if foto_unica:
                        registros_para_salvar.append({
                            "Equipamento": equipamento,
                            "BufferUnico": foto_unica,
                            "Tipo": "Padrao"
                        })
        st.markdown("---")

    # ------------------------------------------------------------------------------
    # 5. PROCESSAMENTO E GRAVAÇÃO NO GOOGLE SHEETS
    # ------------------------------------------------------------------------------
    if st.button("💾 Finalizar e Salvar Movimentação", type="primary", key=f"btn_salvar_{v}"):
        nome_final_paciente = novo_paciente_nome if paciente_selecionado == "+ CADASTRAR NOVO PACIENTE (AVULSO)" else paciente_selecionado
        
        if not nome_final_paciente or nome_final_paciente.strip() == "":
            st.error("Por favor, preencha o nome do paciente antes de salvar.")
        elif len(registros_para_salvar) == 0:
            st.warning("Nenhuma foto foi capturada para os equipamentos marcados.")
        else:
            sucesso_geral = True
            linhas_novas = []
            data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            progresso = st.progress(0)
            status_texto = st.empty()
            
            def enviar_foto_drive(buffer_arquivo, sufixo):
                nome_arq = f"{unidade_selecionada}_{nome_final_paciente}_{item_nome}_{sufixo}_{datetime.now().strftime('%d%m%Y_%H%M%S')}.jpg"
                try:
                    bytes_data = buffer_arquivo.getvalue()
                    base64_data = base64.b64encode(bytes_data).decode("utf-8")
                    payload = {"fileName": nome_arq, "mimeType": "image/jpeg", "base64Data": base64_data}
                    resposta = requests.post(URL_API_FOTOS, json=payload)
                    res_json = resposta.json()
                    if res_json.get("success"):
                        return res_json.get("url")
                except:
                    pass
                return None

            for i, reg in enumerate(registros_para_salvar):
                item_nome = reg["Equipamento"]
                status_texto.text(f"Processando mídia do(a) {item_nome}...")
                
                link_retirada_final = "N/A"
                link_entrega_final = "N/A"
                
                if reg["Tipo"] == "Troca":
                    link_retirada_final = enviar_foto_drive(reg["BufferRetirada"], "SAIDA")
                    link_entrega_final = enviar_foto_drive(reg["BufferEntrega"], "ENTRADA")
                    
                    if not link_retirada_final or not link_entrega_final:
                        st.error(f"Falha ao processar par de fotos da troca de: {item_nome}")
                        sucesso_geral = False
                        break
                else:
                    link_foto_u = enviar_foto_drive(reg["BufferUnico"], "REGISTRO")
                    if not link_foto_u:
                        st.error(f"Falha ao enviar imagem do(a) {item_nome}.")
                        sucesso_geral = False
                        break
                    
                    if operacao_selecionada == "Recolhimento (Retirada)":
                        link_retirada_final = link_foto_u
                        link_entrega_final = "N/A"
                    else:  # Implantação ou Inventário
                        link_entrega_final = link_foto_u
                        link_retirada_final = "N/A"
                
                linhas_novas.append({
                    "Data/Hora": data_hora_atual,
                    "Unidade": unidade_selecionada,
                    "Operação": operacao_selecionada,
                    "Paciente": nome_final_paciente,
                    "Equipamento": item_nome,
                    "Foto Retirada": link_retirada_final,
                    "Foto Entrega": link_entrega_final
                })
                
                progresso.progress((i + 1) / len(registros_para_salvar))
            
            if sucesso_geral and len(linhas_novas) > 0:
                try:
                    status_texto.text("Atualizando tabelas do histórico...")
                    df_historico_atual = conn.read(spreadsheet=URL_HISTORICO, ttl="0s")
                    
                    df_novas_linhas = pd.DataFrame(linhas_novas)
                    df_final = pd.concat([df_historico_atual, df_novas_linhas], ignore_index=True)
                    
                    # Salva os dados atualizados de volta no Sheets
                    conn.update(spreadsheet=URL_HISTORICO, data=df_final)
                    
                    if paciente_selecionado == "+ CADASTRAR NOVO PACIENTE (AVULSO)":
                        lista_equipamentos_novos = ", ".join([r["Equipamento"] for r in registros_para_salvar])
                        nova_linha_paciente = pd.DataFrame([{
                            "Nome": nome_final_paciente,
                            "Equipamentos Previstos": lista_equipamentos_novos,
                            "Unidade": unidade_selecionada
                        }])
                        df_pac_final = pd.concat([df_pacientes_raw, nova_linha_paciente], ignore_index=True)
                        conn.update(spreadsheet=URL_PACIENTES, data=df_pac_final)
                    
                    status_texto.empty()
                    progresso.empty()
                    
                    st.success(f"✅ Sucesso completo! Movimentação registrada!")
                    st.balloons()
                    
                    st.session_state["versao_tela"] += 1
                    
                    import time
                    time.sleep(2)
                    st.rerun()
                    
                except Exception as erro_salvar:
                    st.error(f"Erro crítico ao registrar tabelas de histórico: {erro_salvar}")
else:
    if paciente_selecionado != "+ CADASTRAR NOVO PACIENTE (AVULSO)":
        st.info("Selecione um paciente ativo para iniciar a conferência.")
