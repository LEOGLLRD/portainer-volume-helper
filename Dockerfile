FROM python:3.13-alpine

RUN python -m venv /config/python_env && \
    adduser -u 1001 --ingroup users -D python && \
    echo "python:python" | chpasswd


RUN mkdir -p /exec && \
    mkdir -p /config && \
    mkdir /django && \
    mkdir /volumes && \
    chown -R python /exec && \
    chown -R python /config/python_env && \
    chown -R python /django

COPY entrypoint.sh /exec/
COPY requirements.txt /
COPY volumesform  /django/

ENTRYPOINT ["/exec/entrypoint.sh"]