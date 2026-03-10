# kafka-debezium-dbt — Pipeline CDC em Tempo Real

Pipeline de dados moderno implementando **Change Data Capture (CDC)** com baixa latência via Kafka e Debezium, transformações em camadas via dbt e visualização em tempo real com Streamlit.

## Arquitetura

```
PostgreSQL Source  ──(WAL)──▶  Debezium (Kafka Connect)
                                        │
                               Kafka Topics (dbserver1.public.*)
                                        │
                              kafka_consumer.py (UPSERT)
                                        │
                              PostgreSQL Target (db_target)
                                        │
                              dbt run (Bronze → Silver → Gold)
                                        │
                              Streamlit Dashboard (localhost:8501)
```

## Stack

| Componente | Tecnologia | Porta |
|---|---|---|
| Source DB | PostgreSQL 13 (WAL logical) | 5430 |
| CDC Engine | Debezium 2.5 + Kafka Connect | 8083 |
| Message Broker | Apache Kafka 7.5 | 9092 |
| Target DB | PostgreSQL 13 | 5431 |
| Transformações | dbt-postgres 1.9 | — |
| Dashboard | Streamlit | 8501 |
| Data Lake | MinIO (S3) | 9000/9001 |

**RAM total: ~2GB** (vs ~6GB com Airbyte)

## Início Rápido

### 1. Subir o stack
```bash
cd config
docker-compose up -d
```

### 2. Registrar o conector Debezium
```bash
bash config/init_debezium.sh
```

> Aguarda Kafka Connect, cria o replication slot + publication no PostgreSQL e registra o conector via REST. Idempotente.

### 3. Iniciar o loop de demo
```bash
# Gera dados fake + executa dbt a cada 15s
python3 scripts/pipeline_demo_loop.py 15
```

### 4. Abrir o dashboard
```bash
streamlit run scripts/dashboard.py
# Acesse: http://localhost:8501
```

## Estrutura

```
kafka-debezium-dbt/
├── config/
│   ├── docker-compose.yml          # Stack completa (Kafka + dbt + Postgres)
│   ├── debezium-connector.json     # Configuração do conector Debezium
│   └── init_debezium.sh            # Script de inicialização do conector
├── postgres_init_scripts/          # Schema do db_source
├── postgres_target_init/           # Schema do db_target (sem metadados Airbyte)
├── dbt_project/                    # Modelos dbt
│   └── models/
│       ├── bronze/                 # Dados brutos replicados
│       ├── silver/                 # Dados limpos e padronizados
│       └── gold/                   # Agregações e métricas
├── dbt_profiles/
│   └── profiles.yml
├── scripts/
│   ├── kafka_consumer.py           # Consumer CDC → db_target (UPSERT)
│   ├── gerar_dados_continuos.py    # Gerador de dados fake
│   ├── pipeline_demo_loop.py       # Orquestrador da demo
│   └── dashboard.py                # Dashboard Streamlit
└── apis_simuladas/                 # APIs FastAPI de fontes externas
```

## Camadas dbt

| Camada | Schema | Descrição |
|---|---|---|
| Bronze | `public_bronze` | Dados brutos do CDC |
| Silver | `public_silver` | Dados normalizados |
| Gold | `public_gold` | Métricas e agregações |

## Comandos Úteis

```bash
# Status dos containers
cd config && docker-compose ps

# Logs do consumer Kafka
docker logs kafka_consumer -f

# Status do conector Debezium
curl http://localhost:8083/connectors/postgres-source-connector/status | python3 -m json.tool

# Executar dbt manualmente
docker exec dbt_runner_container bash -c \
  "cd /usr/app/dbt_project && dbt run --profiles-dir /root/.dbt --vars '{source_database: db_target}'"

# Conectar ao Source
psql -h localhost -p 5430 -U admin -d db_source

# Conectar ao Target
psql -h localhost -p 5431 -U admin -d db_target

# Parar tudo
cd config && docker-compose down --remove-orphans
```

## Credenciais

Todos os serviços: `admin / admin`

## Fluxo de Tipos Debezium → PostgreSQL

| Tipo Debezium | Formato | Conversão |
|---|---|---|
| `DATE` | `int32` (epoch days) | `date(1970,1,1) + timedelta(days=v)` |
| `TIMESTAMP` | `int64` (epoch microseconds) | `datetime.utcfromtimestamp(v/1_000_000)` |
| `JSONB` | `dict` | `json.dumps(v)` |
| `GENERATED` columns | Presente no payload | Excluído do INSERT |

---

Credenciais padrão: `admin/admin` | Latência CDC: < 1s