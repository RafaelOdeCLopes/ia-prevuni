import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import joblib
import pandas as pd

app = FastAPI(title="API de Previsão de Evasão Escolar")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

caminho_modelo = os.path.join(os.path.dirname(__file__), 'modelo_evasao.joblib')
modelo = joblib.load(caminho_modelo)

class DadosAluno(BaseModel):
    id: Optional[str] = None
    media_notas: float
    taxa_aprovacao: float
    total_ch_cumprida: float
    total_reprovacoes_pendencias: int
    percentual_conclusao_curso: float

FEATURES = [
    'media_notas', 
    'taxa_aprovacao', 
    'total_ch_cumprida', 
    'total_reprovacoes_pendencias', 
    'percentual_conclusao_curso'
]

@app.get("/")
def home():
    return {"status": "API rodando com sucesso"}

@app.post("/prever-evasao")
def prever_evasao(alunos: List[DadosAluno]):
    dados_lista = [
        aluno.model_dump() if hasattr(aluno, 'model_dump') else aluno.dict() 
        for aluno in alunos
    ]
    
    df_input = pd.DataFrame(dados_lista)
    X_input = df_input[FEATURES]
    
    probabilidades = modelo.predict_proba(X_input)[:, 1] * 100

    resultados = []
    for i, aluno in enumerate(alunos):
        prob = float(probabilidades[i])
        
        if prob < 35.0:
            nivel = "baixo"
        elif 35.0 <= prob <= 65.0:
            nivel = "moderado"
        else:
            nivel = "alto"

        resultados.append({
            "id": aluno.id if aluno.id else str(i),
            "probabilidade_evasao_percent": round(prob, 2),
            "nivel_risco": nivel
        })
        
    return resultados