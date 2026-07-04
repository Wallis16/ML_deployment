#!/bin/bash
set -eux

exec > /var/log/user-data.log 2>&1

# Aguarda boot completo
sleep 30

nvidia-smi

systemctl start docker
systemctl enable docker

REGISTRY=$(echo "${ecr_repository}" | cut -d'/' -f1)

aws ecr get-login-password \
  --region ${region} | \
  docker login \
  --username AWS \
  --password-stdin $REGISTRY

docker pull ${ecr_repository}

mkdir -p /opt/smollm

cat > /opt/smollm/.env <<EOF
MODEL_ID=HuggingFaceTB/SmolLM2-360M-Instruct
SMOLLM_MOCK=0
EOF

docker rm -f smollm || true

docker run -d \
  --name smollm \
  --restart unless-stopped \
  --gpus all \
  --env-file /opt/smollm/.env \
  -p 8000:8000 \
  ${ecr_repository}