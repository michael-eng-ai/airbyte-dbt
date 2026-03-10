-- postgres_target_init/01_schemas.sql
-- Inicialização do banco de destino do pipeline Kafka
-- Schemas espelham o db_source (sem colunas de metadados Airbyte)

-- ─── Clientes ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.clientes (
    id             BIGINT PRIMARY KEY,
    nome           VARCHAR(200),
    email          VARCHAR(200),
    telefone       VARCHAR(30),
    cpf            VARCHAR(20),
    data_nascimento DATE,
    status         VARCHAR(30),
    tipo_cliente   VARCHAR(30),
    limite_credito NUMERIC(15,2),
    data_cadastro  TIMESTAMP,
    updated_at     TIMESTAMP,
    created_by     VARCHAR(100),
    version        INT,
    endereco       TEXT
);

-- ─── Produtos ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.produtos (
    id             BIGINT PRIMARY KEY,
    codigo_produto VARCHAR(50) UNIQUE,
    nome           VARCHAR(200),
    categoria      VARCHAR(100),
    preco_custo    NUMERIC(15,2),
    preco_venda    NUMERIC(15,2),
    estoque_atual  INT,
    ativo          BOOLEAN DEFAULT TRUE,
    updated_at     TIMESTAMP
);

-- ─── Pedidos ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.pedidos (
    id                    BIGINT PRIMARY KEY,
    cliente_id            BIGINT,
    numero_pedido         VARCHAR(50) UNIQUE,
    data_pedido           TIMESTAMP,
    status                VARCHAR(30),
    valor_bruto           NUMERIC(15,2),
    desconto              NUMERIC(15,2) DEFAULT 0,
    valor_liquido         NUMERIC(15,2) GENERATED ALWAYS AS (valor_bruto - desconto) STORED,
    metodo_pagamento      VARCHAR(50),
    canal_venda           VARCHAR(50),
    observacoes           TEXT,
    data_entrega_prevista DATE,
    data_entrega_real     DATE,
    updated_at            TIMESTAMP,
    created_by            VARCHAR(100),
    version               INT
);

-- ─── Leads ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.leads (
    id                BIGINT PRIMARY KEY,
    nome              VARCHAR(200),
    email             VARCHAR(200),
    telefone          VARCHAR(30),
    fonte             VARCHAR(50),
    score             INT,
    status            VARCHAR(50),
    interesse         VARCHAR(50),
    orcamento_estimado NUMERIC(15,2),
    data_contato      DATE,
    data_conversao    DATE,
    updated_at        TIMESTAMP
);

-- ─── Schemas dbt ────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS public_bronze;
CREATE SCHEMA IF NOT EXISTS public_silver;
CREATE SCHEMA IF NOT EXISTS public_gold;
