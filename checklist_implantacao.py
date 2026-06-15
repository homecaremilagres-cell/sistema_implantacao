import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configuração da página do Streamlit
st.set_page_config(page_title="Sistema de Movimentação Pro", layout="wide")

st.title("📋 Sistema de Movimentação Pro")
st.subheader("Operando em tempo real integrado ao Google Drive da Empresa.")
st.markdown("---")

# ==============================================================================
# ⚠️ CONFIGURAÇÃO COM OS LINKS DAS SUAS PLANILHAS
URL_EQUIPAMENTOS = "https://docs.google.com/spreadsheets/d/1bp351uYvt8gusDbp9ih-JUm45ITyAZbX-tYAo4r54fc/edit"
URL_PACIENTES = "https://docs.google.com/spreadsheets/d/19B6LCQJLN8vAhRQZphiEabotUsnWk5_5tKugc6sYWs4/edit"
URL_HISTORICO = "https://docs.google.com/spreadsheets/d/18iMjG81Gq-fVs3FgxlQv50aTtYwPeHxB8VM2mSfnFug/edit"
# ==============================================================================

# Cria a conexão oficial do Streamlit com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ------------------------------------------------------------------------------
# 1. ENTRADAS DO TOPO (Filtros sem acento para combinar com a sua planilha)
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
# 2. CARREGAMENTO DOS DADOS
# ------------------------------------------------------------------------------

# Carrega os Equipamentos Cadastrados
try:
    df_itens = conn.read(spreadsheet=URL_EQUIPAMENTOS, worksheet="cadastro_equipamentos", ttl="5m")
except Exception as e:
    st.error(f"Erro ao conectar com a planilha de Equipamentos: {e}")
    df_itens = pd.DataFrame(columns=["Item", "Tipo de Controle"])

# Carrega a Lista de Pacientes Ativos (Buscando a aba 'pacientes' que você renomeou)
try:
    df_pacientes_raw = conn.read(spreadsheet=URL_PACIENTES, worksheet="pacientes", ttl="1m")
    if not df_pacientes_raw.empty and 'Unidade' in df_pacientes_raw.columns:
        df_pacientes_raw['Unidade'] = df_pacientes_raw['Unidade'].astype(str).str.upper().str.strip()
except Exception as e:
    st.error(f"Erro ao conectar com a planilha de Pacientes: {e}")
    df_pacientes_raw = pd.DataFrame(columns=["Nome", "Equipamentos Previstos", "Unidade"])


# Filtrar pacientes da unidade selecionada
if not df_pacientes_raw.empty:
    df_pacientes_filtrados = df_pacientes_raw[df_pacientes_raw['Unidade'] == unidade_selecionada.strip().upper()]
else:
    df_pacientes_filtrados = pd.DataFrame()

# ------------------------------------------------------------------------------
# 3. INTERFACE PRINCIPAL E FLUXO DO CHECKLIST
# ------------------------------------------------------------------------------

if df_pacientes_filtrados.empty:
    st.warning("Aguardando configuração ou dados na lista de pacientes do Google Sheets.")
    
# Criar lista de seleção para o usuário
opcoes_paciente = ["+ CADASTRAR NOVO PACIENTE (AVULSO)"]
if not df_pacientes_filtrados.empty:
    opcoes_paciente.extend(df_pacientes_filtrados['Nome'].tolist())

paciente_selecionado = st.selectbox("1. Escolha o Paciente:", opcoes_paciente)

# Variável para guardar quais itens serão exibidos na tela
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
        
        # Se tiver equipamentos definidos na planilha do paciente, usa eles
        if pd.notna(previstos_str) and str(previstos_str).strip() != "":
            equipamentos_para_exibir = [item.strip() for item in str(previstos_str).split(",") if item.strip()]
        
        # 🌟 AQUI ESTÁ A MÁGICA DOS TESTES: Se a coluna estiver vazia, abre TODOS os equipamentos do cadastro!
        else:
            if not df_itens.empty:
                equipamentos_para_exibir = df_itens['Item'].tolist()
# ------------------------------------------------------------------------------
# 4. EXIBIÇÃO DINÂMICA DOS CHECKBOXES E CAMPOS
# ------------------------------------------------------------------------------
registros_para_salvar = []

if len(equipamentos_para_exibir) > 0:
    st.markdown("### 2. Conferência de Equipamentos")
    st.info("Marque apenas os equipamentos que estão sendo movimentados agora.")
    
    for equipamento in equipamentos_para_exibir:
        reg_item = df_itens[df_itens['Item'] == equipamento]
        # Procura por 'Patrimonio' sem acento para bater com o que alterou na planilha
        tipo_controle = reg_item.iloc[0]['Tipo de Controle'] if not reg_item.empty else "Por Quantidade"
        
        col_check, col_info, col_dado = st.columns([1, 4, 4])
        
        with col_check:
            marcado = st.checkbox("Sim", key=f"check_{equipamento}")
            
        with col_info:
            st.markdown(f"**{equipamento}** \n*Controle: {tipo_controle}*")
            
        with col_dado:
            if marcado:
                if tipo_controle == "Por Número de Série":
                    dado_inserido = st.text_input(f"Número de Série do(a) {equipamento}:", key=f"input_{equipamento}")
                elif tipo_controle == "Patrimonio":
                    dado_inserido = st.text_input(f"Código do Patrimônio do(a) {equipamento}:", key=f"input_{equipamento}")
                else:
                    dado_inserido = st.number_input(f"Quantidade de {equipamento}:", min_value=1, value=1, step=1, key=f"input_{equipamento}")
                
                registros_para_salvar.append({
                    "Equipamento": equipamento,
                    "Dado": str(dado_inserido)
                })
        st.markdown("---")

    # ------------------------------------------------------------------------------
    # 5. BOTÃO SALVAR E ATUALIZAÇÃO NO GOOGLE SHEETS
    # ------------------------------------------------------------------------------
    if st.button("💾 Finalizar e Salvar Movimentação", type="primary"):
        nome_final_paciente = novo_paciente_nome if paciente_selecionado == "+ CADASTRAR NOVO PACIENTE (AVULSO)" else paciente_selecionado
        
        if not nome_final_paciente or nome_final_paciente.strip() == "":
            st.error("Por favor, preencha o nome do paciente antes de salvar.")
        elif len(registros_para_salvar) == 0:
            st.warning("Nenhum equipamento foi marcado para movimentação.")
        else:
            try:
                # Carrega o histórico atual (Usando a primeira aba padrão da planilha de histórico)
                df_historico_atual = conn.read(spreadsheet=URL_HISTORICO, ttl="0s")
                
                linhas_novas = []
                data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                
                for reg in registros_para_salvar:
                    linhas_novas.append({
                        "Data/Hora": data_hora_atual,
                        "Unidade": unidade_selecionada,
                        "Operação": operacao_selecionada,
                        "Paciente": nome_final_paciente,
                        "Equipamento": reg["Equipamento"],
                        "Identificação/Qtd": reg["Dado"]
                    })
                
                df_novas_linhas = pd.DataFrame(linhas_novas)
                df_final = pd.concat([df_historico_atual, df_novas_linhas], ignore_index=True)
                
                # Salva os dados na planilha de histórico e de pacientes
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
                
                st.success(f"✅ Sucesso! Movimentação de {nome_final_paciente} registrada no Google Sheets!")
                st.balloons()
                
            except Exception as erro_salvar:
                st.error(f"Erro crítico ao tentar salvar no Google Drive: {erro_salvar}")
else:
    if paciente_selecionado != "+ CADASTRAR NOVO PACIENTE (AVULSO)":
        st.info("Nenhum equipamento previsto cadastrado para este paciente no Google Sheets.")
