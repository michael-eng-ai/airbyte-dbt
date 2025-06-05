-- models/silver/silver_leads.sql

-- Este modelo transforma os dados brutos dos leads da camada bronze,
-- aplicando limpezas, padronizações e scoring para CRM.

{{ config(
    tags=["silver", "leads", "crm"],
    materialized='table'
) }}

WITH bronze_leads AS (
    SELECT
        id AS lead_id_origem,
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
        updated_at
    FROM
        {{ ref('bronze_leads') }}
)

SELECT
    l.lead_id_origem,
    INITCAP(TRIM(l.nome)) AS nome_lead_clean,
    LOWER(TRIM(l.email)) AS email_lead_clean,
    l.telefone,
    INITCAP(TRIM(l.empresa)) AS empresa_clean,
    INITCAP(TRIM(l.cargo)) AS cargo_clean,
    UPPER(TRIM(l.fonte)) AS fonte_padronizada,
    l.campanha_id,
    l.score,
    UPPER(TRIM(l.status)) AS status_padronizado,
    UPPER(TRIM(l.interesse)) AS interesse_padronizado,
    CAST(l.orcamento_estimado AS DECIMAL(18, 2)) AS orcamento_estimado_decimal,
    CAST(l.data_contato AS DATE) AS data_contato_clean,
    CAST(l.data_conversao AS DATE) AS data_conversao_clean,
    l.observacoes,
    l.tags,
    CAST(l.ultima_atividade AS TIMESTAMP) AS ultima_atividade_ts,
    CAST(l.updated_at AS TIMESTAMP) AS updated_at_ts,
    CURRENT_TIMESTAMP AS data_processamento,
    -- Colunas derivadas
    CASE 
        WHEN l.score >= 80 THEN 'Lead Quente'
        WHEN l.score >= 50 THEN 'Lead Morno'
        WHEN l.score > 0 THEN 'Lead Frio'
        ELSE 'Sem Score'
    END AS categoria_score,
    CASE 
        WHEN l.orcamento_estimado >= 50000 THEN 'Alto Valor'
        WHEN l.orcamento_estimado >= 10000 THEN 'Médio Valor'
        WHEN l.orcamento_estimado > 0 THEN 'Baixo Valor'
        ELSE 'Valor Não Informado'
    END AS categoria_orcamento,
    CASE 
        WHEN l.data_conversao IS NOT NULL THEN 'Convertido'
        WHEN l.status = 'QUALIFICADO' THEN 'Qualificado'
        WHEN l.status = 'NOVO' THEN 'Novo'
        ELSE 'Em Processo'
    END AS fase_funil,
    CASE 
        WHEN l.ultima_atividade >= CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 'Ativo'
        WHEN l.ultima_atividade >= CURRENT_TIMESTAMP - INTERVAL '30 days' THEN 'Inativo Recente'
        ELSE 'Inativo'
    END AS status_atividade,
    SUBSTRING(l.email FROM POSITION('@' IN l.email) + 1) AS dominio_email_lead
FROM
    bronze_leads l
WHERE
    l.nome IS NOT NULL 
    AND l.email IS NOT NULL 