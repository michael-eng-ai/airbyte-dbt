-- models/silver/fct_pedidos.sql
-- Este modelo cria a tabela de fatos para pedidos, transformando dados de stg_pedidos
-- e possivelmente juntando com dimensões como dim_clientes.

WITH stg_pedidos AS (
    SELECT
        pedido_id,
        cliente_id,
        produto,
        quantidade,
        preco_unitario,
        data_pedido,
        ultima_atualizacao,
        data_ingestao_airbyte
    FROM {{ ref('stg_pedidos') }}
),

dimensao_clientes AS (
    SELECT
        cliente_id,
        nome AS nome_cliente,
        email AS email_cliente
    FROM {{ ref('dim_clientes') }} -- Referencia o modelo da dimensão de clientes
)

SELECT
    p.pedido_id,
    p.cliente_id,
    dc.nome_cliente, -- Adiciona o nome do cliente para facilitar a análise
    p.produto,
    p.quantidade,
    p.preco_unitario,
    (p.quantidade * p.preco_unitario) AS valor_total_pedido, -- Cálculo de uma métrica importante
    p.data_pedido,
    EXTRACT(YEAR FROM p.data_pedido) AS ano_pedido,
    EXTRACT(MONTH FROM p.data_pedido) AS mes_pedido,
    EXTRACT(DAY FROM p.data_pedido) AS dia_pedido,
    p.ultima_atualizacao AS data_ultima_atualizacao_pedido,
    p.data_ingestao_airbyte
FROM
    stg_pedidos p
LEFT JOIN
    dimensao_clientes dc ON p.cliente_id = dc.cliente_id
-- WHERE p.quantidade > 0 AND p.preco_unitario > 0 -- Exemplo de regra de negócio/limpeza
