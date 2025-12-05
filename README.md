
# Projeto Carteira Digital 🪙

Implementação completa de uma **API de Carteira Digital** para a disciplina Projeto Banco de Dados:

- **FastAPI**
- **MySQL**
- **SQLAlchemy (Core, sem ORM)**
- **SQL puro para DDL/DML**
- Integração com API pública da **Coinbase** para conversão de moedas

A carteira permite:

- Criar carteiras (com chave pública e chave privada)
- Ver saldos por moeda (BTC, ETH, SOL, USD)
- Fazer **depósitos**
- Fazer **saques** (com taxa e validação da chave privada)
- Fazer **conversão entre moedas** (usando cotação da Coinbase)
- Fazer **transferência entre carteiras**

---

## 1. Pré-requisitos

Antes de começar, você precisa ter instalado no seu computador:

- Python 3.10+
- MySQL 8+
- git (opcional)

Verifique as versões:

```bash
python --version
mysql --version
```

---

## 2. Instalação e Configuração

### 2.1 Clonar ou baixar o projeto

```bash
git clone https://github.com/SofiaTravassos/Projeto_Carteira_Digital.git
cd Projeto_Carteira_Digital
```

Ou extraia o ZIP e abra o terminal dentro da pasta do projeto.

---

### 2.2 Criar e ativar o ambiente virtual (venv)

### Windows:
```bash
python -m venv venv
.\venv\Scripts\Activate
```

### Linux/Mac:
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 2.3 Instalar dependências

```bash
pip install -r requirements.txt
```

---

## 2.4 Configuração do Banco de Dados (MySQL)

Acesse seu MySQL e execute o script abaixo para criar o banco, o usuário e todas as tabelas:

```sql
-- 1. Base e Usuário
CREATE DATABASE IF NOT EXISTS wallet_homolog;
CREATE USER IF NOT EXISTS 'wallet_api_homolog'@'%' IDENTIFIED BY 'api123';
GRANT SELECT, INSERT, UPDATE, DELETE ON wallet_homolog.* TO 'wallet_api_homolog'@'%';
FLUSH PRIVILEGES;

USE wallet_homolog;

-- 2. Tabela Carteira
CREATE TABLE IF NOT EXISTS carteira (
    endereco_carteira VARCHAR(255) NOT NULL,
    hash_chave_privada VARCHAR(255) NOT NULL,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ATIVA',
    PRIMARY KEY (endereco_carteira)
);

-- 3. Tabela Moeda
CREATE TABLE IF NOT EXISTS moeda (
    id_moeda SMALLINT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL UNIQUE,
    nome VARCHAR(50) NOT NULL,
    tipo VARCHAR(10) NOT NULL
);

INSERT IGNORE INTO moeda (codigo, nome, tipo) VALUES
('BTC', 'Bitcoin', 'CRYPTO'),
('ETH', 'Ethereum', 'CRYPTO'),
('SOL', 'Solana', 'CRYPTO'),
('USD', 'Dólar Americano', 'FIAT'),
('BRL', 'Real Brasileiro', 'FIAT');

-- 4. Tabela Saldo
CREATE TABLE IF NOT EXISTS saldo_carteira (
    endereco_carteira VARCHAR(255) NOT NULL,
    id_moeda SMALLINT NOT NULL,
    saldo DECIMAL(18, 8) DEFAULT 0.0,
    data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (endereco_carteira, id_moeda),
    FOREIGN KEY (endereco_carteira) REFERENCES carteira(endereco_carteira),
    FOREIGN KEY (id_moeda) REFERENCES moeda(id_moeda)
);

-- 5. Histórico Deposito/Saque
CREATE TABLE IF NOT EXISTS deposito_saque (
    id_movimento BIGINT AUTO_INCREMENT PRIMARY KEY,
    endereco_carteira VARCHAR(255) NOT NULL,
    id_moeda SMALLINT NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    valor DECIMAL(18, 8) NOT NULL,
    taxa_valor DECIMAL(18, 8) DEFAULT 0.0,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (endereco_carteira) REFERENCES carteira(endereco_carteira),
    FOREIGN KEY (id_moeda) REFERENCES moeda(id_moeda)
);

-- 6. Conversões
CREATE TABLE IF NOT EXISTS conversao (
    id_conversao BIGINT AUTO_INCREMENT PRIMARY KEY,
    endereco_carteira VARCHAR(255) NOT NULL,
    id_moeda_origem SMALLINT NOT NULL,
    id_moeda_destino SMALLINT NOT NULL,
    valor_origem DECIMAL(18, 8) NOT NULL,
    valor_destino DECIMAL(18, 8) NOT NULL,
    taxa_percentual DECIMAL(5, 4) NOT NULL,
    taxa_valor DECIMAL(18, 8) NOT NULL,
    cotacao_utilizada DECIMAL(18, 8) NOT NULL,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (endereco_carteira) REFERENCES carteira(endereco_carteira),
    FOREIGN KEY (id_moeda_origem) REFERENCES moeda(id_moeda),
    FOREIGN KEY (id_moeda_destino) REFERENCES moeda(id_moeda)
);

-- 7. Transferências
CREATE TABLE IF NOT EXISTS transferencia (
    id_transferencia BIGINT AUTO_INCREMENT PRIMARY KEY,
    endereco_origem VARCHAR(255) NOT NULL,
    endereco_destino VARCHAR(255) NOT NULL,
    id_moeda SMALLINT NOT NULL,
    valor DECIMAL(18, 8) NOT NULL,
    taxa_valor DECIMAL(18, 8) NOT NULL,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (endereco_origem) REFERENCES carteira(endereco_carteira),
    FOREIGN KEY (endereco_destino) REFERENCES carteira(endereco_carteira),
    FOREIGN KEY (id_moeda) REFERENCES moeda(id_moeda)
);
```

---

## 2.5 Criar o arquivo `.env`

Crie o arquivo `.env` na raiz do projeto:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=wallet_api_homolog
DB_PASSWORD=api123
DB_NAME=wallet_homolog

TAXA_SAQUE_PERCENTUAL=0.01
TAXA_CONVERSAO_PERCENTUAL=0.02
TAXA_TRANSFERENCIA_PERCENTUAL=0.01

PRIVATE_KEY_SIZE=32
PUBLIC_KEY_SIZE=16
```

---

## 3. Estrutura do projeto

```
projeto_carteira_digital/
│
├── api/
│   ├── main.py
│   ├── models/
│   ├── routers/
│   ├── services/
│   └── persistence/
│       │── repositories/
│       └── db.py
│
├── sql/DDL_Carteira_Digital.sql
├── requirements.txt
└── .env
```

---

## 4. Subir a API

```bash
uvicorn api.main:app --reload
```

Acesse:

👉 http://127.0.0.1:8000/docs

---

## 5. Endpoints Disponíveis

### Gestão
- POST /carteiras: Cria carteira.
- GET /carteiras/{endereco}: Dados públicos da carteira.
- GET /carteiras/{endereco}/saldos: Lista saldos de todas as moedas.

### Operações
- POST /carteiras/{endereco}/depositos: Realizar depósito (BTC, ETH, SOL, USD, BRL).
- POST /carteiras/{endereco}/saques: Realizar saque.
- POST /carteiras/{endereco}/conversoes: Converter entre moedas (Ex: USD -> BTC) usando cotação Coinbase.
- POST /carteiras/{endereco}/transferencias: Enviar dinheiro para outra carteira.

---

## 10. Problemas comuns

- Banco não encontrado → conferir `.env`
- MySQL parado → iniciar serviço
- ImportError → verificar `__init__.py`

---

## Integrantes da Equipe

- Milo Moreira e Castro [@DuMilo]
- Sofia Travassos Bezerra [@SofiaTravassos]
