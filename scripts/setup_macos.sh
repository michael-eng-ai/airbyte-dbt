#!/bin/bash
# Setup específico para macOS - Resolve problemas com psycopg2

echo "🍎 SETUP PARA macOS - Pipeline de Dados"
echo "======================================"

# Instalar PostgreSQL se não existir
if ! command -v psql &> /dev/null; then
    echo "📦 Instalando PostgreSQL via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew não encontrado. Instale primeiro:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    brew install postgresql
fi

# Instalar dependências Python
echo "🐍 Instalando dependências Python..."
python3 -m pip install --upgrade pip

# Instalar dependências uma por uma para melhor controle
echo "   📚 Instalando pandas..."
python3 -m pip install "pandas>=2.0.0"

echo "   📊 Instalando streamlit..."
python3 -m pip install "streamlit>=1.28.0"

echo "   📈 Instalando plotly..."
python3 -m pip install "plotly>=5.15.0"

echo "   📋 Instalando tabulate..."
python3 -m pip install "tabulate>=0.9.0"

echo "   🔌 Instalando psycopg2..."
# Usar variáveis de ambiente para ajudar na compilação
export LDFLAGS="-L$(brew --prefix postgresql)/lib"
export CPPFLAGS="-I$(brew --prefix postgresql)/include"
python3 -m pip install psycopg2-binary

echo "✅ Setup concluído!"
echo ""
echo "🚀 Para iniciar a demo:"
echo "   ./iniciar_demo_completa.sh" 