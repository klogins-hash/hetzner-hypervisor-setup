#!/bin/bash
set -e

echo "=========================================="
echo "Hetzner Hypervisor Setup Installer"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
   echo "Please run as root (use sudo)"
   exit 1
fi

# Check virtualization support
echo "Checking virtualization support..."
if ! grep -qE '(vmx|svm)' /proc/cpuinfo; then
    echo "ERROR: CPU virtualization not available"
    exit 1
fi

if ! ls /dev/kvm &>/dev/null; then
    echo "ERROR: /dev/kvm not found. KVM kernel module may not be loaded"
    exit 1
fi

echo "✓ Virtualization support confirmed"
echo ""

# Install Firecracker
echo "Installing Firecracker v1.10.0..."
wget -q https://github.com/firecracker-microvm/firecracker/releases/download/v1.10.0/firecracker-v1.10.0-x86_64.tgz
tar -xzf firecracker-v1.10.0-x86_64.tgz
mv release-v1.10.0-x86_64/firecracker-v1.10.0-x86_64 /usr/local/bin/firecracker
chmod +x /usr/local/bin/firecracker
rm -rf firecracker-v1.10.0-x86_64.tgz release-v1.10.0-x86_64
echo "✓ Firecracker installed: $(firecracker --version 2>&1 | head -1)"
echo ""

# Install Cloud Hypervisor
echo "Installing Cloud Hypervisor v49.0..."
wget -q https://github.com/cloud-hypervisor/cloud-hypervisor/releases/download/v49.0/cloud-hypervisor
chmod +x cloud-hypervisor
mv cloud-hypervisor /usr/local/bin/cloud-hypervisor
echo "✓ Cloud Hypervisor installed: $(cloud-hypervisor --version)"
echo ""

# Install Flintlock
echo "Installing Flintlock v0.9.0..."
wget -q https://github.com/liquidmetal-dev/flintlock/releases/download/v0.9.0/flintlockd_amd64
chmod +x flintlockd_amd64
mv flintlockd_amd64 /usr/local/bin/flintlock
echo "✓ Flintlock installed: $(flintlock version)"
echo ""

# Download test resources
echo "Downloading test resources..."
mkdir -p /root/firecracker-test
cd /root/firecracker-test

echo "  - Downloading kernel..."
wget -q https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/x86_64/kernels/vmlinux.bin

echo "  - Downloading rootfs..."
wget -q https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/x86_64/rootfs/bionic.rootfs.ext4

# Create Firecracker config
cat > vm_config.json << 'EOF'
{
  "boot-source": {
    "kernel_image_path": "/root/firecracker-test/vmlinux.bin",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "/root/firecracker-test/bionic.rootfs.ext4",
      "is_root_device": true,
      "is_read_only": false
    }
  ],
  "machine-config": {
    "vcpu_count": 2,
    "mem_size_mib": 1024
  }
}
EOF

echo "✓ Test resources downloaded"
echo ""

# Get network interface
IFACE=$(ip -br link show | grep -v lo | grep UP | head -1 | awk '{print $1}')
echo "Detected network interface: $IFACE"

# Create Flintlock systemd service
echo "Creating Flintlock systemd service..."
cat > /etc/systemd/system/flintlock.service << EOF
[Unit]
Description=Flintlock MicroVM Management Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/flintlock run \\
  --grpc-endpoint=0.0.0.0:9090 \\
  --firecracker-bin=/usr/local/bin/firecracker \\
  --cloudhypervisor-bin=/usr/local/bin/cloud-hypervisor \\
  --default-provider=firecracker \\
  --parent-iface=$IFACE \\
  --bridge-name=flkbr0 \\
  --insecure
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable flintlock
systemctl start flintlock

echo "✓ Flintlock service created and started"
echo ""

echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Installed components:"
echo "  - Firecracker v1.10.0 at /usr/local/bin/firecracker"
echo "  - Cloud Hypervisor v49.0 at /usr/local/bin/cloud-hypervisor"
echo "  - Flintlock v0.9.0 at /usr/local/bin/flintlock"
echo ""
echo "Flintlock service status:"
systemctl status flintlock --no-pager | head -5
echo ""
echo "Test files located at: /root/firecracker-test/"
echo ""
echo "Run 'sudo bash scripts/verify-setup.sh' to verify the installation"
