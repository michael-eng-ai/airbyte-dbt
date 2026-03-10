#!/usr/bin/env python3
"""
Gerador de dados contínuos para demonstração em tempo real.
Insere clientes, produtos, pedidos e leads no db_source a cada N segundos.
"""

import psycopg2
import random
import time
import uuid
import logging
import sys
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("gerador")

DB = dict(host="localhost", port=5430, database="db_source", user="admin", password="admin")

NOMES = ["Ana Silva", "Carlos Oliveira", "Mariana Santos", "Pedro Costa",
         "Juliana Ferreira", "Rafael Lima", "Beatriz Souza", "Lucas Mendes",
         "Camila Rocha", "Fernando Alves", "Isabela Nunes", "Thiago Carvalho",
         "Amanda Ribeiro", "Gustavo Pinto", "Larissa Barbosa", "Diego Moraes"]

PRODUTOS_LISTA = [
    ("Notebook Pro 15", "Eletrônicos", 2999.90, 4599.00),
    ("Smartphone X12",  "Eletrônicos", 899.00,  1499.00),
    ("Camiseta Eco",    "Vestuário",   29.90,   89.90),
    ("Tênis Runner",    "Calçados",    149.90,  299.90),
    ("Fone Bluetooth",  "Acessórios",  99.00,   249.00),
    ("Mochila Urban",   "Acessórios",  79.90,   179.90),
    ("Smart Watch S3",  "Eletrônicos", 499.00,  899.00),
    ("Livro Python",    "Livros",      49.90,   89.90),
]

STATUS_PEDIDO   = ["pendente", "processando", "enviado", "entregue"]
METODOS_PAG     = ["cartao_credito", "pix", "boleto", "cartao_debito"]
CANAIS_VENDA    = ["web", "app", "loja_fisica", "marketplace"]
STATUS_CLIENTE  = ["ativo", "inativo", "premium"]
TIPOS_CLIENTE   = ["pessoa_fisica", "pessoa_juridica"]
FONTES_LEAD     = ["google_ads", "facebook", "indicacao", "email", "organico"]
STATUS_LEAD     = ["novo", "qualificado", "proposta", "negociacao", "convertido"]


def gerar_cpf():
    return f"{random.randint(100,999)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(10,99)}"


def inserir_dados(conn, n_iter: int) -> dict:
    cur = conn.cursor()
    stats = {"clientes": 0, "pedidos": 0, "produtos": 0, "leads": 0}

    # ── Clientes ──────────────────────────────────────────────────────────────
    n_clientes = random.randint(1, 3)
    for _ in range(n_clientes):
        nome = random.choice(NOMES)
        email = f"{nome.split()[0].lower()}{random.randint(1,9999)}@demo.com"
        cur.execute("""
            INSERT INTO public.clientes
              (nome, email, telefone, cpf, data_nascimento, status, tipo_cliente,
               limite_credito, data_cadastro, updated_at, created_by, version, endereco)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'generator', 1,
                    '{"cidade": "São Paulo", "estado": "SP"}')
            ON CONFLICT DO NOTHING
        """, (
            nome, email,
            f"11{random.randint(900000000, 999999999)}",
            gerar_cpf(),
            datetime.now() - timedelta(days=random.randint(6570, 20000)),
            random.choice(STATUS_CLIENTE),
            random.choice(TIPOS_CLIENTE),
            round(random.uniform(500, 15000), 2),
        ))
        stats["clientes"] += 1

    # ── Produtos ──────────────────────────────────────────────────────────────
    for nome_p, cat, custo, venda in random.sample(PRODUTOS_LISTA, k=random.randint(1, 3)):
        codigo = f"PROD-{uuid.uuid4().hex[:8].upper()}"
        cur.execute("""
            INSERT INTO public.produtos
              (codigo_produto, nome, categoria, preco_custo, preco_venda,
               estoque_atual, ativo, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, true, NOW())
            ON CONFLICT (codigo_produto) DO NOTHING
        """, (codigo, nome_p, cat, custo, venda, random.randint(5, 200)))
        stats["produtos"] += 1

    # ── Pedidos com Itens ──────────────────────────────────────────────────────
    cur.execute("SELECT id FROM public.clientes ORDER BY RANDOM() LIMIT 5")
    cliente_ids = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT id, preco_venda FROM public.produtos ORDER BY RANDOM() LIMIT 10")
    produto_rows = cur.fetchall()

    if cliente_ids and produto_rows:
        n_pedidos = random.randint(2, 6)
        for _ in range(n_pedidos):
            cid = random.choice(cliente_ids)
            # Primeiro calcula o valor a partir dos itens que vamos criar
            n_itens = random.randint(1, 4)
            itens_selecionados = random.choices(produto_rows, k=n_itens)
            
            valor_bruto = sum(
                round(float(p[1]) * random.randint(1, 5), 2) for p in itens_selecionados
            )
            desconto = round(valor_bruto * random.uniform(0, 0.12), 2)

            cur.execute("""
                INSERT INTO public.pedidos
                  (cliente_id, numero_pedido, data_pedido, status, valor_bruto,
                   desconto, metodo_pagamento, canal_venda,
                   data_entrega_prevista, updated_at, created_by, version)
                VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s,
                        NOW() + INTERVAL '7 days', NOW(), 'generator', 1)
                RETURNING id
            """, (
                cid,
                f"PED-{uuid.uuid4().hex[:10].upper()}",
                random.choice(STATUS_PEDIDO),
                valor_bruto, desconto,
                random.choice(METODOS_PAG),
                random.choice(CANAIS_VENDA),
            ))
            pedido_id = cur.fetchone()[0]
            stats["pedidos"] += 1

            # Itens do pedido
            for prod_id, preco_venda in itens_selecionados:
                qtd = random.randint(1, 5)
                preco = float(preco_venda)
                cur.execute("""
                    INSERT INTO public.itens_pedido
                      (pedido_id, produto_id, quantidade, preco_unitario,
                       desconto_item, observacoes, updated_at)
                    VALUES (%s, %s, %s, %s, %s, '', NOW())
                """, (
                    pedido_id, prod_id, qtd, round(preco, 2),
                    round(preco * qtd * random.uniform(0, 0.08), 2),
                ))

    # ── Leads ─────────────────────────────────────────────────────────────────
    if random.random() > 0.4:
        nome = random.choice(NOMES)
        email = f"lead.{nome.split()[0].lower()}{random.randint(1,9999)}@prospect.com"
        cur.execute("""
            INSERT INTO public.leads
              (nome, email, telefone, fonte, score, status, interesse,
               orcamento_estimado, data_contato, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT DO NOTHING
        """, (
            nome, email,
            f"11{random.randint(900000000, 999999999)}",
            random.choice(FONTES_LEAD),
            random.randint(10, 100),
            random.choice(STATUS_LEAD),
            random.choice(["alto", "medio", "baixo"]),
            round(random.uniform(1000, 50000), 2),
        ))
        stats["leads"] += 1

    conn.commit()
    cur.close()
    return stats


def main():
    once = "--once" in sys.argv
    interval = int(next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--interval"), "8"))

    logger.info(f"Iniciando gerador de dados (intervalo={interval}s, once={once})")
    n_iter = 0

    while True:
        n_iter += 1
        try:
            with psycopg2.connect(**DB) as conn:
                stats = inserir_dados(conn, n_iter)
                logger.info(f"[iter {n_iter}] Inseridos: {stats}")
        except Exception as e:
            logger.error(f"Erro na iteração {n_iter}: {e}")

        if once:
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
