#  SISTEMA DE CREDENCIAIS CENTRALIZADO

##  Credenciais Padronizadas

**Todas as credenciais foram padronizadas para facilitar o uso:**

```
Usuário: admin
Senha: admin
```

## 🗂️ Arquivos de Configuração

### 📄 `env.config`
- **Arquivo principal** com todas as variáveis de ambiente
- Define credenciais, portas e configurações
- Usado automaticamente pelo `docker-compose.yml`

### 📄 `load_env.sh`
- **Script helper** para carregar variáveis no terminal
- Uso: `source config/load_env.sh`
- Mostra resumo das configurações carregadas

### 📄 `docker-compose.yml`
- **Configuração principal** dos serviços
- Usa variáveis de `env.config` automaticamente
- Valores padrão incorporados (fallback)

##  Serviços e Credenciais

### 🐘 PostgreSQL Source (Dados originais)
```
Host: localhost:5430
Usuário: admin
Senha: admin
Database: db_source
```

### 🐘 PostgreSQL Target (Airbyte destino)
```
Host: localhost:5431
Usuário: admin
Senha: admin
Database: db_target
```

###  Airbyte (CDC Engine)
```
UI: http://localhost:8080
Usuário: admin (default no Airbyte)
Senha: admin (default no Airbyte)
```

### 🗃️ MinIO (Data Lake)
```
Console: http://localhost:9001
API: http://localhost:9000
Usuário: admin
Senha: admin
```

###  DBT (Transformações)
```
Conecta automaticamente no PostgreSQL Target
Usuário: admin
Senha: admin
Database: db_target
```

###  APIs Externas
```
E-commerce API: http://localhost:8010
CRM API: http://localhost:8011
```

## 🔧 Como Usar

### 1. Carregar Variáveis (Opcional)
```bash
source config/load_env.sh
```

### 2. Iniciar Ambiente
```bash
cd config
docker compose up -d
```

### 3. Verificar Serviços
```bash
docker compose ps
```

### 4. Testar Conexões
```bash
# PostgreSQL Source
psql -h localhost -p 5430 -U admin -d db_source

# PostgreSQL Target
psql -h localhost -p 5431 -U admin -d db_target

# DBT
docker compose exec dbt_runner dbt debug
```

##  Personalizações

### Alterar Credenciais
1. Edite `config/env.config`
2. Reinicie os serviços: `docker compose down && docker compose up -d`

### Alterar Portas
1. Edite as variáveis `*_PORT` em `config/env.config`
2. Reinicie os serviços

### Adicionar Variáveis
1. Adicione em `config/env.config`
2. Adicione no `env_file` dos serviços relevantes no `docker-compose.yml`
3. Use `${VARIAVEL:-valor_padrao}` no docker-compose

## 🔍 Troubleshooting

### Verificar Variáveis Carregadas
```bash
source config/load_env.sh
echo $POSTGRES_SOURCE_USER
echo $POSTGRES_TARGET_USER
```

### Testar Conexões de Banco
```bash
# Source
docker compose exec postgres_source pg_isready -U admin -d db_source

# Target  
docker compose exec postgres_target pg_isready -U admin -d db_target
```

### Ver Logs dos Serviços
```bash
docker compose logs postgres_source
docker compose logs airbyte-server
docker compose logs dbt_runner
```

##  Pipeline Completo

1. **Source Database** → Dados originais (admin/admin)
2. **Airbyte** → Replicação CDC (admin/admin)
3. **Target Database** → Dados replicados (admin/admin)
4. **DBT** → Transformações (admin/admin)
5. **MinIO** → Data Lake (admin/admin)

**Todos os componentes usam as mesmas credenciais para simplicidade!**  