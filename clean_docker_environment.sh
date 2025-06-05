#!/bin/bash
# SCRIPT DE LIMPEZA COMPLETA DO AMBIENTE DOCKER
# Remove TODOS os containers, volumes, redes, imagens e dados do projeto
# Use quando quiser resetar completamente o ambiente

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_step() { echo -e "${PURPLE}🧹 ETAPA $1${NC}"; }
log_highlight() { echo -e "${CYAN}💥 $1${NC}"; }

echo ""
echo "🧹 LIMPEZA COMPLETA DO AMBIENTE DOCKER"
echo "======================================"
echo "⚠️  ATENÇÃO: Isso vai APAGAR TUDO relacionado ao projeto!"
echo "📦 Containers, volumes, redes, imagens e dados"
echo "🔐 Você terá que refazer toda a configuração depois"
echo ""

# Confirmação de segurança
read -p "🚨 Tem certeza que quer limpar TUDO? (digite 'LIMPAR' para confirmar): " confirmacao

if [ "$confirmacao" != "LIMPAR" ]; then
    log_info "Operação cancelada pelo usuário"
    exit 0
fi

echo ""
log_highlight "🧹 INICIANDO LIMPEZA COMPLETA..."

# ============================================================================
# ETAPA 1: PARAR TODOS OS PROCESSOS PYTHON
# ============================================================================
log_step "1: PARANDO PROCESSOS PYTHON"

log_info "Matando processos Python do projeto..."
pkill -f "streamlit run" 2>/dev/null || true
pkill -f "dashboard.py" 2>/dev/null || true
pkill -f "ecommerce_api.py" 2>/dev/null || true
pkill -f "crm_api.py" 2>/dev/null || true
pkill -f "insere_dados.py" 2>/dev/null || true
pkill -f "verificar_ambiente.py" 2>/dev/null || true
pkill -f "criar_tabelas.py" 2>/dev/null || true
pkill -f "executar_dbt.py" 2>/dev/null || true

log_success "Processos Python finalizados"

# ============================================================================
# ETAPA 2: PARAR E REMOVER CONTAINERS DO PROJETO
# ============================================================================
log_step "2: REMOVENDO CONTAINERS"

cd config 2>/dev/null || true

log_info "Parando todos os containers do projeto..."
docker compose down --remove-orphans 2>/dev/null || true

log_info "Removendo containers órfãos e parados..."
docker container prune -f 2>/dev/null || true

# Listar containers que podem estar relacionados
log_info "Verificando containers relacionados ao projeto..."
related_containers=$(docker ps -a --filter "name=postgres_source" --filter "name=postgres_target" --filter "name=airbyte" --filter "name=dbt_runner" --filter "name=minio" --filter "name=api_" -q 2>/dev/null || true)

if [ ! -z "$related_containers" ]; then
    log_warning "Removendo containers relacionados ao projeto..."
    docker rm -f $related_containers 2>/dev/null || true
fi

cd .. 2>/dev/null || true

log_success "Containers removidos"

# ============================================================================
# ETAPA 3: REMOVER VOLUMES (DADOS PERSISTENTES)
# ============================================================================
log_step "3: REMOVENDO VOLUMES E DADOS"

log_warning "🗑️ Removendo TODOS os volumes (dados serão perdidos permanentemente)..."

# Volumes específicos do projeto
volumes_projeto=(
    "config_postgres_source_data"
    "config_postgres_target_data"
    "config_airbyte_db_data"
    "config_airbyte_config"
    "config_airbyte_jobs"
    "config_airbyte_logs"
    "config_airbyte_secrets"
    "config_airbyte_server_logs"
    "config_airbyte_worker_logs"
    "config_minio_data"
    "config_dbt_profiles"
)

for volume in "${volumes_projeto[@]}"; do
    if docker volume ls -q | grep -q "^${volume}$"; then
        log_info "Removendo volume: $volume"
        docker volume rm "$volume" 2>/dev/null || true
    fi
done

# Remover volumes órfãos
log_info "Removendo volumes órfãos..."
docker volume prune -f 2>/dev/null || true

log_success "Volumes removidos"

# ============================================================================
# ETAPA 4: REMOVER REDES
# ============================================================================
log_step "4: REMOVENDO REDES"

log_info "Removendo redes do projeto..."
networks=$(docker network ls --filter "name=config_" -q 2>/dev/null || true)
if [ ! -z "$networks" ]; then
    docker network rm $networks 2>/dev/null || true
fi

log_info "Removendo redes órfãs..."
docker network prune -f 2>/dev/null || true

log_success "Redes removidas"

# ============================================================================
# ETAPA 5: REMOVER IMAGENS DO PROJETO
# ============================================================================
log_step "5: REMOVENDO IMAGENS"

log_info "Removendo imagens não utilizadas..."
docker image prune -f 2>/dev/null || true

# Opcionalmente remover imagens específicas do projeto
read -p "🗑️ Remover também as imagens baixadas? (postgres, airbyte, etc.) [s/N]: " remover_imagens

if [[ $remover_imagens =~ ^[Ss]$ ]]; then
    log_warning "Removendo imagens relacionadas ao projeto..."
    
    # Imagens principais do projeto
    images_projeto=(
        "postgres:13"
        "airbyte/db:*"
        "airbyte/server:*"
        "airbyte/webapp:*"
        "airbyte/worker:*"
        "airbyte/temporal:*"
        "minio/minio:*"
        "minio/mc:*"
    )
    
    for image_pattern in "${images_projeto[@]}"; do
        images=$(docker images --filter=reference="$image_pattern" -q 2>/dev/null || true)
        if [ ! -z "$images" ]; then
            log_info "Removendo imagens: $image_pattern"
            docker rmi $images 2>/dev/null || true
        fi
    done
    
    log_success "Imagens do projeto removidas"
else
    log_info "Imagens mantidas (para inicialização mais rápida)"
fi

# ============================================================================
# ETAPA 6: LIMPAR ARQUIVOS LOCAIS TEMPORÁRIOS
# ============================================================================
log_step "6: LIMPANDO ARQUIVOS TEMPORÁRIOS"

log_info "Removendo logs e arquivos temporários..."

# Logs do projeto
rm -f dashboard.log 2>/dev/null || true
rm -f insersor.log 2>/dev/null || true
rm -f environment_check_error.log 2>/dev/null || true

# Cache do DBT
rm -rf dbt_project/target/ 2>/dev/null || true
rm -rf dbt_project/logs/ 2>/dev/null || true
rm -rf dbt_project/.dbt/ 2>/dev/null || true

# Cache Python
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Logs do Docker Compose
rm -f config/*.log 2>/dev/null || true

log_success "Arquivos temporários removidos"

# ============================================================================
# ETAPA 7: LIMPEZA FINAL DO SISTEMA DOCKER
# ============================================================================
log_step "7: LIMPEZA FINAL"

log_info "Executando limpeza geral do Docker..."
docker system prune -f 2>/dev/null || true

# Verificação final
log_info "Verificando estado final..."
echo ""
echo "📊 ESTADO FINAL:"
echo "Containers ativos: $(docker ps -q | wc -l)"
echo "Volumes: $(docker volume ls -q | wc -l)"
echo "Redes customizadas: $(docker network ls --filter type=custom -q | wc -l)"
echo "Imagens: $(docker images -q | wc -l)"

# ============================================================================
# RESULTADO FINAL
# ============================================================================
echo ""
log_highlight "🎉 LIMPEZA COMPLETA FINALIZADA!"
echo ""
log_success "✅ TUDO FOI REMOVIDO:"
echo "   🗑️ Containers do projeto removidos"
echo "   🗑️ Volumes e dados persistentes apagados"
echo "   🗑️ Redes customizadas removidas"
echo "   🗑️ Arquivos temporários e logs limpos"
if [[ $remover_imagens =~ ^[Ss]$ ]]; then
echo "   🗑️ Imagens do projeto removidas"
fi

echo ""
log_highlight "🚀 PRÓXIMOS PASSOS:"
echo "1. Para recriar o ambiente: ./start_pipeline.sh"
echo "2. Todos os dados e configurações precisarão ser refeitos"
echo "3. Airbyte, MinIO e outras configurações voltarão ao zero"

echo ""
log_warning "⚠️ LEMBRE-SE: Isso foi uma limpeza COMPLETA!"
log_info "Use este script apenas quando quiser realmente recomeçar do zero."

echo "" 