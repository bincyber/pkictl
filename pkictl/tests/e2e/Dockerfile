# requires Docker 17.05+

FROM debian:9-slim

ARG VAULT_VERSION=1.0.3

RUN set -ex && apt-get update -qq \
    && apt-get install -y --no-install-recommends unzip wget openssl ca-certificates \
    && wget -q "https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip" \
    && unzip "vault_${VAULT_VERSION}_linux_amd64.zip" \
    && cp vault /usr/local/bin/vault \
    && mkdir -p /etc/vault/ssl \
    && openssl req -x509 -newkey rsa:2048 -nodes -keyout /etc/vault/ssl/server.key -out /etc/vault/ssl/server.crt -days 365 -subj '/CN=Vault Server/'

# -----------------------------------------------

FROM debian:9-slim

LABEL APP="vault"
LABEL URL="http://github.com/hashicorp/vault"

RUN mkdir -p /etc/vault /var/lib/vault

COPY ./config.hcl /etc/vault/config.hcl
COPY --from=0 /usr/local/bin/vault /usr/local/bin/vault
COPY --from=0 /etc/vault/ssl/server.key /etc/vault/ssl/server.key
COPY --from=0 /etc/vault/ssl/server.crt /etc/vault/ssl/server.crt

RUN chown -R 10001:root /etc/vault /var/lib/vault

ENV VAULT_ADDR="https://localhost:8200" VAULT_SKIP_VERIFY="True"

WORKDIR /var/lib/vault

USER 10001:10001

EXPOSE 8200

ENTRYPOINT [ "/usr/local/bin/vault", "server", "-config", "/etc/vault/config.hcl" ]
