# Publicar o CRM

O CRM de produção roda numa imagem Docker própria, construída a partir do branch `develop` deste repositório.
O roteiro `deploy.ps1` faz tudo na ordem certa e **para se qualquer etapa falhar**:

1. roda os testes de fumaça no ambiente local (`crm/tests/run_smoke.py`);
2. envia o código ao GitHub;
3. faz backup do site em produção;
4. constrói a nova imagem no servidor;
5. recria os containers, aplica a migração e limpa o cache;
6. confere que o login responde.

## Uso

```powershell
$env:CRM_DEPLOY_HOST = "endereco-do-servidor"   # não fica no repositório
.\deploy\deploy.ps1
```

Requisitos: Docker Desktop com os containers locais de pé, chave SSH do servidor e tudo commitado.

## Testes

```powershell
docker exec -w /home/frappe/frappe-bench crm-frappe-1 bench --site crm.localhost execute crm.tests.run_smoke.run_all
```

Os testes ficam em `crm/tests/smoke/` e cobrem Instagram, financeiro, agenda, documentos do cliente, ficha, sugestões,
interligações e mapas. **Rodam só no ambiente local**: criam dados de teste e apagam no fim. Nunca rode em produção.
Para cada recurso novo, adicione um teste em `crm/tests/smoke/` e registre o nome em `MODULES`, no `run_smoke.py`.

## Depois de publicar

- Confira em Visão Geral > Saúde do negócio > "Saúde do sistema" se tudo está verde.
- O CRM confere isso de hora em hora e avisa os gestores por e-mail se algo falhar.
