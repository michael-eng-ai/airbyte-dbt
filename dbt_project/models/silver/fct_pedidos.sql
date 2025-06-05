-- models/silver/fct_pedidos.sql
-- Este modelo cria a tabela de fatos para pedidos, transformando dados de bronze_pedidos
-- e juntando com dimensões como bronze_clientes.

{{ config(
    materialized='table',
    tags=['silver', 'fact']
) }}

-- Silver: Fatos de pedidos com estrutura empresarial
-- Nova estrutura completa de e-commerce

WITH bronze_pedidos AS (
    SELECT
        id as pedido_id,
        cliente_id,
        numero_pedido,
        data_pedido,
        status,
        valor_bruto,
        desconto,
        valor_liquido,
        metodo_pagamento,
        canal_venda,
        observacoes,
        data_entrega_prevista,
        data_entrega_real,
        updated_at
    FROM {{ ref('bronze_pedidos') }}
),

bronze_clientes AS (
    SELECT
        id as cliente_id,
        nome as nome_cliente,
        email as email_cliente,
        tipo_cliente,
        status as status_cliente
    FROM {{ ref('bronze_clientes') }}
)

SELECT
    p.pedido_id,
    p.cliente_id,
    bc.nome_cliente,
    bc.tipo_cliente,
    p.numero_pedido,
    p.status as status_pedido,
    p.valor_bruto,
    p.desconto,
    p.valor_liquido,
    p.metodo_pagamento,
    p.canal_venda,
    p.observacoes,
    p.data_pedido,
    p.data_entrega_prevista,
    p.data_entrega_real,
    EXTRACT(YEAR FROM p.data_pedido) AS ano_pedido,
    EXTRACT(MONTH FROM p.data_pedido) AS mes_pedido,
    EXTRACT(DAY FROM p.data_pedido) AS dia_pedido,
    p.updated_at,
    -- Cálculos derivados
    CASE 
        WHEN p.valor_bruto > 0 
        THEN (p.desconto / p.valor_bruto * 100)
        ELSE 0 
    END AS percentual_desconto,
    CASE 
        WHEN p.data_entrega_real IS NOT NULL AND p.data_entrega_prevista IS NOT NULL
        THEN p.data_entrega_real - p.data_entrega_prevista
        ELSE NULL
    END AS atraso_entrega_dias
FROM bronze_pedidos p
LEFT JOIN bronze_clientes bc ON p.cliente_id = bc.cliente_id
WHERE p.valor_bruto > 0  -- Validação básica
