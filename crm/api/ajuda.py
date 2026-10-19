# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Central de ajuda (botão "?" em todas as telas): guias curtos por tela e, quando houver, o vídeo.
# Os guias e os links dos vídeos ficam AQUI, num lugar só, e valem para todos os clientes:
# gravou um vídeo novo, é só colocar o link no campo "video" do guia correspondente.

import frappe

# cada guia: chave, telas onde aparece primeiro (nomes das rotas), título, passos e vídeo (YouTube, opcional)
GUIAS = [
	{"chave": "caso_processo", "telas": ["Deal"], "titulo": "Processo, partes e andamentos", "video": "",
	 "passos": ["Abra o caso e vá na aba Processo.", "Cadastre o nº do processo (o CRM confere o número CNJ) e o tribunal.",
				"Adicione a parte contrária: se ela já foi cliente ou atendimento do escritório, aparece o aviso de conflito.",
				"Registre andamentos em linguagem simples e marque “Mostrar ao cliente” no que ele pode ver.",
				"Copie o link do portal e mande ao cliente: ele acompanha tudo sem ligar."]},
	{"chave": "caso_prestacao", "telas": ["Deal"], "titulo": "Prestação de contas (alvará, acordo, RPV)", "video": "",
	 "passos": ["Na aba Prestação de contas, salve o % de êxito combinado.", "Lance as custas que o escritório adiantou e marque “Cobrar do cliente”.",
				"Quando entrar um valor, clique em Registrar recebimento: o CRM calcula honorários, desconta as custas e mostra o valor do cliente.",
				"Se houver parceiro ou correspondente, informe a parte dele (sai dos honorários).",
				"Gere o Demonstrativo em PDF e marque o repasse quando pagar o cliente."]},
	{"chave": "caso_documentos", "telas": ["Deal"], "titulo": "Documentos, procuração e assinatura", "video": "",
	 "passos": ["Na aba Documentos, preencha os dados do cliente (CPF, endereço...).", "Escolha o modelo (contrato, procuração...) e clique em Gerar PDF.",
				"Clique em Enviar para assinatura: o link é copiado. Mande ao cliente pelo WhatsApp.",
				"O cliente assina pelo celular e o PDF assinado cai sozinho na pasta do caso.",
				"Para pedir documentos, marque a lista e gere o link: o CRM lembra o cliente a cada 3 dias."]},
	{"chave": "ficha_audio", "telas": ["Deal", "Lead"], "titulo": "Ficha da consulta por áudio", "video": "",
	 "passos": ["Abra a ficha e clique em Preencher com texto.", "Use Ditar agora para falar e ver o texto aparecer, ou Gravar a consulta / Enviar áudio.",
				"Clique em Preencher a ficha: a IA organiza fatos, urgência, partes e próximos passos.",
				"Confira e ajuste. A IA não opina sobre o caso: só registra o que foi dito."]},
	{"chave": "atendimentos", "telas": ["Leads", "Lead"], "titulo": "Atendimentos (quem procurou o escritório)", "video": "",
	 "passos": ["Todo contato novo vira um atendimento: pelo site, Instagram, agendamento ou cadastrado à mão.",
				"Preencha “Indicado por” para saber quem mais indica clientes.", "Faça a consulta e registre a ficha.",
				"Fechou? Converta em caso: o contrato, a procuração e as tarefas de início saem sozinhos."]},
	{"chave": "financeiro", "telas": ["Financeiro", "FinanceiroReports", "FinanceiroVisaoGeral"], "titulo": "Financeiro, carnê-leão e rentabilidade", "video": "",
	 "passos": ["Honorários em aberto e atrasados aparecem no Financeiro; o CRM cobra sozinho pelo e-mail.",
				"Em Relatórios, baixe a planilha do carnê-leão do mês (recebido de pessoa física).",
				"Veja a rentabilidade por área e por cliente: quanto sobra e quanto vale cada hora.",
				"Veja quem mais indica clientes e quanto essas indicações renderam."]},
	{"chave": "importar", "telas": [], "titulo": "Trazer a planilha que você já usa", "video": "",
	 "passos": ["Configurações → Importar planilha.", "Escolha o tipo (contatos, casos, honorários ou despesas).",
				"Envie o seu Excel ou CSV: o CRM reconhece as colunas sozinho.", "Confira a prévia e clique em Importar. Quem já existe não é duplicado."]},
	{"chave": "areas", "telas": [], "titulo": "Modelos de área e tabela de honorários", "video": "",
	 "passos": ["Configurações → Modelos de área: documentos, perguntas da consulta e êxito padrão de cada área.",
				"Configurações → Tabela de honorários: cadastre a tabela da sua seccional e o valor que o escritório pratica."]},
	{"chave": "comunicados", "telas": [], "titulo": "Comunicados aos clientes", "video": "",
	 "passos": ["Configurações → Comunicados aos clientes.", "Escolha a área e quais clientes (ativos, encerrados ou todos).",
				"Escreva em tom informativo, sem prometer resultado, e envie por e-mail ou baixe a lista para o WhatsApp."]},
	{"chave": "seguranca", "telas": ["Equipe"], "titulo": "Segurança, LGPD e equipe", "video": "",
	 "passos": ["Configurações → Segurança e dados: ligue o login em duas etapas e baixe todos os dados quando quiser.",
				"Pedido de titular (LGPD): busque a pessoa e exporte ou anonimize os dados.",
				"Marque um caso como sigiloso para só o responsável enxergar.", "Em Equipe, veja a carga de trabalho de cada pessoa."]},
	{"chave": "agenda", "telas": ["Calendar", "Tasks"], "titulo": "Agendamento online e consulta paga", "video": "",
	 "passos": ["Configurações → Automações: ligue o agendamento online e defina horários.",
				"Se a consulta for paga, informe o valor: o cliente recebe o link de pagamento ao agendar.",
				"O e-mail de confirmação e o lembrete têm os botões Confirmar presença e Desmarcar."]},
	{"chave": "celular", "telas": [], "titulo": "Usar no celular como aplicativo", "video": "",
	 "passos": ["Abra o CRM no navegador do celular.", "Android (Chrome): menu ⋮ → Adicionar à tela inicial. iPhone (Safari): Compartilhar → Adicionar à Tela de Início.",
				"O ícone aparece com o nome e a marca do escritório.", "No painel de notificações, toque em Ativar avisos."]},
]


SO_ESCRITORIO = {"caso_processo", "caso_prestacao", "areas"}


@frappe.whitelist()
def guias(tela: str = "") -> dict:
	from crm.provision import PERFIS_JURIDICOS, get_profile

	juridico = get_profile() in PERFIS_JURIDICOS
	lista = [g for g in GUIAS if juridico or g["chave"] not in SO_ESCRITORIO]
	primeiro = [g for g in lista if tela and tela in g["telas"]]
	resto = [g for g in lista if g not in primeiro]
	return {"desta_tela": primeiro, "outros": resto}
