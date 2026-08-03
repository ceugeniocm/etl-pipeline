# Desenvolvimento Baseado em Especificações (Spec-Driven Development)
- A metodologia é o desenvolvimento passo a passo, seguindo a abordagem de Desenvolvimento Baseado em Especificações (SDD - Spec-Driven Development).

## Escopo desta etapa:
- Baseado em `docs/vision.md` e `.junie/AGENTS.md`;
  
### 1. Criar ou Atualizar `docs/requirements.md`
- Criar ou atualizar os requisitos de alto nível em `docs/requirements.md` com base no escopo descrito acima.
- O arquivo contém requisitos funcionais e requisitos não funcionais no formato Markdown.
- Cada requisito possui um id único, uma descrição (como uma user story), uma prioridade e um status.

- Título: **Documento de Requisitos**
- Introdução: Resumir o Escopo desta etapa: propósito e funcionalidades principais.
- Seção de requisitos:
    - Use um id único (FR-XXX) para requisitos funcionais e (NFR-XXX) para requisitos não funcionais.
    - Cada requisito deve incluir:
        - **User Story** no formato:
          > Como um usuário, eu quero [objetivo] para que [benefício/razão]

        - **Acceptance Criteria** no formato:
          > QUANDO [condição] ENTÃO o sistema DEVE [comportamento esperado]
    - Status: **Not Started**, **In Progress**, **Completed**, **Deferred**

### 2. Criar ou Atualizar `docs/plan.md`
- Analisar `docs/requirements.md`.
- Desenvolver um **plano de implementação detalhado**:
    - Vincular cada item do plano explicitamente aos requisitos correspondentes.
    - Atribuir prioridades (ex: High, Medium, Low).
    - Agrupar itens do plano relacionados de forma lógica.
- Garantir a cobertura abrangente de todos os requisitos.

### 3. Criar ou atualizar `docs/tasks.md`
- Com base no plano de implementação em `docs/plan.md`, produzir uma **lista de tarefas técnicas enumerada detalhada**:
    - Cada tarefa deve ter um placeholder `[ ]` para marcar a conclusão.
    - Vincular cada tarefa a:
        - o item do plano de desenvolvimento em `docs/plan.md`
        - o(s) requisito(s) relacionado(s) em `docs/requirements.md`
- Agrupar tarefas em **fases de desenvolvimento**.
- Organizar as fases logicamente (ex: Setup → Core Features → Advanced Features → Testing & QA).

