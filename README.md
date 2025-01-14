# QuickFinance

QuickFinance é uma aplicação robusta desenvolvida em Python, com foco na gestão de usuários e operações financeiras relacionadas a empréstimos. O sistema possui funcionalidades de cadastro, autenticação de usuários, simulação de empréstimos, acompanhamento de parcelas, geração de relatórios e muito mais. A aplicação adota uma interface gráfica moderna e responsiva construída com a biblioteca `CustomTkinter`.

## Funcionalidades Principais

- **Gerenciamento de Usuários**: Cadastro, autenticação e gerenciamento de informações pessoais e bancárias.
- **Simulação e Registro de Empréstimos**: Permite simular, registrar e acompanhar empréstimos com cálculos de parcelas, juros e totais.
- **Atualização Automática de Status**: Monitora e atualiza automaticamente o status das parcelas (em atraso, disponível, efetuado).
- **Geração de Relatórios**: Criação de relatórios customizados em formato Excel para clientes e empréstimos.
- **Interface Gráfica Intuitiva**: Navegação amigável e design moderno utilizando `CustomTkinter`.

## Tecnologias e Bibliotecas Utilizadas

### Bibliotecas Principais

- **CustomTkinter**: Para construção da interface gráfica moderna e personalizável.
- **tkcalendar**: Para seleção e validação de datas de forma intuitiva.
- **bcrypt**: Para hash e armazenamento seguro de senhas.
- **sqlite3**: Banco de dados embutido para armazenamento local e consultas eficientes.
- **Pandas**: Para manipulação de dados e exportação de relatórios em Excel.
- **xlsxwriter**: Para geração de relatórios formatados em Excel.
- **requests**: Para integração com APIs externas (ex.: consulta de CEP).
- **Pillow**: Para manipulação de imagens usadas na interface gráfica.

### Motivo da Escolha

- **CustomTkinter e tkinter**: Proporcionam uma interface simples e estilizada, facilitando a navegação para o usuário.
- **sqlite3**: Banco de dados leve e ideal para aplicações locais.
- **bcrypt**: Garantia de segurança ao armazenar informações sensíveis.
- **Pandas e xlsxwriter**: Oferecem ferramentas poderosas para análise de dados e relatórios customizados.

## Estrutura do Projeto

```plaintext
├── main.py         # Arquivo principal da aplicação
├── images/         # Imagens utilizados na interface gráfica
   └── icons/       # Icones utilizados na interface gráfica
├── data/           # Arquivos de dados, como o banco SQLite
└── README.md       # Documentação do projeto
```

## Como Executar o Projeto

1. **Pré-requisitos**:
   - Python 3.8 ou superior.
   - Dependências listadas no arquivo `requirements.txt`. Use `pip install -r requirements.txt` para instalá-las.

2. **Inicie o Sistema**:
   ```bash
   python main.py
   ```

3. **Navegue pela Interface**:
   - Faça login como administrador ou usuário.
   - Acesse funcionalidades como registro de empréstimos, simulação ou geração de relatórios.

## Funcionalidades em Detalhes

### Cadastro de Usuários

- O sistema valida CPF e RG em tempo real.
- Realiza buscas automáticas de endereço com base no CEP fornecido via API pública (ViaCEP).
- Hash seguro de senhas utilizando `bcrypt`.

### Gerenciamento de Empréstimos

- Registro detalhado de empréstimos, incluindo número de parcelas, taxas de juros e datas de vencimento.
- Monitoramento contínuo das parcelas com atualização automática de status (disponível, em atraso, efetuado).

### Geração de Relatórios

- Relatórios gerados no formato Excel com design responsivo e funcionalidade de filtro automático.
- Relatórios disponíveis para clientes e empréstimos registrados no sistema.

## Telas e Fluxos

1. **Tela de Login**:
   - Login para administradores e usuários comuns.
   - Acesso a tela de cadastro
  
2. **Tela de cadastro**:
   - Disponível para cadastro de usuários comuns, onde há a coleta de dados

3. **Dashboard**:
   - Resumo das principais informações do sistema.

4. **Simulação de Empréstimos**:
   - Permite calcular valores de parcelas com base no montante e taxa de juros.

5. **Gerenciamento de Parcelas**:
   - Visualização detalhada das parcelas de cada empréstimo.

## Melhorias Futuras

- Integração com APIs de pagamentos.
- Funcionalidade para exportação de dados em outros formatos (CSV, PDF).
- Suporte a múltiplos idiomas.
- Login via auth, Facebook e Google

## Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e pull requests para melhorias ou correções.

## Licença

Este projeto é licenciado sob a [MIT License](LICENSE).
