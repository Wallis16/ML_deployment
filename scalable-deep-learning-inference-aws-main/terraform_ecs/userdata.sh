#!/bin/bash
set -eux

exec > /var/log/user-data.log 2>&1

cat <<EOF >> /etc/ecs/ecs.config
ECS_CLUSTER=smollm-cluster
ECS_ENABLE_GPU_SUPPORT=true
EOF

systemctl enable ecs
systemctl restart ecs