#!/usr/bin/env python3
"""
API CRM Simulada
Simula um sistema de CRM com leads, oportunidades e campanhas
Para demonstrar CDC e integração multi-fonte
"""

from fastapi import FastAPI
import uvicorn
import random
from datetime import datetime, timedelta
from faker import Faker
import time
import threading

app = FastAPI(title="CRM API", version="1.0.0")
fake = Faker('pt_BR')

# Base de dados em memória
leads_db = []
oportunidades_db = []
campanhas_db = []
atividades_db = []

# Contadores
lead_id_counter = 1
oportunidade_id_counter = 1
campanha_id_counter = 1
atividade_id_counter = 1

def gerar_campanhas_iniciais():
    """Gera campanhas de marketing"""
    global campanha_id_counter
    
    tipos_campanha = [
        "Email Marketing", "Google Ads", "Facebook Ads", 
        "LinkedIn Ads", "Webinar", "Trade Show", "Cold Call"
    ]
    
    for _ in range(10):
        campanha = {
            "id": campanha_id_counter,
            "nome": f"Campanha {fake.catch_phrase()}",
            "tipo": random.choice(tipos_campanha),
            "orcamento": round(random.uniform(1000, 50000), 2),
            "data_inicio": fake.date_between(start_date='-6m', end_date='now').isoformat(),
            "data_fim": fake.date_between(start_date='now', end_date='+3m').isoformat(),
            "status": random.choice(["Ativa", "Pausada", "Finalizada"]),
            "meta_leads": random.randint(50, 500),
            "leads_gerados": 0,
            "ctr": round(random.uniform(0.5, 5.0), 2),
            "cpc": round(random.uniform(0.50, 15.0), 2)
        }
        campanhas_db.append(campanha)
        campanha_id_counter += 1

def gerar_leads_iniciais():
    """Gera leads iniciais"""
    global lead_id_counter
    
    for _ in range(200):
        campanha = random.choice(campanhas_db) if campanhas_db else None
        
        lead = {
            "id": lead_id_counter,
            "nome": fake.name(),
            "email": fake.email(),
            "telefone": fake.phone_number(),
            "empresa": fake.company(),
            "cargo": fake.job(),
            "fonte": random.choice(["Website", "Social Media", "Referência", "Cold Call", "Email"]),
            "campanha_id": campanha["id"] if campanha else None,
            "score": random.randint(1, 100),
            "status": random.choice(["Novo", "Contactado", "Qualificado", "Convertido", "Perdido"]),
            "data_criacao": fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
            "ultimo_contato": fake.date_time_between(start_date='-30d', end_date='now').isoformat(),
            "interesse": random.choice(["Alto", "Médio", "Baixo"]),
            "orcamento_estimado": round(random.uniform(1000, 100000), 2),
            "observacoes": fake.text(max_nb_chars=300)
        }
        leads_db.append(lead)
        
        # Atualizar contador da campanha
        if campanha:
            campanha["leads_gerados"] += 1
            
        lead_id_counter += 1

def simular_atividades():
    """Simula atividades de CRM em tempo real"""
    global atividade_id_counter
    
    while True:
        if leads_db:
            # 60% chance de gerar uma atividade
            if random.random() < 0.6:
                lead = random.choice(leads_db)
                tipos_atividade = ["Ligação", "Email", "Reunião", "Proposta", "Follow-up"]
                
                atividade = {
                    "id": atividade_id_counter,
                    "lead_id": lead["id"],
                    "tipo": random.choice(tipos_atividade),
                    "descricao": fake.sentence(nb_words=10),
                    "data_atividade": datetime.now().isoformat(),
                    "duracao_minutos": random.randint(5, 120),
                    "resultado": random.choice(["Positivo", "Neutro", "Negativo"]),
                    "proximo_passo": fake.sentence(nb_words=8),
                    "responsavel": fake.name()
                }
                
                atividades_db.append(atividade)
                
                # Atualizar último contato do lead
                lead["ultimo_contato"] = atividade["data_atividade"]
                
                # 20% chance de alterar status do lead
                if random.random() < 0.2:
                    if lead["status"] == "Novo":
                        lead["status"] = "Contactado"
                    elif lead["status"] == "Contactado":
                        lead["status"] = random.choice(["Qualificado", "Perdido"])
                    elif lead["status"] == "Qualificado":
                        lead["status"] = random.choice(["Convertido", "Perdido"])
                
                atividade_id_counter += 1
                print(f"📞 Nova atividade: {atividade['tipo']} com lead {lead['nome']}")
        
        time.sleep(random.uniform(5, 15))

@app.on_event("startup")
async def startup_event():
    """Inicialização da API"""
    print("🚀 Iniciando API CRM...")
    gerar_campanhas_iniciais()
    gerar_leads_iniciais()
    
    # Iniciar simulador
    simulator_thread = threading.Thread(target=simular_atividades, daemon=True)
    simulator_thread.start()
    
    print("✅ API CRM iniciada com sucesso!")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    return {
        "service": "CRM API",
        "version": "1.0.0",
        "endpoints": [
            "/leads",
            "/oportunidades",
            "/campanhas",
            "/atividades",
            "/stats",
            "/health"
        ]
    }

@app.get("/leads")
async def listar_leads(limit: int = 100, status: str = None):
    """Lista leads"""
    leads = leads_db
    
    if status:
        leads = [l for l in leads if l['status'].lower() == status.lower()]
    
    leads = leads[-limit:]
    
    return {
        "total": len(leads),
        "dados": leads,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/campanhas")
async def listar_campanhas(limit: int = 50):
    """Lista campanhas"""
    return {
        "total": len(campanhas_db),
        "dados": campanhas_db[-limit:],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/atividades")
async def listar_atividades(limit: int = 100, lead_id: int = None):
    """Lista atividades"""
    atividades = atividades_db
    
    if lead_id:
        atividades = [a for a in atividades if a['lead_id'] == lead_id]
    
    atividades = atividades[-limit:]
    
    return {
        "total": len(atividades),
        "dados": atividades,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stats")
async def estatisticas():
    """Estatísticas do CRM"""
    # Leads por status
    leads_por_status = {}
    for lead in leads_db:
        status = lead['status']
        leads_por_status[status] = leads_por_status.get(status, 0) + 1
    
    # Taxa de conversão
    total_leads = len(leads_db)
    leads_convertidos = len([l for l in leads_db if l['status'] == 'Convertido'])
    taxa_conversao = (leads_convertidos / max(1, total_leads)) * 100
    
    # Score médio
    score_medio = sum(l['score'] for l in leads_db) / max(1, len(leads_db))
    
    # Atividades por tipo
    atividades_por_tipo = {}
    for atividade in atividades_db:
        tipo = atividade['tipo']
        atividades_por_tipo[tipo] = atividades_por_tipo.get(tipo, 0) + 1
    
    return {
        "resumo": {
            "total_leads": total_leads,
            "leads_convertidos": leads_convertidos,
            "taxa_conversao": round(taxa_conversao, 2),
            "score_medio": round(score_medio, 1),
            "total_campanhas": len(campanhas_db),
            "total_atividades": len(atividades_db)
        },
        "leads_por_status": leads_por_status,
        "atividades_por_tipo": atividades_por_tipo,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 Iniciando API CRM na porta 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 