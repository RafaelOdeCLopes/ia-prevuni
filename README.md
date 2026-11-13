# PrevUni: API de Previsão de Evasão

Motor preditivo do sistema **PrevUni**. A API recebe indicadores acadêmicos de estudantes e retorna, para cada um, a **probabilidade de evasão** (%) e o respectivo **nível de risco**: `baixo`, `moderado` ou `alto` (ou `sem_historico`, para alunos sem nenhuma matrícula concluída).

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
| `total_ch_cumprida` | float | Sim | Carga horária total cumprida nas disciplinas concluídas, em horas |
| `total_reprovacoes_pendencias` | int | Sim | Quantidade de reprovações e pendências |
| `percentual_conclusao_curso` | float (0–1) | Sim | Semestres concluídos ÷ períodos do curso |

> **Cálculo dos atributos:** a API recebe os indicadores já calculados. Ao calculá-los, o cliente deve considerar apenas as matrículas **já finalizadas** (aprovado, reprovado ou pendente) e **ignorar as matrículas em andamento** (`situacao = matriculado`), da mesma forma que no treinamento. Devem ser enviados apenas alunos ativos (não formados).
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
    "probabilidade_evasao_percent": 25.89,
    "nivel_risco": "baixo"
  }
]
```

## Níveis de risco

| Nível | Probabilidade de evasão | Evasão observada na validação* |
|---|---|---|
| `baixo` | `< 40%` | ~19% |
| `moderado` | `40% – 60%` | ~49% |
| `alto` | `> 60%` | ~73% |
| `sem_historico` | não calculada (`probabilidade_evasao_percent` retorna `null`) | não se aplica |

\* Proporção de alunos que de fato evadiram em cada faixa, estimada por validação cruzada nos dados sintéticos de treino.

> **`baixo` não significa ausência de risco:** cerca de 1 em cada 5 alunos dessa faixa evade.

O nível `sem_historico` é retornado quando **todos** os indicadores do aluno são zero (por exemplo, um aluno recém-ingresso, sem nenhuma matrícula concluída). Nesse caso a API não executa o modelo. **Esse nível não indica baixo risco, apenas que não há dados para avaliar:** nos dados de treino, 36% dos alunos sem histórico evadiram ainda no primeiro semestre.

## Modelo

- **Algoritmo:** Regressão Logística com padronização das variáveis (`StandardScaler` + `LogisticRegression`, `C=0.05`), em um pipeline do Scikit-Learn.
- **Atributos:** os cinco indicadores descritos acima.
- **Limiar de avaliação:** 0,30, usado no treinamento para calcular as métricas abaixo. A API **não** aplica esse limiar: ela retorna a probabilidade e a classifica pelos cortes de risco da seção anterior.
- **Persistência:** modelo exportado com Joblib (`modelo_evasao.joblib`) e carregado na inicialização da API. Depois da avaliação, o modelo final é treinado com todos os alunos disponíveis.

### Dados de treinamento

O modelo foi treinado com dados **sintéticos** de 1.500 alunos, gerados para validar o pipeline.

- Alunos formados (84) foram excluídos, pois não estão em risco de evasão.
- Alunos sem nenhuma matrícula concluída (297) foram excluídos do treino. A API os trata separadamente (`sem_historico`).
- Restaram **1.119 alunos**, com 30% de evasão.
- Para evitar vazamento de informação, os atributos de cada aluno são calculados apenas com o histórico **anterior ao semestre do desfecho**: para quem evadiu, até o semestre anterior à saída; para os demais, até o semestre anterior ao corrente. Sem isso, o desempenho no semestre da evasão (97,8% de reprovação) revelaria a resposta ao modelo e inflaria artificialmente as métricas.

### Desempenho

Avaliado em um conjunto de teste de 224 alunos (20% da base), com 30% de evasão (67 alunos).

| Métrica | Valor |
|---|---|
| AUC-ROC | ~0,78 |
| Acurácia | ~74% |
| Recall (evasão) | ~0,70 |
| Precisão (evasão) | ~0,55 |
| F1-score (evasão) | ~0,61 |

Com o limiar de 0,30, o modelo detecta cerca de 70% dos alunos que evadem, e pouco mais da metade dos alertas se confirma. Para um sistema de alerta precoce, essa troca costuma ser mais útil do que um limiar que maximize apenas a acurácia.

Como o conjunto de teste é pequeno, as métricas são aproximadas: o AUC varia entre cerca de 0,71 e 0,85 (intervalo de confiança de 95%). As probabilidades estão calibradas: a média prevista (~30%) coincide com a taxa real de evasão.

> **Atenção:** o modelo foi treinado com **dados sintéticos**. As métricas acima **não representam** o desempenho esperado com dados reais.

## Tecnologias

- **Python** e **FastAPI** (API)
- **Uvicorn** (servidor)
- **Scikit-Learn 1.6.1** (modelo e pipeline) e **Joblib 1.6.0** (persistência)
- **Pandas 2.2.3** (processamento de dados)
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
- Os cortes de risco (40% e 60%) são independentes do limiar de avaliação (0,30) usado no treinamento.
- O arquivo `modelo_evasao.joblib` foi gerado com **scikit-learn 1.6.1**. Use exatamente essa versão (já fixada no `requirements.txt`), pois modelos serializados não têm compatibilidade garantida entre versões diferentes. Ao retreinar o modelo, atualize a versão no `requirements.txt`.

## Limitações e próximos passos

- Treinar e validar com dados institucionais reais.
- O desempenho é limitado pelos atributos disponíveis: nos dados sintéticos, a evasão também depende de fatores que o modelo não enxerga, como vínculo de trabalho e situação financeira. Incluir variáveis como essas, ou frequência, é o caminho mais promissor.
- Em testes, atributos adicionais de tendência (reprovações por semestre, variação da média) e modelos mais complexos não trouxeram ganho relevante com os dados atuais.
- Revisar os cortes de risco com a coordenação acadêmica, conforme o número de alertas que a instituição consegue acompanhar.
- Validar os intervalos dos campos de entrada (por exemplo, com `Field(ge=0, le=1)` do Pydantic).