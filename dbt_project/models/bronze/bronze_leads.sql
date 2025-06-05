-- models/bronze/bronze_leads.sql
-- Camada Bronze: Dados brutos de leads do CRM

{{ config(
    materialized='view',
    tags=['bronze', 'leads', 'crm', 'cdc']
) }}

-- Bronze: Dados brutos de leads diretamente do source (replicado via Airbyte CDC)
-- Prospects de vendas com informações de qualificação
SELECT 
    id,
    nome,
    email,
    telefone,
    empresa,
    cargo,
    fonte,
    campanha_id,
    score,
    status,
    interesse,
    orcamento_estimado,
    data_contato,
    data_conversao,
    observacoes,
    tags,
    ultima_atividade,
    updated_at,
    created_by,
    version,
    -- Metadados para auditoria CDC
    updated_at as ultima_modificacao_fonte
FROM {{ source('raw_data', 'leads') }}
WHERE nome IS NOT NULL  -- Validação básica: lead deve ter nome 