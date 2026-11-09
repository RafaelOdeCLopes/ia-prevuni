# PrevUni: API de Previsão de Evasão

Motor preditivo do sistema **PrevUni**. A API recebe indicadores acadêmicos de estudantes e retorna, para cada um, a **probabilidade de evasão** (%) e o respectivo **nível de risco**: `baixo`, `moderado` ou `alto`.

## Como funciona

1. O cliente envia uma lista de alunos com seus indicadores acadêmicos.
2. O modelo estima a probabilidade de evasão de cada aluno.
3. A API devolve, para cada aluno, a probabilidade em % e a classificação de risco.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Verificação de disponibilidade. Retorna `{"status": "API rodando com sucesso"}` |
| `POST` | `/prever-evasao` | Recebe uma lista de alunos e retorna a previsão de cada um |

A documentação interativa (Swagger) fica disponível em `/docs`.

## Atributos de entrada

Cada aluno enviado ao endpoint `/prever-evasao` deve conter os campos abaixo.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | string | Não | Identificador do aluno. Se omitido, a API usa o índice do aluno na lista |
| `media_notas` | float | Sim | Média das notas das disciplinas concluídas |
| `taxa_aprovacao` | float (0–1) | Sim | Proporção de disciplinas aprovadas entre as concluídas |
| `total_ch_cumprida` | float | Sim | Carga horária total cumprida, em horas |
| `total_reprovacoes_pendencias` | int | Sim | Quantidade de reprovações e pendências |
| `percentual_conclusao_curso` | float (0–1) | Sim | Semestres concluídos ÷ períodos do curso |

> **Cálculo dos atributos:** a API recebe os indicadores já calculados. Ao calculá-los, o cliente deve **ignorar as matrículas em andamento** (`situacao = matriculado`), da mesma forma que no treinamento. O percentual de conclusão deve ser calculado como o número de semestres concluídos dividido pela quantidade de períodos do curso.
>
> A API não valida os intervalos esperados (por exemplo, `taxa_aprovacao` entre 0 e 1).

## Exemplo de uso

```http
POST /prever-evasao
Content-Type: application/json
```

Requisição:

```json
[
  {
    "id": "aluno-001",
    "media_notas": 7.5,
    "taxa_aprovacao": 0.85,
    "total_ch_cumprida": 400,
    "total_reprovacoes_pendencias": 1,
    "percentual_conclusao_curso": 0.5
  }
]
```

Resposta:

```json
[
  {
    "id": "aluno-001",
    "probabilidade_evasao_percent": 29.87,
    "nivel_risco": "baixo"
  }
]
```

## Níveis de risco

| Nível | Probabilidade de evasão |
|---|---|
| `baixo` | `< 35%` |
| `moderado` | `35% – 65%` |
| `alto` | `> 65%` |
| `sem_historico` | não calculada (`probabilidade_evasao_percent` retorna `null`) |

O nível `sem_historico` é retornado quando **todos** os indicadores do aluno são zero (por exemplo, um aluno recém-ingresso, sem nenhuma matrícula concluída). Nesse caso a API não executa o modelo.

## Modelo

- **Algoritmo:** Regressão Logística com padronização das variáveis (`StandardScaler` + `LogisticRegression`, `C=0.05`), em um pipeline do Scikit-Learn.
- **Atributos:** os cinco indicadores descritos acima.
- **Limiar de avaliação:** 0,25, usado no treinamento para calcular as métricas abaixo. A API **não** aplica esse limiar: ela retorna a probabilidade e a classifica pelos cortes de risco da seção anterior.
- **Persistência:** modelo exportado com Joblib (`modelo_evasao.joblib`) e carregado na inicialização da API.

### Desempenho

Avaliado em um conjunto de teste de 500 alunos (20% da base), com 19,4% de evasão (97 alunos).

| Métrica | Valor |
|---|---|
| AUC-ROC | 0,86 |
| Acurácia | 82,0% |
| Recall (evasão) | 0,68 |
| Precisão (evasão) | 0,53 |
| F1-score (evasão) | 0,59 |

Com o limiar de 0,25, o modelo detecta cerca de 68% dos alunos que evadem, e pouco mais da metade dos alertas se confirma. Para um sistema de alerta precoce, essa troca costuma ser mais útil do que um limiar que maximize apenas a acurácia.

> **Atenção:** o modelo foi treinado com **dados sintéticos**, gerados para validar o pipeline. As métricas acima **não representam** o desempenho esperado com dados reais.

## Tecnologias

- **Python** e **FastAPI** (API)
- **Uvicorn** (servidor)
- **Scikit-Learn** (modelo e pipeline) e **Joblib** (persistência)
- **Pandas** (processamento de dados)
- **Pydantic** (validação de entrada)
- **Google Colab** (treinamento do modelo)
- **Vercel** (deploy)

## Executando localmente

```bash
pip install -r requirements.txt
uvicorn index:app --reload
```

A API ficará disponível em `http://127.0.0.1:8000`, e a documentação interativa em `http://127.0.0.1:8000/docs`.

## Observações

- O CORS está liberado para qualquer origem (`allow_origins=["*"]`). Restrinja as origens antes de usar em produção.
- Os cortes de risco (35% e 65%) são independentes do limiar de avaliação (0,25) usado no treinamento.

## Limitações e próximos passos

- Treinar e validar com dados institucionais reais.
- Incluir variáveis como frequência, situação financeira e vínculo de trabalho.
- Calibrar as probabilidades e revisar os cortes de risco com a coordenação acadêmica.
- Validar os intervalos dos campos de entrada (por exemplo, com `Field(ge=0, le=1)` do Pydantic).
