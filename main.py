import customtkinter as ctk
from tkinter import *
from datetime import datetime, timedelta
from tkcalendar import Calendar
import re
import requests
import sqlite3
from tkinter import messagebox
import bcrypt
from PIL import Image
import pandas as pd
from tkinter import filedialog
import xlsxwriter


window = ctk.CTk()

class BackEnd():

    def __init__(self):
        self.conn = None
        self.cursor = None
    
    #limpa os registros de cadastro   
    def limpa_entry_register(self):
        entries = [
            self.name_entry, self.username_entry, self.cpf_entry, self.rg_entry, self.date_entry,
            self.email_entry, self.password_entry, self.cep_entry, self.logradouro_entry, self.bairro_entry,
            self.numero_entry, self.cidade_entry, self.estado_entry, self.agencia_entry, self.conta_entry,
            self.pix_entry, self.convenio_entry
        ]

        combos = [self.sex_combo, self.tipacc_combo, self.bancos_combo]
        
        #limpa widgets de input
        for entry in entries:
            entry.delete(0, END)

        #limpa widgets de combo 
        for combo in combos:
            combo.set("")

    #limpa os registros de login
    def limpa_entry_login(self):
        self.usernamelogin_entry.delete(0, END)
        self.passwordlogin_entry.delete(0, END)

    #conecta o banco de dados
    def conecta_db(self):
        try:
            self.conn = sqlite3.connect('data\quick-finance.db')
            self.cursor = self.conn.cursor()
            print('Banco de dados conectado')
        except sqlite3.Error as e:
            print(f'Erro ao conectar ao banco: {e}')
            raise

    #desconecta o banco de dados
    def desconecta_db(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            print('Banco de dados desconectado')

    #cria a tabela no banco de dados
    def create_tabela(self) :
        self.conecta_db()
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Usuarios(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    cpf CHAR(14) NOT NULL,
                    rg TEXT NOT NULL,
                    date DATE NOT NULL,
                    sex TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    cep TEXT NOT NULL,
                    logradouro TEXT NOT NULL,
                    bairro TEXT NOT NULL,
                    numerocasa TEXT NOT NULL,
                    cidade TEXT NOT NULL,
                    estado TEXT NOT NULL,
                    agencia TEXT NOT NULL,
                    conta TEXT NOT NULL,
                    tipaccount TEXT NOT NULL,
                    bancos TEXT NOT NULL,
                    pix TEXT,
                    convenio TEXT
                    );
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Emprestimos(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    valor_emprestimo REAL NOT NULL,
                    num_parcelas INTEGER NOT NULL,
                    prim_data_pagamento DATE NOT NULL,
                    juros REAL NOT NULL,
                    total_juros REAL NOT NULL,
                    total_final REAL NOT NULL,
                    FOREIGN KEY(username) REFERENCES Usuarios(username)
                );
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS DetailsEmprestimos(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    emprestimo_id INTEGER NOT NULL,
                    parcela INTEGER NOT NULL,
                    data_vencimento TEXT NOT NULL,
                    valor_parcela REAL NOT NULL,
                    amortizacao REAL NOT NULL,
                    juros REAL NOT NULL,
                    saldo_devedor REAL NOT NULL,
                    status_pagamento TEXT DEFAULT 'Disponível', 
                    FOREIGN KEY(emprestimo_id) REFERENCES Emprestimos(id)
                    CHECK (status_pagamento IN ('Efetuado', 'Em atraso', 'Disponível'))
                );
            ''')
            self.conn.commit()
            print('Tabela criada com sucesso!')
        except sqlite3.Error as e:
            print(f"Erro ao criar tabela: {e}")
        finally:
            self.desconecta_db()
    
    #atualiza o status das parcelas
    def update_payment_status(self):
        """Atualiza o status das parcelas atrasadas."""
        self.conecta_db()
        today = datetime.now().strftime('%d/%m/%Y')
        try:
            # Atualiza o status das parcelas vencidas
            self.cursor.execute('''
                UPDATE DetailsEmprestimos
                SET status_pagamento = 'Em atraso'
                WHERE data_vencimento < ? AND status_pagamento = 'Disponível'
            ''', (today,))
            
            # Para o caso de pagamento que já ocorreram
            self.cursor.execute('''
                UPDATE DetailsEmprestimos
                SET status_pagamento = 'Efetuado'
                WHERE data_vencimento < ? AND status_pagamento = 'Em atraso'
            ''', (today,))
            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f'Erro ao atualizar status de status_pagamento: {e}')
        finally:
            self.desconecta_db()

    #processa o pagamento
    def process_payment(self, parcela_id):
        """Registra o pagamento de uma parcela."""
        self.conecta_db()
        try:
            self.cursor.execute('''
                UPDATE DetailsEmprestimos
                SET status_pagamento = 'Efetuado'
                WHERE id = ? AND status_pagamento IN ('Disponível', 'Em atraso')
            ''', (parcela_id,))
            self.conn.commit()

            # Verificar se a atualização foi efetiva
            print(f"Pagamento da parcela {parcela_id} realizado com sucesso.\nO valor será debitado do seu cartão cadastrado.")
            
            # Verificação após atualização
            self.cursor.execute('SELECT status_pagamento FROM DetailsEmprestimos WHERE id = ?', (parcela_id,))
            status = self.cursor.fetchone()
            print(f"Status atual: {status[0] if status else 'não encontrado'}")  # Ajustado para evitar erro de sintaxe

            messagebox.showinfo('Sucesso', f"Pagamento da parcela {parcela_id} realizado com sucesso.\nO valor será debitado do seu cartão cadastrado.")
        except sqlite3.Error as e:
            messagebox.showerror('Erro', f'Erro ao processar pagamento: {e}')
        finally:
            self.desconecta_db()

    #busca as parcelas
    def fetch_installments(self, emprestimo_id):
        self.conecta_db()
        try:
            self.cursor.execute('''
                SELECT id, parcela, data_vencimento, valor_parcela, status_pagamento
                FROM DetailsEmprestimos
                WHERE emprestimo_id = ?
            ''', (emprestimo_id,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f'Erro ao buscar parcelas: {e}')
            return []
        finally:
            self.desconecta_db()

    #gera o relatório
    def generate_report(self, report_type):
        try:
            if report_type == 'clientes':
                #consulta todos os usuários
                self.conecta_db()
                self.cursor.execute('SELECT name, username, cpf, rg, email FROM Usuarios')
                users = self.cursor.fetchall()
                
                #cria um DataFrame
                df = pd.DataFrame(users, columns=['Nome', 'Username', 'CPF', 'RG', 'Email'])
                report_name = "relatorio_clientes.xlsx"
            
            elif report_type == 'emprestimos':
                #consulta todos os empréstimos
                self.conecta_db()
                self.cursor.execute('''
                    SELECT u.name, e.valor_emprestimo, e.prim_data_pagamento, e.num_parcelas
                    FROM Emprestimos e
                    JOIN Usuarios u ON e.username = u.username
                ''')
                loans = self.cursor.fetchall()
                
                #cria um DataFrame
                df = pd.DataFrame(loans, columns=['Nome do Cliente', 'Valor do Empréstimo', 'Data da 1ª Parcela', 'Parcelas'])
                report_name = "relatorio_emprestimos.xlsx"
            
            #path para salvar arquivo
            file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                    filetypes=[("Excel files", "*.xlsx")],
                                                    initialfile=report_name)
            if file_path:
                #limpa o DataFrame para linhas vazias
                df = df.dropna(how='all')

                with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                    #escreve os dados sem indice
                    df.to_excel(writer, sheet_name='Dados', index=False)
                    
                    workbook = writer.book
                    worksheet = writer.sheets['Dados']
                    
                    #define os formatos
                    format_header = workbook.add_format({
                        'bold': True,
                        'font_size': 12,
                        'font_name': 'Poppins',
                        'font_color': 'white',
                        'bg_color': '#f78d35',
                        'align': 'center',
                        'valign': 'vcenter',
                        'border': 1
                    })

                    #formata as células
                    format_cells = workbook.add_format({
                        'font_name': 'Poppins',
                        'align': 'center',
                        'valign': 'vcenter',
                        'border': 1
                    })

                    #formatação monetária
                    format_currency = workbook.add_format({
                        'num_format': '#,##0.00',
                        'font_name': 'Poppins',
                        'align': 'center',
                        'valign': 'vcenter',
                        'border': 1
                    })

                    #função para calcular a coluna
                    def get_column_width(series, column_name):
                        # Largura do cabeçalho
                        max_header_length = len(str(column_name))
                        
                        # Largura do conteúdo
                        content_lengths = [len(str(val)) for val in series if pd.notna(val)]
                        max_content_length = max(content_lengths) if content_lengths else 0
                        
                        # Adicionar padding extra para melhor visualização
                        base_width = max(max_header_length, max_content_length)
                        return base_width + 4

                    #configura as larguras das colunas
                    for col_num, column in enumerate(df.columns):
                        width = get_column_width(df[column], column)
                        worksheet.set_column(col_num, col_num, width)

                    #cria uma tabela Excel
                    table_range = f'A1:{chr(65 + len(df.columns) - 1)}{len(df) + 1}'
                    worksheet.add_table(table_range, {
                        'name': 'DadosTabela',
                        'style': 'Table Style Medium 14',  # Estilo da tabela
                        'columns': [
                            {
                                'header': column,
                                'header_format': format_header,
                                'format': format_currency if column == 'Valor do Empréstimo' else format_cells
                            } for column in df.columns
                        ],
                        'autofilter': True  # Adiciona filtros automáticos
                    })

                    #ajusta altura das linhas
                    worksheet.set_row(0, 30)  # Altura do cabeçalho
                    for row in range(1, len(df) + 1):
                        worksheet.set_row(row, 20)  # Altura das células de dados

                messagebox.showinfo("Sucesso", f"Relatório '{report_name}' salvo com sucesso em: {file_path}")

        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
        finally:
            self.desconecta_db()

    #reseta as tabelas
    def reset_tables(self):
        self.conecta_db()
        try:
            self.cursor.execute('DROP TABLE IF EXISTS DetailsEmprestimos')
            self.cursor.execute('DROP TABLE IF EXISTS Emprestimos')
            self.conn.commit()
        finally:
            self.desconecta_db()
        self.create_tabela()

    #registra o usuários no banco de dados
    #e tratamento de exceções
    def register_user(self):
        name = self.name_entry.get()
        username = self.username_entry.get()
        cpf = self.cpf_entry.get()
        rg = self.rg_entry.get()
        date = self.date_entry.get() 
        sex = self.sex_combo.get() 
        email = self.email_entry.get()
        password = self.password_entry.get()
        cep = self.cep_entry.get()
        logradouro = self.logradouro_entry.get()
        bairro = self.bairro_entry.get()
        numero = self.numero_entry.get() 
        cidade = self.cidade_entry.get()
        estado = self.estado_entry.get()
        agencia = self.agencia_entry.get()
        conta = self.conta_entry.get()
        tipacc = self.tipacc_combo.get()
        bancos = self.bancos_combo.get()
        pix = self.pix_entry.get()
        convenio = self.convenio_entry.get()

        if not all(
            [name, username, cpf, rg, date, sex, email, password, cep, logradouro, bairro, numero, cidade, estado, agencia, conta, tipacc, bancos, pix, convenio]
            ):
            messagebox.showerror('Erro', 'Preencha todos os campos obrigatórios.')
            return
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        self.conecta_db()
        
        try:
            self.cursor.execute('''
                INSERT INTO Usuarios (name, username, cpf, rg, date, sex, email, password, cep, logradouro, bairro, numerocasa, cidade, estado, agencia, conta, tipaccount, bancos, pix, convenio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', 
                (name, username, cpf, rg, date, sex, email,      hashed_password, cep, logradouro,
                  bairro, numero, cidade, estado, agencia, conta, tipacc, bancos,
                  pix, convenio))
            self.conn.commit()
            messagebox.showinfo('Sucesso', f'Usuário {username} registrado com sucesso!')
            self.limpa_entry_register()
            window.destroy()
            self.window_main()
        except sqlite3.Error as e:
            messagebox.showerror('Erro', f"Erro ao registrar usuário: {e}")
        finally:
            self.desconecta_db()
    
    #registra o empréstimo
    def loan_register(self, loan_amount, num_installments, first_payment_date, interest_rate, 
    total_interest, total_final):
        try:
            # Verificando se os valores calculados estão disponíveis
            if not hasattr(self, 'calculated_loan_amount'):
                raise ValueError("Por favor, calcule os valores antes de registrar")

            # Recuperando os valores calculados
            loan_amount = self.calculated_loan_amount
            num_installments = self.calculated_num_installments
            first_payment_date = self.calculated_first_payment_date.strftime("%d/%m/%Y")
            interest_rate = self.calculated_interest_rate / 100  # Certifique-se de que o percentual esteja no formato correto
            total_interest = self.total_interest
            total_final = self.total_final
            
            print(f"""
            Valores para inserção:
            Username: {self.username_logged_in}
            Empréstimo: {loan_amount}
            Parcelas: {num_installments}
            Data: {first_payment_date}
            Juros: {interest_rate}
            Total Juros: {total_interest:,.2f}
            Total Final: {total_final:,.2f}
            """)

            self.conecta_db()
            try:
                # Inserindo o registro principal do empréstimo
                self.cursor.execute('''
                    INSERT INTO Emprestimos (
                        username, valor_emprestimo, num_parcelas, prim_data_pagamento, juros, total_juros, total_final
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.username_logged_in, 
                    loan_amount, 
                    num_installments, 
                    first_payment_date,
                    interest_rate, 
                    total_interest,
                    total_final
                ))
                emprestimo_id = self.cursor.lastrowid  # Pegando o ID do último empréstimo inserido
                
                # Inserindo cada parcela
                for dados in self.dados_mensais:
                    self.cursor.execute('''
                        INSERT INTO DetailsEmprestimos (
                            emprestimo_id, parcela, data_vencimento,
                            valor_parcela, amortizacao, juros, saldo_devedor
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        emprestimo_id,
                        dados['mes'],
                        dados['data'],
                        dados['prestacao'],
                        dados['amortizacao'],
                        dados['juros'],
                        dados['saldo_devedor']
                    ))
                    
                self.conn.commit()  # Comitando uma única vez após inserir tudo
                
                messagebox.showinfo('Sucesso', f"Empréstimo registrado com sucesso!\nPara mais informações sobre o empréstimo, consulte o menu de empréstimos.")
                
                global top_bar
                if 'top_bar' in globals() and top_bar.winfo_exists():
                    top_bar.destroy()
                    
                if loan_frame.winfo_exists():
                    loan_frame.destroy()

                load_dashboard()  # Carregue o dashboard após registrar

            except sqlite3.Error as e:
                print(f"Erro ao salvar dados do empréstimo: {e}")
                self.conn.rollback()
                messagebox.showerror('Erro', f"Erro ao registrar o empréstimo: {e}")
            finally:
                self.desconecta_db()

        except ValueError as e:
            messagebox.showerror('Erro de Validação', str(e))
            print(f"Erro de validação: {e}")  # Debug
        except sqlite3.Error as e:
            messagebox.showerror('Erro do Banco de Dados', f"Erro ao registrar: {e}")
            print(f"Erro SQL: {e}")  # Debug
        except Exception as e:
            messagebox.showerror('Erro', f"Erro inesperado: {str(e)}")
            print(f"Erro detalhado: {e}")  # Debug
        finally:
            self.desconecta_db()
    
    #consulta todos os empréstimos do banco de dados
    def get_all_loans_from_db(self):
        loans = []
        try:
            # Conectar ao banco de dados
            self.conecta_db()
            
            # Consultar empréstimos com nomes de usuários
            self.cursor.execute('''
                SELECT u.name, e.valor_emprestimo, e.prim_data_pagamento, e.num_parcelas 
                FROM Emprestimos e
                JOIN Usuarios u ON e.username = u.username
            ''')
            
            # Recuperar os resultados
            rows = self.cursor.fetchall()

            # Imprimir os resultados
            print(rows)

            # Organizar os dados em um formato adequado para exibição
            for row in rows:
                loan = {
                    "nome": row[0],  # Nome do cliente
                    "valor_emprestimo": row[1],  # valor do empréstimo
                    "data_primeira_parcela": row[2],  # primeira parcela
                    "parcelas": row[3]  # número de parcelas
                }
                loans.append(loan)
        except sqlite3.Error as e:
            print(f"Erro ao consultar empréstimos: {e}")
        finally:
            # Desconectar do banco
            self.desconecta_db()
        
        return loans

    #consulta os empréstimos
    def get_loans_from_db(self):
        loans = []
        try:
            #conecta ao banco de dados
            self.conecta_db()
            
            #Consulta empréstimos do usuário logado
            self.cursor.execute('''
                SELECT valor_emprestimo, prim_data_pagamento, num_parcelas 
                FROM Emprestimos
                WHERE username = ?
            ''', (self.username_logged_in,))
            
            #recupera os resultados
            rows = self.cursor.fetchall()
            
            #organiza os dados em um formato adequado para exibição
            for row in rows:
                loan = {
                    "valor_emprestimo": row[0],  # valor do empréstimo
                    "data_primeira_parcela": row[1],  # primeira parcela
                    "parcelas": row[2]  # número de parcelas
                }
                loans.append(loan)
        except sqlite3.Error as e:
            print(f"Erro ao consultar empréstimos: {e}")
        finally:
            self.desconecta_db()
        
        return loans

    #checa se nome de usuário já existe
    def check_username_exists(self, username):
        try:
            self.conecta_db()
            query = "SELECT * FROM Usuarios WHERE username = ?"
            self.cursor.execute(query, (username,))
            result = self.cursor.fetchone()  
            return result is not None
        except sqlite3.Error as e:
            print(f"Erro ao verificar username: {e}")
            return False
        finally:
            self.desconecta_db()

    #verifica o login
    def login_check(self):
        global username, username_logged_in
        username = self.usernamelogin_entry.get()
        password = self.passwordlogin_entry.get()
    
        if not all([username, password]):
            messagebox.showwarning('Erro', 'Preencha todos os campos.')
            return

        self.conecta_db()
        try:
            self.cursor.execute('SELECT password FROM Usuarios WHERE username = ?', (username,))
            stored_password = self.cursor.fetchone()

            if stored_password and bcrypt.checkpw(password.encode('utf-8'), stored_password[0]):
                self.username_logged_in = username
                messagebox.showinfo('Sucesso', f'Bem-vindo, {username}!')
                window.destroy()
                self.window_main()
            else:
                messagebox.showerror('Erro', 'Credenciais inválidas.')
        except sqlite3.Error as e:
            messagebox.showerror('Erro', f"Erro no login: {e}")
        finally:
            self.desconecta_db()

    #verifica o login do admin
    def login_check_admin(self):
        global username, username_logged_in
        username = self.usernamelogin_entry.get()
        password = self.passwordlogin_entry.get()

        if username.lower() == "admin":
            if not all([username, password]):
                messagebox.showwarning('Erro', 'Preencha todos os campos.')
                return
        else:
            if not all([username, password]):
                messagebox.showwarning('Erro', 'Preencha todos os campos.')
                return

        self.conecta_db()
        try:
            self.cursor.execute('SELECT password FROM Usuarios WHERE username = ?', (username,))
            stored_password = self.cursor.fetchone()

            if username.lower() == "admin":
                if bcrypt.checkpw(password.encode('utf-8'), stored_password[0]):
                    self.username_logged_in = username
                    messagebox.showinfo('Sucesso', f'Bem-vindo, {username}!')
                    window.destroy()
                    self.window_main_admin()
                else:
                    messagebox.showerror('Erro', 'Credenciais inválidas.')
            else:
                if stored_password and bcrypt.checkpw(password.encode('utf-8'), stored_password[0]):
                    self.username_logged_in = username
                    messagebox.showinfo('Sucesso', f'Bem-vindo, {username}!')
                    window.destroy()
                    self.window_main_admin()
                else:
                    messagebox.showerror('Erro', 'Credenciais inválidas.')

        except sqlite3.Error as e:
            messagebox.showerror('Erro', f"Erro no login: {e}")
        finally:
            self.desconecta_db()

    #tela de erro ao cadastrar admin
    def register_admin(self):
        messagebox.showwarning('Cadastro', 'Consulte o responsável para realizar o cadastro.')

class Application(ctk.CTk, BackEnd):

    def __init__(self):
        #self.window=window
        super().__init__()
        self.username_logged_in = None
        self.loan_amount_entry = None  # Inicializado como None
        self.installments_entry = None
        self.first_payment_entry = None
        self.interest_rate_entry = None
        self.total_interest = None
        self.total_final = None
        self.dados_mensais = []
        self.theme()
        self.window()
        self.window_login()
        self.create_tabela()
        window.mainloop()

    #define um tema escuro para a window
    def theme(self):    
        try:
            ctk.set_appearance_mode('dark')
            ctk.set_default_color_theme('dark-blue')
        except Exception as e:
            print(f"Erro ao configurar o tema: {e}")

    #configurações da tela
    def window(self):
        window_width = 800
        window_height = 800        
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        position_x = (screen_width // 2) - (window_width // 2)
        position_y = (screen_height // 2) - (window_height // 2)
        window.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        #window.geometry('800x800')
        window.title('QUICKFINANCE')
        window.iconbitmap('images/icon-310x310.ico')
        window.resizable(False, False)

    #alternar entre tela de login e admin
    def toggle_action(self):
        if self.toggle_switch.get() == "Ligado":
            self.clear_window()
            self.window_login_admin()  # Vai para a tela de admin
        else:
            self.clear_window()
            self.window_login()  # Volta para a tela de usuário

    #limpa a tela
    def clear_window(self):
        for widget in window.winfo_children():
            widget.destroy()
    
    def show_loan_details(self, loan):
        self.conecta_db()
        try:
            # Recuperar detalhes do empréstimo
            self.cursor.execute('''
                SELECT id, valor_emprestimo, prim_data_pagamento, num_parcelas,
                    juros, total_juros, total_final
                FROM Emprestimos
                WHERE username = ? AND valor_emprestimo = ?
            ''', (self.username_logged_in, loan['valor_emprestimo']))

            loan_details = self.cursor.fetchone()
            if not loan_details:
                messagebox.showerror("Erro", "Empréstimo não encontrado")
                return

            loan_id, loan_amount, first_payment_date, num_installments, \
            interest_rate, total_interest, total_final = loan_details
            
            # Criar uma nova janela para os detalhes
            details_window = ctk.CTkToplevel()
            details_window.title("Detalhes do Empréstimo")
            details_window.geometry("800x600")
            details_window.iconbitmap('images/logoquickfinance-32x32.png')

            details_window.attributes('-topmost', True)  # Faz a janela ser a principal e ficar em cima
            details_window.lift()  # Levanta a janela

            widgettext = ctk.CTkLabel(
                master=details_window,
                text="Detalhes do Empréstimo",
                font=("Poppins", 18, "bold"),
                text_color="#f78d35"
            )
            widgettext.pack(pady=10)

            # Frame de resumo
            summary_frame = ctk.CTkFrame(master=details_window,
                                        corner_radius=25,
                                        border_width=2, border_color='#f78d35')
            summary_frame.pack(padx=20, pady=20, fill="x")

            # Resumo das informações
            summary_labels = [
                f"Valor do Empréstimo: R$ {loan_amount:,.2f}",
                f"Data da 1° Parcela: {first_payment_date} | Número de Parcelas: {num_installments}",
                f"Taxa de Juros: {interest_rate:.2f}% | Total de Juros: R$ {total_interest:,.2f}",
                f"Total Final: R$ {total_final:,.2f}"
            ]

            for text in summary_labels:
                ctk.CTkLabel(summary_frame, text=text, font=("Poppins", 12, 'bold')).pack(pady=5)

            # Frame da tabela com scroll
            table_frame = ctk.CTkFrame(master=details_window,
                                        corner_radius=25,
                                        border_width=2,
                                        border_color='#f78d35')
            table_frame.pack(padx=20, pady=20, fill="both", expand=True)

            # Frame rolável para a tabela
            table_scroll = ctk.CTkScrollableFrame(master=table_frame,
                                                    corner_radius=0)
            table_scroll.pack(fill="both", expand=True, padx=10, pady=10)

            # Cabeçalhos da tabela
            headers = ['Mês', 'Data', 'Prestação', 'Amortização', 'Juros', 'Saldo Devedor', 'Status do Pagamento']
            for col, header in enumerate(headers):
                ctk.CTkLabel(table_scroll, text=header, font=("Poppins", 12, "bold"), text_color="#f78d35").grid(row=0, column=col, padx=5, pady=5)

            # Detalhes das parcelas
            self.cursor.execute('''
                SELECT parcela, data_vencimento, valor_parcela,
                    amortizacao, juros, saldo_devedor, status_pagamento
                FROM DetailsEmprestimos
                WHERE emprestimo_id = ?
                ORDER BY parcela
            ''', (loan_id,))

            for row, installment in enumerate(self.cursor.fetchall(), start=1):
                values = [
                    str(installment[0]),
                    installment[1],
                    f"R$ {installment[2]:,.2f}",
                    f"R$ {installment[3]:,.2f}",
                    f"R$ {installment[4]:,.2f}",
                    f"R$ {installment[5]:,.2f}",
                    installment[6]  # Status do pagamento
                ]
                
                for col, value in enumerate(values):
                    ctk.CTkLabel(table_scroll, text=value, font=("Poppins", 12, 'bold')).grid(row=row, column=col, padx=5, pady=2)

                # Review pay button
                payment_button = ctk.CTkButton(table_scroll, text="Pagar",
                    width=100, font=('Poppins', 12, 'bold'),
                    corner_radius=10,
                    command=lambda idx=installment[0]: self.process_payment(idx))
                payment_button.grid(row=row, column=len(values), padx=5, pady=2)

        except sqlite3.Error as e:
            print(f"Erro ao buscar detalhes do empréstimo: {e}")
            messagebox.showerror("Erro", "Erro ao carregar detalhes do empréstimo")
        finally:
            self.desconecta_db()

    #tela login
    def window_login(self):
        #Trabalhando com a imagem da tela      
        self.img = ctk.CTkImage(Image.open(r"images/login.png"), size=(800, 800))
        self.label_img = ctk.CTkLabel(master=window, image=self.img, text=None)
        self.label_img.place(x=0, y=0)

        #frame de login

        self.frame_login = ctk.CTkFrame(
            master=window, 
            width=400, 
            height=550, 
            corner_radius=25,
            border_width=2
            )
        self.frame_login.pack(pady=120)

        #logo no frame de login
        self.logoimg = ctk.CTkImage(Image.open(r"images/logoquickfinancefront.png"), size=(228, 104))
        self.label_logoimg = ctk.CTkLabel(master=self.frame_login, image=self.logoimg, text=None)
        self.label_logoimg.place(x=90, y=20)

        #botão toggle para mudar para tela de admin
        # Adicionando um botão toggle ao lado de self.label_logoimg
        self.toggle_switch = ctk.CTkSwitch(
            master=self.frame_login, 
            text="",
            command=self.toggle_action,
            onvalue="Ligado",  # Valor quando está ativo
            offvalue="Desligado",
            button_color='#f78d35'  # Valor quando está inativo
        )
        self.toggle_switch.place(x=17, y=20)  # Ajuste a posição ao lado de self.label_logoimg
        self.toggle_switch.deselect()

        #botões de login /estetica
        self.googlebuttonimg = ctk.CTkImage(Image.open(r"images/googlebutton.png"), size=(204, 27))
        self.googlebutton_label = ctk.CTkButton(master=self.frame_login, image=self.googlebuttonimg, fg_color='#ffffff', hover_color='#b5b5b5', corner_radius=60, text=None, width=350, height=40)
        self.googlebutton_label.place(x=25, y=337)
        self.facebookbuttonimg = ctk.CTkImage(Image.open(r"images/facebookbutton.png"), size=(204, 27))
        self.facebookbutton_label = ctk.CTkButton(master=self.frame_login, image=self.facebookbuttonimg, fg_color='#3f5896', corner_radius=60, text=None, width=350, height=40)
        self.facebookbutton_label.place(x=25, y=290)

        self.or_label = ctk.CTkLabel(master=self.frame_login,text='ou', font=('Poppins', 14), text_color='gray')
        self.or_label.place(x=185, y=250)
        
        #entrada de username de login
        self.usernamelogin_entry = ctk.CTkEntry(master=self.frame_login, placeholder_text='Username', width=350, height=40, corner_radius=60, font=('Poppins', 14))
        self.usernamelogin_entry.place(x=25, y=145)
        
        #entrada de senha de login
        self.passwordlogin_entry = ctk.CTkEntry(master=self.frame_login, placeholder_text='Password', width=350, height=40, corner_radius=60,show='*', font=('Poppins', 14))
        self.passwordlogin_entry.place(x=25, y=195)

        #checkbox para manter conectado 'estetica'
        #self.checkbox = ctk.CTkCheckBox(master=self.frame_login, text='Manter conectado', font=('Poppins', 14), corner_radius=20)
        #self.checkbox.place(x=25, y=280)

        #botão para efetuar o login
        self.loginbutton = ctk.CTkImage(Image.open(r"images/loginbutton.png"), size=(50, 26))
        self.login_button = ctk.CTkButton(master=self.frame_login, image=self.loginbutton, text=None, font=('Poppins', 14), width=350, height=40, corner_radius=60, command=self.login_check)
        self.login_button.place(x=25, y=385)

        #span para mostrar se não há cadastro
        self.register_span = ctk.CTkLabel(master=self.frame_login, text="Ao continuar, você concorda com os Termos \nde Serviço e a Política de Privacidade do QuickFinance", text_color="gray")
        self.register_span.place(x=45, y=440)

        #botão para realizar o cadastro
        self.registerbutton = ctk.CTkImage(Image.open(r"images/cadastrobutton.png"), size=(214, 36))
        self.register_button = ctk.CTkButton(master=self.frame_login, image=self.registerbutton, text=None, width=150, fg_color='#191f27', font=('Poppins', 12), hover_color='#191f27', command=self.window_register1)
        self.register_button.place(x=87, y=500)

    #tela de login admin
    def window_login_admin(self):
        #Trabalhando com a imagem da tela        
        self.img = ctk.CTkImage(Image.open(r"images/login.png"), size=(800, 800))
        self.label_img = ctk.CTkLabel(master=window, image=self.img, text=None)
        self.label_img.place(x=0, y=0)

        #frame de login

        self.frame_login = ctk.CTkFrame(
            master=window, 
            width=400, 
            height=550, 
            corner_radius=25,
            border_width=2
            )
        self.frame_login.pack(pady=120)

        #logo no frame de login
        self.logoimg = ctk.CTkImage(Image.open(r"images/logoquickfinancefront.png"), size=(228, 104))
        self.label_logoimg = ctk.CTkLabel(master=self.frame_login, image=self.logoimg, text=None)
        self.label_logoimg.place(x=90, y=20)

        #botão toggle para mudar para tela de admin
        # Adicionando um botão toggle ao lado de self.label_logoimg
        self.toggle_switch = ctk.CTkSwitch(
            master=self.frame_login, 
            text="",
            command=self.toggle_action,
            onvalue="Ligado",  # Valor quando está ativo
            offvalue="Desligado",
            button_color='#f78d35'  # Valor quando está inativo
        )
        self.toggle_switch.place(x=17, y=20)  # Ajuste a posição ao lado de self.label_logoimg
        self.toggle_switch.select()

        self.admin_label = ctk.CTkLabel(master=self.frame_login,text='Modo\nAdmin', font=('Poppins', 12), text_color='gray')
        self.admin_label.place(x=17, y=45)

        #botões de login /estetica
        self.googlebuttonimg = ctk.CTkImage(Image.open(r"images/googlebutton.png"), size=(204, 27))
        self.googlebutton_label = ctk.CTkButton(master=self.frame_login, image=self.googlebuttonimg, fg_color='#ffffff', hover_color='#b5b5b5', corner_radius=60, text=None, width=350, height=40)
        self.googlebutton_label.place(x=25, y=337)
        self.facebookbuttonimg = ctk.CTkImage(Image.open(r"images/facebookbutton.png"), size=(204, 27))
        self.facebookbutton_label = ctk.CTkButton(master=self.frame_login, image=self.facebookbuttonimg, fg_color='#3f5896', corner_radius=60, text=None, width=350, height=40)
        self.facebookbutton_label.place(x=25, y=290)

        self.or_label = ctk.CTkLabel(master=self.frame_login,text='ou', font=('Poppins', 14), text_color='gray')
        self.or_label.place(x=185, y=250)
        
        #entrada de username de login
        self.usernamelogin_entry = ctk.CTkEntry(master=self.frame_login, placeholder_text='Username', width=350, height=40, corner_radius=60, font=('Poppins', 14))
        self.usernamelogin_entry.place(x=25, y=145)
        
        #entrada de senha de login
        self.passwordlogin_entry = ctk.CTkEntry(master=self.frame_login, placeholder_text='Password', width=350, height=40, corner_radius=60,show='*', font=('Poppins', 14))
        self.passwordlogin_entry.place(x=25, y=195)

        #checkbox para manter conectado 'estetica'
        #self.checkbox = ctk.CTkCheckBox(master=self.frame_login, text='Manter conectado', font=('Poppins', 14), corner_radius=20)
        #self.checkbox.place(x=25, y=280)

        #botão para efetuar o login
        self.loginbutton = ctk.CTkImage(Image.open(r"images/loginbutton.png"), size=(50, 26))
        self.login_button = ctk.CTkButton(master=self.frame_login, image=self.loginbutton, text=None, font=('Poppins', 14), width=350, height=40, corner_radius=60, command=self.login_check_admin)
        self.login_button.place(x=25, y=385)

        #span para mostrar se não há cadastro
        self.register_span = ctk.CTkLabel(master=self.frame_login, text="Ao continuar, você concorda com os Termos \nde Serviço e a Política de Privacidade do QuickFinance", text_color="gray")
        self.register_span.place(x=45, y=440)

        #botão para realizar o cadastro
        self.registerbutton = ctk.CTkImage(Image.open(r"images/cadastrobutton.png"), size=(214, 36))
        self.register_button = ctk.CTkButton(master=self.frame_login, image=self.registerbutton, text=None, width=150, fg_color='#191f27', font=('Poppins', 12), hover_color='#191f27', command=self.register_admin)
        self.register_button.place(x=87, y=500)

    #tela registro 1
    def window_register1(self):
        #remover o frame de login
        self.frame_login.pack_forget()
        self.label_img.place_forget()
        #self.label_imgm.place_forget()

        #imagem da esquerda
        self.step_img = ctk.CTkImage(Image.open(r"images/register.png"), size=(800, 800))
        self.label_stepimg = ctk.CTkLabel(master=window, image=self.step_img, text=None)
        self.label_stepimg.place(x=0, y=0)

        #criando a tela de cadastro de usuários
        self.register_frame = ctk.CTkFrame(master=window, 
            width=500, 
            height=550,
            corner_radius=25,
            border_width=2
            )
        self.register_frame.pack(pady=120)
        
        self.stepregister = ctk.CTkImage(Image.open(r"images/steps-register.png"), size=(500, 42))
        self.label_stepregister = ctk.CTkLabel(master=self.register_frame, image=self.stepregister, text=None)
        self.label_stepregister.place(x=6, y=25)

        #nome de span
        span = ctk.CTkLabel(master=self.register_frame,text='Por favor, preencha todos os campos com dados corretos', font=('Poppins', 10), text_color='gray')
        span.place(x=100, y=57)

        #campo que guarda nome completo
        self.name_entry = ctk.CTkEntry(master=self.register_frame, placeholder_text='Nome completo', width=310, height=35, corner_radius=60, font=('Poppins', 14))
        self.name_entry.place(x=100, y=145)

        #função para validar o cpf
        def validate_cpf(event=None):
            text = self.cpf_entry.get()
            text = re.sub(r'[^0-9]', '', text)

            if not text:
                self.error_label.configure(text="")
                return
                
            if len(text) < 11:
                missing_digits = 11 - len(text)
                self.error_label.configure(
                     text=f"Faltam {missing_digits} dígito{'s' if missing_digits > 1 else ''} para completar o CPF",text_color="red"
                )
            else:
                self.error_label.configure(text="")

            if len(text) <= 11:
                cpf_formataded = '.'.join([text[:3], text[3:6], text[6:9]]) + ('-' + text[9:] if len(text) > 9 else '')
                self.cpf_entry.delete(0, ctk.END)
                self.cpf_entry.insert(0, cpf_formataded)

        #campo de entrada para cpf
        self.cpf_entry = ctk.CTkEntry(master=self.register_frame, placeholder_text='CPF', width=155, height=35, corner_radius=60,font=('Poppins', 14))
        self.cpf_entry.place(x=100, y=185)

        #label que mostra qts digitos falta do cpf
        self.error_label = ctk.CTkLabel(master=self.register_frame, text="",font=('Poppins', 12),text_color="red")
        self.error_label.place(x=150, y=475)
        self.cpf_entry.bind("<KeyRelease>", validate_cpf)  # Associa a validação ao evento de digitação

        #função para validar rg
        def validate_rg(event=None):
            text = self.rg_entry.get()
            text = re.sub(r'[^0-9]', '', text)  # Remove caracteres não numéricos
            if len(text) <= 9:
                rg_formatado = '.'.join([text[:2], text[2:5], text[5:8]]) + ('-' + text[8:] if len(text) > 8 else '')
                self.rg_entry.delete(0, ctk.END)
                self.rg_entry.insert(0, rg_formatado)
            
        #campo de entrada para rg
        self.rg_entry = ctk.CTkEntry(master=self.register_frame, placeholder_text='RG', width=150, height=35, corner_radius=60, font=('Poppins', 14))
        self.rg_entry.place(x=260, y=185)
        self.rg_entry.bind("<KeyRelease>", validate_rg)  # Associa a 
        #validação ao evento de digitação

        #função para checar se é maior de idade
        def check_age(date_str):
            try:
                birth_date = datetime.strptime(date_str, "%d/%m/%Y")
                today = datetime.now()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                if age < 18:
                    self.age_error_label.configure(text="Usuário menor de idade não permitido", text_color="red")
                else:
                    self.age_error_label.configure(text="")
            except ValueError:
                self.age_error_label.configure(text="Data inválida", text_color="red")
        
        #função para abrir calendario
        def open_calendar():
            def select_data():
                data_select = calendar.get_date()
                self.date_entry.delete(0, ctk.END)
                self.date_entry.insert(0, data_select)
                check_age(data_select)  # Check age when date is selected
                calendar_window.destroy()

            # Janela do calendário
            calendar_window = ctk.CTkToplevel(window)
            calendar_window.title("Selecionar data")
            calendar_window.geometry("300x300")
            calendar_window.grab_set()

            calendar = Calendar(calendar_window, date_pattern="dd/mm/yyyy")
            calendar.pack(pady=10)

            button_select = ctk.CTkButton(calendar_window, text="Selecionar", command=select_data)
            button_select.pack(pady=10)

        #entrada da data e botão
        self.date_entry = ctk.CTkEntry(master=self.register_frame, placeholder_text='Nascimento', width=125, height=35, corner_radius=60, font=('Poppins', 14))
        self.date_entry.place(x=225, y=225)
        self.date_entry.bind('<KeyRelease>', lambda e: check_age(self.date_entry.get()))
        self.calendarimg = ctk.CTkImage(Image.open(r"images/icons/calendario.png"), size=(20, 20))
        self.button_calendar = ctk.CTkButton(master=self.register_frame, image=self.calendarimg, text=None, width=2, height=32, fg_color='#f78d35', hover_color='#cd3e1e', corner_radius=60, command=open_calendar)
        self.button_calendar.place(x=355, y=225) 

        #label para exibir erro da idade
        self.age_error_label = ctk.CTkLabel(master=self.register_frame, text="", font=('Poppins', 12))
        self.age_error_label.place(x=150, y=475)

        #campo para selecionar o sexo
        self.sex_combo = ctk.CTkComboBox(
            self.register_frame, 
            values=["Masculino", "Feminino", "Outros"],  # Opções
            width=120, height=35, corner_radius=60,
            font=("Poppins", 14)
        )
        self.sex_combo.set("Sexo")
        self.sex_combo.place(x=100, y=225) 

        self.sex_combo._entry.grid_configure(padx=(10, 40))

        #função para validar se email possui @
        def validate_email(event):
            email = self.email_entry.get()
            if "@" in email:
                # If the email is valid, clear any error message
                self.errorM_label.configure(text="")
            else:
            # If the email is invalid, show error message
                self.errorM_label.configure(text="Email não contém '@'",
                    text_color="red")

        #campo para e-mail
        self.email_entry = ctk.CTkEntry(master=self.register_frame, placeholder_text='E-mail', width=310, height=35, corner_radius=60, font=('Poppins', 14))
        self.email_entry.place(x=100, y=265)
        
        #label para mostrar o erro
        self.errorM_label = ctk.CTkLabel(master=self.register_frame, text="", text_color="red", font=('Poppins', 12))
        self.errorM_label.place(x=180, y=475)
        self.email_entry.bind('<KeyRelease>', validate_email) 

                #campo que guarda nome de usuario
        self.username_entry = ctk.CTkEntry(master=self.register_frame, placeholder_text='Username', width=310, height=35, corner_radius=60,font=('Poppins', 14))
        self.username_entry.place(x=100, y=305)

        #label para mostrar resultado
        self.username_check_label = ctk.CTkLabel(master=self.register_frame, text="", font=('Poppins', 12), text_color="red")
        self.username_check_label.place(x=25, y=475)

        #mostra label de username
        def show_username_label(event):
            self.username_check_label.place(x=160, y=475)

        #esconde label de username
        def hide_username_label(event):
            self.username_check_label.place_forget()

        self.username_entry.bind('<FocusIn>', show_username_label)
        self.username_entry.bind('<FocusOut>', hide_username_label)
        

        #função para checar se nome do usuário existe
        def check_username():
            username = self.username_entry.get() 
            if username:
                if self.check_username_exists(username):
                    self.username_check_label.configure(text="Nome de usuário já está em uso", text_color="red")
                else:
                    self.username_check_label.configure(text="Nome de usuário disponível", text_color="green")
            else:
                self.username_check_label.configure(text="Digite um nome de usuário", text_color="red")
        #chave para chamar o evento
        self.username_entry.bind("<KeyRelease>", lambda event: check_username())

        #campo para senha
        self.password_entry = ctk.CTkEntry(master=self.register_frame, placeholder_text='Password', width=310, show='*', height=35, corner_radius=60, font=('Poppins', 14))
        self.password_entry.place(x=100, y=345)
        
        #função para voltar para tela de login
        def back(): #volta para tela de login
            self.register_frame.pack_forget()  # Remove tela de registro
            self.label_stepimg.place_forget()
            self.frame_login.pack(pady=120)  # Volta para a tela de login
            self.label_img.place(x=0, y=0)
            #self.label_imgm.place(x=105, y=31)

        #imagem dos botões de avançar e voltar
        self.avançar_img = ctk.CTkImage(Image.open(r"images/avançarbutton.png"), size=(79, 20))
        self.voltar_img = ctk.CTkImage(Image.open(r"images/voltarbutton.png"), size=(50, 20))

        #botão para voltar
        back_button = ctk.CTkButton(master=self.register_frame, text=None, width=120, image=self.voltar_img, corner_radius=100, fg_color='gray', hover_color='#202020', command=back)
        back_button.place(x=100, y=385)

        #botão para avançar
        next_button = ctk.CTkButton(master=self.register_frame, text=None, fg_color='#f78d35', hover_color='#cd3e1e', image=self.avançar_img, width=120, corner_radius=100, command=self.window_register2)
        next_button.place(x=290, y=385)

    #tela registro 2
    def window_register2(self):
        #remove a tela de registro 1
        self.register_frame.pack_forget()

        #self.step_img = ctk.CTkImage(Image.open(r"images/register.png"), size=(800, 800))
        #self.label_registerimg = ctk.CTkLabel(master=window, image=self.step_img, text=None)
        #self.label_registerimg.place(x=0, y=0)

        #chama as imagens novas
        self.register_frame2 = ctk.CTkFrame(master=window, 
            width=500, 
            height=550,
            corner_radius=25,
            border_width=2
            )
        self.register_frame2.pack(pady=120)

        self.stepregister = ctk.CTkImage(Image.open(r"images/steps-register2.png"), size=(500, 42))
        self.label_stepregister = ctk.CTkLabel(master=self.register_frame2, image=self.stepregister, text=None)
        self.label_stepregister.place(x=6, y=25)

        #função usando api de cep
        def buscar_endereco():
                    cep = self.cep_entry.get()

                    if len(cep) != 8 or not cep.isdigit():
                        self.resultado_label.configure(
                            text="CEP inválido. Digite um CEP válido.", text_color="red"
                        )
                        return

                    url = f"https://viacep.com.br/ws/{cep}/json/"
                    try:
                        response = requests.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            if "erro" in data:
                                self.resultado_label.configure(
                                    text="CEP não encontrado.", text_color="red"
                                )
                                limpar_campos()
                            else:
                                self.logradouro_entry.delete(0, ctk.END)
                                self.logradouro_entry.insert(0, data.get("logradouro", ""))

                                self.bairro_entry.delete(0, ctk.END)
                                self.bairro_entry.insert(0, data.get("bairro", ""))

                                self.cidade_entry.delete(0, ctk.END)
                                self.cidade_entry.insert(0, data.get("localidade", ""))

                                self.estado_entry.delete(0, ctk.END)
                                self.estado_entry.insert(0, data.get("uf", ""))

                                self.resultado_label.configure(
                                    text="Endereço encontrado!", text_color="green"
                                )
                        else:
                            self.resultado_label.configure(
                                text="Erro ao buscar o CEP.", text_color="red"
                            )
                            limpar_campos()
                    except requests.RequestException:
                        self.resultado_label.configure(
                            text="Erro de conexão.", text_color="red"
                        )

        #função para limpar os campos de cep
        def limpar_campos():
                    self.logradouro_entry.delete(0, ctk.END)
                    self.bairro_entry.delete(0, ctk.END)
                    self.cidade_entry.delete(0, ctk.END)
                    self.estado_entry.delete(0, ctk.END)

                #titulo da tela
        self.next_step_label = ctk.CTkLabel(master=self.register_frame2, text="Por favor, preencha todos os campos com dados corretos.", font=("Poppins", 10), text_color="gray").place(x=100, y=57)

        #entrada do campo de cep
        self.cep_entry = ctk.CTkEntry(master=self.register_frame2, placeholder_text='CEP', width=257,  corner_radius=60, font=('Poppins', 14))
        self.cep_entry.place(x=100, y=165)

        #botão cep
        self.cepimg = ctk.CTkImage(Image.open(r"images/icons/cep.png"), size=(20, 20))
        self.button_cep = ctk.CTkButton(master=self.register_frame2, text=None, image=self.cepimg,fg_color='#f78d35', hover_color='#cd3e1e',corner_radius=60, font=("Poppins", 14), width=50, command=buscar_endereco).place(x=360, y=165)

        #entrada de logradouro
        self.logradouro_entry = ctk.CTkEntry(master=self.register_frame2, placeholder_text='Logradouro',  corner_radius=60, width=310, font=('Poppins', 14))
        self.logradouro_entry.place(x=100, y=205)

        #entrada do bairro
        self.bairro_entry = ctk.CTkEntry(master=self.register_frame2, placeholder_text='Bairro', corner_radius=60, width=250, font=('Poppins', 14))
        self.bairro_entry.place(x=100, y=245)

        #entrada do número
        self.numero_entry = ctk.CTkEntry(master=self.register_frame2, placeholder_text='N°',  corner_radius=60, width=56, font=('Poppins', 14))
        self.numero_entry.place(x=355, y=245)

        #entrada da cidade
        self.cidade_entry = ctk.CTkEntry(master=self.register_frame2, placeholder_text='Cidade', width=256,  corner_radius=60, font=('Poppins', 14))
        self.cidade_entry.place(x=100, y=285)

        #entrada do estado
        self.estado_entry = ctk.CTkEntry(master=self.register_frame2, placeholder_text='UF', width=50,  corner_radius=60, font=('Poppins', 14))
        self.estado_entry.place(x=360, y=285)

        #label para retornar resultado
        self.resultado_label = ctk.CTkLabel(master=self.register_frame2, text="", font=("Poppins", 12), text_color="red")
        self.resultado_label.place(x=300, y=325)

        #volta para tela de registro 1  
        def back(): 
            self.register_frame2.pack_forget()
            self.label_stepimg.place_forget()
            self.register_frame.pack(pady=120)
            self.label_stepimg.place(x=0, y=0)
            self.label_stepregister.place(x=6, y=25)
        
        #imagens para os botões
        self.avançar_img = ctk.CTkImage(Image.open(r"images/avançarbutton.png"), size=(79, 20))
        self.voltar_img = ctk.CTkImage(Image.open(r"images/voltarbutton.png"), size=(50, 20))

        #botão para voltar para tela 1
        back_button = ctk.CTkButton(master=self.register_frame2, text=None, width=120, image=self.voltar_img, corner_radius=100, fg_color='gray', hover_color='#202020', command=back)
        back_button.place(x=100, y=325)

        #botão para avançar para tela 3
        next_button = ctk.CTkButton(master=self.register_frame2, text=None, fg_color='#f78d35', hover_color='#cd3e1e', image=self.avançar_img, width=120, corner_radius=100, command=self.window_register3)
        next_button.place(x=290, y=325)
                
    #tela registro 3
    def window_register3(self):
        #remove a tela de registro 1
        self.register_frame2.pack_forget()

        #self.step_img = ctk.CTkImage(Image.open(r"images/register.png"), size=(800, 800))
        #self.label_registerimg = ctk.CTkLabel(master=window, image=self.step_img, text=None)
        #self.label_registerimg.place(x=0, y=0)

        #chama as imagens novas
        self.register_frame3 = ctk.CTkFrame(master=window, 
            width=500, 
            height=550,
            corner_radius=25,
            border_width=2
            )
        self.register_frame3.pack(pady=120)

        self.stepregister = ctk.CTkImage(Image.open(r"images/steps-register3.png"), size=(500, 42))
        self.label_stepregister = ctk.CTkLabel(master=self.register_frame3, image=self.stepregister, text=None)
        self.label_stepregister.place(x=6, y=25)
                    
        #titulo da tela 3
        self.next_step_label3 = ctk.CTkLabel(master=self.register_frame3, text="Por favor, preencha todos os campos com dados corretos.", font=("Poppins", 10), text_color="gray").place(x=100, y=57)
        self.info = ctk.CTkLabel(master=self.register_frame3, text="Não é necessário usar hífen para separar o número do dígito", font=("Poppins", 10), text_color="red").place(x=95, y=75)

        #entrada da agencia
        self.agencia_entry = ctk.CTkEntry(master=self.register_frame3, placeholder_text='Agência', width=152, corner_radius=60,font=('Poppins', 14))
        self.agencia_entry.place(x=100, y=165)
                    
        #entrada da conta
        self.conta_entry = ctk.CTkEntry(master=self.register_frame3, placeholder_text='Conta', corner_radius=60, width=152, font=('Poppins', 14))
        self.conta_entry.place(x=255, y=165)

        #entrada do tipo de conta
        self.tipacc_combo = ctk.CTkComboBox(
        self.register_frame3, 
        values=["Corrente", "Poupança"],  # Opções
        width=310,
        corner_radius=60,
        font=("Poppins", 14)
        )
        self.tipacc_combo.set("Tipo de Conta")
        self.tipacc_combo.place(x=100, y=205)
        self.tipacc_combo._entry.grid_configure(padx=(10, 40))

        #entrada dos bancos
        self.bancos_combo = ctk.CTkComboBox(
        self.register_frame3, 
        values=["Banco do Brasil - 001", "Banco Santander - 033", "Banco Itaú - 341", "Banco Bradesco - 237", "Caixa Econômica Federal - 104", "Banco Safra - 422", "Banco Inter - 077", "Nubank - 260", "BTG Pactual - 208", "Banco Original - 212", "Banco Pan - 623", "Banco C6 Bank - 336", "Citibank - 745", "Banco Daycoval - 707", "Banco Mercantil do Brasil - 389", "Banco Neon - 735", "Banco Sicredi - 748", "Banco Banrisul - 041", "Banco da Amazônia - 003", "Banco do Nordeste - 004", "Banco BMG - 318", "Banco BRB (de Brasília) - 070", "Banco Topázio - 082", "Banco ABC Brasil - 246", "Banco Fibra - 224", "Banco Agibank - 121", "Banco Pine - 643", "Banco Rendimento - 633", "Banco Banestes - 021", "Banco Banpará - 037", "Banco Banese - 047", "Banco Paraná - 254", "Banco Alfa - 025", "Banco Luso Brasileiro - 600", "Banco Cetelem - 739", "Banco Digimais - 654", "Banco BS2 - 218", "Banco Western Union - 119", "PagBank - 290", "PicPay - 380", "Banco Next - 237", "Banco Sofisa Direto - 637", "Will Bank - 492", "Mercado Pago - 323", "HSBC Brasil - 399", "JP Morgan - 376", "Bank of America - 755", "Deutsche Bank - 487", "ING Bank - 492", "Morgan Stanley - 066", "Goldman Sachs - 188", "Sicoob - 756", "Unicred - 136", "Cresol - 133", "Bancoob - 756", "CoopMil - 322", "XP Investimentos - 102", "Easynvest - 140", "Órama - 325", "Genial Investimentos - 278", "Guide Investimentos - 177", "Banco Banif - 719", "Banco Voiter - 610", "Banco Triângulo - 634", "Banco CNH Industrial - 190", "Banco BBM - 107", "Banco Toyota - 383", "Banco GMAC - 630", "Banco Volkswagen - 637", "Banco PSA Finance - 386", "Banco Renault - 359", "Banco Honda - 442", "Banco Topázio - 082", "Banco Real - 356", "Banco Nossa Caixa - 151", "Banco BCN - 013", "Banco Unibanco - 409", "PayPal Brasil - 333", "Banco Rabobank - 747", "Banco Sumitomo Mitsui - 464", "Banco Tokyo-Mitsubishi - 389"],
        width=310,
        corner_radius=60,
        font=("Poppins", 14)
        )
        self.bancos_combo.set("Banco")
        self.bancos_combo.place(x=100, y=245)
        self.bancos_combo._entry.grid_configure(padx=(10, 40))

        #entrada do pix
        self.pix_entry = ctk.CTkEntry(master=self.register_frame3, placeholder_text='Chave pix', width=310,corner_radius=60, font=('Poppins', 14))
        self.pix_entry.place(x=100, y=285)

        #entrada do convenio
        self.convenio_entry = ctk.CTkEntry(master=self.register_frame3, placeholder_text='Convênio', width=310,corner_radius=60, font=('Poppins', 14))
        self.convenio_entry.place(x=100, y=325)

        #volta para tela de registro 2
        def back3(): 
            self.register_frame3.pack_forget()
            self.label_stepimg.place_forget()
            self.register_frame2.pack(pady=120)
            self.label_stepimg.place(x=0, y=0)
            self.label_stepregister.place(x=6, y=25)

        #imagens para os botões
        self.avançar_img = ctk.CTkImage(Image.open(r"images/avançarbutton.png"), size=(79, 20))
        self.concluir_img = ctk.CTkImage(Image.open(r"images/concluirbutton.png"), size=(88, 22))

        #botão para voltar para tela 2
        back_button = ctk.CTkButton(master=self.register_frame3,  text=None, width=120, image=self.voltar_img, corner_radius=100, fg_color='gray', hover_color='#202020', command=back3)
        back_button.place(x=100, y=365)

        #botão para concluir cadastro e avançar para tela principal
        concluir_button = ctk.CTkButton(master=self.register_frame3, text=None, fg_color='#f78d35', hover_color='#cd3e1e', image=self.concluir_img, width=120, corner_radius=100, command=self.register_user)
        concluir_button.place(x=290, y=365)       

    #tela principal
    def window_main(self):
        #cria uma tela nova e centraliza no centro
        main_window = ctk.CTk()
        main_window_width = 1600
        main_window_height = 900        
        screen_width = main_window.winfo_screenwidth()
        screen_height = main_window.winfo_screenheight()
        position_x = (screen_width // 2) - (main_window_width // 2)
        position_y = (screen_height // 2) - (main_window_height // 2)
        main_window.geometry(f"{main_window_width}x{main_window_height}+{position_x}+{position_y}")
        main_window.geometry("1600x900")
        main_window.title("QUICKFINANCE")
        main_window.iconbitmap('images/icon-310x310.ico')
        main_window.resizable(False, False)
        main_window.configure(fg_color="#191f27")

        #frame sidebar
        sidebar_frame = ctk.CTkFrame(
            main_window,
            width=67,
            height=720,
            fg_color="#0d4b8a",
            corner_radius=0
        )
        sidebar_frame.pack_propagate(False)
        sidebar_frame.pack(side="left", fill="y")

        #rastrea o estado da barra lateral
        is_expanded = ctk.BooleanVar(value=False)
        is_toggling = False
        
        
        #função para manipular a animação da barra lateral
        def toggle_sidebar(event=None):
            nonlocal is_toggling 
            if is_toggling:
                return

            is_toggling = True
            try:
                if is_expanded.get():
                    #contrai sidebar
                    sidebar_frame.configure(width=67)
                    for widget in sidebar_frame.winfo_children():
                        if isinstance(widget, ctk.CTkButton):
                            widget.configure(text="", width=67)
                    is_expanded.set(False)
                else:
                    #expande sidebar
                    sidebar_frame.configure(width=200)
                    for widget in sidebar_frame.winfo_children():
                        if isinstance(widget, ctk.CTkButton):
                            widget.configure(text=f" {widget.name.replace('_btn', '').capitalize()}", width=200)
                    is_expanded.set(True)
            finally:
                main_window.after(300, lambda: set_toggling_false())

        #função para rastrear o estado da barra lateral
        def set_toggling_false():
            nonlocal is_toggling
            is_toggling = False

        #função para criar o topbar
        def topbar():
            global top_bar
            #cria um frame para o topbar
            top_bar = ctk.CTkFrame(
                content_frame,
                height=50,
                fg_color="#0d4b8a",
                corner_radius=0
            )
            top_bar.pack(fill="x", side="top")

            # Logout and Profile buttons in the top bar
            logout_btn = ctk.CTkButton(
                top_bar,
                text="Sair",
                width=100,
                fg_color="#e90313",
                hover_color="#c9302c",
                image=exit_icon,
                compound="left",
                corner_radius=60,
                font=("Poppins", 14, 'bold'),
                command=self.close_application
            )
            logout_btn.pack(side="right", padx=10, pady=8)


            profile_btn = ctk.CTkButton(
                top_bar,
                text="Perfil",
                width=100,
                fg_color='#f78d35', 
                hover_color='#cd3e1e',
                image=profile_icon,
                compound="left",
                corner_radius=60,
                font=("Poppins", 14, 'bold')
            )
            profile_btn.pack(side="right", padx=10, pady=8)
        
        #logo na sidebar
        logo_img = ctk.CTkImage(Image.open(r"images/logoquickfinance-32x32.png"), size=(32, 32))
        logo_label = ctk.CTkLabel(
            sidebar_frame,
            image=logo_img,
            text=None
        )
        logo_label.pack(pady=(20, 30))


        #função para criar botões da barra lateral
        #com efeito de foco
        def create_sidebar_button(text, icon=None, font=('Poppins', 12), command=None):
            btn = ctk.CTkButton(
                sidebar_frame,
                text="" if not is_expanded.get() else f"{text}",
                image=icon, #icone será mostrado sempre
                compound="left",
                width=60 if not is_expanded.get() else 200,
                height=40,
                font=font,
                corner_radius=8,
                fg_color="transparent",
                text_color="#ffffff",
                hover_color="#2d2d2d",
                anchor="w",
                command=command
            )
            btn.name = f"{text.lower()}_btn"
            btn.pack(pady=5, padx=10)
            return btn

        #icones
        dashboard_icon = ctk.CTkImage(Image.open(r"images/icons/dashboard.png"), size=(24, 24))
        loan_icon = ctk.CTkImage(Image.open(r'images/icons/loan.png'), size=(24, 24))
        simulation_icon = ctk.CTkImage(Image.open(r'images/icons/simulation.png'), size=(24, 24))
        #reports_icon = ctk.CTkImage(Image.open(r'images/icons/reports.png'), size=(24, 24))
        settings_icon = ctk.CTkImage(Image.open(r'images/icons/settings.png'), size=(24, 24))
        help_icon = ctk.CTkImage(Image.open(r'images/icons/help.png'), size=(24, 24))
        profile_icon = ctk.CTkImage(Image.open(r'images/icons/profile.png'), size=(20, 24))
        exit_icon = ctk.CTkImage(Image.open(r'images/icons/exit.png'), size=(24, 24))

        #botões da barra lateral
        custom_font = ("Poppins", 12, 'bold')
        dashboard_btn = create_sidebar_button("Dashboard", icon=dashboard_icon)
        simulation_btn = create_sidebar_button("Simulação", icon=simulation_icon)
        loan_btn = create_sidebar_button("Empréstimo", icon=loan_icon)
        #reports_btn = create_sidebar_button("Relatórios", icon=reports_icon)
        settings_btn = create_sidebar_button("Configurações", icon=settings_icon)
        help_btn = create_sidebar_button("Ajuda", icon=help_icon)

        def input_mouse(event):
            if not is_expanded.get():
                sidebar_frame.after(100, toggle_sidebar)
        
        def output_mouse(event):
            if is_expanded.get():
                sidebar_frame.after(300, toggle_sidebar)

        #eventos de passar mouse na barra lateral
        sidebar_frame.bind("<Enter>", input_mouse)
        sidebar_frame.bind("<Leave>", output_mouse)

        #área de conteúdo principal
        content_frame = ctk.CTkFrame(
            main_window,
            fg_color="#191f27",
            corner_radius=0
        )
        content_frame.pack(side="right", fill="both", expand=True)

        #barra superior
        top_bar = ctk.CTkFrame(
            content_frame,
            height=50,
            fg_color="#1a1a1a",
            corner_radius=0
        )
        top_bar.pack(fill="x")

        #botão para realizar logout no topo
        logout_btn = ctk.CTkButton(
            top_bar,
            text="Logout",
            width=100,
            fg_color="#d9534f",
            hover_color="#c9302c",
            command=self.close_application
        )
        logout_btn.pack(side="right", padx=10, pady=8)

        #botão de perfil no topo
        profile_btn = ctk.CTkButton(
            top_bar,
            text="Perfil",
            width=100,
            fg_color="#2d2d2d",
            hover_color="#3d3d3d"
        )
        profile_btn.pack(side="right", padx=10, pady=8)

        #função para trocar a tela
        def switch_screen(new_screen_function):
            #limpa a tela
            for widget in content_frame.winfo_children():
                widget.destroy()
            #chama a nova tela
            new_screen_function()

        #tela de dashboard
        global load_dashboard
        def load_dashboard():
            topbar()
            # Create a frame for the image slider
            slider_frame = ctk.CTkFrame(
                content_frame,
                fg_color="transparent"
            )
            slider_frame.pack(fill="both", expand=True)
            
            # Load and resize images for the slider
            image_paths = [
                "images/dashboard.png",
                "images/emprestimo.png",
                "images/simulacao.png"
            ]
            
            # Calculate dimensions based on content frame size
            def calculate_image_size(event=None):
                # Get the current frame dimensions
                frame_width = slider_frame.winfo_width()
                frame_height = slider_frame.winfo_height()
                return (frame_width, frame_height)
            
            # Initialize images list
            slider_images = []
            current_image_index = 0
            
            # Function to load and resize images
            def load_images(size):
                nonlocal slider_images
                slider_images = []
                for path in image_paths:
                    img = Image.open(path)
                    # Resize image to fit the frame while maintaining aspect ratio
                    img = img.resize(size, Image.Resampling.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                    slider_images.append(ctk_img)
                return slider_images
            
            # Create label for displaying images
            image_label = ctk.CTkLabel(slider_frame, text="")
            image_label.pack(fill="both", expand=True)
            
            # Function to update image with fade effect
            def update_image(index):
                nonlocal current_image_index
                
                # Configure the next image
                image_label.configure(image=slider_images[index])
                current_image_index = index
                
                # Schedule the next image change
                next_index = (index + 1) % len(slider_images)
                slider_frame.after(5000, update_image, next_index)
            
            # Function to handle window resize
            def on_resize(event):
                # Calculate new size and reload images
                new_size = calculate_image_size()
                nonlocal slider_images
                slider_images = load_images(new_size)
                # Update current image
                image_label.configure(image=slider_images[current_image_index])
            
            # Bind resize event
            slider_frame.bind('<Configure>', on_resize)
            
            # Initial load of images (with default size)
            initial_size = (1366, 728)  # Default size
            slider_images = load_images(initial_size)
            
            # Start the slideshow
            update_image(0)
     
        #tela de simulação
        def load_simulation():
            topbar()

            main_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            main_frame.pack(fill='both', expand=True)
            
            # Criar canvas com fundo transparente
            canvas = ctk.CTkCanvas(main_frame, bg='#242424', highlightthickness=0)
            scrollbar = ctk.CTkScrollbar(main_frame, command=canvas.yview)
            
            # Frame scrollable que conterá todo o conteúdo
            scrollable_frame = ctk.CTkFrame(canvas, fg_color='transparent')
            
            # Configurar o canvas
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # texto no top de simulação
            simulationtoptext = ctk.CTkImage(Image.open(r"images/simulationtop.png"), size=(566, 77))
            simulation_top = ctk.CTkLabel(scrollable_frame, text=None, image=simulationtoptext)
            simulation_top.pack(pady=20)

            #label inputs que irão receber os valores
            simulation_frame = ctk.CTkFrame(
            master=scrollable_frame, 
            width=750, 
            height=250,
            corner_radius=25,
            border_width=2,
            border_color='#f78d35'
            )
            simulation_frame.pack(pady=20, padx=50)
            simulation_frame.pack_propagate(False)
            
            global textpass_label
            #texto de passo a passo
            textpass = ctk.CTkImage(Image.open(r"images/textpass.png"), size=(591, 345))
            textpass_label = ctk.CTkLabel(scrollable_frame, text=None, image=textpass)
            textpass_label.pack(pady=20, padx=50)

            #função para calcular o emprestimo e jogar na tela
            def calcular():
                global resultado_frame, table_container_frame, interest_type, interest_rate, textpass_label, pmt, total_interest, total_final, num_installments, first_payment_date, loan_amount
                def convert_currency_to_float(value_str):
                    # Remove R$ se existir e quaisquer espaços
                    value_str = value_str.replace('R$', '').strip()
                    # Remove pontos dos milhares e substitui vírgula por ponto
                    value_str = value_str.replace('.', '').replace(',', '.')
                    return float(value_str)
                try:
                    self.dados_mensais = []
                    # Get input values
                    loan_amount = convert_currency_to_float(self.loan_amount_entry.get())
                    num_installments = int(self.installments_entry.get())
                    interest_rate = float(self.interest_rate_entry.get()) / 100
                    interest_type = self.interest_type_combo.get()
                    first_payment_date = datetime.strptime(self.first_payment_entry.get(), "%d/%m/%Y")

                    self.calculated_loan_amount = loan_amount
                    self.calculated_num_installments = num_installments
                    self.calculated_first_payment_date = first_payment_date
                    self.calculated_interest_rate = interest_rate
                    
                    # Convert annual rate to monthly if necessary
                    if interest_type == "Anual":
                        monthly_rate = interest_rate / 12
                    else:  # Monthly
                        monthly_rate = interest_rate

                    self.dados_mensais = []
                    
                    # Fixed installment calculation (Price Table)
                    pmt = loan_amount * (monthly_rate * (1 + monthly_rate)**num_installments) / ((1 + monthly_rate)**num_installments - 1)
                    remaining_balance = loan_amount

                    total_interest = (pmt * num_installments) - loan_amount  # Total interest paid
                    total_final = loan_amount + total_interest

                    self.total_interest = total_interest
                    self.total_final = total_final
                    
                    for month in range(num_installments):
                        interest_payment = remaining_balance * monthly_rate
                        principal_payment = pmt - interest_payment
                        remaining_balance -= principal_payment
                        
                        payment_date = first_payment_date + timedelta(days=30 * month)
                        
                        self.dados_mensais.append({
                            'mes': month + 1,
                            'data': payment_date.strftime("%d/%m/%Y"),
                            'prestacao': pmt,
                            'amortizacao': principal_payment,
                            'juros': interest_payment,
                            'saldo_devedor': max(0, remaining_balance)
                        })

                    # Clear previous frames safely
                    if 'resultado_frame' in globals():
                        try:
                            resultado_frame.destroy()
                        except:
                            pass

                    if 'table_container_frame' in globals():
                        try:
                            table_container_frame.destroy()
                        except:
                            pass

                    if 'textpass_label' in globals():
                        try:
                            textpass_label.destroy()
                        except:
                            pass

                    # Create table container
                    table_container_frame = ctk.CTkFrame(
                        master=scrollable_frame,
                        corner_radius=25,
                        border_width=2,
                        border_color='#f78d35',
                        height=400
                    )
                    table_container_frame.pack(padx=20, pady=(0,20))

                    #frame para mostrar os resultados
                    resultado_frame = ctk.CTkFrame(
                    master=table_container_frame, 
                    width=800, 
                    height=220, 
                    corner_radius=25, 
                    border_width=2, 
                    border_color='#f78d35'
                    )
                    resultado_frame.pack(padx=20, pady=(20, 30))

                    #design para mostrar os resultados
                    resultadoimg = ctk.CTkImage(Image.open(r"images/resultado.png"), size=(723, 145))
                    resultado_img = ctk.CTkLabel(resultado_frame, text=None, image=resultadoimg)
                    resultado_img.place(x=38, y=40)

                    # label com os resultados
                    resultado_valortt = ctk.CTkLabel(resultado_frame, text="")
                    resultado_valortt.place(x=100, y=125)

                    resultado_juros = ctk.CTkLabel(resultado_frame, text="")
                    resultado_juros.place(x=340, y=125)

                    resultado_final = ctk.CTkLabel(resultado_frame, text="")
                    resultado_final.place(x=590, y=125)

                    resultado_valortt.configure(
                        bg_color="#f78d35",
                        text=f"R${loan_amount:,.2f}",
                        text_color="white",
                        font=("Poppins", 20) 
                    )

                    resultado_juros.configure(
                        bg_color="white",
                        text=f"R${total_interest:,.2f}",
                        text_color="#f78d35",
                        font=("Poppins", 20)
                    )

                    resultado_final.configure(
                        bg_color="white",
                        text=f"R${total_final:,.2f}",
                        text_color="#f78d35",
                        font=("Poppins", 20),
                    )
                    
                    # Table title
                    table_title = ctk.CTkLabel(
                        table_container_frame,
                        text="Detalhamento das Prestações",
                        font=("Poppins", 16, "bold"),
                        text_color="#f78d35"
                    )
                    table_title.pack(pady=(10, 0))
                    
                    # Create scrollable frame for table
                    table_frame = ctk.CTkFrame(table_container_frame)
                    table_frame.pack(side="top", padx=20, pady=20, fill="both", expand=True)

                    # Create canvas and scrollbar
                    canvas = ctk.CTkCanvas(table_frame, bg='#242424', highlightthickness=0)
                    scrollbar_y = ctk.CTkScrollbar(table_frame, command=canvas.yview)
                    canvas.configure(yscrollcommand=scrollbar_y.set)

                    # Scrollable table frame
                    scrollable_table_frame = ctk.CTkFrame(canvas)
                    canvas.create_window((0, 0), window=scrollable_table_frame, anchor="nw")

                    # Table headers
                    headers = ['Mês', 'Data', 'Prestação', 'Amortização', 'Juros', 'Saldo Devedor']
                    for col, header in enumerate(headers):
                        label = ctk.CTkLabel(
                            scrollable_table_frame,
                            text=header,
                            font=("Poppins", 12, "bold"),
                            text_color="#f78d35"
                        )
                        label.grid(row=0, column=col, padx=5, pady=5)

                    # Fill table with data
                    for row, dados in enumerate(self.dados_mensais, 1):
                        values = [
                            str(dados['mes']),
                            dados['data'],
                            f"R$ {dados['prestacao']:,.2f}",
                            f"R$ {dados['amortizacao']:,.2f}",
                            f"R$ {dados['juros']:,.2f}",
                            f"R$ {dados['saldo_devedor']:,.2f}"
                        ]
                        
                        for col, value in enumerate(values):
                            ctk.CTkLabel(
                                scrollable_table_frame,
                                text=value,
                                font=("Poppins", 12)
                            ).grid(row=row, column=col, padx=5, pady=2)

                    # Update table size
                    scrollable_table_frame.update_idletasks()
                    table_width = scrollable_table_frame.winfo_reqwidth() + 50
                    
                    canvas.configure(width=table_width, height=300)
                    canvas.configure(scrollregion=canvas.bbox("all"))

                    canvas.pack(side="left", fill="both", expand=True, padx=(120))
                    scrollbar_y.pack(side="right", fill="y")

                    buttonloan = ctk.CTkImage(Image.open(r"images/loanbutton.png"), size=(214, 36))
                    continue_loan_button = ctk.CTkButton(
                        table_container_frame,
                        text=None,
                        image=buttonloan,
                        fg_color='#191f27',
                        hover_color='#191f27',
                        command=loanbutton
                    )
                    continue_loan_button.pack(pady=50)

                except ValueError:
                    messagebox.showerror("Erro 5", "Por favor, preencha todos os campos corretamente.")

            #função para atualizar o scrollregion
            def calcular_wrapper():
                calcular()
                # Após calcular, atualizar o scrollregion
                canvas.configure(scrollregion=canvas.bbox("all"))

            #função para limpar os inputs
            def limpar():
                loan_amount_entry.delete(0, ctk.END)
                installments_entry.delete(0, ctk.END)
                interest_rate_entry.delete(0, ctk.END)
                first_payment_entry.delete(0, ctk.END)
                
                try:  
                    if 'textpass_label' in globals():
                        global textpass_label
                        textpass_label.destroy()
                        textpass_label = ctk.CTkLabel(content_frame, text=None, image=textpass)
                        textpass_label.pack(pady=20)
                except NameError:
                    pass                        

                try:
                    if 'table_container_frame' in globals():
                            table_container_frame.destroy()
                except NameError:
                    pass

                try:
                    if 'resultado_frame' in globals():
                            resultado_frame.destroy()
                except NameError:
                    pass
            
            #função para confirmar o empréstimo
            def loanbutton():
                main_frame.destroy()
                simulation_top.destroy()
                simulation_frame.destroy()
                table_container_frame.destroy()
                textpass_label.destroy()
                resultado_frame.destroy()

                global loan_frame
                loan_frame = ctk.CTkFrame(content_frame, 
                width=800, 
                height=800, 
                )
                loan_frame.pack(pady=50)

                imglogo = ctk.CTkImage(Image.open(r"images/logoquickfinancefront.png"), size=(228, 104))
                logoimg = ctk.CTkLabel(loan_frame, image=imglogo, text=None)
                logoimg.pack(pady=20)

                loanconfirme_label = ctk.CTkLabel(
                    loan_frame, 
                    text=f"Sr(a) {self.username_logged_in}, você deseja efetuar o empréstimo no valor de R$ {loan_amount:,.2f} em {num_installments} parcelas?\nA data do primeiro pagamento será {first_payment_date.strftime('%d/%m/%Y')}, e a taxa de juros será de {interest_rate:.2f} {interest_type}.\nO total do pagamento será de R$ {total_final:,.2f}.\nDeseja confirmar o empréstimo?", text_color="#f78d35", 
                    font=("Poppins", 18, "bold")
                )
                loanconfirme_label.pack(pady=50)

                #botão para confirmar o empréstimo
                effective_button = ctk.CTkButton(
                    loan_frame,
                    text="Efetivar",
                    font=("Poppins", 16, 'bold'),
                    fg_color='#f78d35', 
                    command=lambda: self.loan_register(loan_amount, num_installments, 
                    first_payment_date, interest_rate, total_interest, total_final),
                    hover_color='#cd3e1e', 
                    width=200, 
                    corner_radius=200
                )
                effective_button.pack(side="bottom", padx=100, pady=20)

                #botão para cancelar o empréstimo
                cancel_button = ctk.CTkButton(
                    loan_frame,
                    text="Cancelar",
                    font=("Poppins", 16, 'bold'),
                    fg_color='#343638', 
                    hover_color='#545658', 
                    width=200, 
                    corner_radius=200,
                    command=cancel_simulation_effective
                )
                cancel_button.pack(side="bottom", padx=120)

            #função para cancelar o empréstimo
            def cancel_simulation_effective():
                global top_bar
                if 'top_bar' in globals() and top_bar.winfo_exists():
                    top_bar.destroy()
                # Destrói outros elementos necessários
                if loan_frame.winfo_exists():
                    loan_frame.destroy()
                load_simulation()

            #formata o valor para moeda brasileira
            def format_currency(value):
                # Remove todos os caracteres não numéricos
                value = ''.join(filter(str.isdigit, value))
                
                # Se não houver números, retorna "0,00"
                if not value:
                    return "0,00"
                
                # Converte para float (divide por 100 para considerar os centavos)
                value = float(value) / 100
                
                # Formata como moeda brasileira
                return f"{value:,.2f}".replace(".", "*").replace(",", ".").replace("*", ",")

            #função para formatar o valor para moeda brasileira
            def validate_loan_amount(var, index, mode):
                current = loan_amount_var.get()
                
                # Se o usuário pressionar backspace e o campo ficar vazio
                if not current:
                    loan_amount_var.set("0,00")
                    return
                
                # Remove caracteres não numéricos para validação
                numbers = ''.join(filter(str.isdigit, current))
                
                # Formata o valor
                formatted = format_currency(numbers)
                
                # Atualiza o valor sem chamar o trace novamente
                loan_amount_var.set(formatted)
            
            #string var para a entry
            loan_amount_var = StringVar()  # Usando apenas StringVar do tkinter
            loan_amount_var.set("Valor do empréstimo")  # Valor inicial
                
            # Inputs
            #input de emprestimo
            cifrao = ctk.CTkImage(Image.open(r"images/icons/cifrao.png"), size=(20, 17))
            cifrao_label = ctk.CTkLabel(simulation_frame, text=None, image=cifrao)
            cifrao_label.place(x=30, y=50)
            self.loan_amount_entry = ctk.CTkEntry(simulation_frame, textvariable=loan_amount_var, placeholder_text='Valor do empréstimo', width=250, height=35, corner_radius=60, font=('Poppins', 14))
            self.loan_amount_entry.place(x=55, y=50)

            # Adicionar o trace para monitorar mudanças
            loan_amount_var.trace_add("write", validate_loan_amount)

            # Função para obter o valor como float (use quando precisar do valor para cálculos)
            def get_loan_amount():
                value = loan_amount_var.get()
                return float(value.replace(".", "").replace(",", "."))

            #data do primeiro pagamento
            calendar_icon = ctk.CTkImage(Image.open(r"images/icons/calendario2.png"), size=(20, 17))
            calendar_label = ctk.CTkLabel(simulation_frame, text=None, image=calendar_icon)
            calendar_label.place(x=30, y=100)
            self.first_payment_entry = ctk.CTkEntry(simulation_frame, placeholder_text='Data primeira parcela', width=250, height=35, corner_radius=60, font=('Poppins', 14))
            self.first_payment_entry.place(x=55, y=100)
            self.first_payment_entry.insert(0, (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y"))

            #numero de parcelas
            num = ctk.CTkImage(Image.open(r"images/icons/parcelas.png"), size=(20, 17))
            num_label = ctk.CTkLabel(simulation_frame, text=None, image=num)
            num_label.place(x=400, y=50)
            self.installments_entry = ctk.CTkEntry(simulation_frame, placeholder_text='Número de parcelas', width=300, height=35, corner_radius=60, font=('Poppins', 14))
            self.installments_entry.place(x=420, y=50)

            #taxa de juros
            percentimg = ctk.CTkImage(Image.open(r"images/icons/porcent.png"), size=(20, 17))
            percent = ctk.CTkLabel(simulation_frame, text=None, image=percentimg)
            percent.place(x=400, y=103)
            self.interest_rate_entry = ctk.CTkEntry(simulation_frame, placeholder_text='Taxa de juros', width=200, height=35, corner_radius=60, font=('Poppins', 14))
            self.interest_rate_entry.place(x=420, y=100)
            #combo do tipo de juros
            self.interest_type_combo = ctk.CTkComboBox(
                simulation_frame,
                values=["Mensal", "Anual"],
                width=100,
                height=35,
                corner_radius=60,
                font=('Poppins', 14)
            )
            self.interest_type_combo.set("Mensal")
            self.interest_type_combo.place(x=625, y=100)
            self.interest_type_combo._entry.grid_configure(padx=(10, 40))
            
            #botão para calcular o emprestimo
            calcular_btn = ctk.CTkButton(
                simulation_frame, 
                text="Calcular", 
                font=("Poppins", 16, 'bold'),
                fg_color='#f78d35', 
                command=calcular_wrapper, 
                hover_color='#cd3e1e', 
                width=120, 
                corner_radius=200)
            calcular_btn.place(x=55, y=170)

            #botão para limpar
            limpar_btn = ctk.CTkButton(
                simulation_frame, 
                text="Limpar", 
                font=("Poppins", 16, 'bold'),
                fg_color='#343638', 
                hover_color='#545658', 
                width=120, 
                corner_radius=200, 
                command=limpar)
            limpar_btn.place(x=600, y=170)

            # Criar a janela do canvas que conterá o frame scrollable
            canvas.create_window((0, 0), window=scrollable_frame, anchor="n")
            
            # Função para ajustar o scrollregion quando o conteúdo mudar
            def on_frame_configure(event):
                # Configurar a região de scroll para incluir todo o conteúdo
                canvas.configure(scrollregion=canvas.bbox("all"))
                # Centralizar o conteúdo no canvas
                canvas_width = canvas.winfo_width()
                frame_width = event.width
                if canvas_width > frame_width:
                    x = (canvas_width - frame_width) // 2
                    canvas.create_window((x, 0), window=scrollable_frame, anchor="n")
            
            # Função para ajustar a largura do canvas
            def on_canvas_configure(event):
                # Reconfigurar a largura da janela do canvas quando o canvas for redimensionado
                canvas_width = event.width
                frame_width = scrollable_frame.winfo_reqwidth()
                x = (canvas_width - frame_width) // 2 if canvas_width > frame_width else 0
                canvas.coords('frame', x, 0)
            
            # Bind as funções aos eventos
            scrollable_frame.bind("<Configure>", on_frame_configure)
            canvas.bind('<Configure>', on_canvas_configure)
            
            # Função para o scroll do mouse
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            # Bind o scroll do mouse ao canvas
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

            # Posicionar canvas e scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Atualizar as variáveis globais para usar o scrollable_frame
            global content_scroll_frame
            content_scroll_frame = scrollable_frame

            return content_scroll_frame

        #tela de emprestimo
        def load_loan():
            topbar()
            self.update_payment_status()

            #cria o canvas e o frame rolável
            canvas = ctk.CTkCanvas(content_frame, bg="#242424", highlightthickness=0)
            scrollbar = ctk.CTkScrollbar(content_frame, orientation="vertical", command=canvas.yview)
            scrollable_frame = ctk.CTkFrame(canvas)

            #configura o canvas e scrollbar
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            scrollable_frame.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                
            def _bind_mousewheel(event):
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
                
            def _unbind_mousewheel(event):
                canvas.unbind_all("<MouseWheel>")

            canvas.bind('<Enter>', _bind_mousewheel)
            canvas.bind('<Leave>', _unbind_mousewheel)

            loantopimg = ctk.CTkImage(Image.open(r"images/loantop.png"), size=(566, 77))
            loantop = ctk.CTkLabel(scrollable_frame, text=None, image=loantopimg)
            loantop.pack(padx=440,anchor="center", pady=20, fill="x")

            # Consultando os empréstimos no banco de dados
            loans = self.get_loans_from_db()

            # Cabeçalhos da tabela
            header_frame = ctk.CTkFrame(scrollable_frame, fg_color="#0d4b8a")
            header_frame.pack(padx=10, pady=(10, 5), fill="x")

            # Labels para os cabeçalhos
            header_labels = ["Valor do Empréstimo", "Data da 1° Parcela", "Parcelas"]
            for header in header_labels:
                header_label = ctk.CTkLabel(
                    header_frame,
                    text=header,
                    anchor="center",
                    font=("Poppins", 12, 'bold'),
                    text_color="white")
                header_label.pack(side="left", expand=True, padx=(0, 15))

            # Percorre o banco de dados e adiciona os empréstimos
            for loan in loans:
                loan_frame = ctk.CTkFrame(scrollable_frame,
                                        fg_color="#f19b2a",
                                        corner_radius=10,
                                        border_width=2,
                                        border_color="#C7C7C7")
                loan_frame.pack(padx=10, pady=5, fill="x")

                # Labels para os valores, cada uma em uma coluna
                loan_value_label = ctk.CTkLabel(
                    loan_frame,
                    text=f"R$ {loan['valor_emprestimo']:,.2f}",
                    font=("Poppins", 14, 'bold'),
                    text_color="black"
                )
                loan_value_label.pack(side="left", padx=(200, 0), expand=True)

                first_due_date_label = ctk.CTkLabel(
                    loan_frame,
                    text=f"{loan['data_primeira_parcela']}",
                    font=("Poppins", 14, 'bold'),
                    text_color="black"
                )
                first_due_date_label.pack(side="left", padx=(390, 0), expand=True)

                installments_label = ctk.CTkLabel(
                    loan_frame,
                    text=f"{loan['parcelas']}",
                    font=("Poppins", 14, 'bold'),
                    text_color="black"
                )
                installments_label.pack(side="left", padx=(420, 90), expand=True)

                # Botão de detalhes
                details_button = ctk.CTkButton(
                    loan_frame,
                    text="Detalhes",
                    width=100,
                    fg_color="#0d4b8a",
                    hover_color="#084298",
                    corner_radius=10,
                    font=("Poppins", 14, 'bold'),
                    command=lambda loan=loan: self.show_loan_details(loan)
                )
                details_button.pack(side="right", padx=(0, 10))

            #

        #tela de relatórios
        '''def load_reports():
            topbar()
            reports_label = ctk.CTkLabel(content_frame, text="Reports Content", font=("Poppins", 20))
            reports_label.pack(pady=20)'''

        #tela de configuração
        def load_settings():
            topbar()
            manutencaoimg = ctk.CTkImage(Image.open(r"images/manuten.png"), size=(500, 500))
            settings_label = ctk.CTkLabel(content_frame, image=manutencaoimg, text=None)
            settings_label.pack(pady=180)

        #tela de ajuda
        def load_help():
            messagebox.showinfo("Ajuda", "Para obter ajuda, entre em contato com o suporte através do site https://quickfinance.com\nEste projeto está disponível no github, acesse em https://github.com/quickfinance\nProjeto desenvolvido e criado por Chrysto")

        #configuração dos botões
        dashboard_btn.configure(command=lambda: switch_screen(load_dashboard))
        loan_btn.configure(command=lambda: switch_screen(load_loan))
        simulation_btn.configure(command=lambda: switch_screen(load_simulation))
        #reports_btn.configure(command=lambda: switch_screen(load_reports))
        settings_btn.configure(command=lambda: switch_screen(load_settings))
        help_btn.configure(command=load_help)
        
        #tela inicial dashboard
        switch_screen(load_dashboard)
    

        main_window.mainloop()
    
    def window_main_admin(self):
        #cria uma tela nova e centraliza no centro
        main_window_admin = ctk.CTk()
        main_window_admin_width = 1600
        main_window_admin_height = 900        
        screen_width = main_window_admin.winfo_screenwidth()
        screen_height = main_window_admin.winfo_screenheight()
        position_x = (screen_width // 2) - (main_window_admin_width // 2)
        position_y = (screen_height // 2) - (main_window_admin_height // 2)
        main_window_admin.geometry(f"{main_window_admin_width}x{main_window_admin_height}+{position_x}+{position_y}")
        main_window_admin.geometry("1600x900")
        main_window_admin.title("QUICKFINANCE - Versão Admin")
        main_window_admin.iconbitmap('images/icon-310x310.ico')
        main_window_admin.resizable(False, False)
        main_window_admin.configure(fg_color="#191f27")

        #frame sidebar
        sidebar_frame = ctk.CTkFrame(
            main_window_admin,
            width=67,
            height=720,
            fg_color="#0d4b8a",
            corner_radius=0
        )
        sidebar_frame.pack_propagate(False)
        sidebar_frame.pack(side="left", fill="y")

        #rastrea o estado da barra lateral
        is_expanded = ctk.BooleanVar(value=False)
        is_toggling = False
        
        
        #função para manipular a animação da barra lateral
        def toggle_sidebar(event=None):
            nonlocal is_toggling 
            if is_toggling:
                return

            is_toggling = True
            try:
                if is_expanded.get():
                    #contrai sidebar
                    sidebar_frame.configure(width=67)
                    for widget in sidebar_frame.winfo_children():
                        if isinstance(widget, ctk.CTkButton):
                            widget.configure(text="", width=67)
                    is_expanded.set(False)
                else:
                    #expande sidebar
                    sidebar_frame.configure(width=200)
                    for widget in sidebar_frame.winfo_children():
                        if isinstance(widget, ctk.CTkButton):
                            widget.configure(text=f" {widget.name.replace('_btn', '').capitalize()}", width=200)
                    is_expanded.set(True)
            finally:
                main_window_admin.after(300, lambda: set_toggling_false())

        #função para rastrear o estado da barra lateral
        def set_toggling_false():
            nonlocal is_toggling
            is_toggling = False

        #função para criar o topbar
        def topbar():
            global top_bar
            #cria um frame para o topbar
            top_bar = ctk.CTkFrame(
                content_frame,
                height=50,
                fg_color="#0d4b8a",
                corner_radius=0
            )
            top_bar.pack(fill="x", side="top")

            # Logout and Profile buttons in the top bar
            logout_btn = ctk.CTkButton(
                top_bar,
                text="Sair",
                width=100,
                fg_color="#e90313",
                hover_color="#c9302c",
                image=exit_icon,
                compound="left",
                corner_radius=60,
                font=("Poppins", 14, 'bold'),
                command=self.close_application
            )
            logout_btn.pack(side="right", padx=10, pady=8)


            profile_btn = ctk.CTkButton(
                top_bar,
                text="Perfil",
                width=100,
                fg_color='#f78d35', 
                hover_color='#cd3e1e',
                image=profile_icon,
                compound="left",
                corner_radius=60,
                font=("Poppins", 14, 'bold')
            )
            profile_btn.pack(side="right", padx=10, pady=8)
        
        #logo na sidebar
        logo_img = ctk.CTkImage(Image.open(r"images/logoquickfinance-32x32.png"), size=(32, 32))
        logo_label = ctk.CTkLabel(
            sidebar_frame,
            image=logo_img,
            text=None
        )
        logo_label.pack(pady=(20, 30))


        #função para criar botões da barra lateral
        #com efeito de foco
        def create_sidebar_button(text, icon=None, font=('Poppins', 12), command=None):
            btn = ctk.CTkButton(
                sidebar_frame,
                text="" if not is_expanded.get() else f"{text}",
                image=icon, #icone será mostrado sempre
                compound="left",
                width=60 if not is_expanded.get() else 200,
                height=40,
                font=font,
                corner_radius=8,
                fg_color="transparent",
                text_color="#ffffff",
                hover_color="#2d2d2d",
                anchor="w",
                command=command
            )
            btn.name = f"{text.lower()}_btn"
            btn.pack(pady=5, padx=10)
            return btn

        #icones
        dashboard_icon = ctk.CTkImage(Image.open(r"images/icons/dashboard.png"), size=(24, 24))
        loan_icon = ctk.CTkImage(Image.open(r'images/icons/loan.png'), size=(24, 24))
        simulation_icon = ctk.CTkImage(Image.open(r'images/icons/simulation.png'), size=(24, 24))
        reports_icon = ctk.CTkImage(Image.open(r'images/icons/reports.png'), size=(24, 24))
        settings_icon = ctk.CTkImage(Image.open(r'images/icons/settings.png'), size=(24, 24))
        help_icon = ctk.CTkImage(Image.open(r'images/icons/help.png'), size=(24, 24))
        profile_icon = ctk.CTkImage(Image.open(r'images/icons/profile.png'), size=(20, 24))
        exit_icon = ctk.CTkImage(Image.open(r'images/icons/exit.png'), size=(24, 24))

        #botões da barra lateral
        custom_font = ("Poppins", 12, 'bold')
        dashboard_btn = create_sidebar_button("Dashboard", icon=dashboard_icon)
        simulation_btn = create_sidebar_button("Simulação", icon=simulation_icon)
        loan_btn = create_sidebar_button("Empréstimos", icon=loan_icon)
        reports_btn = create_sidebar_button("Relatórios", icon=reports_icon)
        settings_btn = create_sidebar_button("Configurações", icon=settings_icon)
        help_btn = create_sidebar_button("Ajuda", icon=help_icon)

        def input_mouse(event):
            if not is_expanded.get():
                sidebar_frame.after(100, toggle_sidebar)
        
        def output_mouse(event):
            if is_expanded.get():
                sidebar_frame.after(300, toggle_sidebar)

        #eventos de passar mouse na barra lateral
        sidebar_frame.bind("<Enter>", input_mouse)
        sidebar_frame.bind("<Leave>", output_mouse)

        #área de conteúdo principal
        content_frame = ctk.CTkFrame(
            main_window_admin,
            fg_color="#191f27",
            corner_radius=0
        )
        content_frame.pack(side="right", fill="both", expand=True)

        #barra superior
        top_bar = ctk.CTkFrame(
            content_frame,
            height=50,
            fg_color="#1a1a1a",
            corner_radius=0
        )
        top_bar.pack(fill="x")

        #botão para realizar logout no topo
        logout_btn = ctk.CTkButton(
            top_bar,
            text="Logout",
            width=100,
            fg_color="#d9534f",
            hover_color="#c9302c",
            command=self.close_application
        )
        logout_btn.pack(side="right", padx=10, pady=8)

        #botão de perfil no topo
        profile_btn = ctk.CTkButton(
            top_bar,
            text="Perfil",
            width=100,
            fg_color="#2d2d2d",
            hover_color="#3d3d3d"
        )
        profile_btn.pack(side="right", padx=10, pady=8)

        #função para trocar a tela
        def switch_screen(new_screen_function):
            #limpa a tela
            for widget in content_frame.winfo_children():
                widget.destroy()
            #chama a nova tela
            new_screen_function()

        #tela de dashboard
        global load_dashboard
        def load_dashboard():
            topbar()
            # Create a frame for the image slider
            slider_frame = ctk.CTkFrame(
                content_frame,
                fg_color="transparent"
            )
            slider_frame.pack(fill="both", expand=True)
            
            # Load and resize images for the slider
            image_paths = [
                "images/dashboard.png",
                "images/emprestimo.png",
                "images/simulacao.png"
            ]
            
            # Calculate dimensions based on content frame size
            def calculate_image_size(event=None):
                # Get the current frame dimensions
                frame_width = slider_frame.winfo_width()
                frame_height = slider_frame.winfo_height()
                return (frame_width, frame_height)
            
            # Initialize images list
            slider_images = []
            current_image_index = 0
            
            # Function to load and resize images
            def load_images(size):
                nonlocal slider_images
                slider_images = []
                for path in image_paths:
                    img = Image.open(path)
                    # Resize image to fit the frame while maintaining aspect ratio
                    img = img.resize(size, Image.Resampling.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                    slider_images.append(ctk_img)
                return slider_images
            
            # Create label for displaying images
            image_label = ctk.CTkLabel(slider_frame, text="")
            image_label.pack(fill="both", expand=True)
            
            # Function to update image with fade effect
            def update_image(index):
                nonlocal current_image_index
                
                # Configure the next image
                image_label.configure(image=slider_images[index])
                current_image_index = index
                
                # Schedule the next image change
                next_index = (index + 1) % len(slider_images)
                slider_frame.after(5000, update_image, next_index)
            
            # Function to handle window resize
            def on_resize(event):
                # Calculate new size and reload images
                new_size = calculate_image_size()
                nonlocal slider_images
                slider_images = load_images(new_size)
                # Update current image
                image_label.configure(image=slider_images[current_image_index])
            
            # Bind resize event
            slider_frame.bind('<Configure>', on_resize)
            
            # Initial load of images (with default size)
            initial_size = (1366, 728)  # Default size
            slider_images = load_images(initial_size)
            
            # Start the slideshow
            update_image(0)
     
        #tela de simulação
        def load_simulation():
            topbar()

            main_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            main_frame.pack(fill='both', expand=True)
            
            # Criar canvas com fundo transparente
            canvas = ctk.CTkCanvas(main_frame, bg='#242424', highlightthickness=0)
            scrollbar = ctk.CTkScrollbar(main_frame, command=canvas.yview)
            
            # Frame scrollable que conterá todo o conteúdo
            scrollable_frame = ctk.CTkFrame(canvas, fg_color='transparent')
            
            # Configurar o canvas
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # texto no top de simulação
            simulationtoptext = ctk.CTkImage(Image.open(r"images/simulationtop.png"), size=(566, 77))
            simulation_top = ctk.CTkLabel(scrollable_frame, text=None, image=simulationtoptext)
            simulation_top.pack(pady=20)

            #label inputs que irão receber os valores
            simulation_frame = ctk.CTkFrame(
            master=scrollable_frame, 
            width=750, 
            height=250,
            corner_radius=25,
            border_width=2,
            border_color='#f78d35'
            )
            simulation_frame.pack(pady=20, padx=50)
            simulation_frame.pack_propagate(False)
            
            global textpass_label
            #texto de passo a passo
            textpass = ctk.CTkImage(Image.open(r"images/textpass.png"), size=(591, 345))
            textpass_label = ctk.CTkLabel(scrollable_frame, text=None, image=textpass)
            textpass_label.pack(pady=20, padx=50)

            #função para calcular o emprestimo e jogar na tela
            def calcular():
                global resultado_frame, table_container_frame, interest_type, interest_rate, textpass_label, pmt, total_interest, total_final, num_installments, first_payment_date, loan_amount
                def convert_currency_to_float(value_str):
                    # Remove R$ se existir e quaisquer espaços
                    value_str = value_str.replace('R$', '').strip()
                    # Remove pontos dos milhares e substitui vírgula por ponto
                    value_str = value_str.replace('.', '').replace(',', '.')
                    return float(value_str)
                try:
                    # Get input values
                    loan_amount = convert_currency_to_float(self.loan_amount_entry.get())
                    num_installments = int(self.installments_entry.get())
                    interest_rate = float(self.interest_rate_entry.get()) / 100
                    interest_type = self.interest_type_combo.get()
                    first_payment_date = datetime.strptime(self.first_payment_entry.get(), "%d/%m/%Y")

                    self.calculated_loan_amount = loan_amount
                    self.calculated_num_installments = num_installments
                    self.calculated_first_payment_date = first_payment_date
                    self.calculated_interest_rate = interest_rate
                    
                    # Convert annual rate to monthly if necessary
                    if interest_type == "Anual":
                        monthly_rate = interest_rate / 12
                    else:  # Monthly
                        monthly_rate = interest_rate

                    self.dados_mensais = []
                    
                    # Fixed installment calculation (Price Table)
                    pmt = loan_amount * (monthly_rate * (1 + monthly_rate)**num_installments) / ((1 + monthly_rate)**num_installments - 1)
                    remaining_balance = loan_amount

                    total_interest = (pmt * num_installments) - loan_amount  # Total interest paid
                    total_final = loan_amount + total_interest

                    self.total_interest = total_interest
                    self.total_final = total_final
                    
                    for month in range(num_installments):
                        interest_payment = remaining_balance * monthly_rate
                        principal_payment = pmt - interest_payment
                        remaining_balance -= principal_payment
                        
                        payment_date = first_payment_date + timedelta(days=30 * month)
                        
                        dados_mensais.append({
                            'mes': month + 1,
                            'data': payment_date.strftime("%d/%m/%Y"),
                            'prestacao': pmt,
                            'amortizacao': principal_payment,
                            'juros': interest_payment,
                            'saldo_devedor': max(0, remaining_balance)
                        })

                    # Clear previous frames safely
                    if 'resultado_frame' in globals():
                        try:
                            resultado_frame.destroy()
                        except:
                            pass

                    if 'table_container_frame' in globals():
                        try:
                            table_container_frame.destroy()
                        except:
                            pass

                    if 'textpass_label' in globals():
                        try:
                            textpass_label.destroy()
                        except:
                            pass

                    table_container_frame = ctk.CTkFrame(
                        master=scrollable_frame,
                        corner_radius=25,
                        border_width=2,
                        border_color='#f78d35',
                        height=400
                    )
                    table_container_frame.pack(padx=20, pady=(0,20))

                    #frame para mostrar os resultados
                    resultado_frame = ctk.CTkFrame(
                    master=table_container_frame, 
                    width=800, 
                    height=220, 
                    corner_radius=25, 
                    border_width=2, 
                    border_color='#f78d35'
                    )
                    resultado_frame.pack(padx=20, pady=(20, 30))

                    #design para mostrar os resultados
                    resultadoimg = ctk.CTkImage(Image.open(r"images/resultado.png"), size=(723, 145))
                    resultado_img = ctk.CTkLabel(resultado_frame, text=None, image=resultadoimg)
                    resultado_img.place(x=38, y=40)

                    # label com os resultados
                    resultado_valortt = ctk.CTkLabel(resultado_frame, text="")
                    resultado_valortt.place(x=100, y=125)

                    resultado_juros = ctk.CTkLabel(resultado_frame, text="")
                    resultado_juros.place(x=340, y=125)

                    resultado_final = ctk.CTkLabel(resultado_frame, text="")
                    resultado_final.place(x=590, y=125)

                    resultado_valortt.configure(
                        bg_color="#f78d35",
                        text=f"R${loan_amount:,.2f}",
                        text_color="white",
                        font=("Poppins", 20) 
                    )

                    resultado_juros.configure(
                        bg_color="white",
                        text=f"R${total_interest:,.2f}",
                        text_color="#f78d35",
                        font=("Poppins", 20)
                    )

                    resultado_final.configure(
                        bg_color="white",
                        text=f"R${total_final:,.2f}",
                        text_color="#f78d35",
                        font=("Poppins", 20),
                    )
                    
                    # Table title
                    table_title = ctk.CTkLabel(
                        table_container_frame,
                        text="Detalhamento das Prestações",
                        font=("Poppins", 16, "bold"),
                        text_color="#f78d35"
                    )
                    table_title.pack(pady=(10, 0))
                    
                    # Create scrollable frame for table
                    table_frame = ctk.CTkFrame(table_container_frame)
                    table_frame.pack(side="top", padx=20, pady=20, fill="both", expand=True)

                    # Create canvas and scrollbar
                    canvas = ctk.CTkCanvas(table_frame, bg='#242424', highlightthickness=0)
                    scrollbar_y = ctk.CTkScrollbar(table_frame, command=canvas.yview)
                    canvas.configure(yscrollcommand=scrollbar_y.set)

                    # Scrollable table frame
                    scrollable_table_frame = ctk.CTkFrame(canvas)
                    canvas.create_window((0, 0), window=scrollable_table_frame, anchor="nw")

                    # Table headers
                    headers = ['Mês', 'Data', 'Prestação', 'Amortização', 'Juros', 'Saldo Devedor']
                    for col, header in enumerate(headers):
                        label = ctk.CTkLabel(
                            scrollable_table_frame,
                            text=header,
                            font=("Poppins", 12, "bold"),
                            text_color="#f78d35"
                        )
                        label.grid(row=0, column=col, padx=5, pady=5)

                    # Fill table with data
                    for row, dados in enumerate(dados_mensais, 1):
                        values = [
                            str(dados['mes']),
                            dados['data'],
                            f"R$ {dados['prestacao']:,.2f}",
                            f"R$ {dados['amortizacao']:,.2f}",
                            f"R$ {dados['juros']:,.2f}",
                            f"R$ {dados['saldo_devedor']:,.2f}"
                        ]
                        
                        for col, value in enumerate(values):
                            ctk.CTkLabel(
                                scrollable_table_frame,
                                text=value,
                                font=("Poppins", 12)
                            ).grid(row=row, column=col, padx=5, pady=2)

                    # Update table size
                    scrollable_table_frame.update_idletasks()
                    table_width = scrollable_table_frame.winfo_reqwidth() + 50
                   
                    canvas.configure(width=table_width, height=300)
                    canvas.configure(scrollregion=canvas.bbox("all"))

                    canvas.pack(side="left", fill="both", expand=True, padx=(120))
                    scrollbar_y.pack(side="right", fill="y")
                    
                except ValueError:
                    messagebox.showerror("Erro 5", "Por favor, preencha todos os campos corretamente.")

            #função para atualizar o scrollregion
            def calcular_wrapper():
                calcular()
                # Após calcular, atualizar o scrollregion
                canvas.configure(scrollregion=canvas.bbox("all"))

            #função para limpar os inputs
            def limpar():
                loan_amount_entry.delete(0, ctk.END)
                installments_entry.delete(0, ctk.END)
                interest_rate_entry.delete(0, ctk.END)
                first_payment_entry.delete(0, ctk.END)
                
                try:  
                    if 'textpass_label' in globals():
                        global textpass_label
                        textpass_label.destroy()
                        textpass_label = ctk.CTkLabel(content_frame, text=None, image=textpass)
                        textpass_label.pack(pady=20)
                except NameError:
                    pass                        

                try:
                    if 'table_container_frame' in globals():
                            table_container_frame.destroy()
                except NameError:
                    pass

                try:
                    if 'resultado_frame' in globals():
                            resultado_frame.destroy()
                except NameError:
                    pass
            
            #formata o valor para moeda brasileira
            def format_currency(value):
                # Remove todos os caracteres não numéricos
                value = ''.join(filter(str.isdigit, value))
                
                # Se não houver números, retorna "0,00"
                if not value:
                    return "0,00"
                
                # Converte para float (divide por 100 para considerar os centavos)
                value = float(value) / 100
                
                # Formata como moeda brasileira
                return f"{value:,.2f}".replace(".", "*").replace(",", ".").replace("*", ",")

            #função para formatar o valor para moeda brasileira
            def validate_loan_amount(var, index, mode):
                current = loan_amount_var.get()
                
                # Se o usuário pressionar backspace e o campo ficar vazio
                if not current:
                    loan_amount_var.set("0,00")
                    return
                
                # Remove caracteres não numéricos para validação
                numbers = ''.join(filter(str.isdigit, current))
                
                # Formata o valor
                formatted = format_currency(numbers)
                
                # Atualiza o valor sem chamar o trace novamente
                loan_amount_var.set(formatted)
            
            #string var para a entry
            loan_amount_var = StringVar()  # Usando apenas StringVar do tkinter
            loan_amount_var.set("Valor do empréstimo")  # Valor inicial
                
            # Inputs
            #input de emprestimo
            cifrao = ctk.CTkImage(Image.open(r"images/icons/cifrao.png"), size=(20, 17))
            cifrao_label = ctk.CTkLabel(simulation_frame, text=None, image=cifrao)
            cifrao_label.place(x=30, y=50)
            self.loan_amount_entry = ctk.CTkEntry(simulation_frame, textvariable=loan_amount_var, placeholder_text='Valor do empréstimo', width=250, height=35, corner_radius=60, font=('Poppins', 14))
            self.loan_amount_entry.place(x=55, y=50)

            # Adicionar o trace para monitorar mudanças
            loan_amount_var.trace_add("write", validate_loan_amount)

            # Função para obter o valor como float (use quando precisar do valor para cálculos)
            def get_loan_amount():
                value = loan_amount_var.get()
                return float(value.replace(".", "").replace(",", "."))

            #data do primeiro pagamento
            calendar_icon = ctk.CTkImage(Image.open(r"images/icons/calendario2.png"), size=(20, 17))
            calendar_label = ctk.CTkLabel(simulation_frame, text=None, image=calendar_icon)
            calendar_label.place(x=30, y=100)
            self.first_payment_entry = ctk.CTkEntry(simulation_frame, placeholder_text='Data primeira parcela', width=250, height=35, corner_radius=60, font=('Poppins', 14))
            self.first_payment_entry.place(x=55, y=100)
            self.first_payment_entry.insert(0, (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y"))

            #numero de parcelas
            num = ctk.CTkImage(Image.open(r"images/icons/parcelas.png"), size=(20, 17))
            num_label = ctk.CTkLabel(simulation_frame, text=None, image=num)
            num_label.place(x=400, y=50)
            self.installments_entry = ctk.CTkEntry(simulation_frame, placeholder_text='Número de parcelas', width=300, height=35, corner_radius=60, font=('Poppins', 14))
            self.installments_entry.place(x=420, y=50)

            #taxa de juros
            percentimg = ctk.CTkImage(Image.open(r"images/icons/porcent.png"), size=(20, 17))
            percent = ctk.CTkLabel(simulation_frame, text=None, image=percentimg)
            percent.place(x=400, y=103)
            self.interest_rate_entry = ctk.CTkEntry(simulation_frame, placeholder_text='Taxa de juros', width=200, height=35, corner_radius=60, font=('Poppins', 14))
            self.interest_rate_entry.place(x=420, y=100)
            #combo do tipo de juros
            self.interest_type_combo = ctk.CTkComboBox(
                simulation_frame,
                values=["Mensal", "Anual"],
                width=100,
                height=35,
                corner_radius=60,
                font=('Poppins', 14)
            )
            self.interest_type_combo.set("Mensal")
            self.interest_type_combo.place(x=625, y=100)
            self.interest_type_combo._entry.grid_configure(padx=(10, 40))
            
            #botão para calcular o emprestimo
            calcular_btn = ctk.CTkButton(
                simulation_frame, 
                text="Calcular", 
                font=("Poppins", 16, 'bold'),
                fg_color='#f78d35', 
                command=calcular_wrapper, 
                hover_color='#cd3e1e', 
                width=120, 
                corner_radius=200)
            calcular_btn.place(x=55, y=170)

            #botão para limpar
            limpar_btn = ctk.CTkButton(
                simulation_frame, 
                text="Limpar", 
                font=("Poppins", 16, 'bold'),
                fg_color='#343638', 
                hover_color='#545658', 
                width=120, 
                corner_radius=200, 
                command=limpar)
            limpar_btn.place(x=600, y=170)

            # Criar a janela do canvas que conterá o frame scrollable
            canvas.create_window((0, 0), window=scrollable_frame, anchor="n")
            
            # Função para ajustar o scrollregion quando o conteúdo mudar
            def on_frame_configure(event):
                # Configurar a região de scroll para incluir todo o conteúdo
                canvas.configure(scrollregion=canvas.bbox("all"))
                # Centralizar o conteúdo no canvas
                canvas_width = canvas.winfo_width()
                frame_width = event.width
                if canvas_width > frame_width:
                    x = (canvas_width - frame_width) // 2
                    canvas.create_window((x, 0), window=scrollable_frame, anchor="n")
            
            # Função para ajustar a largura do canvas
            def on_canvas_configure(event):
                # Reconfigurar a largura da janela do canvas quando o canvas for redimensionado
                canvas_width = event.width
                frame_width = scrollable_frame.winfo_reqwidth()
                x = (canvas_width - frame_width) // 2 if canvas_width > frame_width else 0
                canvas.coords('frame', x, 0)
            
            # Bind as funções aos eventos
            scrollable_frame.bind("<Configure>", on_frame_configure)
            canvas.bind('<Configure>', on_canvas_configure)
            
            # Função para o scroll do mouse
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            # Bind o scroll do mouse ao canvas
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

            # Posicionar canvas e scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Atualizar as variáveis globais para usar o scrollable_frame
            global content_scroll_frame
            content_scroll_frame = scrollable_frame

            return content_scroll_frame

        #tela de emprestimo
        def load_loan():
            topbar()

            # Cria o canvas e o frame rolável
            canvas = ctk.CTkCanvas(content_frame, bg="#242424", highlightthickness=0)
            scrollbar = ctk.CTkScrollbar(content_frame, orientation="vertical", command=canvas.yview)
            scrollable_frame = ctk.CTkFrame(canvas)

            # Criação de um frame centralizador
            center_frame = ctk.CTkFrame(scrollable_frame)
            center_frame.pack(padx=10, pady=10, expand=True, fill="both")  # Frame centralizado

            # Configura o canvas e scrollbar
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Função para o scroll do mouse
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            # Bind o scroll do mouse ao canvas
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

            # Adiciona a barra de pesquisa
            search_frame = ctk.CTkFrame(center_frame)  # Mudança para usar o frame central
            search_frame.pack(padx=10, pady=(10, 5), fill="x")

            search_label = ctk.CTkLabel(
                search_frame, 
                text="Buscar por Nome:",
                font=("Poppins", 12, 'bold'))
            search_label.pack(side="left", padx=(0, 10))

            search_entry = ctk.CTkEntry(
                search_frame,
                corner_radius=50,
                font=("Poppins", 12, 'bold')
            )
            search_entry.pack(side="left", expand=True, fill="x")

            def search_loans():
                query = search_entry.get().lower()  # Obtém o texto da barra de pesquisa
                filter_loans(query)

            search_button = ctk.CTkButton(
                search_frame, 
                text="Pesquisar", 
                font=("Poppins", 12, 'bold'), 
                command=search_loans,
                corner_radius=50
            )
            search_button.pack(side="left", padx=(10, 0))

            # Cabeçalhos da tabela
            header_frame = ctk.CTkFrame(center_frame, fg_color="#0d4b8a")  # Mudança para usar o frame central
            header_frame.pack(padx=10, pady=(10, 5), fill="x")

            header_labels = ["Cliente", "Valor do Empréstimo", "Data da 1ª Parcela", "Parcelas", 'Status do Pagamento']
            for header in header_labels:
                header_label = ctk.CTkLabel(
                    header_frame,
                    text=header,
                    anchor="center",
                    font=("Poppins", 14, 'bold'),
                    text_color="white"
                )
                header_label.pack(side="left", expand=True, padx=10)

            # Listagem de empréstimos
            global loan_frames
            loan_frames = []  # Variável global para armazenar os frames dos empréstimos

            def filter_loans(query):
                # Remove os frames existentes
                for frame in loan_frames:
                    frame.destroy()
                loan_frames.clear()

                # Consultando os empréstimos no banco de dados
                loans = self.get_all_loans_from_db()

                for loan in loans:
                    if query in loan['nome'].lower():  # Filtra os empréstimos com base na pesquisa
                        loan_frame = ctk.CTkFrame(center_frame,
                                                fg_color="#f19b2a",
                                                corner_radius=10,
                                                border_width=2,
                                                border_color="#C7C7C7")
                        loan_frame.pack(padx=10, pady=5, fill="x")  # Mudança para usar o frame central
                        loan_frames.append(loan_frame)

                        # Centraliza as labels e aumenta o tamanho
                        client_label = ctk.CTkLabel(
                            loan_frame,
                            text=f"{loan['nome']}",
                            font=("Poppins", 16, 'bold'),  # Aumentei o tamanho da fonte
                            text_color="black",
                            width=200,  # Largura fixa
                            anchor="center"  # Centraliza o texto
                        )
                        client_label.pack(side="left", padx=(10, 5), expand=True)

                        loan_value_label = ctk.CTkLabel(
                            loan_frame,
                            text=f"R$ {loan['valor_emprestimo']:,.2f}",
                            font=("Poppins", 16, 'bold'),  # Aumentei o tamanho da fonte
                            text_color="black",
                            width=150,  # Largura fixa
                            anchor="center"  # Centraliza o texto
                        )
                        loan_value_label.pack(side="left", padx=(10, 5), expand=True)

                        first_due_date_label = ctk.CTkLabel(
                            loan_frame,
                            text=f"{loan['data_primeira_parcela']}",
                            font=("Poppins", 16, 'bold'),  # Aumentei o tamanho da fonte
                            text_color="black",
                            width=120,  # Largura fixa
                            anchor="center"  # Centraliza o texto
                        )
                        first_due_date_label.pack(side="left", padx=(10, 5), expand=True)

                        installments_label = ctk.CTkLabel(
                            loan_frame,
                            text=f"{loan['parcelas']}",
                            font=("Poppins", 16, 'bold'),  # Aumentei o tamanho da fonte
                            text_color="black",
                            width=100,  # Largura fixa
                            anchor="center"  # Centraliza o texto
                        )
                        installments_label.pack(side="left", padx=(10, 5), expand=True)

                        details_button = ctk.CTkButton(
                            loan_frame,
                            text="Detalhes",
                            width=100,
                            fg_color="#0d4b8a",
                            hover_color="#084298",
                            corner_radius=10,
                            font=("Poppins", 14, 'bold'),
                            command=lambda l=loan: show_loan_details(l)
                        )
                        details_button.pack(side="right", padx=(0, 10))

            # Chamada inicial para listar todos os empréstimos
            filter_loans("")  # Carrega todos os empréstimos inicialmente


            def show_loan_details(loan):
                self.conecta_db()
                try:
                    # Get the loan ID first
                    self.cursor.execute('''
                        SELECT id, valor_emprestimo, prim_data_pagamento, num_parcelas, 
                                juros, total_juros, total_final
                        FROM Emprestimos
                        WHERE username = ? AND valor_emprestimo = ?
                    ''', (self.username_logged_in, loan['valor_emprestimo']))
                        
                    loan_details = self.cursor.fetchone()
                    if not loan_details:
                        messagebox.showerror("Erro", "Empréstimo não encontrado")
                        return
                    
                    loan_id, loan_amount, first_payment_date, num_installments, \
                    interest_rate, total_interest, total_final = loan_details
                    
                    # Create a new window for the details
                    details_window = ctk.CTkToplevel()
                    details_window.title("Detalhes do Empréstimo")
                    details_window.geometry("800x600")
                    details_window.iconbitmap('images/logoquickfinance-32x32.png')
                    
                    details_window.attributes('-topmost', True)  # Faz a janela ser a principal e ficar em cima
                    details_window.lift()  # Levanta a janela

                    widgettext = ctk.CTkLabel(
                        master=details_window,
                        text="Detalhes do Empréstimo",
                        font=("Poppins", 18, "bold"),
                        text_color="#f78d35"
                    )
                    widgettext.pack(pady=10)

                    # Create frames for summary and table
                    summary_frame = ctk.CTkFrame(
                        master=details_window,
                        corner_radius=25,
                        border_width=2,
                        border_color='#f78d35'
                    )
                    summary_frame.pack(padx=20, pady=20, fill="x")

                    # Summary labels
                    summary_labels = [
                        f"Valor do Empréstimo: R$ {loan_amount:,.2f}",
                        f"Data da 1° Parcela: {first_payment_date} | Número de Parcelas: {num_installments}",
                        f"Taxa de Juros: {interest_rate:.2f}% | Total de Juros: R$ {total_interest:,.2f}",
                        f"Total Final: R$ {total_final:,.2f}",
                        ]
                        
                    for i, text in enumerate(summary_labels):
                        ctk.CTkLabel(
                            summary_frame,
                            text=text,
                            font=("Poppins", 12, 'bold')
                        ).pack(pady=5)
                        
                    # Create table frame
                    table_frame = ctk.CTkFrame(
                        master=details_window,
                        corner_radius=25,
                        border_width=2,
                        border_color='#f78d35'
                    )
                    table_frame.pack(padx=20, pady=20, fill="both", expand=True)
                        
                    # Create scrollable frame for table
                    table_scroll = ctk.CTkScrollableFrame(
                        master=table_frame,
                        corner_radius=0
                    )
                    table_scroll.pack(fill="both", expand=True, padx=10, pady=10)
                        
                    # Table headers
                    headers = ['Mês', 'Data', 'Prestação', 'Amortização', 'Juros', 'Saldo Devedor', 'Status do Pagamento']
                    for col, header in enumerate(headers):
                        ctk.CTkLabel(
                            table_scroll,
                            text=header,
                            font=("Poppins", 12, "bold"),
                            text_color="#f78d35"
                        ).grid(row=0, column=col, padx=5, pady=5)
                        
                    # Get and display installment details
                    self.cursor.execute('''
                        SELECT parcela, data_vencimento, valor_parcela,
                            amortizacao, juros, saldo_devedor, status_pagamento
                        FROM DetailsEmprestimos
                        WHERE emprestimo_id = ?
                            ORDER BY parcela
                        ''', (loan_id,))
                        
                    for row, installment in enumerate(self.cursor.fetchall(), 1):
                        values = [
                            str(installment[0]),
                            installment[1],
                            f"R$ {installment[2]:,.2f}",
                            f"R$ {installment[3]:,.2f}",
                            f"R$ {installment[4]:,.2f}",
                            f"R$ {installment[5]:,.2f}",
                            str(installment[6])
                        ]
                        
                        for col, value in enumerate(values):
                            ctk.CTkLabel(
                                table_scroll,
                                text=value,
                                font=("Poppins", 12, 'bold')
                            ).grid(row=row, column=col, padx=5, pady=2)

                    # Update scroll region after adding all items
                    table_frame.update_idletasks()
                    table_width = table_scroll.winfo_reqwidth() + 50
                    canvas.configure(width=table_width, height=300)
                    canvas.configure(scrollregion=canvas.bbox("all"))
                    
                    # Bind mouse wheel events
                    def _on_mousewheel(event):
                        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                        
                    def _bind_mousewheel(event):
                        canvas.bind_all("<MouseWheel>", _on_mousewheel)
                        
                    def _unbind_mousewheel(event):
                        canvas.unbind_all("<MouseWheel>")
                    
                    canvas.bind('<Enter>', _bind_mousewheel)
                    canvas.bind('<Leave>', _unbind_mousewheel)
                    
                    # Bind window close event to remove mousewheel binding
                    def on_closing():
                        canvas.unbind_all("<MouseWheel>")
                        details_window.destroy()
                        
                    details_window.protocol("WM_DELETE_WINDOW", on_closing)
                                
                except sqlite3.Error as e:
                    print(f"Erro ao buscar detalhes do empréstimo: {e}")
                    messagebox.showerror("Erro", "Erro ao carregar detalhes do empréstimo")
                finally:
                    self.desconecta_db()

        #tela de relatórios
        def load_reports():
            topbar()

            # Criar uma janela de seleção de relatórios
            report_window = ctk.CTkFrame(content_frame)
            report_window.pack(padx=20, pady=20, fill="both", expand=True)
            
            reporttopimg = ctk.CTkImage(Image.open(r"images/relatoriotop.png"), size=(566, 77))
            report_top = ctk.CTkLabel(report_window, text=None, image=reporttopimg)
            report_top.pack(pady=20)
            # Label de instruções
            instruction_label = ctk.CTkLabel(report_window, text="Escolha o relatório a ser baixado:", font=("Poppins", 16))
            instruction_label.pack(pady=20)
            
            # Botões para baixar relatórios
            buttonclientereport = ctk.CTkImage(Image.open(r"images/reportclientbutton.png"), size=(179, 29))
            btn_client_report = ctk.CTkButton(
                report_window, 
                text=None, 
                image=buttonclientereport,
                width=350,
                height=40, 
                corner_radius=60,
                fg_color="#1f538d",
                command=lambda: self.generate_report('clientes')
                )
            btn_client_report.pack(pady=10, padx=20)

            buttonloanreport = ctk.CTkImage(Image.open(r"images/reportloanbutton.png"), size=(224, 27))
            btn_loan_report = ctk.CTkButton(
                report_window, 
                text=None, 
                image=buttonloanreport,
                width=350,
                height=40, 
                corner_radius=60,
                fg_color="#1f538d",
                command=lambda: self.generate_report('emprestimos')
                )
            btn_loan_report.pack(pady=10, padx=20)

        #tela de configuração
        def load_settings():
            topbar()
            manutencaoimg = ctk.CTkImage(Image.open(r"images/manuten.png"), size=(500, 500))
            settings_label = ctk.CTkLabel(content_frame, image=manutencaoimg, text=None)
            settings_label.pack(pady=180)

        #tela de ajuda
        def load_help():
            messagebox.showinfo("Ajuda", "Para obter ajuda, entre em contato com o suporte através do site https://quickfinance.com.br\nEste projeto está disponível no github, acesse em https://github.com/quickfinance\nProjeto desenvolvido e criado por Chrysto")

        #configuração dos botões
        dashboard_btn.configure(command=lambda: switch_screen(load_dashboard))
        loan_btn.configure(command=lambda: switch_screen(load_loan))
        simulation_btn.configure(command=lambda: switch_screen(load_simulation))
        reports_btn.configure(command=lambda: switch_screen(load_reports))
        settings_btn.configure(command=lambda: switch_screen(load_settings))
        help_btn.configure(command=load_help)
        
        #tela inicial dashboard
        switch_screen(load_dashboard)
        
        #inicia a janela
        main_window_admin.mainloop()

    #função para fechar a aplicação
    def close_application(self):
        try:
            self.desconecta_db()

            exit()
        except Exception as e:
            print(f"An exception occurred while closing the application: {e}")
            exit()
    
if __name__=='__main__':
    app = Application()
    #app.mainloop()