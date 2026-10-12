#!/bin/bash
# แปลง external IP ปัจจุบันของ VM ให้เป็น static IP (รันครั้งเดียว ไม่ต้องหยุดเครื่อง)
# ใช้: ./scripts/gcp-static-ip.sh [VM_NAME] [ZONE]
set -euo pipefail

VM_NAME="${1:-hai-nida-prod}"
ZONE="${2:-asia-southeast1-b}"
REGION="${ZONE%-*}"
ADDRESS_NAME="hai-nida-ip"

IP=$(gcloud compute instances describe "$VM_NAME" --zone "$ZONE" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

if [ -z "$IP" ]; then
  echo "VM $VM_NAME ไม่มี external IP" >&2
  exit 1
fi

EXISTING=$(gcloud compute addresses list --filter="address=$IP" --format='get(name)')
if [ -n "$EXISTING" ]; then
  echo "IP $IP เป็น static อยู่แล้ว (ชื่อ $EXISTING)"
  exit 0
fi

gcloud compute addresses create "$ADDRESS_NAME" \
  --addresses="$IP" --region="$REGION"

echo "แปลง $IP เป็น static แล้ว (ชื่อ $ADDRESS_NAME)"
