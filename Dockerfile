# requires Docker 17.05+

FROM python:3.6-slim

COPY Pipfile* /

RUN set -ex && pip install pipenv==2018.10.13 --no-cache-dir --disable-pip-version-check \
    && pipenv --python 3.6 lock -r > requirements.txt

# -----------------------------------------------------------------------------------------

FROM python:3.6-slim

LABEL APP="pkictl"
LABEL MAINTAINER="@bincyber"
LABEL URL="http://github.com/bincyber/pkictl"

COPY --from=0 /requirements.txt /tmp/requirements.txt

RUN set -e \
    && pip install -r /tmp/requirements.txt --no-cache-dir --disable-pip-version-check \
    && rm -rf /usr/src/python /root/.cache /root/.local /tmp/requirements.txt \
    && find /usr/local -depth -type f -a -name '*.pyc' -exec rm -rf '{}' \;

COPY pkictl /app/pkictl

WORKDIR /app

USER 10001:10001

ENTRYPOINT [ "/usr/local/bin/python", "-m", "pkictl" ]
