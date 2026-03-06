#  Pipeline CDC Completo - Airbyte + DBT

##  **Visão Geral**

Pipeline de dados moderno implementando **Change Data Capture (CDC)** com:
- **PostgreSQL Source** → Dados originais com CDC habilitado
- **Airbyte** → Engine de replicação em tempo real  
- **PostgreSQL Target** → Destino da replicação
- **DBT** → Transformações de dados (Bronze → Silver → Gold)
- **MinIO** → Data Lake S3-compatible
- **APIs Simuladas** → Fontes de dados externas

##  **Credenciais Padronizadas**

**Todos os serviços usam:**
```
Usuário: admin
Senha: admin
```

##  **Início Rápido**

###  **Executar Pipeline Completo**
```bash
./start_pipeline.sh
```

###  **Configurar Airbyte CDC (Manual)**
1. Abra http://localhost:8080
2. Configure Source: PostgreSQL `localhost:5430` (admin/admin)
3. Configure Target: PostgreSQL `localhost:5431` (admin/admin)
4. Ative CDC para tabelas: `clientes`, `pedidos`, `produtos`, `leads`
5. Inicie sincronização

###  **Executar DBT (Após CDC configurado)**
```bash
python3 scripts/executar_dbt.py debug    # Testar conexão
python3 scripts/executar_dbt.py bronze   # Modelos bronze
python3 scripts/executar_dbt.py silver   # Modelos silver
python3 scripts/executar_dbt.py gold     # Modelos gold
python3 scripts/executar_dbt.py full     # Pipeline completo
```

###  **Limpeza Completa (quando quiser resetar tudo)**
```bash
./clean_docker_environment.sh
```
** CUIDADO:** Remove TUDO - containers, volumes, dados, configurações!

## ��️ **Arquitetura**

### **Abordagem Híbrida: Docker + Python**
- **Docker**: Apenas para infraestrutura (PostgreSQL, Airbyte, MinIO)
- **Python**: Execução de lógica (DBT, verificações, criação de tabelas)
- **Credenciais Padronizadas**: admin/admin para todos os serviços

### **Fluxo de Dados**
```
1. PostgreSQL Source (dados originais)
   ↓
2. Airbyte CDC (Change Data Capture)
   ↓
3. PostgreSQL Target (dados replicados)
   ↓
4. DBT Python (transformações)
   ↓
5. Dashboard Streamlit
```

##  **Estrutura de Dados**

### **Tabelas Principais:**
- **clientes** - Dados de clientes com perfil empresarial
- **pedidos** - Pedidos sem itens (estrutura empresarial)
- **produtos** - Catálogo de produtos e-commerce
- **itens_pedido** - Relacionamento produtos↔pedidos
- **campanhas_marketing** - Campanhas de marketing
- **leads** - Leads gerados pelas campanhas

### **Camadas DBT:**
- ** Bronze** - Dados brutos replicados via Airbyte
- ** Silver** - Dados limpos e padronizados
- ** Gold** - Agregações e métricas de negócio

##  **URLs dos Serviços**

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Airbyte UI** | http://localhost:8080 | admin/admin |
| **MinIO Console** | http://localhost:9001 | admin/admin |
| **PostgreSQL Source** | localhost:5430 | admin/admin |
| **PostgreSQL Target** | localhost:5431 | admin/admin |
| **E-commerce API** | http://localhost:8010 | - |
| **CRM API** | http://localhost:8011 | - |

##  **Comandos Úteis**

### **Verificar Status**
```bash
cd config && docker compose ps
```

### **Logs dos Serviços**
```bash
cd config
docker compose logs postgres_source
docker compose logs airbyte-server
docker compose logs dbt_runner
```

### **Testar Conexões**
```bash
# PostgreSQL Source
psql -h localhost -p 5430 -U admin -d db_source

# PostgreSQL Target  
psql -h localhost -p 5431 -U admin -d db_target

# DBT Debug
cd config && docker compose exec dbt_runner dbt debug
```

### **Parar Tudo**
```bash
cd config && docker compose down --remove-orphans
```

##  **Estrutura do Projeto**

```
├── start_pipeline.sh              #  Script principal
├── config/
│   ├── env.config                 # Variáveis centralizadas
│   ├── docker-compose.yml         # Configuração completa
│   ├── load_env.sh               # Helper para variáveis
│   └── README_CREDENCIAIS.md     # Documentação de credenciais
├── postgres_init_scripts/
│   └── init_source_db.sql        # Schema do banco source
├── dbt_project/                  # Projeto DBT
│   ├── models/
│   │   ├── bronze/              # Camada Bronze
│   │   ├── silver/              # Camada Silver
│   │   └── gold/                # Camada Gold
│   └── dbt_project.yml
├── dbt_profiles/
│   └── profiles.yml             # Configuração DBT
└── apis_simuladas/              # APIs de dados externos
```

##  **Troubleshooting**

### **Problema: "role admin does not exist"**
```bash
cd config && docker compose down --volumes
docker system prune -f
./start_pipeline.sh
```

### **Problema: DBT não encontra tabelas**
1. Verifique se Airbyte replicou os dados:
```bash
cd config
docker compose exec postgres_target psql -U admin -d db_target -c "SELECT COUNT(*) FROM clientes;"
```

2. Se retornar erro, configure Airbyte primeiro

### **Problema: Portas ocupadas**
```bash
# Verificar portas em uso
lsof -i :5430 -i :5431 -i :8001 -i :8080 -i :9001

# Matar processos se necessário
killall postgres
docker compose down --remove-orphans
```

##  **Fluxo CDC Completo**

1. ** APIs inserem dados** → PostgreSQL Source
2. ** Airbyte captura CDC** → Replica para Target  
3. ** DBT processa** → Bronze → Silver → Gold
4. ** Dashboard consome** → Dados transformados

##  **Próximos Passos**

1. Execute `./start_pipeline.sh`
2. Configure Airbyte CDC no browser  
3. Aguarde dados serem replicados
4. Execute transformações DBT
5. Monitore pipeline em tempo real

---

** Pipeline CDC pronto para produção com credenciais admin/admin!**