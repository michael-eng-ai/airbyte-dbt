-- models/bronze/bronze_produtos.sql
-- Camada Bronze: Dados brutos de produtos do e-commerce

{{ config(
    materialized='view',
    tags=['bronze', 'produtos', 'ecommerce', 'cdc']
) }}

-- Bronze: Dados brutos de produtos diretamente do source (replicado via Airbyte CDC)
-- Catálogo completo de produtos com informações comerciais
SELECT 
    id,
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
    updated_at,
    created_by,
    version,
    -- Metadados para auditoria CDC
    updated_at as ultima_modificacao_fonte
FROM {{ source('raw_data', 'produtos') }}
WHERE nome IS NOT NULL  -- Validação básica: produto deve ter nome 