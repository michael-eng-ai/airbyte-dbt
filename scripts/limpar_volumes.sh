#!/bin/bash
# Script para limpeza completa de volumes Docker
# Força a reinicialização do banco com scripts de inicialização

echo "🧹 LIMPEZA TOTAL DOS VOLUMES DOCKER"
echo "=================================="
echo "  Isso irá DELETAR todos os dados persistentes!"
echo ""

read -p "🤔 Confirma a limpeza total? (s/N): " resposta
if [[ ! $resposta =~ ^[Ss]$ ]]; then
    echo " Operação cancelada"
    exit 0
fi

echo ""
echo "🛑 Parando todos os containers..."
cd config
docker compose --profile "*" down --remove-orphans

echo ""
echo "🗑️  Removendo volumes relacionados ao projeto..."
docker volume ls -q | grep -E "(config|postgres|airflow|airbyte)" | xargs -r docker volume rm 2>/dev/null || true

echo ""
echo "🔍 Verificando volumes restantes..."
docker volume ls | grep -E "(config|postgres|airflow|airbyte)"

echo ""
echo "🧹 Limpando containers orfãos..."
docker container prune -f

echo ""
echo " LIMPEZA CONCLUÍDA!"
echo "    Containers parados"
echo "    Volumes deletados" 
echo "    Containers orfãos removidos"
echo ""
echo " Agora execute: ./start_demo.sh"
echo "   Os scripts de inicialização irão executar automaticamente!" 