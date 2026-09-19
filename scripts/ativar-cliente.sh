#!/usr/bin/env bash
# Cria e ativa um CRM novo para um escritório, no servidor (VPS).
#
#   ./ativar-cliente.sh crm.escritoriox.com.br "Escritório X" /caminho/logo.png [https://site.com.br] [agencia|escritorio|escritorio_empresarial]
#
# Pré-requisitos: DNS do domínio apontando pro servidor; senha root do MariaDB em
# DB_ROOT_PASSWORD (ou DB_PASSWORD no /root/frappe.env). O certificado HTTPS do
# domínio novo depende do seu proxy reverso e é feito à parte.
set -euo pipefail

SITE="${1:?domínio do site, ex: crm.escritoriox.com.br}"
BRAND="${2:?nome da agência/escritório}"
LOGO="${3:-}"
WEBSITE="${4:-}"
PROFILE="${5:-agencia}"   # agencia | escritorio (pessoa física) | escritorio_empresarial (atende empresas)

BACKEND="${BACKEND:-frappe-backend-1}"
[ -f /root/frappe.env ] && set -a && . /root/frappe.env && set +a
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-${DB_PASSWORD:-}}"
: "${DB_ROOT_PASSWORD:?defina DB_ROOT_PASSWORD}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-$(openssl rand -base64 12 | tr -d '=+/')}"

echo ">> Criando site $SITE"
docker exec "$BACKEND" bench new-site "$SITE" \
  --mariadb-root-password "$DB_ROOT_PASSWORD" \
  --admin-password "$ADMIN_PASSWORD" \
  --install-app crm --set-default=false

LOGO_ARGS=()
if [ -n "$LOGO" ]; then
  docker cp "$LOGO" "$BACKEND:/tmp/logo_cliente.${LOGO##*.}"
  LOGO_ARGS=(-e "CRM_LOGO_PATH=/tmp/logo_cliente.${LOGO##*.}")
fi

echo ">> Aplicando padrões (português, fuso, moeda, marca, áreas do direito)"
docker exec -e "CRM_BRAND_NAME=$BRAND" -e "CRM_WEBSITE_URL=$WEBSITE" -e "CRM_PROFILE=$PROFILE" "${LOGO_ARGS[@]}" \
  "$BACKEND" bench --site "$SITE" execute crm.provision.provision_from_env

docker exec "$BACKEND" bench --site "$SITE" clear-cache

echo
echo "CRM pronto: https://$SITE/crm"
echo "Usuário: Administrator | Senha: $ADMIN_PASSWORD   (troque no primeiro acesso)"
