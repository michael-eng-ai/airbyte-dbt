# Comparação de Arquiteturas — Pipeline de Dados

## Arquitetura Atual: Kafka + Debezium (Implementada)

### Fluxo:
```
PostgreSQL Source (WAL) → Debezium → Kafka → Consumer → PostgreSQL Target → dbt → Streamlit
```

### Características:
- **CDC Sub-segundo** — Latência < 1s entre Source e Target
- **Streaming Real** — Eventos fluem continuamente, sem polling
- **Baixo Recurso** — ~2GB RAM total (vs 6GB com Airbyte)
- **Escalável** — Kafka suporta múltiplos consumers e partições
- **Fault Tolerant** — Kafka retém mensagens, consumer pode reconectar

### Quando usar:
- Streaming de dados entre sistemas internos
- CDC com baixa latência exigida
- Projetos educacionais e POCs com infra realista
- Quando o número de fontes é pequeno e bem conhecido

---

## Arquitetura Simples (Near Real-Time)

### Fluxo:
```
PostgreSQL Source → dbt (direto) → Dashboard Streamlit
      ↑
  Simulador Python
```

### Características:
- **Simplicidade máxima** — 3 componentes
- **Latência mínima** — Sem intermediários
- **Recursos mínimos** — PostgreSQL + dbt + Streamlit

### Quando usar:
- POCs rápidas e demonstrações
- Desenvolvimento local sem CDC
- Prototipagem exploratória

---

## Arquitetura com Airbyte (ELT via Connectors)

### Fluxo:
```
PostgreSQL / API / SaaS → Airbyte → PostgreSQL Target → dbt → Dashboard
```

### Características:
- **300+ conectores** — Salesforce, Stripe, Google Ads, S3, etc.
- **ELT gerenciado** — Schema discovery, normalization automática
- **UI de configuração** — Sem código para conectar fontes

### Quando usar:
- Múltiplas fontes heterogêneas (SaaS, APIs externas)
- Times sem expertise em Kafka
- Data Warehouse / Lakehouse (BigQuery, Snowflake)

---

## Arquitetura Enterprise (Kafka + Airflow + dbt)

### Fluxo:
```
PostgreSQL → Kafka (Debezium) → Consumer → Data Lake
                                                ↓
                                         Airflow (DAGs)
                                                ↓
                                           dbt run
                                                ↓
                                           Dashboard
```

### Características:
- **Orquestração robusta** — Retry, SLA, alertas
- **Data Lake** — Armazenamento histórico em S3 / GCS
- **Escalabilidade enterprise** — Múltiplos clusters, partições

### Quando usar:
- Produção de larga escala
- Times grandes com SLAs rígidos
- Pipelines batch + streaming híbridos

---

## Resumo de Decisão

| Cenário | Kafka+Debezium | Airbyte | Airflow | Simples |
|---|---|---|---|---|
| **Demo / Educacional** | ✅ Ideal | ⚠️ Pesado | ❌ | ✅ |
| **CDC de baixa latência** | ✅ | ✅ | ❌ | ❌ |
| **Múltiplas fontes SaaS** | ⚠️ | ✅ Ideal | ✅ | ❌ |
| **Produção enterprise** | ✅ | ✅ | ✅ | ❌ |
| **RAM < 4GB** | ✅ (~2GB) | ❌ (~6GB) | ❌ | ✅ (~512MB) |