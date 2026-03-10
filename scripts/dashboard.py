#!/usr/bin/env python3
"""
Dashboard em Tempo Real - Pipeline Kafka + dbt
Mostra dados chegando em tempo real via Kafka CDC
"""

import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

st.set_page_config(
    page_title="Kafka + dbt Pipeline — Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stMetric label { color: #8ecdf5 !important; font-size: 14px !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700; }
    .stMetric [data-testid="stMetricDelta"] { color: #00ff9d !important; }
</style>
""", unsafe_allow_html=True)

DB_SOURCE = dict(host='localhost', port=5430, database='db_source', user='admin', password='admin')
DB_TARGET = dict(host='localhost', port=5431, database='db_target', user='admin', password='admin')


@st.cache_data(ttl=3)
def query(sql, cfg=None):
    try:
        with psycopg2.connect(**(cfg or DB_TARGET)) as conn:
            return pd.read_sql_query(sql, conn)
    except Exception as e:
        return pd.DataFrame({"Erro": [str(e)]})


# ── Header ────────────────────────────────────────────────────────────────────
st.title("⚡ Kafka + dbt — Dashboard em Tempo Real")
st.caption(f"Atualizado: {datetime.now().strftime('%H:%M:%S')} | CDC: PostgreSQL → Debezium → Kafka → Consumer → dbt")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Controles")
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
    st.divider()
    st.subheader("📡 Conexões")
    for name, cfg in [("Source :5430", DB_SOURCE), ("Target :5431", DB_TARGET)]:
        try:
            with psycopg2.connect(**cfg, connect_timeout=2):
                st.success(f"✅ {name}")
        except Exception as e:
            st.error(f"❌ {name}: {str(e)[:40]}")

    st.divider()
    st.subheader("🔧 Kafka Consumer")
    kafka_meta = query("SELECT topic, event_count, last_event FROM public._pipeline_metadata ORDER BY event_count DESC")
    if 'Erro' not in kafka_meta.columns and not kafka_meta.empty:
        st.dataframe(kafka_meta, hide_index=True, use_container_width=True)
    else:
        st.info("Aguardando primeiro evento CDC...")

# ── KPIs ───────────────────────────────────────────────────────────────────────
st.header("📈 Métricas Principais")
col1, col2, col3, col4 = st.columns(4)

src_c = query("SELECT COUNT(*) n FROM public.clientes", DB_SOURCE)
src_p = query("SELECT COUNT(*) n FROM public.pedidos", DB_SOURCE)
tgt_c = query("SELECT COUNT(*) n FROM public.clientes")
tgt_p = query("SELECT COUNT(*) n FROM public.pedidos")
rec   = query("SELECT COALESCE(SUM(valor_bruto),0) t FROM public.pedidos")
tick  = query("SELECT COALESCE(AVG(valor_liquido),0) t FROM public.pedidos")

n_sc = int(src_c['n'].iloc[0]) if 'n' in src_c else 0
n_sp = int(src_p['n'].iloc[0]) if 'n' in src_p else 0
n_tc = int(tgt_c['n'].iloc[0]) if 'n' in tgt_c else 0
n_tp = int(tgt_p['n'].iloc[0]) if 'n' in tgt_p else 0
receita = float(rec['t'].iloc[0]) if 't' in rec else 0
ticket  = float(tick['t'].iloc[0]) if 't' in tick else 0

with col1:
    st.metric("👥 Clientes", n_sc, delta=f"→ {n_tc} Target")
with col2:
    st.metric("🛒 Pedidos", n_sp, delta=f"→ {n_tp} Target")
with col3:
    st.metric("💰 Receita Total", f"R$ {receita:,.2f}")
with col4:
    st.metric("🎟️ Ticket Médio", f"R$ {ticket:,.2f}")

st.divider()

# ── Lag Kafka ──────────────────────────────────────────────────────────────────
st.header("⚡ Lag Kafka (Source vs Target)")
lag_c = n_sc - n_tc
lag_p = n_sp - n_tp

col_chart, col_lag = st.columns([2, 1])
with col_chart:
    lag_df = pd.DataFrame({
        "Tabela": ["clientes", "pedidos"],
        "Source": [n_sc, n_sp],
        "Target (Kafka)": [n_tc, n_tp],
    })
    fig = px.bar(
        lag_df.melt(id_vars="Tabela", var_name="Camada", value_name="Registros"),
        x="Tabela", y="Registros", color="Camada", barmode="group",
        color_discrete_map={"Source": "#00d4ff", "Target (Kafka)": "#00ff9d"},
        title="Registros por Camada"
    )
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(14,28,54,0.8)',
                      font_color='white', title_font_color='white')
    st.plotly_chart(fig, use_container_width=True)

with col_lag:
    st.metric("Lag clientes", f"{lag_c:+d} rows", delta_color="inverse")
    st.metric("Lag pedidos",  f"{lag_p:+d} rows", delta_color="inverse")
    if lag_c == 0 and lag_p == 0:
        st.success("⚡ Kafka em dia!")
    elif lag_c + lag_p < 10:
        st.info(f"⏳ {lag_c + lag_p} rows replicando...")
    else:
        st.warning(f"🔄 {lag_c + lag_p} rows na fila Kafka")

st.divider()

# ── Tabelas replicadas ──────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("👥 Últimos Clientes (Target)")
    df_c = query("""
        SELECT nome, email, tipo_cliente, status,
               TO_CHAR(data_cadastro, 'DD/MM HH24:MI') as cadastro,
               TO_CHAR(updated_at, 'HH24:MI:SS') as updated
        FROM public.clientes ORDER BY updated_at DESC NULLS LAST LIMIT 10
    """)
    if 'Erro' in df_c.columns or df_c.empty:
        st.info("Aguardando dados do Kafka consumer...")
    else:
        st.dataframe(df_c, use_container_width=True, hide_index=True)

with col_r:
    st.subheader("🛒 Últimos Pedidos (Target)")
    df_p = query("""
        SELECT numero_pedido, status, metodo_pagamento,
               CAST(valor_bruto AS FLOAT)::NUMERIC(10,2) as valor_bruto,
               CAST(valor_liquido AS FLOAT)::NUMERIC(10,2) as valor_liq,
               canal_venda,
               TO_CHAR(updated_at, 'HH24:MI:SS') as updated
        FROM public.pedidos ORDER BY updated_at DESC NULLS LAST LIMIT 10
    """)
    if 'Erro' in df_p.columns or df_p.empty:
        st.info("Aguardando dados do Kafka consumer...")
    else:
        st.dataframe(df_p, use_container_width=True, hide_index=True)

st.divider()

# ── Gold Layer dbt ──────────────────────────────────────────────────────────────
st.header("✨ Gold Layer (dbt)")
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("🏆 Top Clientes por Receita")
    gold = query("""
        SELECT nome, total_pedidos, receita_total::FLOAT as receita
        FROM public_gold.gold_visao_geral_clientes ORDER BY receita DESC LIMIT 10
    """)
    if 'Erro' in gold.columns or gold.empty:
        st.info("Execute `dbt run` para popular a Gold layer.")
    else:
        fig2 = px.bar(gold, x='receita', y='nome', orientation='h',
                      color='receita', color_continuous_scale='Blues',
                      title="Receita por Cliente (Gold)")
        fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(14,28,54,0.8)',
                           font_color='white', yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

with col_g2:
    st.subheader("📊 Receita por Status")
    df_s = query("""
        SELECT status, COUNT(*) n, SUM(valor_bruto::FLOAT) receita
        FROM public.pedidos GROUP BY status ORDER BY receita DESC
    """)
    if 'Erro' in df_s.columns or df_s.empty:
        st.info("Sem dados de pedidos ainda.")
    else:
        fig3 = px.pie(df_s, values='receita', names='status',
                      color_discrete_sequence=px.colors.sequential.Blues_r,
                      title="Distribuição por Status")
        fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
        st.plotly_chart(fig3, use_container_width=True)

if auto_refresh:
    time.sleep(5)
    st.rerun()