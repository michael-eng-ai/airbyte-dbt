-- models/gold/gold_visao_geral_clientes.sql

-- Este modelo de agregação fornece uma visão geral dos clientes,
-- combinando informações da camada silver de clientes e pedidos.

WITH silver_clientes AS (
    SELECT
        cliente_id_origem,
        nome_completo,
        email_padronizado,
        telefone,
        cpf,
        status,
        tipo_cliente,
        limite_credito,
        data_cadastro_ts,
        updated_at_ts,
        dominio_email,
        ano_cadastro,
        idade_estimada
    FROM
        {{ ref('silver_clientes') }}
),

silver_pedidos AS (
    SELECT
        cliente_id_origem,
        pedido_id_origem,
        valor_bruto_decimal,
        valor_liquido_decimal,
        status,
        data_pedido_ts
    FROM
        {{ ref('silver_pedidos') }}
),

pedidos_agregados_por_cliente AS (
    SELECT
        cliente_id_origem,
        COUNT(pedido_id_origem) AS total_pedidos,
        SUM(valor_liquido_decimal) AS valor_total_gasto,
        AVG(valor_liquido_decimal) AS ticket_medio,
        MIN(data_pedido_ts) AS data_primeiro_pedido,
        MAX(data_pedido_ts) AS data_ultimo_pedido,
        COUNT(CASE WHEN status = 'concluido' THEN 1 END) AS pedidos_concluidos
    FROM
        silver_pedidos
    GROUP BY
        cliente_id_origem
)

SELECT
    sc.cliente_id_origem,
    sc.nome_completo,
    sc.email_padronizado,
    sc.telefone,
    sc.cpf,
    sc.status,
    sc.tipo_cliente,
    sc.limite_credito,
    sc.data_cadastro_ts,
    sc.updated_at_ts AS updated_at_cliente_ts,
    sc.dominio_email,
    sc.ano_cadastro,
    sc.idade_estimada,
    COALESCE(pa.total_pedidos, 0) AS total_pedidos_realizados,
    COALESCE(pa.valor_total_gasto, 0.00) AS valor_total_gasto_cliente,
    COALESCE(pa.ticket_medio, 0.00) AS ticket_medio_cliente,
    pa.data_primeiro_pedido,
    pa.data_ultimo_pedido,
    COALESCE(pa.pedidos_concluidos, 0) AS pedidos_concluidos,
    (CASE
        WHEN pa.total_pedidos > 10 THEN 'Cliente VIP'
        WHEN pa.total_pedidos > 5 THEN 'Cliente Regular'
        WHEN pa.total_pedidos > 0 THEN 'Cliente Novo'
        ELSE 'Cliente Inativo (sem pedidos)'
    END) AS segmento_cliente,
    (CASE
        WHEN sc.limite_credito >= 10000 AND pa.total_pedidos > 5 THEN 'Premium'
        WHEN sc.limite_credito >= 5000 AND pa.total_pedidos > 2 THEN 'Gold'
        WHEN pa.total_pedidos > 0 THEN 'Silver'
        ELSE 'Bronze'
    END) AS categoria_valor
FROM
    silver_clientes sc
LEFT JOIN
    pedidos_agregados_por_cliente pa ON sc.cliente_id_origem = pa.cliente_id_origem

-- Adicionar aqui mais lógicas de negócio para a camada Gold:
-- - Cálculo de LTV (Lifetime Value)
-- - Análise de Churn
-- - Segmentação avançada de clientes
-- - Métricas de Recência, Frequência, Valor (RFV)