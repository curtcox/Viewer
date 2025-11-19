#!/bin/bash
set -e

echo "=== /dev/shm status ==="
df -h /dev/shm || echo "/dev/shm not available"
ls -ld /dev/shm || echo "/dev/shm directory check failed"

echo ""
echo "=== Memory info ==="
free -h

echo ""
echo "=== Disk space ==="
df -h /tmp
