FROM python:3.13-alpine

RUN apk update && \
    apk add supervisor openssh-server && \
    mkdir -p /var/log/supervisor && \
    mkdir -p /var/run/sshd

RUN python -m venv /config/python_env && \
    adduser -u 1001 --ingroup users -D python && \
    echo "python:python" | chpasswd

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY django.sh django.sh
COPY sshd.sh sshd.sh
COPY entrypoint.sh entrypoint.sh


RUN chmod +x django.sh

RUN mkdir -p /exec && \
    mkdir -p /config && \
    mkdir /django && \
    mkdir /volumes && \
    mkdir -p /root/.ssh &&\
    chmod 700 /root/.ssh && \
    chown -R python /exec && \
    chown -R python /config/python_env && \
    chown -R python /django


COPY entrypoint.sh /exec/
COPY requirements.txt /
COPY volumesform  /django/

ENTRYPOINT ["/entrypoint.sh"]
