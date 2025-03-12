import sqlite3

# Conecta (ou cria, se não existir) o arquivo de banco de dados chamado "notas_bolao.db"
conn = sqlite3.connect('notas_bolao.db')
cursor = conn.cursor()

# Cria a tabela "notas_bolao" se ela não existir
cursor.execute('''
    CREATE TABLE IF NOT EXISTS notas_bolao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,  -- identificador único para cada registro
        DT_RECEBIMENTO TEXT,                   -- data de recebimento da nota
        N_NF TEXT,                             -- número da nota fiscal
        PESO INT ,                             -- peso da nota fiscal
        FORNECEDOR TEXT,                       -- nome do fornecedor
        CHAVE_NF TEXT,                         -- chave da nota fiscal (usei underscore para não ter problemas com espaços)
        STATUS TEXT,                           -- status da nota (ex: Pendente, Processada, Cancelada)
        DATA_ENVIO TEXT,                       -- data de saida da mercadoria do galpão para entrega ao cliente
        CAMINHO_DO_PDF TEXT                   -- caminho do arquivo PDF salvo    
    )
''')

# Salva (commita) as alterações e fecha a conexão
conn.commit()
conn.close()

print("Banco de dados e tabela criados com sucesso!")
