import streamlit as st 
import sqlite3
import os
import pandas as pd
import datetime
import io
import zipfile
import time
import uuid
from io import BytesIO
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaFileUpload


# Caminho para o arquivo JSON da conta de serviço
SERVICE_ACCOUNT_FILE = "drive_credentials.json"  # Confirme se o arquivo JSON está no mesmo diretório do script

# Escopo da API do Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive"]


# Autenticação com as credenciais
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Criar o serviço do Google Drive
drive_service = build("drive", "v3", credentials=credentials)

# ID da pasta no Google Drive onde os PDFs serão armazenados
FOLDER_ID = "1sb5KW9rj5yRwwIyljw-WqO3Yx6ffzWvq"  # Substitua pelo ID correto da pasta no Google Drive


def listar_arquivos_drive(folder_id):
    """Retorna uma lista de arquivos dentro da pasta do Google Drive."""
    query = f"'{folder_id}' in parents"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])



def baixar_zip_filtrado(df_filtrado_pendentes):
    """Cria um ZIP contendo apenas os PDFs do DataFrame filtrado no Google Drive."""
    if df_filtrado_pendentes.empty:
        st.warning("Nenhuma nota fiscal encontrada para os filtros selecionados.")
        return None
    arquivos_drive = listar_arquivos_drive(FOLDER_ID)
    # Criar dicionário para correspondência exata de nomes
    arquivos_dict = {arquivo["name"].strip(): arquivo["id"] for arquivo in arquivos_drive}

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for _, row in df_filtrado_pendentes.iterrows():
            nome_pdf = os.path.basename(row["CAMINHO_DO_PDF"]).strip()

            if nome_pdf in arquivos_dict:
                file_id = arquivos_dict[nome_pdf]

                # Baixar o arquivo do Google Drive
                request = drive_service.files().get_media(fileId=file_id)
                file_data = io.BytesIO()
                downloader = MediaIoBaseDownload(file_data, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()

                # Adicionar ao ZIP
                zip_file.writestr(nome_pdf, file_data.getvalue())

            else:
                st.warning(f"⚠️ Arquivo {nome_pdf} não encontrado no Google Drive.")

    zip_buffer.seek(0)
    return zip_buffer


def upload_to_drive(file_path, file_name):
    """
    Envia um arquivo PDF para o Google Drive, 
    mantendo o mesmo nome do PDF local.
    """
    file_metadata = {
        "name": file_name,          # Usa exatamente o mesmo nome local
        "parents": ["1sb5KW9rj5yRwwIyljw-WqO3Yx6ffzWvq"]      # Substitua FOLDER_ID pelo ID da pasta no Drive
    }
    
    media = MediaFileUpload(file_path, mimetype="application/pdf")
    
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    # Torna o arquivo público (opcional, mas comum para permitir download)
    drive_service.permissions().create(
        fileId=file["id"],
        body={"role": "reader", "type": "anyone"},
    ).execute()

    st.success("Nota salva no drive com sucesso!!")
    time.sleep(2)
    return file["id"]  # Você pode retornar só o ID ou montar um link


#---------------------------------------------------------------------#
#--- Configurando como se comportara a pagina do streamlit------------#
st.set_page_config(
    # Titulo da pagina a ser exibido no navegador
    page_title="Rip Serviços Industriais",
    # icone da pagina a ser exibido no navegador
    page_icon="📦",
    # modo de vizulização das informações na pagina
    layout="wide",
    # inicializar a pagina com o siderbar expandido
    initial_sidebar_state="expanded",
    # itens do menu para pedir ajuda ou suporte e apresentação do projeto
    menu_items={
    'Get Help': 'https://www.logbr.net/ajuda',
    'Report a bug': 'https://www.logbr.net/suporte',
    'About': "# LOGBR - Gestão de Transportes\n\nA plataforma eficiente para monitoramento e controle de cargas armazenadas e entregues. 🚛📦"
}
)
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
#---Definindo as credenciais atraves do screts------------------------#
user_credentials = st.secrets["users"]
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
# Função para conectar ao banco---------------------------------------#
def get_db_connection():
    # Conecta ao banco de dados SQLite criado anteriormente
    conn = sqlite3.connect('notas_bolao.db')
    return conn
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
# Caminho onde está o logo--------------------------------------------#
logo = "/Users/jadeamaral/Library/Mobile Documents/com~apple~CloudDocs/EU/CURSO - CIENTISTA DE DADOS/repos/bolao_rip/log.png"
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
# Funçao de autenticaçao do usuario-----------------------------------#
def autenticar_usuario(username, password):
    # se o user informado constar nas credenciais definidas anteriormente
    if username in user_credentials:
        # verifica se a senha é a senha do usuario nas credenciais
        if password == user_credentials[username]["password"]:
            # se for retorna o role do usuario
            return user_credentials[username]["role"]
        # caso não seja não retorna  nada
    return None
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
# Funçao para conversão de DF em arquivo xlsx-------------------------#
# crio a função que recebe 2 dataframes
def to_excel(df_pendentes , df_entregues):
    # criamos um buffer me memoria, salvando o arquivo na ram e não no computador permitindo ser baixado depois 
    # usei o bytesIo por conta do arquivo temporário do streamlit
    output = BytesIO()
    # criamos um escritor de arquivos pfds usando o excelwriter que escreverá dados no buffer e apelidamos de writer
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # armazenamos em workbok o objeto de workbook do excel
        workbook = writer.book
        # formatamos o cabeçalho 
        header_format = workbook.add_format({
            "bold" : True, # negrito
            "text_wrap" : True, #Quebra de texto automatica
            "align" : "center", # alinha o texto horizontalmente
            "valign" : "vcenter", #Alinha o texto verticalmente 
            "bg_color" : "#D7E4BC", # define cor de fundo
            "border": 1 # borda 
        })
        
        # crio uma lista que contem o dataframe e o nome da guia que será salva no excel
        df_list = [(df_pendentes, "NF_PENDENTES_ENVIO"), (df_entregues , "NF_ENTREGUES")]
        
        # para cada dataframe e aba dentro da listra de dataframes
        for df, sheet_name in df_list:
            # verifique se o dataframe não é vazio
            if not df.empty:
                df = df.drop(columns=["id", "CAMINHO_DO_PDF"], errors='ignore')
                df = df.rename(
                    columns={
                            "DT_RECEBIMENTO" : "DATA RECEBIMENTO",
                            "N_NF" : "NOTA FISCAL",
                            "CHAVE_NF" : "CHAVE DA NOTA FISCAL",
                            "STATUS" : "STATUS DE ENVIO",
                            "DATA_ENVIO" : "DATA DE ENVIO"
                    }
                )
                # se não for transforme em excel utilizando o escritor de arquivos, considere o index falso e o nome da aba será a sheet_name
                df.to_excel(writer, sheet_name=sheet_name,index=False)
                #acessamos a aba recem criada e armazenaos em worksheet permitindo formatação
                worksheet = writer.sheets[sheet_name]
                # 
                for idx, col in enumerate(df.columns):
                    max_len = max(df[col].astype(str).apply(len).max(), len(col))+2
                    worksheet.set_column(idx,idx, max_len)
                
                for col_num, value in enumerate(df.columns):
                    worksheet.write(0,col_num,value,header_format)
                    
                worksheet.add_table(0,0,len(df), len(df.columns) -1 , {
                    "columns": [{"header": col} for col in df.columns],
                    "style" : "Table Style Medium 9"
                })
                         
        # writer.close()
        
    output.seek(0)
    return output.getvalue()
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
# Funçao para limpar os campos do formulario -------------------------#
def limpar_campos():
    for key in ["n_nf", "peso", "fornecedor", "chave_nf", "status"]:
        if key in st.session_state:
                del st.session_state[key]
    
    st.session_state["pdf_file"] = str(uuid.uuid4())
    st.rerun() 
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
# Inicialização do Session State--------------------------------------#
# Definimos o Session_state para armazenar o estado de logado ou não e definir valores as variaveis
# Se logged_ind não estivr no session_state
if "logged_in" not in st.session_state:
    # definir como logged_ind - Falso
    st.session_state["logged_in"] = False
# se não possuir "role" no session_state
if "role" not in st.session_state:
    # definir role como non
    st.session_state["role"] = None
# se não tiver username no session_state
if "username" not in st.session_state:
    # defirnir username como vazio
    st.session_state["username"] = ""
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
# Sistema de Login----------------------------------------------------#
# se o session_state de login for falso
if not st.session_state["logged_in"]:
    # Abrir a Siderbar com o titulo
    st.sidebar.title("Login")
    # logo da sidebar
    st.logo(logo, size="large")
    # inserir input de username ao usuario
    username = st.sidebar.text_input("Usuário")
    # inserir input de senha ao usuario
    password = st.sidebar.text_input("Senha", type="password")
    # se o botão entrar for clicado (true)
    if st.sidebar.button("Entrar"):
        # armazeno em role o retorno de usarname e senha que serão retornados da função que autentica o usuario
        role = autenticar_usuario(username, password)
        # se tivermos um role
        if role:
            # exibo a mensagem na sidebar de que o loguin foi realizado com sucesso
            st.sidebar.success("Login realizado com sucesso!")
            # dou um tempo de 0.3 segundos para a mensage seguir sendo exibida
            time.sleep(0.3)
            # troco o session_state de logged_in para verdadeiro
            st.session_state['logged_in'] = True
            # passo para o session_state o username autenticado e informado pelo usuario
            st.session_state['username'] = username
            # passo para o session_state o role as informações de usarname e senha
            st.session_state['role'] = role
            # atualizo a pagina
            st.rerun()
        # caso não tenha um role por conta do erro de autenticação
        else:
            # exibo a mensagem de erro
            st.error("Usuário ou senha incorretos")
    # Impede que o resto do código rode até que o login seja feito
    st.stop()
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
# Interface de acordo com o tipo de usuário---------------------------#
# Pega o session_state que havia sido armazenado ao autenticar o usuario, sendo o role o username
role = st.session_state['role']
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#




#---------------------------------------------------------------------#
# LOGIN - MODO ADMINISTRADOR------------------------------------------#
if role == "admin":
    # exiba o titulo de painel administrativo
    st.title("Painel Administrativo")
    # insira o logo 
    st.logo(logo,size="large") 
    # adicione um bem vindo na sidebar
    st.sidebar.markdown("## Bem-vindo!")
    # adicione o boão de sair e caso ele seja clicado
    if st.sidebar.button("Sair"):
            # mude a session_state de login para falso
            st.session_state["logged_in"] = False
            # mudando a session_state do role para nada
            st.session_state["role"] = None
            # e do usuario também
            st.session_state["username"] = ""
            # atualizamos a página
            st.rerun()
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#    
    
    
#---------------------------------------------------------------------#
# ABAS - MODO ADMINISTRADOR-------------------------------------------#  
    # Crio 3 abas
    tab1, tab2, tab3 = st.tabs(["Cadastro", "Atualização", "Visão Cliente"])
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#

    # definindo dat aatual para usar no session_state de data de recebimento
    hoje = datetime.datetime.today()

#---------------------------------------------------------------------#
# DEFINIÇÃO SESSION_STATE - MODO ADMINISTRADOR------------------------# 

    # verifico se data de recebimento já foi estanciada
    if "dt_recebimento" not in st.session_state:
        # se não for estancio com a data atual
        st.session_state.setdefault("dt_recebimento", hoje)
    # verifico se a nota fiscal foi estanciada
    if "n_nf" not in st.session_state:
        # se nao foi estancio como vazio
        st.session_state["n_nf"] = ""
    # verifico se peso foi estanciado
    if "peso" not in st.session_state:
        # se nao foi estancio com 0
        st.session_state["peso"] = 0
    # vejo se fornecedor foi estanciado
    if "fornecedor" not in st.session_state:
        # se não foi estancio com vazio
        st.session_state["fornecedor"] = ""
    # verifico se a chave da nota foi estanciada
    if "chave_nf" not in st.session_state:
        # se não foi estancio com vazio
        st.session_state["chave_nf"] = ""
    # verifico se o status foi estanciado
    if "status" not in st.session_state:
        # se não foi estanciado estancio como pendente
        st.session_state["status"] = "Pendente"
    # verifico se pdf foi estanciado
    if "pdf_file" not in st.session_state:
        # se não foi estancio com uma chave aleatoria para poder limpar o campo depois
        st.session_state["pdf_file"] = str(uuid.uuid4())
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#        
    
#---------------------------------------------------------------------#
# TELA CADASTRO - MODO ADMINISTRADOR----------------------------------# 
    # Na primeira aba    
    with tab1:
        #---------------------------------------------------------------------#
        # crio um formulario chamado form_inserir
        with st.form("form_inserir"):
            # crio o imput de data definindo a chave da estancia
            dt_recebimento = st.date_input("Data de Recebimento", key="dt_recebimento")
            # crio o input de nota fiscal , definindo a chave da estancia
            n_nf = st.text_input("Número da Nota Fiscal", key="n_nf")
            # crio o input de peso , definindo a chave da estancia
            peso = st.number_input("Peso da Nota Fiscal", key="peso")
            # crio o input de fornecedor , definindo a chave da estancia
            fornecedor = st.text_input("Fornecedor",key="fornecedor" )
            # crio o input de chave nota fiscal , definindo a chave da estancia
            chave_nf = st.text_input("Chave da Nota Fiscal", key="chave_nf")
            # crio o input de status , definindo a chave da estancia
            status = st.selectbox("Status", ["Pendente", "Cancelada"], key="status")
            # crio o campo de uploade de pdf e defino a chave dele como a session_state pdf que foi definida anteriormente como chave aleatoria
            pdf_file = st.file_uploader("Upload do PDF", type="pdf", key=st.session_state["pdf_file"])
            # crio o botão de envio do formulario
            submit = st.form_submit_button("Inserir Nota Fiscal")
        #---------------------------------------------------------------------#
        
        
        
            #-----------------------------------------------------------------#
            # Envio informações formulario------------------------------------#
            if submit:
                # se um pdf foi inserido no formulario
                if pdf_file is not None:
                    # definimos o nome da pasta
                    pdf_dir = "pdfs"
                    # caso ela não exista criamos ela utilizando o nome definido
                    if not os.path.exists(pdf_dir):
                        # criando a pasta
                        os.makedirs(pdf_dir)
                    # definindo a data de recebimento formatada para salvar no nome do pdf
                    dt_recebimento_str = dt_recebimento.strftime("%Y%m%d")
                    # definindo o nome do fornecedor sem espaços e em caps lock para salvar o nome do pdf
                    fornecedor_str = fornecedor.replace(" ", "_").upper()
                    # criando a variavel que conterá a frase com o nome do pdf
                    pdf_filename = f"{dt_recebimento_str}_{n_nf}_{fornecedor_str}.pdf"
                    # criando o caminho completo 
                    pdf_path = os.path.join(pdf_dir, pdf_filename)
                    # abre o caminho
                    with open(pdf_path, "wb") as f:
                        # escreve o conteudo do buffer na pasta
                        f.write(pdf_file.getbuffer())
                    # função que salva o pdf na pasta do google
                    drive_link = upload_to_drive(pdf_path, pdf_filename)
                    
                # caso não tenha sido uplodado pdf 
                else:
                    # definimos o caminho como vazio
                    pdf_path = ""
                #-----------------------------------------------------------------#
                
                
                
                #-----------------------------------------------------------------#
                # Insere os dados no banco de dados-------------------------------#
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notas_bolao (DT_RECEBIMENTO, N_NF, PESO ,FORNECEDOR, CHAVE_NF , STATUS, CAMINHO_DO_PDF)
                    VALUES (?, ?, ?, ?,?, ?, ?)
                """, (dt_recebimento.strftime("%Y-%m-%d"), n_nf, peso ,fornecedor, chave_nf, status, pdf_path))
                conn.commit()
                conn.close()
                #-----------------------------------------------------------------#
                
                
                
                #-----------------------------------------------------------------#
                #Envio de mensagem de suceeso-------------------------------------#
                st.success("Nota fiscal inserida com sucesso!")
                # limpeza dos campos
                limpar_campos()
                # atualização da tela
                st.rerun()
                #-----------------------------------------------------------------#
                
                
                
                
        with tab2:
            st.write("Aqui você pode atualizar os status das notas e incluir as datas de envio")
            
            # Conectando ao banco de dados 
            conn = get_db_connection()
            # Selecionando todas as informações da tabela e convertendo em dataframe
            df = pd.read_sql_query("SELECT * FROM notas_bolao", conn)
            
            conn.close()
            
            
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
                    data_envio = st.date_input("Data Envio", value=datetime.datetime.today())
                    novo_status = st.selectbox("Novo Status:", ["Entregue", "Mantovani","Cancelado"])
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
                        # função de apagar pdfs da base de dados ------------------------------------------------------------ ANOTAR DE ARRUMAR VIRAR FUNÇÃO MESMO
                        for idx, row in df_pendentes.iterrows():
                            nome_pdf = os.path.basename(row["CAMINHO_DO_PDF"]).strip()  # Ex: "20250314_65297_PROTENGE.pdf"
                            arquivos_drive = listar_arquivos_drive(FOLDER_ID)
                            arquivos_dict = {arquivo["name"]: arquivo["id"] for arquivo in arquivos_drive}
                            if nome_pdf in arquivos_dict:
                                file_id = arquivos_dict[nome_pdf]
                                drive_service.files().delete(fileId=file_id).execute()   # <- Deletando no Drive
                                st.write(f"PDF {nome_pdf} deletado do Drive.")
                            else:
                                st.warning(f"PDF {nome_pdf} não encontrado no Drive!")
                                                
                        
                        
                        
                        
                        
                        st.success("Todas as notas pendentes foram atualizadas")
                        st.rerun()
            else:
                    st.info("Não há notas pendentes no momento")
        with tab3:
            # st.rerun()
            tab1,tab2 = st.tabs(["Armazenadas", "Enviadas"])
            with tab1:
                st.title("Painel do Cliente")
                st.write("Bem-vindo! Aqui você pode consultar as notas fiscais armazenadas no Galpão e baixar os PDFs.")

                
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
                df_clientes_entregues = df[(df["STATUS"] == "Entregue") | (df["STATUS"] == "Mantovani")]
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


        st.logo(logo,size="large") 
        st.title("Painel do Cliente")
        tab1,tab2 = st.tabs(["📦  Armazenadas", "✅ Enviadas"])
        with tab1:
            st.markdown("📂 Lista de mercadorias armazenadas no galpão e suas respectivas notas fiscais disponíveis para download.")   

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
                df_clientes_entregues = df[(df["STATUS"] == "Entregue") | (df["STATUS"] == "Mantovani")]
                
                df_filtrado_pendentes = df_cliente_pendentes.copy()

                
                st.header("Filtros:")
                col1,col2,col3 = st.columns(3)
                with col1:
                    datas_unicas = df_filtrado_pendentes["DT_RECEBIMENTO"].unique().tolist()
                    dt_recebimento_select = st.multiselect("Data Recebimento", datas_unicas)
                if dt_recebimento_select:
                        df_filtrado_pendentes = df_filtrado_pendentes[df_filtrado_pendentes["DT_RECEBIMENTO"].isin(dt_recebimento_select)]
                    
                with col2:
                    fornecedor_unicos = ["-"] + df_filtrado_pendentes["FORNECEDOR"].unique().tolist()
                    fornecedor_select = st.selectbox("Fornecedor:", fornecedor_unicos)
                if fornecedor_select:
                    if "-" in fornecedor_select:
                        pass
                    else:
                        df_filtrado_pendentes = df_filtrado_pendentes[df_filtrado_pendentes["FORNECEDOR"] == fornecedor_select]
                with col3:
                    nf_unicas = ["-"] + df_filtrado_pendentes["N_NF"].unique().tolist()
                    nf_select = st.selectbox("NF'S:", nf_unicas)
                if nf_select:
                    if "-" in nf_select:
                        pass
                    else:
                      df_filtrado_pendentes = df_filtrado_pendentes[df_filtrado_pendentes["N_NF"] == nf_select]  
                
                df_filtrado_pendentes_exibicao = df_filtrado_pendentes.copy()
                df_filtrado_pendentes_exibicao = df_filtrado_pendentes_exibicao.rename(
                    columns={
                            "DT_RECEBIMENTO" : "DATA RECEBIMENTO",
                            "N_NF" : "NOTA FISCAL",
                            "CHAVE_NF" : "CHAVE DA NOTA FISCAL",
                            "STATUS" : "STATUS DE ENVIO"
                    }
                )
                 
                df_filtrado_pendentes_exibicao = df_filtrado_pendentes_exibicao.set_index("DATA RECEBIMENTO")      
                st.dataframe(df_filtrado_pendentes_exibicao[[ "NOTA FISCAL", "FORNECEDOR", "PESO", "CHAVE DA NOTA FISCAL", "STATUS DE ENVIO"]], use_container_width=True)

                    
                col1,col2 = st.columns(2)
                with col1:
                    if st.button("📂 Gerar ZIP das Notas Fiscais selecionadas"):
                        with st.spinner("Gerando ZIP, aguarde..."):
                            # 🔽 Criar o ZIP apenas com os arquivos filtrados
                            zip_buffer = baixar_zip_filtrado(df_filtrado_pendentes)

                            if zip_buffer:
                                st.download_button(
                                    label="📥 Baixar ZIP com notas fiscais filtradas",
                                    data=zip_buffer,
                                    file_name="notas_fiscais_filtradas.zip",
                                    mime="application/zip"
                                )
                            else:
                                st.info("Nenhum arquivo foi encontrado para gerar o ZIP.")
                        
                    with col2:
                        st.download_button(
                            label="📥 Baixar Relatório Excel das NF disponiveis no Galpão",
                            data=to_excel(df_cliente_pendentes,df_clientes_entregues),
                            file_name="relatorio_notas_bolao.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                       
            with tab2:
                st.write("Acesse as notas fiscais das cargas já entregues e baixe os PDFs quando necessário.")           
                st.header("Filtros:")
                col1,col2,col3 = st.columns(3)
                with col1:
                    df_filtrado_entregues = df_clientes_entregues.copy()
                    
                    datas_unicas = df_filtrado_entregues["DT_RECEBIMENTO"].unique().tolist()
                    dt_recebimento_select = st.multiselect("Data Recebimento", datas_unicas, key="filtro_data")
                if dt_recebimento_select:
                        df_filtrado_entregues = df_filtrado_entregues[df_filtrado_entregues["DT_RECEBIMENTO"].isin(dt_recebimento_select)]
                with col2:
                    fornecedor_unicos = ["-"] + df_filtrado_entregues["FORNECEDOR"].unique().tolist()
                    fornecedor_select = st.selectbox("Fornecedor:", fornecedor_unicos)
                if fornecedor_select:
                    if "-" in fornecedor_select:
                        pass
                    else:
                        df_filtrado_entregues = df_filtrado_entregues[df_filtrado_entregues["FORNECEDOR"] == fornecedor_select]
                with col3:
                    nf_unicas = ["-"] + df_filtrado_entregues["N_NF"].unique().tolist()
                    nf_select = st.selectbox("NF'S:", nf_unicas)
                if nf_select:
                    if "-" in nf_select:
                        pass
                    else:
                      df_filtrado_entregues = df_filtrado_entregues[df_filtrado_entregues["N_NF"] == nf_select]  
                    
                if df_filtrado_entregues is not None and not df_filtrado_entregues.empty:
                    df_filtrado_entregues_exibicao = df_filtrado_entregues.copy()
                    df_filtrado_entregues_exibicao = df_filtrado_entregues_exibicao.rename(
                        columns={
                            "DT_RECEBIMENTO" : "DATA RECEBIMENTO",
                            "N_NF" : "NOTA FISCAL",
                            "CHAVE_NF" : "CHAVE DA NOTA FISCAL",
                            "STATUS" : "STATUS DE ENVIO",
                            "DATA_ENVIO" : "DATA DE ENTREGA"
                         }
                    )
                    df_filtrado_entregues_exibicao = df_filtrado_entregues_exibicao.set_index("DATA RECEBIMENTO") 
                    st.dataframe(df_filtrado_entregues_exibicao[[ "NOTA FISCAL", "FORNECEDOR", "PESO", "CHAVE DA NOTA FISCAL", "STATUS DE ENVIO", "DATA DE ENTREGA"]], use_container_width=True)
                else:
                    st.info("📢 Nenhuma carga entregue registrada até o momento.")  