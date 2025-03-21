import streamlit as st # Biblioteca Streamlit
import sqlite3 # Biblioteca Sqlite
import os # Biblioteca do sistema
import pandas as pd # Biblioteca Pandas <3
import datetime # Biblioteca manupulação datas
import io # Biblioteca para manupular memória (Buffer zip)
import zipfile # Biblioteca para gerar o arquivo zip
import time # Biblioteca para usarmos o sleep
import uuid #Biblioteca usada para gerar a chave aleatórea para limpar o session_state quando pdf cadastrado
from io import BytesIO #Módulo para criar Buffer binario
from googleapiclient.discovery import build #Biblioteca para criar api (drive_service)
from google.oauth2 import service_account #Biblioteca para autenticar a conta do google
from googleapiclient.http import MediaIoBaseDownload,MediaFileUpload #Módulo para fazer upload/download de arquivos com a api da google



#---------------------------------------------------------------------#
#--- Configurando crendenciais, API, drive e caminho pasta------------#
# Caminho para o arquivo JSON da conta de serviço 
SERVICE_ACCOUNT_FILE = "drive_credentials.json"  
# Escopo da API Google Drive - (API que usaremos para manipular os pfds)
SCOPES = ["https://www.googleapis.com/auth/drive"]
# Autenticação com as credenciais - (Carrega o arquivo JSON com as credenciais da conta de serviço)
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
# Criar o serviço do Google Drive
drive_service = build("drive", "v3", credentials=credentials)
# ID da pasta no Google Drive onde os PDFs serão armazenados e baixados
FOLDER_ID = "1sb5KW9rj5yRwwIyljw-WqO3Yx6ffzWvq" 
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
#--- Função para listar os arquivos disponiveis no drive--------------#
def listar_arquivos_drive(folder_id): # Passamos o id como parametro da função
    query = f"'{folder_id}' in parents" # Armazenamos na variavel query que ele procure todos os arquivos cujo campo ‘parents’ contenha esse ID de pasta.
    #utilizamos o metodo list do objeto files para passar a query(forma de pesquisa que queremos), quais informaçoes queremos (id e nome) e executamos armazendo a lista em results
    results = drive_service.files().list(q=query, fields="files(id, name)").execute() 
    return results.get("files", []) #pegamos o dicionario retornado da pesquisa e tentamos acessar a chave files, caso não exista retornamos uma lista vazia []
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
#--- Função para baixar o zip dos pfd---------------------------------# ------------------------------------------ TROQUEI O NOME DO DATAFRAME CASO DE MERDA ANTES TA df_filtrado_pendentes
def baixar_zip_filtrado(df_filtrado):
    # Se o dataframe passado for vazio
    if df_filtrado.empty:
        # exiba um alerta avisando que não tem nota fiscal para os filtros selecionados
        st.warning("Nenhuma nota fiscal encontrada para os filtros selecionados.")
        # não retorna nada
        return None
    # caso exista informações no dataframe...
    # chamamos a função que lista os arquivos presentes na pasta e passamos o id da pasta, armazenamos a lista na variavel arquivos_drive
    arquivos_drive = listar_arquivos_drive(FOLDER_ID)
    # Criamos um dicionario para garantirmos a correnpondecia exata do nome - para cada arquivo da lista , crie um dicionario com o seu nome e id 
    arquivos_dict = {arquivo["name"].strip(): arquivo["id"] for arquivo in arquivos_drive}
    zip_buffer = io.BytesIO() #Criamos um buffer na memoria para armazenar os dados do zip
    
    with zipfile.ZipFile(zip_buffer, "w") as zip_file: #utilizamos o with para criar um bloco de execução onde usaremos o zipfile para criar um novo zip (w) e armazenaremos em zip_buffer
        for _, row in df_filtrado.iterrows(): #utilizamos o _ para ignorar o indice e acessar apenas o conteudo de cada linha do dataframe passado a função
            nome_pdf = os.path.basename(row["CAMINHO_DO_PDF"]).strip() # extraimos apenas o nome do dataframe removendo o diretorio e aproveitamos para remover possiveis espaços em branco

            if nome_pdf in arquivos_dict: # verificamos se o nome encontrado na linha do dataframe está presente na lista de arquivos presentes no google drive
                file_id = arquivos_dict[nome_pdf] # armazenamos em file_id o nome do pdf encontrado no google drive
                request = drive_service.files().get_media(fileId=file_id) # fazemos uma requisição, utilizamos o objeto file e o modulo get media para pegar o pfd e passamos o file_id(nome do pdf) como argumento
                file_data = io.BytesIO() # criamos outro buffer na memória onde armazenaremos o pdf
                downloader = MediaIoBaseDownload(file_data, request) #usamos o modulo media para armazenar no file_data a resposta da requisição realizada
                done = False # criamos a variavel para verificar se o downloado terminou
                
                while not done: # o loop continuar até o dowloand terminar
                    _, done = downloader.next_chunk() #chamamos o metodo next_chunck para que ele baixe mais um pedaço e escreva em file_data
                zip_file.writestr(nome_pdf, file_data.getvalue()) # usamos o zip_file e o metodo writestr para inserirmos os pdfs no zip
                
            # caso não exista o nome do pdf na lista de arquivos presentes ele enviará um aviso ao usuário informando que não encontrou o pdf
            else:
                st.warning(f"⚠️ Arquivo {nome_pdf} não encontrado no Google Drive.")
    # retornamos o cursor para o inicio da gravação para podermos baixar e escrever outros zips no mesmo bufffer apos utilizar 
    zip_buffer.seek(0)
    return zip_buffer # retorna o buffer 
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
#Função para subir os pdfs na pasta do google drive-------------------#
def upload_to_drive(file_path, file_name): # Função criada para envio do pdf para o google drive mantendo o mesmo nome do pdf local
    file_metadata = {
        "name": file_name,# Nome do arquivo
        "parents": ["1sb5KW9rj5yRwwIyljw-WqO3Yx6ffzWvq"]# ID da pasta onde será salvo o pdf
    }
    
    media = MediaFileUpload(file_path, mimetype="application/pdf") # usamos o metodo media fileupload para pegar o caminho do pdf e enviamos para requisição
    file = drive_service.files().create( #usamos o drive_service, acessamos o objeto files e com o metodo create 
        body=file_metadata, # Passamos o nome do arquivo e o id da pasta
        media_body=media, # passamos o metodo que será usado
        fields="id" #informamos que queremos apenas o retorno do id
    ).execute() # executamos a ação

    # Torna o arquivo público (opcional, mas comum para permitir download)
    drive_service.permissions().create( #tornamos o arquivo publico para permitiro o download
        fileId=file["id"], # pegamos o  id 
        body={"role": "reader", "type": "anyone"}, #alteramos atraves do id para leitura qualquer um
    ).execute() # exeuctamos a ação

    st.success("Nota salva no drive com sucesso!!") # Emitimos a  mensagem de sucesso 
    time.sleep(0.8) # damos um tempo para a mensagem ser exibida
    return file["id"]  # retornamos o id caso seja preciso um dia deletar ou ajustar esse arquivo sem precisar de match por nome
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#



#---------------------------------------------------------------------#
#Função para deleção dos pdfs na pasta do google drive----------------#
def deletar_drive(df): #passamos o dataframe para função
    for idx, row in df.iterrows(): # interamos sobre o dataframe, e pegamos o index de cada linha
        nome_pdf = os.path.basename(row["CAMINHO_DO_PDF"]).strip()  #armazenamos na variavel nome pdf, o nome do pdf na coluna caminho, removemos vazio e retiramos o caminho do nome da base
        arquivos_drive = listar_arquivos_drive(FOLDER_ID) # chamamos a função para listar os arquivos do drive
        arquivos_dict = {arquivo["name"]: arquivo["id"] for arquivo in arquivos_drive} # criamos um dicionario pegando o nome do arquivo e o ida para cada arquivo presente no dicionario
        if nome_pdf in arquivos_dict: # se o nome do pdf estiver presente no dicionario 
            file_id = arquivos_dict[nome_pdf] # armazenamos na variavel a busca do nome do pdf no dicionario
            drive_service.files().delete(fileId=file_id,supportsAllDrives=True).execute()   # usamos o objeto file e o metodo delete para deletar o arquivo pelo nome e executamos o processo
            st.write(f"PDF {nome_pdf} deletado do Drive.") # exibimos ao usuario a mensagem de que o pdf foi deletado no drive
        else: # caso o nome do pdf não esteja presente no dicionario
            st.warning(f"PDF {nome_pdf} não encontrado no Drive!") # exibimos ao usuario a mensagem de erro
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
    cadastro, atualizaçao, visao_cliente = st.tabs(["Cadastro", "Atualização", "Visão Cliente"])
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
        
        
        
        
        
        
        
    if "zip_ready" not in st.session_state:
        st.session_state["zip_ready"] = False

    if "zip_buffer" not in st.session_state:
        st.session_state["zip_buffer"] = None    
        
        
        
        
        
        
        
        
#---------------------------------------------------------------------#
#---------------------------------------------------------------------#        
    
#---------------------------------------------------------------------#
# TELA CADASTRO - MODO ADMINISTRADOR----------------------------------# 
    # Na primeira aba    
    with cadastro:
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
                
                
                
       #-----------------------------------------------------------------#
       #ABA ATUALIZAÇÃO--------------------------------------------------#         
        with atualizaçao: # na aba atualização      
            #CONEXÃO COM O BANCO DE DADOS--------------------------------# 
            conn = get_db_connection() # Conectamos no banco de dados
            df = pd.read_sql_query("SELECT * FROM notas_bolao", conn) #selecionamos todos os dados da tabela e transformamos em um dataframe
            conn.close() # fechamos a conexão com o banco de dados
            #------------------------------------------------------------#
            
            #VERIFICAÇÃO DO DATAFRAME------------------------------------#
            if df.empty: # se o dataframe estiver vazio
                st.info("Não há notas cadastradas para atualizar.") #exibimos a mensagem de que não tem notas a serem cadastradas
            else: # caso exista informações no dataframe
                #ALTERAÇÃO DO DATAFRAME----------------------------------#
                df_pendentes_atualizar = df[df["STATUS"] == "Pendente"].copy() # geramos uma copia do dataframe original realizando o filtro de status por pendente
                st.write("Notas Fiscais pendentes de envio:") # exibimos na tela 
                df_pendentes_atualizar = df_pendentes_atualizar.rename( # renomeamos as colunas do dataframe antes da exibição
                    columns={
                        "DT_RECEBIMENTO" : "DATA RECEBIMENTO",
                        "N_NF" : "NOTA FISCAL",
                        "CHAVE_NF": "CHAVE NOTA FISCAL",
                        "DATA_ENVIO" : "DATA ENVIO"
                    })
                df_pendentes_atualizar = df_pendentes_atualizar.set_index("DATA RECEBIMENTO") # setamos o index para data de recebimento para ficar melhor na vizualização
                #EXIBIÇÃO DO DATAFRAME-----------------------------------#
                st.dataframe(df_pendentes_atualizar[["NOTA FISCAL", "PESO", "FORNECEDOR", "CHAVE NOTA FISCAL", "STATUS", "DATA ENVIO"]], use_container_width=True) #exibimos o dataframe com as colunas selecionadas

                #CRIAÇÃO DO FORMULARIO DE ENVIO--------------------------#
                with st.form("form_enviar_pendentes"): # No formulario 
                    st.write("Atualização de Envio:") # escrevemos
                    data_envio = st.date_input("Data Envio", value=datetime.datetime.today()) # inserimos o input de data, definindo a data base como atual
                    novo_status = st.selectbox("Novo Status:", ["Entregue", "Mantovani"]) # Inserindo as opções de novo status
                    confirmar = st.form_submit_button("Enviar todas pendentes") #crimos o botão de envio do formulario
                    if confirmar: # se o botão for clicado (true)
                        #CONEXÃO COM O BANCO DE DADOS--------------------#
                        conn = get_db_connection() # realizamos a conexão com o banco de dados
                        cursor = conn.cursor() # criamos o cursor para poder navegar no banco
                        cursor.execute(""" 
                                    UPDATE notas_bolao
                                    SET STATUS = ? , DATA_ENVIO = ?
                                    WHERE STATUS = "Pendente"
                                    """, (novo_status, data_envio.strftime("%Y-%m-%d"))) # atraves do cursor executamos a query de atualizar a tabela, passamos os paramos de status e envio
                                                                                         # para os dados onde o status estão como pendente
                        conn.commit() # realizamos a alteração
                        conn.close() # fechamos o banco de dados 
                        #DELEÇÃO DO DRIVE--------------------------------#
                        deletar_drive(df_pendentes_atualizar) # chamamos a função para deletar o pdf do drive                                                                                                                     
                        st.success("Todas as notas pendentes foram atualizadas") # exibimos a mensagem de sucesso
                        st.rerun() # atualizamos
       #-----------------------------------------------------------------#
       #-----------------------------------------------------------------#                 
                        
                        
                    
       #-----------------------------------------------------------------#
       #ABA VISAO CLIENTE------------------------------------------------# 
        with visao_cliente:
            st.logo(logo,size="large") 
            st.title("Painel do Cliente")
            armazenadas,enviadas = st.tabs(["📦  Armazenadas", "✅ Enviadas"])
            with armazenadas:
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
                        dt_recebimento_select = st.multiselect("DATA RECEBIMENTO:", datas_unicas)
                    if dt_recebimento_select:
                            df_filtrado_pendentes = df_filtrado_pendentes[df_filtrado_pendentes["DT_RECEBIMENTO"].isin(dt_recebimento_select)]
                        
                    with col2:
                        fornecedor_unicos = ["-"] + df_filtrado_pendentes["FORNECEDOR"].unique().tolist()
                        fornecedor_select = st.selectbox("FORNECEDOR:", fornecedor_unicos)
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
                    st.dataframe(df_filtrado_pendentes_exibicao[[ "FORNECEDOR","NOTA FISCAL","PESO", "CHAVE DA NOTA FISCAL", "STATUS DE ENVIO"]], use_container_width=True)

                        
                    coluna_zip,coluna_excel = st.columns(2)
                    with coluna_zip:                   
                        if not st.session_state["zip_ready"]:
                            # Só mostra o botão "Gerar ZIP" se ainda não geramos
                            if coluna_zip.button("📂 Gerar ZIP das Notas Fiscais selecionadas"):
                                with st.spinner("⏳ Gerando ZIP, aguarde..."):
                                    # Aqui chamamos a função que gera o ZIP
                                    zip_buffer = baixar_zip_filtrado(df_filtrado_pendentes)
                                    
                                    if zip_buffer:
                                        # Armazena o buffer no session_state
                                        st.session_state["zip_buffer"] = zip_buffer
                                        # Marca que o ZIP está pronto
                                        st.session_state["zip_ready"] = True
                                        st.success("✅ ZIP gerado com sucesso!")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.info("Nenhum arquivo foi encontrado para gerar o ZIP.")
                        else:
                            # Se zip_ready = True, exibimos o botão de download
                            if st.session_state["zip_buffer"]:
                                if coluna_zip.download_button(
                                    label="📥 Baixar ZIP com notas fiscais filtradas",
                                    data=st.session_state["zip_buffer"],
                                    file_name="notas_fiscais_filtradas.zip",
                                    mime="application/zip"
                                ):
                                    time.sleep(0.5)
                                    st.session_state["zip_ready"] = False
                                    st.session_state["zip_buffer"] = None
                                    st.rerun()
                            else:
                                st.info("Nenhum ZIP disponível para download.")    
                                                    
                        with coluna_excel:
                            st.download_button(
                                label="📥 Baixar Relatório Excel das NF disponiveis no Galpão",
                                data=to_excel(df_cliente_pendentes,df_clientes_entregues),
                                file_name="relatorio_notas_bolao.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        
                with enviadas:
                    st.write("Acesse as notas fiscais das cargas já entregues e baixe os PDFs quando necessário.")           
                    st.header("Filtros:")
                    col1,col2,col3,col4,col5 = st.columns(5)
                    with col1:
                        df_filtrado_entregues = df_clientes_entregues.copy()
                        
                        datas_unicas = df_filtrado_entregues["DT_RECEBIMENTO"].unique().tolist()
                        dt_recebimento_select = st.multiselect("DATA RECEBIMENTO:", datas_unicas, key="filtro_data")
                    if dt_recebimento_select:
                            df_filtrado_entregues = df_filtrado_entregues[df_filtrado_entregues["DT_RECEBIMENTO"].isin(dt_recebimento_select)]
                    with col2:
                        fornecedor_unicos = ["-"] + df_filtrado_entregues["FORNECEDOR"].unique().tolist()
                        fornecedor_select = st.selectbox("FORNECEDOR:", fornecedor_unicos)
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
                    with col4:
                        status_unicos = ["-"] + df_filtrado_entregues["STATUS"].unique().tolist()
                        status_select = st.selectbox("STATUS:", status_unicos)
                    if status_select:
                        if "-" in status_select:
                            pass
                        else:
                            df_filtrado_entregues = df_filtrado_entregues[df_filtrado_entregues["STATUS"] == status_select]  
                    with col5:
                        datas_unicas_envio = df_filtrado_entregues["DATA_ENVIO"].unique().tolist()
                        dt_envio_select = st.multiselect("DATA ENVIO", datas_unicas_envio, key="filtro_data_envio")
                    if dt_envio_select:
                            df_filtrado_entregues = df_filtrado_entregues[df_filtrado_entregues["DATA_ENVIO"].isin(dt_envio_select)]        
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
                        st.dataframe(df_filtrado_entregues_exibicao[["FORNECEDOR","NOTA FISCAL", "PESO", "CHAVE DA NOTA FISCAL", "STATUS DE ENVIO", "DATA DE ENTREGA"]], use_container_width=True)
                    else:
                        st.info("📢 Nenhuma carga entregue registrada até o momento.")  
            
          
                            
                        

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