import streamlit as st
import sqlite3
import os
import pandas as pd
import datetime
import io
import zipfile

# ---------------------------
# Personalizando o streamlit
# ---------------------------
st.set_page_config(
    page_title="Rip Serviços Industriais",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
    'Get Help': 'https://www.logbr.net/ajuda',
    'Report a bug': 'https://www.logbr.net/suporte',
    'About': "# LOGBR - Gestão de Transportes\n\nA plataforma eficiente para monitoramento e controle de cargas armazenadas e entregues. 🚛📦"
}


)

user_credentials = st.secrets["users"]


# ---------------------------
# Função para conectar ao banco
# ---------------------------
def get_db_connection():
    # Conecta ao banco de dados SQLite criado anteriormente
    conn = sqlite3.connect('notas_bolao.db')
    return conn

# ---------------------------
# Dicionário simples com usuários e senhas
# ---------------------------
# users = {
#     "admin": {"password": "admin123", "role": "admin"},
#     "rip_servicos": {"password": "rip", "role": "rip_servicos"}
# }


logo = "/Users/jadeamaral/Library/Mobile Documents/com~apple~CloudDocs/EU/CURSO - CIENTISTA DE DADOS/repos/bolao_rip/log.png"


# ---------------------------
# Função de Login
# ---------------------------
# def login():
#     st.sidebar.title("Login")
#     st.logo(logo,size="large")
#     username = st.sidebar.text_input("Usuário")
#     password = st.sidebar.text_input("Senha", type="password")
#     if st.sidebar.button("Entrar"):
#         if username in users and password == users[username]["password"]:
#             st.session_state['logged_in'] = True
#             st.session_state['username'] = username
#             st.session_state['role'] = users[username]["role"]
#             st.sidebar.success("Login realizado com sucesso!")
#         else:
#             st.sidebar.error("Usuário ou senha incorretos")

# # ---------------------------
# # Verificação do estado do login
# # ---------------------------
# if 'logged_in' not in st.session_state:
#     st.session_state['logged_in'] = False
    
# if 'role' not in st.session_state:
#     st.session_state['role'] = None    


# # Se o usuário ainda não estiver logado, exibe o login e interrompe o restante do app
# if not st.session_state['logged_in']:
#     login()
#     # st.stop()

def autenticar_usuario(username, password):
    if username in user_credentials:
        if password == user_credentials[username]["password"]:
            return user_credentials[username]["role"]
    return None

# st.sidebar.title("Login")
# st.logo(logo,size="large")
# username = st.sidebar.text_input("Usuário")
# password = st.sidebar.text_input("Senha", type="password")
# if st.sidebar.button("Entrar"):
#     role = autenticar_usuario(username, password)
#     if role:
#         st.success("Login realizado com sucesso!")
#         st.session_state['logged_in'] = True
#         st.session_state['username'] = username
#         st.session_state['role'] = role
#     else:
#         st.error("Usuário ou senha incorretos")


# ---------------------------
# Inicialização do Session State
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ---------------------------
# Exibe o Login se não estiver logado
# ---------------------------
if not st.session_state["logged_in"]:
    st.sidebar.title("Login")
    st.logo(logo, size="large")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type="password")

    if st.sidebar.button("Entrar"):
        role = autenticar_usuario(username, password)
        if role:
            # st.success("Login realizado com sucesso!")
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.session_state['role'] = role
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")

    # Impede que o resto do código rode até que o login seja feito
    st.stop()


# ---------------------------
# Interface de acordo com o tipo de usuário
# ---------------------------
role = st.session_state['role']

# ---- Modo Admin: Inserir novas notas fiscais ----
if role == "admin":
    st.title("Painel Administrativo")
    # st.write("Bem-vindo, admin! Aqui você pode inserir novas notas fiscais.")
    tab1, tab2, tab3 = st.tabs(["Cadastro", "Atualização", "Visão Cliente"])
    
    # Verifica se as chaves já existem em st.session_state; se não, cria com valores padrão
    if "dt_recebimento" not in st.session_state:
        st.session_state["dt_recebimento"] = datetime.today()

    if "n_nf" not in st.session_state:
        st.session_state["n_nf"] = ""

    if "peso" not in st.session_state:
        st.session_state["peso"] = 0

    if "fornecedor" not in st.session_state:
        st.session_state["fornecedor"] = ""

    if "chave_nf" not in st.session_state:
        st.session_state["chave_nf"] = ""

    if "status" not in st.session_state:
        st.session_state["status"] = "Pendente"

    if "pdf_file" not in st.session_state:
        st.session_state["pdf_file"] = None
        
    
    
    
    with tab1:
        # Formulário para inserir uma nova nota fiscal
        with st.form("form_inserir"):
            # Campo para escolher a data; o valor padrão é a data atual
            dt_recebimento = st.date_input("Data de Recebimento", value=datetime.today())
            n_nf = st.text_input("Número da Nota Fiscal")
            peso = st.number_input("Peso da Nota Fiscal")
            fornecedor = st.text_input("Fornecedor")
            chave_nf = st.text_input("Chave da Nota Fiscal")
            status = st.selectbox("Status", ["Pendente", "Processada", "Cancelada"])
            # Campo para upload do arquivo PDF
            pdf_file = st.file_uploader("Upload do PDF", type="pdf")
            submit = st.form_submit_button("Inserir Nota Fiscal")
            # 


            # Quando o formulário é submetido...
            if submit:
                # Se um PDF foi enviado, salvamos o arquivo na pasta "pdfs"
                if pdf_file is not None:
                    pdf_dir = "pdfs"
                    # Cria a pasta "pdfs" se ela não existir
                    if not os.path.exists(pdf_dir):
                        os.makedirs(pdf_dir)
                    
                    dt_recebimento_str = dt_recebimento.strftime("%Y%m%d")
                    fornecedor_str = fornecedor.replace(" ", "_").upper()
                    
                    
                    pdf_filename = f"{dt_recebimento_str}_{n_nf}_{fornecedor_str}.pdf"
                    pdf_path = os.path.join(pdf_dir, pdf_filename)
                    # Salva o arquivo
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_file.getbuffer())
                else:
                    pdf_path = ""
                
                # Insere os dados no banco de dados
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notas_bolao (DT_RECEBIMENTO, N_NF, PESO ,FORNECEDOR, CHAVE_NF , STATUS, CAMINHO_DO_PDF)
                    VALUES (?, ?, ?, ?,?, ?, ?)
                """, (dt_recebimento.strftime("%Y-%m-%d"), n_nf, peso ,fornecedor, chave_nf, status, pdf_path))
                conn.commit()
                conn.close()
                st.success("Nota fiscal inserida com sucesso!")
        with tab2:
            st.write("Aqui você pode atualizar os status das notas e incluir as datas de envio")
            
            # Conectando ao banco de dados 
            conn = get_db_connection()
            # Selecionando todas as informações da tabela e convertendo em dataframe
            df = pd.read_sql_query("SELECT * FROM notas_bolao", conn)
            # fechando conexão
            conn.close()
            
            # verificando se há informações no banco de dados
            if df.empty:
                st.info("Não há notas cadastradas para atualizar.")
            else:
                status_filtro = st.selectbox("Filtrar notas por Status", ["Todas", "Pendente", "Processada", "Cancelada", "Enviado"])
                if status_filtro != "Todas":
                    df = df[df["STATUS"] == status_filtro]
            
            st.dataframe(df)
            
            st.write("Atualizar envios:")
            df_pendentes = df[df["STATUS"] == "Pendente"]
            
            if not df_pendentes.empty:
                st.write("Notas Fiscais pendentes de envio:")
                st.dataframe(df_pendentes)
                
                with st.form("form_enviar_pendentes"):
                    st.write("Atualização de Envio:")
                    data_envio = st.date_input("Data Envio", value=datetime.today())
                    novo_status = st.selectbox("Novo Status:", ["Entregue", "Cancelado"])
                    confirmar = st.form_submit_button("Enviar todas pendentes")
                    
                    if confirmar:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                                    UPDATE notas_bolao
                                    SET STATUS = ? , DATA_ENVIO = ?
                                    WHERE STATUS = "Pendente"
                                    """, (novo_status, data_envio.strftime("%Y-%m-%d")))
                        conn.commit()
                        conn.close()
                        st.success("Todas as notas pendentes foram atualizadas")
            else:
                    st.info("Não há notas pendentes no momento")
        with tab3:
            tab1,tab2 = st.tabs(["Armazenadas", "Enviadas"])
            with tab1:
                st.title("Painel do Cliente")
                st.write("Bem-vindo! Aqui você pode consultar as notas fiscais armazenadas no Galpão e baixar os PDFs.")

                # Conecta ao banco de dados e lê os registros em um DataFrame do pandas
                conn = get_db_connection()
                try:
                    df = pd.read_sql_query("SELECT * FROM notas_bolao", conn)
                except Exception as e:
                    st.error("Erro ao carregar os dados: " + str(e))
                    df = None
                finally:
                    conn.close()

                # Se existirem dados, exibe-os
                if df is not None and not df.empty:
                    df_cliente_pendentes = df[df["STATUS"] == "Pendente"]
                    st.dataframe(df_cliente_pendentes[["DT_RECEBIMENTO", "N_NF", "PESO", "FORNECEDOR", "CHAVE_NF", "STATUS"]])
                    # st.write("Baixar PDFs das Mercadorias em Galpão:")
                    if not df_cliente_pendentes.empty:
                        # Cria um buffer em memória para o ZIP
                        zip_buffer = io.BytesIO()
                        
                        # Cria o arquivo ZIP e adiciona os PDFs pendentes
                        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                            for index, row in df_cliente_pendentes.iterrows():
                                caminho_pdf = row["CAMINHO_DO_PDF"]
                                if caminho_pdf and os.path.exists(caminho_pdf):
                                    # Usa o nome base do arquivo para evitar incluir caminhos completos dentro do ZIP
                                    zip_file.write(caminho_pdf, arcname=os.path.basename(caminho_pdf))
                        
                        # Posiciona o ponteiro do buffer no início
                        zip_buffer.seek(0)
                        
                        # Exibe o botão para download do ZIP
                        st.download_button(
                            label="Baixar Todas as NF disponiveis no Galpão",
                            data=zip_buffer,
                            file_name="notas_fiscais_pendentes.zip",
                            mime="application/zip"
                        )
                    else:
                        st.info("Não há notas fiscais pendentes para baixar.")
                    
                    
                    
            
                else:
                    st.info("Nenhuma nota fiscal encontrada no sistema.")   
            with tab2:
                st.write("Aqui você pode consultar as notas fiscais entregues e baixar os PDFs.")           
                df_clientes_entregues = df[df["STATUS"] == "Entregue"]
                if df_clientes_entregues is not None and not df_clientes_entregues.empty:
                    st.dataframe(df_clientes_entregues)
                else:
                    st.info("Cargas não entregues ainda")           
                            
                        

# ---- Modo Cliente: Consultar e Baixar Notas Fiscais ----
elif role == "rip_servicos":
        # Exibição do título
        st.sidebar.markdown("## Bem-vindo!")

        # Nome da empresa
        st.sidebar.markdown("### RIP SERVIÇOS INDUSTRIAIS")
        st.sidebar.markdown("""
                                🔹 **Nosso sistema facilita a consulta das suas mercadorias!**  
                                Agora você pode acompanhar, em tempo real, todas as **notas fiscais armazenadas no nosso galpão**.  

                                📌 **Funcionalidades disponíveis:**  
                                - Consulta de **data de recebimento**, **fornecedor**, **peso** e **status** da carga.  
                                - **Baixar todas as NFs** disponíveis para maior controle e organização.  

                                ❓ **Dúvidas ou suporte?**  
                                Entre em contato com a nossa equipe. Estamos prontos para oferecer a melhor experiência para você! 🚛📦
                                """)
        if st.sidebar.button("Sair"):
            st.session_state["logged_in"] = False
            # Pode zerar as outras chaves se quiser
            st.session_state["role"] = None
            st.session_state["username"] = ""
            st.rerun()

        # botao = st.sidebar.button("Sair")
        # if botao:
        #     st.logout()
        st.logo(logo,size="large") 
        st.title("Painel do Cliente")
        tab1,tab2 = st.tabs(["📦  Armazenadas", "✅ Enviadas"])
        with tab1:
            # st.write("Bem-vindo! Aqui você pode consultar as notas fiscais armazenadas no Galpão e baixar os PDFs.")
            st.markdown("📂 Lista de mercadorias armazenadas no galpão e suas respectivas notas fiscais disponíveis para download.")
            st.divider()
            st.header("Filtros:")
            # with st.expander("Filtros:"):
            col1,col2,col3 = st.columns(3)   
            with col1:
                dt_recebimento_select = st.multiselect("Data Recebimento", ["11/03/2025", "07/03/2025", "06/03/2025", "28/02/2025"])
                
            with col2:
                fornecedor_select = st.selectbox("Fornecedor:", ["-","INDUSTRIA DE PECAS","ARGONSOLDAS", "APARECIDA DE MAGDALA","BALASKA"])
            with col3:
                # st.date_input("Data Recebimento", value=datetime.date(2019, 7, 6))
                nf_select = st.selectbox("NF'S:", ["-",1,2,3,4])
            st.divider()

            # Conecta ao banco de dados e lê os registros em um DataFrame do pandas
            conn = get_db_connection()
            try:
                df = pd.read_sql_query("SELECT * FROM notas_bolao", conn)
            except Exception as e:
                st.error("Erro ao carregar os dados: " + str(e))
                df = None
            finally:
                conn.close()

            # Se existirem dados, exibe-os
            if df is not None and not df.empty:
                df_cliente_pendentes = df[df["STATUS"] == "Pendente"]
                st.dataframe(df_cliente_pendentes[["DT_RECEBIMENTO", "N_NF", "PESO", "FORNECEDOR", "CHAVE_NF", "STATUS"]])
                # st.write("Baixar PDFs das Mercadorias em Galpão:")
                if not df_cliente_pendentes.empty:
                    # Cria um buffer em memória para o ZIP
                    zip_buffer = io.BytesIO()
                    
                    # Cria o arquivo ZIP e adiciona os PDFs pendentes
                    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                        for index, row in df_cliente_pendentes.iterrows():
                            caminho_pdf = row["CAMINHO_DO_PDF"]
                            if caminho_pdf and os.path.exists(caminho_pdf):
                                # Usa o nome base do arquivo para evitar incluir caminhos completos dentro do ZIP
                                zip_file.write(caminho_pdf, arcname=os.path.basename(caminho_pdf))
                    
                    # Posiciona o ponteiro do buffer no início
                    zip_buffer.seek(0)
                    
                    # Exibe o botão para download do ZIP
                    st.download_button(
                        label="📥 Baixar todas as NF disponiveis no Galpão",
                        data=zip_buffer,
                        file_name="notas_fiscais_pendentes.zip",
                        mime="application/zip"
                    )
                else:
                    st.info("Não há notas fiscais pendentes para baixar.")
            else:
                    st.info("Nenhuma nota fiscal encontrada no sistema.")   
            with tab2:
                st.write("Acesse as notas fiscais das cargas já entregues e baixe os PDFs quando necessário.")           
                df_clientes_entregues = df[df["STATUS"] == "Entregue"]
                if df_clientes_entregues is not None and not df_clientes_entregues.empty:
                    st.dataframe(df_clientes_entregues)
                else:
                    st.info("📢 Nenhuma carga entregue registrada até o momento.")  