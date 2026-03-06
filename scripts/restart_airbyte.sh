#!/bin/bash

# ============================================================================
# SCRIPT DE RESTART OTIMIZADO DO AIRBYTE
# ============================================================================
# Baseado nas melhores práticas para evitar problemas de "Server temporarily unavailable"
# e garantir inicialização correta dos serviços

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
CONFIG_DIR="$PROJECT_DIR/config"

echo -e "${BLUE} Iniciando restart otimizado do Airbyte...${NC}"

# Função para verificar se um serviço está saudável
check_service_health() {
    local service_name=$1
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}⏳ Aguardando $service_name ficar saudável...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "$CONFIG_DIR/docker-compose.yml" ps $service_name | grep -q "healthy\|Up"; then
            echo -e "${GREEN} $service_name está saudável${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}⏳ Tentativa $attempt/$max_attempts - Aguardando $service_name...${NC}"
        sleep 10
        ((attempt++))
    done
    
    echo -e "${RED} $service_name não ficou saudável após $max_attempts tentativas${NC}"
    return 1
}

# Função para verificar uso de memória
check_memory_usage() {
    echo -e "${BLUE} Verificando uso de memória...${NC}"
    
    # Verificar memória disponível no sistema
    available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    echo -e "${BLUE}💾 Memória disponível: ${available_memory}MB${NC}"
    
    if [ $available_memory -lt 4096 ]; then
        echo -e "${YELLOW}  Aviso: Memória disponível baixa. Recomendado: 8GB+ para Airbyte${NC}"
    fi
}

# Função para limpar recursos temporários
clean_temp_resources() {
    echo -e "${BLUE}🧹 Limpando recursos temporários...${NC}"
    
    # Limpar containers parados
    docker container prune -f > /dev/null 2>&1 || true
    
    # Limpar volumes órfãos (cuidado para não remover dados importantes)
    echo -e "${YELLOW}  Limpando volumes órfãos (dados temporários)...${NC}"
    docker volume prune -f > /dev/null 2>&1 || true
    
    # Limpar cache de imagens não utilizadas
    docker image prune -f > /dev/null 2>&1 || true
    
    echo -e "${GREEN} Limpeza concluída${NC}"
}

# Função principal de restart
restart_airbyte() {
    cd "$CONFIG_DIR"
    
    echo -e "${BLUE}🛑 Parando serviços do Airbyte na ordem correta...${NC}"
    
    # Parar serviços na ordem inversa de dependência
    echo -e "${YELLOW}⏹️  Parando airbyte-webapp...${NC}"
    docker-compose stop airbyte-webapp || true
    
    echo -e "${YELLOW}⏹️  Parando airbyte-worker...${NC}"
    docker-compose stop airbyte-worker || true
    
    echo -e "${YELLOW}⏹️  Parando airbyte-server...${NC}"
    docker-compose stop airbyte-server || true
    
    echo -e "${YELLOW}⏹️  Parando airbyte-temporal...${NC}"
    docker-compose stop airbyte-temporal || true
    
    echo -e "${YELLOW}⏹️  Parando airbyte-db...${NC}"
    docker-compose stop airbyte-db || true
    
    # Aguardar um momento para garantir que os containers pararam
    echo -e "${YELLOW}⏳ Aguardando containers pararem completamente...${NC}"
    sleep 5
    
    # Verificar memória antes de reiniciar
    check_memory_usage
    
    echo -e "${BLUE} Iniciando serviços do Airbyte na ordem correta...${NC}"
    
    # Iniciar banco de dados primeiro
    echo -e "${YELLOW}🗄️  Iniciando airbyte-db...${NC}"
    docker-compose up -d airbyte-db
    check_service_health "airbyte-db"
    
    # Iniciar Temporal
    echo -e "${YELLOW}⏰ Iniciando airbyte-temporal...${NC}"
    docker-compose up -d airbyte-temporal
    check_service_health "airbyte-temporal"
    
    # Iniciar servidor
    echo -e "${YELLOW}🖥️  Iniciando airbyte-server...${NC}"
    docker-compose up -d airbyte-server
    check_service_health "airbyte-server"
    
    # Iniciar worker
    echo -e "${YELLOW}👷 Iniciando airbyte-worker...${NC}"
    docker-compose up -d airbyte-worker
    check_service_health "airbyte-worker"
    
    # Iniciar webapp
    echo -e "${YELLOW} Iniciando airbyte-webapp...${NC}"
    docker-compose up -d airbyte-webapp
    check_service_health "airbyte-webapp"
    
    echo -e "${GREEN} Todos os serviços do Airbyte foram reiniciados com sucesso!${NC}"
}

# Função para mostrar status dos serviços
show_status() {
    echo -e "${BLUE} Status dos serviços Airbyte:${NC}"
    cd "$CONFIG_DIR"
    docker-compose ps airbyte-db airbyte-temporal airbyte-server airbyte-worker airbyte-webapp
    
    echo -e "\n${BLUE}🔗 URLs de acesso:${NC}"
    echo -e "${GREEN}• Airbyte UI: http://localhost:8080${NC}"
    echo -e "${GREEN}• Airbyte API: http://localhost:8001${NC}"
    echo -e "${GREEN}• Temporal UI: http://localhost:7233${NC}"
}

# Função para mostrar logs
show_logs() {
    local service=${1:-"airbyte-server"}
    echo -e "${BLUE}📜 Mostrando logs do $service...${NC}"
    cd "$CONFIG_DIR"
    docker-compose logs -f --tail=50 $service
}

# Menu principal
case "${1:-restart}" in
    "restart")
        restart_airbyte
        show_status
        ;;
    "clean-restart")
        clean_temp_resources
        restart_airbyte
        show_status
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "${2:-airbyte-server}"
        ;;
    "stop")
        echo -e "${BLUE}🛑 Parando todos os serviços Airbyte...${NC}"
        cd "$CONFIG_DIR"
        docker-compose stop airbyte-webapp airbyte-worker airbyte-server airbyte-temporal airbyte-db
        echo -e "${GREEN} Serviços Airbyte parados${NC}"
        ;;
    "help")
        echo -e "${BLUE}🔧 Script de Restart Otimizado do Airbyte${NC}"
        echo -e "\nUso: $0 [comando] [opções]"
        echo -e "\nComandos disponíveis:"
        echo -e "  restart       - Restart padrão dos serviços (padrão)"
        echo -e "  clean-restart - Restart com limpeza de recursos temporários"
        echo -e "  status        - Mostra status dos serviços"
        echo -e "  logs [serviço]- Mostra logs (padrão: airbyte-server)"
        echo -e "  stop          - Para todos os serviços"
        echo -e "  help          - Mostra esta ajuda"
        echo -e "\nExemplos:"
        echo -e "  $0                    # Restart padrão"
        echo -e "  $0 clean-restart      # Restart com limpeza"
        echo -e "  $0 logs airbyte-worker # Ver logs do worker"
        ;;
    *)
        echo -e "${RED} Comando inválido: $1${NC}"
        echo -e "${YELLOW}Use '$0 help' para ver os comandos disponíveis${NC}"
        exit 1
        ;;
esac