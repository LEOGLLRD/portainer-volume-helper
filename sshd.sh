#!/bin/sh
ssh-keygen -A
if [ ! -e "/root/.ssh/.dockerToolboxKey" ]; then
    if [ -e "/volumes/.dockerToolboxKey" ]; then
        ssh-keygen -f /volumes/.dockerToolboxKey -y > /etc/ssh/.dockerToolboxKey.pub
        cat /etc/ssh/.dockerToolboxKey.pub >> /root/.ssh/authorized_keys
        rm /etc/ssh/.dockerToolboxKey.pub
    else
        ssh-keygen -t ed25519 -f /etc/ssh/.dockerToolboxKey -C "dockerToolboxKey" -N ''
        cat /etc/ssh/.dockerToolboxKey.pub >> /root/.ssh/authorized_keys
        cp /etc/ssh/.dockerToolboxKey /volumes
        rm /etc/ssh/.dockerToolboxKey
        rm /etc/ssh/.dockerToolboxKey.pub
    fi

else
    chmod 600 /root/.ssh/authorized_keys
    exec /usr/sbin/sshd -D
fi

chmod 600 /root/.ssh/authorized_keys
exec /usr/sbin/sshd -D