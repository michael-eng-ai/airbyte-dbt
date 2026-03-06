#!/bin/bash
# Script de Finalização - Pipeline de Dados
# Para todos os processos e containers Docker

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para logs coloridos
log_info() {
    echo -e "${BLUE}  $1${NC}"
}

log_success() {
    echo -e "${GREEN} $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}  $1${NC}"
}

log_error() {
    echo -e "${RED} $1${NC}"
}

# Detectar diretório do script e ir para a raiz
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "🛑 FINALIZANDO PIPELINE DE DADOS"
echo "================================="

# Parar processos Python
log_info "Parando processos Python..."

# Parar Dashboard Streamlit
if pgrep -f "streamlit run scripts/dashboard.py" > /dev/null; then
    pkill -f "streamlit run scripts/dashboard.py"
    log_success "Dashboard Streamlit parado"
else
    log_info "Dashboard não estava rodando"
fi

# Parar Simulador de dados
if pgrep -f "scripts/insere_dados.py" > /dev/null; then
    pkill -f "scripts/insere_dados.py"
    log_success "Simulador de dados parado"
else
    log_info "Simulador de dados não estava rodando"
fi

# Parar Demo Apresentação se estiver rodando
if pgrep -f "scripts/demo_apresentacao.py" > /dev/null; then
    pkill -f "scripts/demo_apresentacao.py"
    log_success "Demo apresentação parada"
fi

# Parar qualquer processo do start_demo.sh
if pgrep -f "start_demo.sh" > /dev/null; then
    pkill -f "start_demo.sh"
    log_success "Script principal parado"
fi

# Parar todos os containers Docker
log_info "Parando containers Docker..."

if command -v docker &> /dev/null; then
    # Parar containers com profiles
    docker compose -f config/docker-compose.yml --profile airbyte --profile airflow down 2>/dev/null || true
    
    # Verificar se ainda há containers rodando
    if docker compose -f config/docker-compose.yml ps -q | grep -q .; then
        log_warning "Forçando parada de containers restantes..."
        docker compose -f config/docker-compose.yml down --remove-orphans 2>/dev/null || true
    fi
    
    log_success "Containers Docker parados"
else
    log_warning "Docker não encontrado"
fi

# Limpar arquivos de log se existirem
log_info "Limpando arquivos temporários..."

if [ -f "dashboard.log" ]; then
    rm dashboard.log
    log_success "Log do dashboard removido"
fi

if [ -f "insersor.log" ]; then
    rm insersor.log
    log_success "Log do insersor removido"
fi

# Verificar se ainda há processos rodando
log_info "Verificando processos restantes..."

remaining_processes=$(pgrep -f "streamlit\|insere_dados\|demo_apresentacao\|start_demo" || true)
if [ -n "$remaining_processes" ]; then
    log_warning "Ainda há processos relacionados rodando:"
    ps -f -p $remaining_processes 2>/dev/null || true
    echo ""
    read -p "Deseja forçar a parada destes processos? (s/N): " resposta
    if [[ $resposta =~ ^[Ss]$ ]]; then
        kill -9 $remaining_processes 2>/dev/null || true
        log_success "Processos forçadamente parados"
    fi
fi

# Verificar containers Docker restantes
if command -v docker &> /dev/null; then
    remaining_containers=$(docker ps -q --filter "label=com.docker.compose.project=airbyte-dbt" 2>/dev/null || true)
    if [ -n "$remaining_containers" ]; then
        log_warning "Ainda há containers relacionados rodando:"
        docker ps --filter "label=com.docker.compose.project=airbyte-dbt" 2>/dev/null || true
        echo ""
        read -p "Deseja forçar a parada destes containers? (s/N): " resposta
        if [[ $resposta =~ ^[Ss]$ ]]; then
            docker stop $remaining_containers 2>/dev/null || true
            docker rm $remaining_containers 2>/dev/null || true
            log_success "Containers forçadamente parados"
        fi
    fi
fi

echo ""
echo " FINALIZAÇÃO CONCLUÍDA!"
echo "========================="
echo ""
echo " Status:"
echo "    Processos Python parados"
echo "    Containers Docker parados"
echo "    Arquivos temporários limpos"
echo ""
echo "🔗 Portas liberadas:"
echo "    5430 (PostgreSQL)"
echo "    8501 (Dashboard)"
echo "    8001 (Airbyte)"
echo "    8080 (Airflow)"
echo ""
echo " Para reiniciar: ./start_demo.sh"
echo ""

log_success "Pipeline de dados finalizado com sucesso!" 