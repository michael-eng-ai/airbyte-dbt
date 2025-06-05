-- models/silver/silver_produtos.sql

-- Este modelo transforma os dados brutos dos produtos da camada bronze,
-- aplicando limpezas, padronizações e cálculos para e-commerce.

{{ config(
    tags=["silver", "produtos", "ecommerce"],
    materialized='table'
) }}

WITH bronze_produtos AS (
    SELECT
        id AS produto_id_origem,
        codigo_produto,
        nome,
        categoria,
        subcategoria,
        marca,
        preco_custo,
        preco_venda,
        margem_lucro,
        estoque_atual,
        estoque_minimo,
        ativo,
        peso,
        dimensoes,
        descricao,
        tags,
        data_lancamento,
        fornecedor_id,
        updated_at
    FROM
        {{ ref('bronze_produtos') }}
)

SELECT
    p.produto_id_origem,
    TRIM(p.codigo_produto) AS codigo_produto_clean,
    INITCAP(TRIM(p.nome)) AS nome_produto_clean,
    UPPER(TRIM(p.categoria)) AS categoria_padronizada,
    UPPER(TRIM(p.subcategoria)) AS subcategoria_padronizada,
    INITCAP(TRIM(p.marca)) AS marca_clean,
    CAST(p.preco_custo AS DECIMAL(18, 2)) AS preco_custo_decimal,
    CAST(p.preco_venda AS DECIMAL(18, 2)) AS preco_venda_decimal,
    CAST(p.margem_lucro AS DECIMAL(8, 2)) AS margem_lucro_decimal,
    p.estoque_atual,
    p.estoque_minimo,
    p.ativo,
    p.peso,
    p.dimensoes,
    p.descricao,
    p.tags,
    p.data_lancamento,
    p.fornecedor_id,
    CAST(p.updated_at AS TIMESTAMP) AS updated_at_ts,
    CURRENT_TIMESTAMP AS data_processamento,
    -- Colunas derivadas
    CASE 
        WHEN p.estoque_atual <= p.estoque_minimo THEN 'Estoque Baixo'
        WHEN p.estoque_atual <= (p.estoque_minimo * 2) THEN 'Estoque Normal'
        ELSE 'Estoque Alto'
    END AS status_estoque,
    CASE 
        WHEN p.margem_lucro >= 50 THEN 'Alta Margem'
        WHEN p.margem_lucro >= 20 THEN 'Margem Normal'
        WHEN p.margem_lucro > 0 THEN 'Baixa Margem'
        ELSE 'Sem Margem'
    END AS categoria_margem,
    CASE 
        WHEN p.data_lancamento >= CURRENT_DATE - INTERVAL '30 days' THEN 'Lançamento'
        WHEN p.data_lancamento >= CURRENT_DATE - INTERVAL '365 days' THEN 'Recente'
        ELSE 'Estabelecido'
    END AS fase_produto
FROM
    bronze_produtos p
WHERE
    p.nome IS NOT NULL 
    AND p.preco_venda > 0
    AND p.ativo = true 