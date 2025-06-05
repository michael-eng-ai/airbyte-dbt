#!/usr/bin/env python3
"""
Dashboard em Tempo Real - Pipeline de Dados
Mostra métricas e gráficos atualizados automaticamente
"""

import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Configuração da página
st.set_page_config(
    page_title="Pipeline de Dados - Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações de conexão
DB_CONFIG = {
    'host': 'localhost',
    'port': 5430,
    'database': 'db_source',
    'user': 'admin',
    'password': 'admin'
}

@st.cache_data(ttl=5)  # Cache por 5 segundos
def conectar_e_consultar(query):
    """Conecta ao banco e executa query com cache"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao conectar ao banco: {e}")
        return pd.DataFrame()

def main():
    # Header
    st.title("📊 Pipeline de Dados - Dashboard em Tempo Real")
    st.markdown("**🎯 Demonstração de CDC e Transformações DBT**")
    
    # Sidebar com controles
    st.sidebar.header("⚙️ Configurações")
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (5s)", value=True)
    
    if auto_refresh:
        # Auto-refresh usando rerun
        time.sleep(5)
        st.rerun()
    
    # ====== MÉTRICAS PRINCIPAIS ======
    st.header("📈 Métricas Principais")
    
    # Consulta para métricas
    query_metricas = """
    SELECT 
        (SELECT COUNT(*) FROM public.clientes) as total_clientes,
        (SELECT COUNT(*) FROM public.pedidos) as total_pedidos,
        (SELECT COALESCE(SUM(quantidade * preco_unitario), 0) FROM public.pedidos) as receita_total,
        (SELECT COALESCE(AVG(quantidade * preco_unitario), 0) FROM public.pedidos) as ticket_medio
    """
    
    df_metricas = conectar_e_consultar(query_metricas)
    
    if not df_metricas.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="👥 Total Clientes",
                value=int(df_metricas['total_clientes'].iloc[0]),
                delta=None
            )
        
        with col2:
            st.metric(
                label="🛒 Total Pedidos", 
                value=int(df_metricas['total_pedidos'].iloc[0]),
                delta=None
            )
        
        with col3:
            st.metric(
                label="💰 Receita Total",
                value=f"R$ {df_metricas['receita_total'].iloc[0]:,.2f}",
                delta=None
            )
        
        with col4:
            st.metric(
                label="🎯 Ticket Médio",
                value=f"R$ {df_metricas['ticket_medio'].iloc[0]:,.2f}",
                delta=None
            )

    # ====== GRÁFICOS ======
    st.header("📊 Análises Visuais")
    
    # Row 1: Vendas por Cliente e por Produto
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top 10 Clientes por Receita")
        query_top_clientes = """
        SELECT 
            c.nome,
            COUNT(p.id) as total_pedidos,
            SUM(p.quantidade * p.preco_unitario) as receita_total
        FROM public.clientes c
        LEFT JOIN public.pedidos p ON c.id = p.cliente_id
        GROUP BY c.id, c.nome
        HAVING SUM(p.quantidade * p.preco_unitario) IS NOT NULL
        ORDER BY receita_total DESC
        LIMIT 10
        """
        
        df_top_clientes = conectar_e_consultar(query_top_clientes)
        
        if not df_top_clientes.empty:
            fig_clientes = px.bar(
                df_top_clientes,
                x='receita_total',
                y='nome',
                orientation='h',
                title="Receita por Cliente",
                labels={'receita_total': 'Receita (R$)', 'nome': 'Cliente'}
            )
            fig_clientes.update_layout(height=400)
            st.plotly_chart(fig_clientes, use_container_width=True)
        else:
            st.info("Aguardando dados de clientes...")
    
    with col2:
        st.subheader("📦 Top 10 Produtos por Vendas")
        query_top_produtos = """
        SELECT 
            produto,
            COUNT(*) as total_vendas,
            SUM(quantidade) as quantidade_total,
            SUM(quantidade * preco_unitario) as receita_total
        FROM public.pedidos
        GROUP BY produto
        ORDER BY receita_total DESC
        LIMIT 10
        """
        
        df_top_produtos = conectar_e_consultar(query_top_produtos)
        
        if not df_top_produtos.empty:
            fig_produtos = px.pie(
                df_top_produtos,
                values='receita_total',
                names='produto',
                title="Receita por Produto"
            )
            fig_produtos.update_layout(height=400)
            st.plotly_chart(fig_produtos, use_container_width=True)
        else:
            st.info("Aguardando dados de produtos...")
    
    # Row 2: Evolução Temporal
    st.subheader("📈 Evolução de Vendas (Últimos 7 dias)")
    
    query_evolucao = """
    SELECT 
        DATE(data_pedido) as data,
        COUNT(*) as pedidos_do_dia,
        SUM(quantidade * preco_unitario) as receita_do_dia
    FROM public.pedidos
    WHERE data_pedido >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY DATE(data_pedido)
    ORDER BY data
    """
    
    df_evolucao = conectar_e_consultar(query_evolucao)
    
    if not df_evolucao.empty:
        # Duas métricas em gráfico de linha
        fig_evolucao = go.Figure()
        
        # Pedidos (eixo Y esquerdo)
        fig_evolucao.add_trace(
            go.Scatter(
                x=df_evolucao['data'],
                y=df_evolucao['pedidos_do_dia'],
                name='Pedidos',
                line=dict(color='blue'),
                yaxis='y'
            )
        )
        
        # Receita (eixo Y direito)
        fig_evolucao.add_trace(
            go.Scatter(
                x=df_evolucao['data'],
                y=df_evolucao['receita_do_dia'],
                name='Receita (R$)',
                line=dict(color='green'),
                yaxis='y2'
            )
        )
        
        # Layout com dois eixos Y
        fig_evolucao.update_layout(
            title="Evolução de Pedidos e Receita",
            xaxis=dict(title="Data"),
            yaxis=dict(title="Número de Pedidos", side="left"),
            yaxis2=dict(title="Receita (R$)", side="right", overlaying="y"),
            height=400
        )
        
        st.plotly_chart(fig_evolucao, use_container_width=True)
    else:
        st.info("Aguardando dados de evolução temporal...")
    
    # ====== DADOS RECENTES ======
    st.header("🔥 Atividade Recente")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👥 Últimos Clientes")
        query_ultimos_clientes = """
        SELECT nome, email, data_cadastro
        FROM public.clientes
        ORDER BY id DESC
        LIMIT 5
        """
        
        df_ultimos_clientes = conectar_e_consultar(query_ultimos_clientes)
        if not df_ultimos_clientes.empty:
            st.dataframe(df_ultimos_clientes, use_container_width=True)
        else:
            st.info("Nenhum cliente encontrado")
    
    with col2:
        st.subheader("🛒 Últimos Pedidos")
        query_ultimos_pedidos = """
        SELECT 
            p.id,
            c.nome,
            p.produto,
            p.quantidade,
            (p.quantidade * p.preco_unitario) as valor_total,
            p.data_pedido
        FROM public.pedidos p
        JOIN public.clientes c ON p.cliente_id = c.id
        ORDER BY p.id DESC
        LIMIT 5
        """
        
        df_ultimos_pedidos = conectar_e_consultar(query_ultimos_pedidos)
        if not df_ultimos_pedidos.empty:
            # Formatar valor
            df_ultimos_pedidos['valor_total'] = df_ultimos_pedidos['valor_total'].apply(lambda x: f"R$ {x:.2f}")
            st.dataframe(df_ultimos_pedidos, use_container_width=True)
        else:
            st.info("Nenhum pedido encontrado")
    
    # ====== STATUS DO PIPELINE ======
    st.header("⚙️ Status do Pipeline DBT")
    
    # Verificar se as tabelas DBT existem
    query_pipeline_status = """
    SELECT 
        'bronze_clientes' as tabela,
        COUNT(*) as registros
    FROM public_bronze.bronze_clientes
    UNION ALL
    SELECT 
        'bronze_pedidos',
        COUNT(*)
    FROM public_bronze.bronze_pedidos
    UNION ALL
    SELECT 
        'silver_clientes',
        COUNT(*)
    FROM public_silver.dim_clientes
    UNION ALL
    SELECT 
        'silver_pedidos',
        COUNT(*)
    FROM public_silver.fct_pedidos
    """
    
    df_pipeline = conectar_e_consultar(query_pipeline_status)
    
    if not df_pipeline.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        for i, (col, row) in enumerate(zip([col1, col2, col3, col4], df_pipeline.itertuples())):
            with col:
                camada = "🟤 Bronze" if "bronze" in row.tabela else "🥈 Silver"
                st.metric(
                    label=f"{camada}",
                    value=f"{row.registros} registros",
                    delta=None
                )
    
    # Footer
    st.markdown("---")
    st.markdown(f"🕐 Última atualização: {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("💡 **Dica**: Os dados são atualizados automaticamente a cada 5 segundos")

if __name__ == "__main__":
    main() 