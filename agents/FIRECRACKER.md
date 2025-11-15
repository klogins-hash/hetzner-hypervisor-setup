# Firecracker Deployment Guide

Deploy the Strands Agent Framework in Firecracker microVMs instead of Docker containers.

## Overview

**Why Firecracker for Agents?**
- Lightweight VMs (~5-10MB memory overhead)
- Better isolation than containers
- Direct hardware access for SSH
- Perfect for testing hypervisor workflows
- Aligns with project's Firecracker focus

**Architecture:**
```
Host Machine
└── Firecracker VMM (Virtual Machine Monitor)
    ├── Agent VM 1 (Python + Orchestrator)
    ├── Agent VM 2 (Monitoring/Logging - optional)
    └── Agent VM 3 (Testing - optional)

Local Network: 172.15.0.0/24
├── Host:    172.15.0.1
├── Agent 1: 172.15.0.2 (Primary)
└── Agent 2: 172.15.0.3 (Secondary - optional)
```

## Prerequisites

### 1. Install Firecracker

```bash
# macOS - via Homebrew (or build from source)
brew install firecracker

# Verify installation
firecracker --version
# Should output: Firecracker v1.0.0

# Linux - download from GitHub
wget https://github.com/firecracker-microvm/firecracker/releases/download/v1.0.0/firecracker-v1.0.0-x86_64.tgz
tar xf firecracker-v1.0.0-x86_64.tgz
sudo mv release-v1.0.0-x86_64/firecracker /usr/local/bin/
sudo chmod +x /usr/local/bin/firecracker
```

### 2. Create Root Filesystem Image

We'll use a minimal Ubuntu image optimized for Firecracker.

```bash
cd /Users/franksimpson/CascadeProjects/hetzner-hypervisor-setup/agents

# Download minimal Ubuntu image for Firecracker
mkdir -p firecracker/vms
cd firecracker/vms

# Get Ubuntu image (or build custom)
wget https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img
# Decompress if needed
gunzip focal-server-cloudimg-amd64.img

# Copy to VM directory
cp focal-server-cloudimg-amd64.img agent-rootfs.img

# Expand image for our use case
qemu-img resize agent-rootfs.img +5G

# Verify
ls -lh agent-rootfs.img
```

### 3. Build Custom Kernel

```bash
# Download Linux kernel optimized for Firecracker
mkdir -p firecracker/kernel
cd firecracker/kernel

# Get pre-built kernel (recommended for quick start)
wget https://s3.amazonaws.com/firecracker-microvm/latest/x86_64/vmlinux.bin

# OR compile custom kernel
git clone https://github.com/torvalds/linux.git
cd linux
make defconfig
make -j$(nproc)
# Result: arch/x86/boot/bzImage
```

## Setup: Option A - Quick Start (Pre-built)

### Create Agent VM Configuration

```bash
cd /Users/franksimpson/CascadeProjects/hetzner-hypervisor-setup/agents

# Create VM directory structure
mkdir -p firecracker/vms/agent-primary
mkdir -p firecracker/vms/agent-primary/metadata

# Create VM socket directory
mkdir -p firecracker/sockets

# Copy filesystem image
cp firecracker/kernel/rootfs.img firecracker/vms/agent-primary/

# Download kernel
wget -O firecracker/kernel/vmlinux.bin \
  https://s3.amazonaws.com/firecracker-microvm/latest/x86_64/vmlinux.bin
```

### Create VM Configuration File

Create `firecracker/launch-agent-vm.sh`:

```bash
#!/bin/bash

# Firecracker Agent VM Launcher
set -e

VM_NAME="agent-primary"
VM_DIR="$PWD/firecracker/vms/$VM_NAME"
SOCKET_DIR="$PWD/firecracker/sockets"
KERNEL="$PWD/firecracker/kernel/vmlinux.bin"
ROOTFS="$VM_DIR/rootfs.img"

echo "Starting Firecracker VM: $VM_NAME"

# Create socket
SOCKET="$SOCKET_DIR/$VM_NAME.sock"
mkdir -p "$(dirname "$SOCKET")"
rm -f "$SOCKET"

# Start Firecracker in background
firecracker \
  --config-file /dev/stdin \
  --socket-path "$SOCKET" < /dev/null > "$VM_DIR/firecracker.log" 2>&1 &

FC_PID=$!
echo "Firecracker PID: $FC_PID"

# Wait for socket to be ready
sleep 1

# Configure VM via API
curl -X PUT http+unix:///$SOCKET/api/v1/machine/config \
  -d "{
    \"vcpu_count\": 2,
    \"mem_size_mib\": 1024,
    \"cpu_template\": \"T2\",
    \"smt\": false,
    \"track_dirty_pages\": false
  }"

# Add kernel
curl -X PUT http+unix:///$SOCKET/api/v1/boot-source \
  -d "{
    \"kernel_image_path\": \"$KERNEL\",
    \"boot_args\": \"console=ttyS0 reboot=k panic=1 pci=off\"
  }"

# Add root filesystem
curl -X PUT http+unix:///$SOCKET/api/v1/drives/rootfs \
  -d "{
    \"drive_id\": \"rootfs\",
    \"path_on_host\": \"$ROOTFS\",
    \"is_root_device\": true,
    \"is_read_only\": false
  }"

# Add network interface
curl -X PUT http+unix:///$SOCKET/api/v1/network-interfaces/eth0 \
  -d "{
    \"iface_id\": \"eth0\",
    \"host_dev_name\": \"tap0\",
    \"state\": \"Attached\"
  }"

# Start VM
curl -X PUT http+unix:///$SOCKET/api/v1/machine/start

echo "VM Started! Access logs at: $VM_DIR/firecracker.log"
echo "SSH will be available at: 172.15.0.2 (after boot)"
echo "PID: $FC_PID"
```

Make executable:
```bash
chmod +x firecracker/launch-agent-vm.sh
```

## Setup: Option B - Flintlock (Production)

Use Flintlock (from the project!) for VM management:

```bash
# Install Flintlock
cd /Users/franksimpson/CascadeProjects/hetzner-hypervisor-setup

# Build Flintlock image
docker build -t flintlock-client -f - . << 'EOF'
FROM golang:1.19
RUN git clone https://github.com/liquid-metal/flintlock.git && \
    cd flintlock && \
    make build
EOF

# Or use existing Flintlock from project setup
flintlock start --version
```

Create Flintlock agent VM spec:

```yaml
# firecracker/flintlock-agent.yaml
apiVersion: liquid.io/v1alpha1
kind: MicroVM
metadata:
  name: agent-primary
  namespace: firecracker
spec:
  vmSpec:
    kernel:
      image: linuxkit/kernel:5.10
    initrd:
      image: linuxkit/init:latest
    memoryMb: 1024
    vcpu: 2
    networkInterfaces:
      - guestDeviceName: eth0
        address: 172.15.0.2/24
    volumes:
      - name: agent-data
        volumeSource:
          emptyDir: {}
  template:
    spec:
      containers:
        - name: agent
          image: hetzner-hypervisor-agents:latest
          env:
            - name: ANTHROPIC_API_KEY
              valueFrom:
                secretKeyRef:
                  name: api-keys
                  key: anthropic
            - name: SSH_HOST
              value: "172.15.0.1"
          volumeMounts:
            - name: agent-data
              mountPath: /app/state
```

Deploy with Flintlock:
```bash
# Apply to Flintlock
kubectl apply -f firecracker/flintlock-agent.yaml

# Verify
kubectl get microvm -n firecracker
```

## Network Setup

### Create TAP Interface

```bash
#!/bin/bash
# firecracker/setup-tap.sh

TAP_DEV="tap0"
TAP_IP="172.15.0.1"
VM_IP="172.15.0.2"

# Create TAP device
sudo ip tuntap add dev $TAP_DEV mode tap user $(whoami)

# Bring it up
sudo ip link set dev $TAP_DEV up

# Assign IP
sudo ip addr add ${TAP_IP}/24 dev $TAP_DEV

# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1

# Add iptables rule (macOS uses pfctl instead)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo iptables -A FORWARD -i $TAP_DEV -j ACCEPT
    sudo iptables -A FORWARD -o $TAP_DEV -j ACCEPT
fi

echo "TAP interface $TAP_DEV ready: $TAP_IP"
echo "VM will be accessible at: $VM_IP"
```

Make executable and run:
```bash
chmod +x firecracker/setup-tap.sh
./firecracker/setup-tap.sh
```

### macOS Network Setup (Alternative)

```bash
#!/bin/bash
# For macOS using vmnet

# Create vmnet interface
sudo ifconfig vmnet0 inet 172.15.0.1 172.15.0.255 up

# Configure sharing
# System Preferences → Network → Sharing → Internet Sharing
```

## Deploying Agent Framework to Firecracker VM

### 1. Prepare VM Image with Agent Code

```bash
# Mount VM filesystem
VM_IMG="firecracker/vms/agent-primary/rootfs.img"

# Use qemu tools
mkdir -p /tmp/agent-root
sudo modprobe nbd
sudo qemu-nbd --connect=/dev/nbd0 "$VM_IMG"
sudo mount /dev/nbd0p1 /tmp/agent-root

# Copy agent code
sudo mkdir -p /tmp/agent-root/opt/agents
sudo cp -r . /tmp/agent-root/opt/agents/
sudo cp agents/.env.template /tmp/agent-root/opt/agents/.env

# Create init script
sudo tee /tmp/agent-root/etc/init.d/agent-start > /dev/null << 'EOF'
#!/bin/bash
cd /opt/agents
python orchestrator.py
EOF

sudo chmod +x /tmp/agent-root/etc/init.d/agent-start

# Unmount
sudo umount /tmp/agent-root
sudo qemu-nbd --disconnect /dev/nbd0
```

### 2. Boot VM and Access

```bash
# Start VM
./firecracker/launch-agent-vm.sh

# Wait for boot (30-60 seconds)
sleep 30

# SSH into VM
ssh -i firecracker/ssh/id_rsa ubuntu@172.15.0.2

# Inside VM:
cd /opt/agents
cp .env.template .env
nano .env  # Add API keys

# Run orchestrator
python orchestrator.py --dry-run
python orchestrator.py  # Full execution
```

### 3. Configure SSH Access

```bash
# Generate SSH keypair for VM
mkdir -p firecracker/ssh
ssh-keygen -t rsa -b 4096 -f firecracker/ssh/id_rsa -N ""

# Copy public key to VM image (during image preparation)
# Or add via cloud-init
```

## Volume Management

### Persistent Storage

```bash
# Create data volume
mkdir -p firecracker/volumes/agent-data
dd if=/dev/zero of=firecracker/volumes/agent-data.img bs=1M count=10G

# Format
sudo mkfs.ext4 firecracker/volumes/agent-data.img

# Mount in VM configuration
curl -X PUT http+unix:///$SOCKET/api/v1/drives/data \
  -d "{
    \"drive_id\": \"data\",
    \"path_on_host\": \"$PWD/firecracker/volumes/agent-data.img\",
    \"is_root_device\": false,
    \"is_read_only\": false
  }"
```

### State Persistence

```bash
# Configure in orchestrator
volumes:
  state:
    path: /firecracker/volumes/agent-state
    type: ext4
    size: 5G
```

## Multi-VM Setup

### Multiple Agent VMs

```bash
#!/bin/bash
# firecracker/launch-agent-cluster.sh

for i in {1..3}; do
    VM_NAME="agent-$i"
    VM_IP="172.15.0.$((i+1))"

    # Create VM config
    mkdir -p firecracker/vms/$VM_NAME

    # Copy filesystem
    cp firecracker/kernel/rootfs.img firecracker/vms/$VM_NAME/

    # Configure network in cloud-init
    cat > firecracker/vms/$VM_NAME/network-config.yaml << EOF
    version: 2
    ethernets:
      eth0:
        dhcp4: false
        addresses:
          - $VM_IP/24
        gateway4: 172.15.0.1
        nameservers:
          addresses: [8.8.8.8, 8.8.4.4]
EOF

    # Launch VM
    ./firecracker/launch-agent-vm.sh "$VM_NAME"

    echo "VM $VM_NAME started at $VM_IP"
done
```

## Monitoring & Logging

### VM Logs

```bash
# Tail VM output
tail -f firecracker/vms/agent-primary/firecracker.log

# Connect to serial console
socat - UNIX-CONNECT:firecracker/sockets/agent-primary.sock
```

### Metrics

```bash
# Check VM metrics
curl http+unix:///$SOCKET/api/v1/vm/metrics | jq .

# Monitor from host
watch 'ps aux | grep firecracker'
```

## Cleanup

```bash
#!/bin/bash
# firecracker/cleanup.sh

# Stop VMs
pkill -f firecracker

# Clean up network
sudo ip link delete tap0
sudo ip link delete vmnet0

# Clean up volumes
rm -rf firecracker/sockets/*.sock
rm -rf firecracker/vms/*/firecracker.log

echo "Cleanup complete"
```

## Comparison: Docker vs Firecracker

| Aspect | Docker | Firecracker |
|--------|--------|------------|
| **Start Time** | 1-2s | 100-500ms |
| **Memory/VM** | 50-100MB | 5-10MB |
| **Isolation** | Process | Full VM |
| **Hardware Access** | Limited | Direct |
| **Nested Virt** | Not supported | Supported |
| **SSH Access** | IP-based | IP-based |
| **Complexity** | Simple | Medium |
| **Use Case** | General apps | Hypervisor testing |

## Firecracker vs Docker for This Project

### Choose Firecracker if:
✅ Testing hypervisor workflows
✅ Need full VM isolation
✅ Want minimal overhead
✅ Testing Flintlock/hypervisor stack
✅ Need to verify multi-VM setups

### Choose Docker if:
✅ Quick local development
✅ Want simplicity
✅ Don't need full isolation
✅ CI/CD integration
✅ Team familiarity with containers

## Getting Started

### Quick Start (5 minutes)
```bash
cd /Users/franksimpson/CascadeProjects/hetzner-hypervisor-setup/agents

# 1. Setup network
./firecracker/setup-tap.sh

# 2. Launch VM
./firecracker/launch-agent-vm.sh

# 3. Wait for boot and SSH
sleep 30
ssh -i firecracker/ssh/id_rsa ubuntu@172.15.0.2

# 4. Inside VM:
cd /opt/agents
python orchestrator.py --dry-run
```

### Production Setup (Use Flintlock)
```bash
# Follow "Option B: Flintlock" above
kubectl apply -f firecracker/flintlock-agent.yaml
kubectl get microvm
```

## Troubleshooting

### VM Won't Start
```bash
# Check Firecracker logs
tail -f firecracker/vms/agent-primary/firecracker.log

# Verify socket created
ls -la firecracker/sockets/

# Check kernel/rootfs exist
ls -la firecracker/kernel/vmlinux.bin
ls -la firecracker/vms/agent-primary/rootfs.img
```

### SSH Connection Fails
```bash
# Verify TAP interface
ip addr show tap0

# Ping VM from host
ping 172.15.0.2

# Check SSH key permissions
chmod 600 firecracker/ssh/id_rsa

# Try with verbose SSH
ssh -v -i firecracker/ssh/id_rsa ubuntu@172.15.0.2
```

### Network Issues
```bash
# Inside VM:
ip addr show
route -n

# From host:
host agent-primary 172.15.0.2
```

## Next Steps

1. **Complete Agent Implementation** (as per EVALUATION.md)
2. **Test with Firecracker** (local sandbox)
3. **Validate Workflow** (parallel team execution)
4. **Deploy to Hetzner** (production)

---

**Benefits of Firecracker Approach:**
- 🎯 Test in same environment as production (VMs)
- 🚀 Faster than Docker (boot time, memory)
- 🔒 Full isolation like production
- 💾 Minimal overhead
- 🧪 Perfect sandbox for hypervisor workflows
