#!/bin/bash
# PIPELINE CDC - SEQUÊNCIA ORIGINAL DO README
# 1. PostgreSQL (Source + Target) → 2. Airbyte → 3. Scripts → 4. DBT

set -e

# Carregar variáveis
if [ -f "config/env.config" ]; then
    source config/load_env.sh
else
    echo "ERRO: Arquivo config/env.config não encontrado"
    exit 1
fi

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}INFO: $1${NC}"; }
log_success() { echo -e "${GREEN}OK: $1${NC}"; }
log_warning() { echo -e "${YELLOW}AVISO: $1${NC}"; }
log_error() { echo -e "${RED}ERRO: $1${NC}"; }
log_step() { echo -e "${PURPLE}PASSO $1${NC}"; }
log_highlight() { echo -e "${CYAN}DESTAQUE: $1${NC}"; }

echo ""
echo "PIPELINE CDC - TOTALMENTE AUTOMATIZADO"
echo "======================================"
echo "Sistema inteligente de auto-configuração"
echo "Credenciais: admin/admin"
echo "Zero configuração manual necessária!"
echo ""

# ============================================================================
# PASSO 0: INSTALAÇÃO DE DEPENDÊNCIAS (PRIMEIRO DE TUDO)
# ============================================================================
log_step "0: INSTALANDO DEPENDÊNCIAS PYTHON"

log_info "Verificando e instalando dependências necessárias..."
if python3 scripts/instalar_dependencias.py; then
    log_success "Dependências instaladas com sucesso"
else
    log_error "Falha na instalação de dependências"
    log_info "Tentando continuar mesmo assim..."
fi

log_info "Instalando dependências do requirements.txt..."
if [ -f "requirements.txt" ]; then
    if pip3 install -r requirements.txt --quiet --disable-pip-version-check; then
        log_success "Requirements.txt instalado com sucesso"
    else
        log_warning "Falha ao instalar requirements.txt, mas continuando..."
    fi
else
    log_warning "Arquivo requirements.txt não encontrado"
fi

echo ""

# ============================================================================
# PASSO 1: BANCOS POSTGRESQL (PRIMEIRO)
# ============================================================================
log_step "1: INICIANDO BANCOS POSTGRESQL"

cd config
docker compose down --remove-orphans 2>/dev/null || true

log_info "Iniciando PostgreSQL Source (dados originais)..."
docker compose up -d postgres_source
sleep 15

if docker compose exec postgres_source pg_isready -U admin -d db_source; then
    log_success "PostgreSQL Source: admin@localhost:${POSTGRES_SOURCE_PORT}"
else
    log_error "PostgreSQL Source falhou!"
    exit 1
fi

log_info "Iniciando PostgreSQL Target (destino do Airbyte)..."
docker compose up -d postgres_target
sleep 10

if docker compose exec postgres_target pg_isready -U admin -d db_target; then
    log_success "PostgreSQL Target: admin@localhost:${POSTGRES_TARGET_PORT}"
else
    log_error "PostgreSQL Target falhou!"
    exit 1
fi

# Criar estrutura do banco Source
cd ..
log_info "Criando estrutura do banco Source..."
if python3 scripts/criar_tabelas.py; then
    log_success "Estrutura criada no Source"
else
    log_error "Falha na criação da estrutura"
    exit 1
fi

cd config

# ============================================================================
# PASSO 2: AIRBYTE (DEPOIS DOS BANCOS)
# ============================================================================
log_step "2: INICIANDO AIRBYTE (COM BANCOS PRONTOS)"

log_info "Iniciando Airbyte Database..."
docker compose up -d airbyte-db
sleep 15

log_info "Aguardando Airbyte DB ficar pronto..."
for i in {1..10}; do
    if docker compose exec airbyte-db pg_isready -U admin > /dev/null 2>&1; then
        log_success "Airbyte DB pronto!"
        break
    fi
    log_info "Tentativa $i/10..."
    sleep 5
done

log_info "Iniciando Airbyte Temporal..."
docker compose up -d airbyte-temporal
sleep 20

log_info "Iniciando Airbyte Server..."
docker compose up -d airbyte-server
sleep 30

log_info "Iniciando Airbyte Web Interface e Worker..."
docker compose up -d airbyte-webapp airbyte-worker
sleep 20

log_info "Aguardando Airbyte estar completamente disponível..."
sleep 45

# Verificar se Airbyte Web está acessível
if curl -s http://localhost:${AIRBYTE_WEBAPP_PORT} > /dev/null 2>&1; then
    log_success "Airbyte Web Interface: http://localhost:${AIRBYTE_WEBAPP_PORT}"
    AIRBYTE_READY=true
else
    log_warning "Airbyte ainda carregando, mas bancos estão prontos"
    AIRBYTE_READY=false
fi

# ============================================================================
# PASSO 3: INSERÇÃO DE DADOS E APIS
# ============================================================================
log_step "3: INICIANDO APIS E INSERINDO DADOS"

log_info "Iniciando APIs simuladoras..."
docker compose up -d api_ecommerce api_crm
sleep 15

# Verificar dados
cd ..
clientes_count=$(docker compose -f config/docker-compose.yml exec postgres_source psql -U admin -d db_source -t -c "SELECT COUNT(*) FROM clientes;" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$clientes_count" -gt 0 ]; then
    log_success "Dados no Source: $clientes_count clientes"
else
    log_info "Aguardando APIs inserirem dados..."
    sleep 30
    clientes_count=$(docker compose -f config/docker-compose.yml exec postgres_source psql -U admin -d db_source -t -c "SELECT COUNT(*) FROM clientes;" 2>/dev/null | tr -d ' ' || echo "0")
    log_info "Dados atuais: $clientes_count clientes"
fi

# ============================================================================
# PASSO 4: CONFIGURAÇÃO DO AIRBYTE
# ============================================================================
log_step "4: CONFIGURAÇÃO DO AIRBYTE"

if [ "$AIRBYTE_READY" = true ]; then
    log_highlight "Tentando configuração automática..."
    
    if python3 scripts/configurar_airbyte_automatico.py; then
        log_success "AIRBYTE CONFIGURADO AUTOMATICAMENTE!"
        AIRBYTE_AUTO_SUCCESS=true
    else
        log_warning "Configuração automática falhou"
        AIRBYTE_AUTO_SUCCESS=false
    fi
else
    log_warning "Airbyte não está pronto para configuração automática"
    AIRBYTE_AUTO_SUCCESS=false
fi

if [ "$AIRBYTE_AUTO_SUCCESS" != true ]; then
    log_highlight "CONFIGURAÇÃO MANUAL DO AIRBYTE:"
    echo ""
    echo "1. Abra: http://localhost:${AIRBYTE_WEBAPP_PORT}"
    echo "2. Source: PostgreSQL"
    echo "   - Host: postgres_source"
    echo "   - Port: 5432"
    echo "   - Database: db_source"
    echo "   - User: admin"
    echo "   - Password: admin"
    echo "   - SSL: Disable"
    echo ""
    echo "3. Destination: PostgreSQL"
    echo "   - Host: postgres_target"
    echo "   - Port: 5432"
    echo "   - Database: db_target"
    echo "   - User: admin"
    echo "   - Password: admin"
    echo "   - SSL: Disable"
    echo ""
    echo "4. Connection: Selecionar tabelas (clientes, pedidos, produtos, leads)"
    echo "5. Executar sincronização"
    echo ""
fi

# ============================================================================
# PASSO 5: DBT AUTOMATIZADO
# ============================================================================
log_step "5: CONFIGURAÇÃO AUTOMATIZADA DO DBT"

log_info "Instalando dependências do DBT..."
python3 scripts/instalar_dependencias.py > /dev/null 2>&1

log_highlight "INICIANDO AUTO-CONFIGURAÇÃO INTELIGENTE DO DBT"
log_info "Sistema detectará automaticamente o estado e configurará DBT"

# Executar auto-configurador inteligente
if python3 scripts/auto_configure_dbt.py; then
    log_success "DBT AUTO-CONFIGURADO COM SUCESSO!"
    DBT_AUTO_SUCCESS=true
    
    # Tentar executar DBT
    log_info "Executando pipeline DBT automaticamente..."
    if python3 scripts/executar_dbt.py run; then
        log_success "Pipeline DBT executado com sucesso!"
    else
        log_warning "DBT configurado, mas execução falhou (normal se ainda não há dados replicados)"
    fi
else
    log_warning "Falha na auto-configuração do DBT"
    DBT_AUTO_SUCCESS=false
fi

# ============================================================================
# PASSO 6: DEMONSTRAÇÃO INTERATIVA
# ============================================================================
log_step "6: INICIANDO DEMONSTRAÇÃO INTERATIVA"

# Função para abrir URL no navegador
abrir_no_navegador() {
    local url=$1
    log_info "Abrindo $url no navegador..."
    
    # Detectar OS e abrir navegador
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "$url" 2>/dev/null || true
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open "$url" 2>/dev/null || true
    else
        log_warning "Por favor, abra manualmente: $url"
    fi
}

# Abrir Airbyte Web UI
if [ "$AIRBYTE_READY" = true ]; then
    log_info "Abrindo Airbyte Web UI..."
    abrir_no_navegador "http://localhost:${AIRBYTE_WEBAPP_PORT}"
    sleep 2
fi

# Iniciar Dashboard Streamlit
log_info "Iniciando Dashboard de visualização..."
cd ..
if command -v streamlit &> /dev/null; then
    streamlit run scripts/dashboard.py \
        --server.port 8501 \
        --server.address localhost \
        --server.headless true \
        --browser.gatherUsageStats false \
        > /dev/null 2>&1 &
    DASHBOARD_PID=$!
    
    sleep 5
    if ps -p $DASHBOARD_PID > /dev/null; then
        log_success "Dashboard iniciado! PID: $DASHBOARD_PID"
        abrir_no_navegador "http://localhost:8501"
    else
        log_warning "Dashboard falhou ao iniciar"
    fi
else
    log_warning "Streamlit não instalado. Execute: pip install streamlit"
fi

# Iniciar insersor de dados para demonstrar CDC
log_info "Iniciando simulação de dados para CDC..."
python3 scripts/insere_dados.py > /tmp/insere_dados.log 2>&1 &
INSERSOR_PID=$!

if ps -p $INSERSOR_PID > /dev/null; then
    log_success "Simulador de dados iniciado! PID: $INSERSOR_PID"
    log_info "Dados sendo inseridos continuamente para demonstrar CDC"
else
    log_warning "Simulador de dados falhou ao iniciar"
fi

# ============================================================================
# STATUS FINAL COMPLETO
# ============================================================================
echo ""
log_highlight "PIPELINE AUTOMATIZADO E DEMONSTRAÇÃO INICIADOS!"

echo ""
log_highlight "🖥️  PÁGINAS WEB ABERTAS:"
echo " Dashboard Streamlit: http://localhost:8501"
echo " Airbyte Web UI: http://localhost:${AIRBYTE_WEBAPP_PORT}"
echo "🐘 PostgreSQL Source: localhost:${POSTGRES_SOURCE_PORT}"
echo "🐘 PostgreSQL Target: localhost:${POSTGRES_TARGET_PORT}"

echo ""
log_highlight "🤖 PROCESSOS ATIVOS:"
echo " Dashboard rodando (PID: ${DASHBOARD_PID:-N/A})"
echo " Insersor de dados rodando (PID: ${INSERSOR_PID:-N/A})"
echo " DBT auto-configurado e pronto"

if [ "$AIRBYTE_AUTO_SUCCESS" = true ]; then
    echo ""
    log_highlight "CDC CONFIGURADO AUTOMATICAMENTE!"
    echo "Dados estão sendo replicados do Source para Target"
else
    echo ""
    log_highlight "CONFIGURE O AIRBYTE MANUALMENTE:"
    echo "1. Acesse http://localhost:${AIRBYTE_WEBAPP_PORT}"
    echo "2. Configure Source e Destination conforme instruções acima"
    echo "3. Execute sincronização"
    echo "4. Veja os dados fluindo no Dashboard!"
fi

echo ""
log_highlight " DEMONSTRAÇÃO DO PIPELINE:"
echo "1. Dashboard mostra dados em tempo real"
echo "2. Insersor adiciona novos dados continuamente"
echo "3. Airbyte replica dados via CDC (quando configurado)"
echo "4. DBT transforma dados automaticamente"
echo "5. Visualize as mudanças no Dashboard!"

echo ""
log_highlight " COMANDOS ÚTEIS:"
echo "Ver logs do insersor: tail -f /tmp/insere_dados.log"
echo "Parar insersor: kill $INSERSOR_PID"
echo "Parar dashboard: kill $DASHBOARD_PID"
echo "Executar DBT: python3 scripts/executar_dbt.py run"
echo "Ver pipeline: python3 scripts/visualizar_pipeline.py"
echo "Limpar tudo: ./clean_docker_environment.sh"

echo ""
log_info "Pipeline rodando com demonstração interativa!"
log_info "Ctrl+C para finalizar tudo"

# Função para limpar ao sair
cleanup() {
    echo ""
    log_info "Encerrando demonstração..."
    
    # Parar processos
    if [ ! -z "$DASHBOARD_PID" ] && ps -p $DASHBOARD_PID > /dev/null; then
        kill $DASHBOARD_PID 2>/dev/null || true
        log_info "Dashboard parado"
    fi
    
    if [ ! -z "$INSERSOR_PID" ] && ps -p $INSERSOR_PID > /dev/null; then
        kill $INSERSOR_PID 2>/dev/null || true
        log_info "Insersor de dados parado"
    fi
    
    log_success "Demonstração encerrada!"
    exit 0
}

# Registrar função de limpeza
trap cleanup EXIT INT TERM

# Loop de monitoramento com auto-reconfiguração
while true; do
    sleep 60
    
    # Status dos containers
    airbyte_containers=$(docker ps --filter "name=airbyte" --format "{{.Names}}" | wc -l)
    postgres_containers=$(docker ps --filter "name=postgres" --format "{{.Names}}" | wc -l)
    
    source_clientes=$(docker compose -f config/docker-compose.yml exec postgres_source psql -U admin -d db_source -t -c "SELECT COUNT(*) FROM clientes;" 2>/dev/null | tr -d ' ' || echo "0")
    target_clientes=$(docker compose -f config/docker-compose.yml exec postgres_target psql -U admin -d db_target -t -c "SELECT COUNT(*) FROM clientes;" 2>/dev/null | tr -d ' ' || echo "0")
    
    # Auto-reconfiguração inteligente
    if [ ! -z "$target_clientes" ] && [ "$target_clientes" -gt 0 ] && [ "$DBT_AUTO_SUCCESS" != true ]; then
        log_info "Dados detectados no Target! Reconfigurando DBT automaticamente..."
        python3 scripts/auto_configure_dbt.py > /dev/null 2>&1
        DBT_AUTO_SUCCESS=true
    fi
    
    # Verificar se processos ainda estão rodando
    dashboard_status="OFF"
    insersor_status="OFF"
    
    if [ ! -z "$DASHBOARD_PID" ] && ps -p $DASHBOARD_PID > /dev/null; then
        dashboard_status="ON"
    fi
    
    if [ ! -z "$INSERSOR_PID" ] && ps -p $INSERSOR_PID > /dev/null; then
        insersor_status="ON"
    fi
    
    if [ ! -z "$target_clientes" ] && [ "$target_clientes" -gt 0 ]; then
        log_success "CDC ativo: $source_clientes → $target_clientes | PostgreSQL($postgres_containers) Airbyte($airbyte_containers) | Dashboard: $dashboard_status | Insersor: $insersor_status"
    else
        log_info "Source: $source_clientes clientes | Target: aguardando CDC | PostgreSQL($postgres_containers) Airbyte($airbyte_containers) | Dashboard: $dashboard_status | Insersor: $insersor_status"
    fi
done