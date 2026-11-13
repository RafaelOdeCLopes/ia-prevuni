import os
import json
import math
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="API de Previsão de Evasão Escolar")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

caminho_modelo = os.path.join(os.path.dirname(__file__), 'modelo_evasao.json')
with open(caminho_modelo, 'r', encoding='utf-8') as f:
    PARAMS = json.load(f)

FEATURES = PARAMS['features']


def calcular_probabilidade(valores: dict) -> float:
    z = PARAMS['intercept']
    for nome, media, escala, coef in zip(FEATURES, PARAMS['mean'], PARAMS['scale'], PARAMS['coef']):
        z += coef * (valores[nome] - media) / escala
    z = max(-50.0, min(50.0, z))
    return 1.0 / (1.0 + math.exp(-z))


class DadosAluno(BaseModel):
    id: Optional[str] = None
    media_notas: float
    taxa_aprovacao: float
    total_ch_cumprida: float
    total_reprovacoes_pendencias: int
    percentual_conclusao_curso: float


@app.get("/")
def home():
    return {"status": "API rodando com sucesso"}


@app.post("/prever-evasao")
def prever_evasao(alunos: List[DadosAluno]):
    resultados = []
    for i, aluno in enumerate(alunos):
        valores = aluno.model_dump() if hasattr(aluno, 'model_dump') else aluno.dict()
        aluno_id = aluno.id if aluno.id else str(i)

        if all(valores[f] == 0 for f in FEATURES):
            resultados.append({
                "id": aluno_id,
                "probabilidade_evasao_percent": None,
                "nivel_risco": "sem_historico"
            })
            continue

        prob = calcular_probabilidade(valores) * 100
        if prob < 40.0:
            nivel = "baixo"
        elif 40.0 <= prob <= 60.0:
            nivel = "moderado"
        else:
            nivel = "alto"

        resultados.append({
            "id": aluno_id,
            "probabilidade_evasao_percent": round(prob, 2),
            "nivel_risco": nivel
        })

    return resultados