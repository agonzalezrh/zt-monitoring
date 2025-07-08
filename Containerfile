FROM registry.access.redhat.com/ubi9/python-311:9.6
WORKDIR /app/
USER root
RUN dnf install -y sshpass sqlite
RUN chown -R ${USER_UID}:0 /app
USER ${USER_UID}

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

ENV BASE_DIR="/app"

COPY ./monitoring.py /app/monitoring.py
COPY ./api.py /app/api.py
COPY ./main.yml /app/main.yml
COPY ./ansible.cfg /app/ansible.cfg

# Copy the entrypoint script into the container
COPY ./entrypoint.sh /entrypoint.sh
# Make the entrypoint script executable and change ownership
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
