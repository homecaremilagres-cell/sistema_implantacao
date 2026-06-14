import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Ajusta o visual para ficar excelente no celular
st.set_page_config(page_title="Gestão de Equipamentos Home Care", layout="centered")

# Estilo CSS para o visual
st.markdown("""
    <style>
        .titulo-principal {
            color: #FF4B4B;
            font-size: 2.2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .subtitulo-descricao {
            color: #555;
            font-size: 1.0rem;
            margin-bottom: 2rem;
        }
        div[data-baseweb="input"] {
            background-color: #f9f9f9;
        }
        div[data-testid="stCameraInput"] {
            margin-top: -15px;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="titulo-principal">📋 Sistema de Movimentação</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo-descricao">Controle de entregas (Implantação) e retiradas (Explantação) por unidade operacional.</p>', unsafe_allow_html=True)

# --- CONFIGURAÇÃO DOS ARQUIVOS E PASTAS ---
EXCEL_HISTORICO = "implantacoes.xlsx"          
EXCEL_EQUIPAMENTOS = "cadastro_equipamentos.xlsx" 
EXCEL_PACIENTES = "lista_pacientes.xlsx"       
PASTA_FOTOS = "fotos_patrimonio"               

if not os.path.exists(PASTA_FOTOS):
    os.makedirs(PASTA_FOTOS)

# --- INTERFACE NO CELULAR: SELEÇÃO DE OPERAÇÃO ANTES PARA FILTRAGEM ---

col_unid, col_oper = st.columns(2)

with col_unid:
    unidade_selecionada = st.selectbox("Selecione sua Unidade:", ["BRASÍLIA", "GOIÂNIA"])

with col_oper:
    operacao_selecionada = st.selectbox("Tipo de Operação:", ["Implantação (Entrega)", "Explantação (Retirada)"])


# --- VERIFICAÇÃO E LEITURA DOS ARQUIVOS EXTERNOS ---

# 1. Lendo os Equipamentos (Com auto-criação automática caso não exista)
if os.path.exists(EXCEL_EQUIPAMENTOS):
    try:
        df_itens = pd.read_excel(EXCEL_EQUIPAMENTOS, sheet_name="cadastro_equipamentos")
        df_itens.columns = ["Item", "Tipo de Controle"] + list(df_itens.columns[2:])
        df_itens["Item"] = df_itens["Item"].astype(str).str.strip()
        df_itens["Tipo de Controle"] = df_itens["Tipo de Controle"].astype(str).str.strip()
    except Exception as e:
        st.error(f"Erro ao ler o arquivo de itens: {e}")
        st.stop()
else:
    # Cria uma lista fictícia de teste se o arquivo não existir na nuvem
    df_padrao_itens = pd.DataFrame({
        "Item": ["Concentrador de Oxigênio", "Cama Elétrica Com 3 Movimentos_1", "Máscara Facial", "Cilindro de O2"],
        "Tipo de Controle": ["Patrimônio", "Patrimônio", "Lote", "Patrimônio"]
    })
    with pd.ExcelWriter(EXCEL_EQUIPAMENTOS) as writer:
        df_padrao_itens.to_excel(writer, sheet_name="cadastro_equipamentos", index=False)
    df_itens = df_padrao_itens

# 2. Lendo os Pacientes e a Pré-Implantação (Com auto-criação estruturada)
dicionario_pre_implantacao = {}
lista_pacientes = ["Selecione um paciente...", "➕ CADASTRAR NOVO PACIENTE (AVULSO)"]

if os.path.exists(EXCEL_PACIENTES):
    try:
        df_pacientes_raw = pd.read_excel(EXCEL_PACIENTES)
        df_pacientes_raw.columns = df_pacientes_raw.columns.str.strip()
        df_pacientes_raw.columns = ["Nome", "Equipamentos Previstos", "Unidade"] + list(df_pacientes_raw.columns[3:])
        
        # Filtra por unidade escolhida
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
        st.error(f"Erro ao ler a planilha de pacientes: {e}")
        st.stop()
else:
    # Se rodar na nuvem sem planilha, gera dados simulados para testes rápidos
    df_exemplo_pac = pd.DataFrame({
        "Nome": ["ANA SOUZA (TESTE BSB)", "CARLOS EDUARDO (TESTE GYN)"],
        "Equipamentos Previstos": ["Concentrador de Oxigênio, Máscara Facial", "Cama Elétrica Com 3 Movimentos_1"],
        "Unidade": ["BRASÍLIA", "GOIÂNIA"]
    })
    df_exemplo_pac.to_excel(EXCEL_PACIENTES, index=False)
    
    df_filtrado = df_exemplo_pac[df_exemplo_pac["Unidade"] == unidade_selecionada]
    lista_pacientes.extend(df_filtrado["Nome"].tolist())


# 3. Campo para selecionar o paciente filtrado
paciente_selecionado = st.selectbox("1. Escolha o Paciente:", lista_pacientes)

nome_paciente_final = ""
if paciente_selecionado == "➕ CADASTRAR NOVO PACIENTE (AVULSO)":
    nome_avulso = st.text_input("Digite o nome completo do novo paciente:")
    if nome_avulso.strip() != "":
        nome_paciente_final = nome_avulso.strip().upper()
else:
    if paciente_selecionado != "Selecione um paciente...":
        nome_paciente_final = paciente_selecionado


# O fluxo do checklist só aparece se tivermos um paciente válido
if nome_paciente_final != "":
    
    st.markdown("---")
    st.markdown(f"### 2. Checklist de {operacao_selecionada}")
    st.caption("Marque os itens, informe o controle e registre a foto caso seja Patrimônio.")
    
    # Se for retirada, começa desmarcado. Se for entrega, puxa a pré-implantação
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
    
    # Botão de Envio
    if st.button(f"Finalizar e Salvar {operacao_selecionada.split(' ')[0]}", use_container_width=True):
        
        if "Sim" not in respostas_tecnico.values():
            st.error("Atenção: Você precisa marcar pelo menos um item para salvar o registro!")
            
        else:
            agora = datetime.now()
            data_registro = grandmother = agora.strftime("%Y-%m-%d %H:%M:%S")
            data_nome_foto_base = agora.strftime("%Y%m%d_%H%M%S")
            
            nome_pac_limpo = nome_paciente_final.replace(" ", "_")
            tipo_acao_limpa = "ENTREGA" if "Implantação" in operacao_selecionada else "RETIRADA"
            
            dados_linha = {
                "Data/Hora": data_registro,
                "Unidade": unidade_selecionada,
                "Operação": tipo_acao_limpa,
                "Paciente": nome_paciente_final
            }
            
            # Processamento das fotos
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
                    
            # Salvamento no Histórico
            df_nova_linha = pd.DataFrame([dados_linha])
            if os.path.exists(EXCEL_HISTORICO):
                df_historico_atual = pd.read_excel(EXCEL_HISTORICO)
                df_final = pd.concat([df_historico_atual, df_nova_linha], ignore_index=True)
            else:
                df_final = df_nova_linha
            df_final.to_excel(EXCEL_HISTORICO, index=False)
            
            # Salvamento automático do novo paciente avulso na lista oficial
            if paciente_selecionado == "➕ CADASTRAR NOVO PACIENTE (AVULSO)":
                if os.path.exists(EXCEL_PACIENTES):
                    df_pac_atual = pd.read_excel(EXCEL_PACIENTES)
                    df_pac_atual.columns = ["Nome", "Equipamentos Previstos", "Unidade"] + list(df_pac_atual.columns[3:])
                    
                    if nome_paciente_final not in df_pac_atual["Nome"].astype(str).values:
                        df_novo_pac = pd.DataFrame([{"Nome": nome_paciente_final, "Equipamentos Previstos": "", "Unidade": unidade_selecionada}])
                        df_pac_final = pd.concat([df_pac_atual, df_novo_pac], ignore_index=True)
                        df_pac_final.to_excel(EXCEL_PACIENTES, index=False)
            
            st.success(f"Excelente! Registro de {tipo_acao_limpa} do paciente {nome_paciente_final} foi salvo com sucesso!")
            st.balloons()
