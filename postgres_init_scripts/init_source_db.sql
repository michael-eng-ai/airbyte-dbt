-- Script para criar schema, tabelas e popular o banco de dados de origem (postgres_source)

-- Inicialização PostgreSQL - CDC Completo
-- Configuração avançada para Change Data Capture

-- Criação de schemas organizacionais
CREATE SCHEMA IF NOT EXISTS transacional;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS public;

-- ============================================================================
-- CONFIGURAÇÕES CDC
-- ============================================================================

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Função para atualizar timestamp automaticamente
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TABELAS TRANSACIONAIS ORIGINAIS (Aprimoradas)
-- ============================================================================

-- Tabela de Clientes (Aprimorada para CDC)
CREATE TABLE IF NOT EXISTS public.clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    cpf VARCHAR(14) UNIQUE,
    data_nascimento DATE,
    endereco JSONB,
    status VARCHAR(20) DEFAULT 'ativo',
    tipo_cliente VARCHAR(20) DEFAULT 'pessoa_fisica',
    limite_credito DECIMAL(15,2) DEFAULT 0,
    data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'sistema',
    version INTEGER DEFAULT 1
);

-- Trigger para atualizar timestamp (com verificação de existência)
DROP TRIGGER IF EXISTS update_clientes_updated_at ON public.clientes;
CREATE TRIGGER update_clientes_updated_at
    BEFORE UPDATE ON public.clientes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Tabela de Pedidos (Aprimorada para CDC)
CREATE TABLE IF NOT EXISTS public.pedidos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES public.clientes(id),
    numero_pedido VARCHAR(50) UNIQUE NOT NULL,
    data_pedido TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) DEFAULT 'pendente',
    valor_bruto DECIMAL(15,2) NOT NULL,
    desconto DECIMAL(15,2) DEFAULT 0,
    valor_liquido DECIMAL(15,2) GENERATED ALWAYS AS (valor_bruto - desconto) STORED,
    metodo_pagamento VARCHAR(50),
    canal_venda VARCHAR(50) DEFAULT 'loja_online',
    observacoes TEXT,
    data_entrega_prevista DATE,
    data_entrega_real DATE,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'sistema',
    version INTEGER DEFAULT 1
);

-- Trigger para atualizar timestamp (com verificação de existência)
DROP TRIGGER IF EXISTS update_pedidos_updated_at ON public.pedidos;
CREATE TRIGGER update_pedidos_updated_at
    BEFORE UPDATE ON public.pedidos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- NOVAS TABELAS PARA DEMONSTRAR MÚLTIPLAS FONTES
-- ============================================================================

-- Produtos (para e-commerce)
CREATE TABLE IF NOT EXISTS public.produtos (
    id SERIAL PRIMARY KEY,
    codigo_produto VARCHAR(50) UNIQUE NOT NULL,
    nome VARCHAR(255) NOT NULL,
    categoria VARCHAR(100),
    subcategoria VARCHAR(100),
    marca VARCHAR(100),
    preco_custo DECIMAL(15,2),
    preco_venda DECIMAL(15,2) NOT NULL,
    margem_lucro DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN preco_custo > 0 THEN ((preco_venda - preco_custo) / preco_custo * 100)
            ELSE 0
        END
    ) STORED,
    estoque_atual INTEGER DEFAULT 0,
    estoque_minimo INTEGER DEFAULT 10,
    ativo BOOLEAN DEFAULT true,
    peso DECIMAL(8,3),
    dimensoes JSONB,
    descricao TEXT,
    tags TEXT[],
    data_lancamento DATE,
    fornecedor_id INTEGER,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'sistema',
    version INTEGER DEFAULT 1
);

DROP TRIGGER IF EXISTS update_produtos_updated_at ON public.produtos;
CREATE TRIGGER update_produtos_updated_at
    BEFORE UPDATE ON public.produtos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Itens do Pedido (relacionamento many-to-many)
CREATE TABLE IF NOT EXISTS public.itens_pedido (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER REFERENCES public.pedidos(id) ON DELETE CASCADE,
    produto_id INTEGER REFERENCES public.produtos(id),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario DECIMAL(15,2) NOT NULL,
    desconto_item DECIMAL(15,2) DEFAULT 0,
    valor_total DECIMAL(15,2) GENERATED ALWAYS AS (
        (quantidade * preco_unitario) - desconto_item
    ) STORED,
    observacoes TEXT,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'sistema',
    version INTEGER DEFAULT 1
);

DROP TRIGGER IF EXISTS update_itens_pedido_updated_at ON public.itens_pedido;
CREATE TRIGGER update_itens_pedido_updated_at
    BEFORE UPDATE ON public.itens_pedido
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Campanhas de Marketing (para CRM)
CREATE TABLE IF NOT EXISTS public.campanhas_marketing (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    canal VARCHAR(50),
    orcamento DECIMAL(15,2),
    data_inicio DATE NOT NULL,
    data_fim DATE,
    status VARCHAR(30) DEFAULT 'planejada',
    meta_leads INTEGER,
    leads_gerados INTEGER DEFAULT 0,
    taxa_conversao DECIMAL(5,2) DEFAULT 0,
    roi DECIMAL(8,2) DEFAULT 0,
    descricao TEXT,
    parametros JSONB,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'sistema',
    version INTEGER DEFAULT 1
);

DROP TRIGGER IF EXISTS update_campanhas_marketing_updated_at ON public.campanhas_marketing;
CREATE TRIGGER update_campanhas_marketing_updated_at
    BEFORE UPDATE ON public.campanhas_marketing
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Leads (prospects de vendas)
CREATE TABLE IF NOT EXISTS public.leads (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telefone VARCHAR(20),
    empresa VARCHAR(255),
    cargo VARCHAR(100),
    fonte VARCHAR(50),
    campanha_id INTEGER REFERENCES public.campanhas_marketing(id),
    score INTEGER DEFAULT 0 CHECK (score >= 0 AND score <= 100),
    status VARCHAR(30) DEFAULT 'novo',
    interesse VARCHAR(20) DEFAULT 'medio',
    orcamento_estimado DECIMAL(15,2),
    data_contato DATE DEFAULT CURRENT_DATE,
    data_conversao DATE,
    observacoes TEXT,
    tags TEXT[],
    ultima_atividade TIMESTAMP WITHOUT TIME ZONE,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'sistema',
    version INTEGER DEFAULT 1
);

DROP TRIGGER IF EXISTS update_leads_updated_at ON public.leads;
CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON public.leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- ÍNDICES PARA PERFORMANCE E CDC
-- ============================================================================

-- Índices para clientes
CREATE INDEX IF NOT EXISTS idx_clientes_email ON public.clientes(email);
CREATE INDEX IF NOT EXISTS idx_clientes_cpf ON public.clientes(cpf);
CREATE INDEX IF NOT EXISTS idx_clientes_status ON public.clientes(status);
CREATE INDEX IF NOT EXISTS idx_clientes_updated_at ON public.clientes(updated_at);

-- Índices para pedidos
CREATE INDEX IF NOT EXISTS idx_pedidos_cliente_id ON public.pedidos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON public.pedidos(status);
CREATE INDEX IF NOT EXISTS idx_pedidos_data ON public.pedidos(data_pedido);
CREATE INDEX IF NOT EXISTS idx_pedidos_updated_at ON public.pedidos(updated_at);

-- Índices para produtos
CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON public.produtos(categoria);
CREATE INDEX IF NOT EXISTS idx_produtos_ativo ON public.produtos(ativo);
CREATE INDEX IF NOT EXISTS idx_produtos_updated_at ON public.produtos(updated_at);

-- Índices para leads
CREATE INDEX IF NOT EXISTS idx_leads_email ON public.leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_status ON public.leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_campanha ON public.leads(campanha_id);
CREATE INDEX IF NOT EXISTS idx_leads_updated_at ON public.leads(updated_at);

-- ============================================================================
-- DADOS INICIAIS
-- ============================================================================

-- Inserir dados de exemplo (se não existirem)
INSERT INTO public.clientes (nome, email, telefone, cpf, data_nascimento, endereco, status, tipo_cliente, limite_credito)
SELECT 
    'João Silva', 
    'joao.silva@email.com', 
    '(11) 99999-1111',
    '123.456.789-01',
    '1985-03-15',
    '{"rua": "Rua das Flores, 123", "cidade": "São Paulo", "estado": "SP", "cep": "01234-567"}',
    'ativo',
    'pessoa_fisica',
    5000.00
WHERE NOT EXISTS (SELECT 1 FROM public.clientes WHERE email = 'joao.silva@email.com');

INSERT INTO public.clientes (nome, email, telefone, cpf, data_nascimento, endereco, status, tipo_cliente, limite_credito)
SELECT 
    'Maria Santos', 
    'maria.santos@email.com', 
    '(11) 99999-2222',
    '987.654.321-09',
    '1990-07-22',
    '{"rua": "Av. Principal, 456", "cidade": "Rio de Janeiro", "estado": "RJ", "cep": "22222-333"}',
    'ativo',
    'pessoa_fisica',
    3000.00
WHERE NOT EXISTS (SELECT 1 FROM public.clientes WHERE email = 'maria.santos@email.com');

-- Inserir produtos de exemplo
INSERT INTO public.produtos (codigo_produto, nome, categoria, marca, preco_custo, preco_venda, estoque_atual, ativo)
SELECT 'PROD001', 'Smartphone XYZ', 'Eletrônicos', 'TechCorp', 800.00, 1200.00, 50, true
WHERE NOT EXISTS (SELECT 1 FROM public.produtos WHERE codigo_produto = 'PROD001');

INSERT INTO public.produtos (codigo_produto, nome, categoria, marca, preco_custo, preco_venda, estoque_atual, ativo)
SELECT 'PROD002', 'Notebook ABC', 'Eletrônicos', 'CompuBrand', 1500.00, 2500.00, 25, true
WHERE NOT EXISTS (SELECT 1 FROM public.produtos WHERE codigo_produto = 'PROD002');

-- Inserir campanha de exemplo
INSERT INTO public.campanhas_marketing (nome, tipo, canal, orcamento, data_inicio, status, meta_leads)
SELECT 'Black Friday 2024', 'Promocional', 'Email + Social', 10000.00, CURRENT_DATE, 'ativa', 1000
WHERE NOT EXISTS (SELECT 1 FROM public.campanhas_marketing WHERE nome = 'Black Friday 2024');

-- ============================================================================
-- CONFIGURAÇÃO ESPECÍFICA PARA CDC
-- ============================================================================

-- Criar publicação para replicação lógica (apenas se não existir)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'airbyte_publication') THEN
        CREATE PUBLICATION airbyte_publication FOR ALL TABLES;
    END IF;
END $$;

-- Log de sucesso
DO $$
BEGIN
    RAISE NOTICE 'Database inicializado com sucesso para CDC';
    RAISE NOTICE 'Tabelas criadas: clientes, pedidos, produtos, itens_pedido, campanhas_marketing, leads';
    RAISE NOTICE 'CDC configurado com publicação: airbyte_publication';
    RAISE NOTICE 'Pronto para integração Airbyte + DBT';
END $$;
