# Restaurar o CRM a partir da cópia do Google Drive

Toda noite o CRM guarda uma cópia completa na pasta **Backups do CRM** do Google Drive do escritório, em uma
subpasta por dia (`AAAA-MM-DD`). As 10 últimas ficam guardadas. Use isto se o servidor for perdido ou danificado.

## O que tem em cada pasta do dia

| Arquivo | O que é |
|---|---|
| `...-database.sql.gz` | Todos os dados (leads, negócios, financeiro, mensagens, configurações do CRM) |
| `...-files.tar` | Arquivos públicos (logos, imagens) |
| `...-private-files.tar` | Arquivos privados (documentos dos clientes, propostas, contratos, resumos) |

## Passo a passo (em um servidor novo, com o CRM já instalado)

1. Baixe os quatro arquivos do dia desejado no Google Drive para o servidor (por exemplo, para `/tmp/restore/`).
2. Crie o site vazio, se ainda não existir: `bench new-site SEU-DOMINIO --admin-password ...` e `bench --site SEU-DOMINIO install-app crm`.
3. Restaure: 
   ```
   bench --site SEU-DOMINIO restore /tmp/restore/...-database.sql.gz \
     --with-public-files /tmp/restore/...-files.tar \
     --with-private-files /tmp/restore/...-private-files.tar
   ```
4. Rode `bench --site SEU-DOMINIO migrate` e `bench --site SEU-DOMINIO clear-cache`.
5. A configuração do servidor (senhas, chaves do Google e chave de criptografia) **não vai na cópia, por segurança**.
   No `site_config.json` do novo servidor, reinsira `gdrive_client_id` e `gdrive_client_secret` (e `gdrive_redirect_uri`,
   se usar). Como a chave de criptografia é nova, os acessos guardados (token do Instagram, chave da IA, conexão do
   Google Drive) precisam ser **inseridos de novo** nas Configurações. Os dados em si (leads, negócios etc.) voltam intactos.
6. Reconecte o Google Drive em Configurações > Google Drive e confira a Saúde do sistema (Visão Geral).

## Teste a restauração de vez em quando

Uma cópia que nunca foi restaurada é só uma esperança. Uma vez por trimestre, restaure a cópia mais recente em um
ambiente de teste e confira se os leads, os documentos e o financeiro estão lá.