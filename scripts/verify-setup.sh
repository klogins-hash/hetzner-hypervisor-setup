#!/bin/bash

echo "=========================================="
echo "Hetzner Hypervisor Setup Verification"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1"
        return 1
    fi
}

# Virtualization Support
echo "1. Checking Virtualization Support..."
grep -qE '(vmx|svm)' /proc/cpuinfo
check "CPU virtualization extensions"

ls /dev/kvm &>/dev/null
check "/dev/kvm device exists"

lsmod | grep -q kvm
check "KVM kernel modules loaded"
echo ""

# Firecracker
echo "2. Checking Firecracker..."
if [ -f /usr/local/bin/firecracker ]; then
    VERSION=$(firecracker --version 2>&1 | head -1)
    echo -e "${GREEN}✓${NC} Firecracker installed: $VERSION"

    # Test if it can run
    if [ -f /root/firecracker-test/vm_config.json ]; then
        echo -e "${GREEN}✓${NC} Test configuration exists"
    else
        echo -e "${YELLOW}⚠${NC} Test configuration not found"
    fi
else
    echo -e "${RED}✗${NC} Firecracker not installed"
fi
echo ""

# Cloud Hypervisor
echo "3. Checking Cloud Hypervisor..."
if [ -f /usr/local/bin/cloud-hypervisor ]; then
    VERSION=$(cloud-hypervisor --version 2>&1)
    echo -e "${GREEN}✓${NC} Cloud Hypervisor installed: $VERSION"
else
    echo -e "${RED}✗${NC} Cloud Hypervisor not installed"
fi
echo ""

# Flintlock
echo "4. Checking Flintlock..."
if [ -f /usr/local/bin/flintlock ]; then
    VERSION=$(flintlock version 2>&1)
    echo -e "${GREEN}✓${NC} Flintlock installed: $VERSION"

    # Check service
    if systemctl is-active --quiet flintlock; then
        echo -e "${GREEN}✓${NC} Flintlock service is running"

        # Check if listening on port
        if ss -tln | grep -q ':9090'; then
            echo -e "${GREEN}✓${NC} Flintlock listening on port 9090"
        else
            echo -e "${YELLOW}⚠${NC} Flintlock not listening on port 9090"
        fi
    else
        echo -e "${RED}✗${NC} Flintlock service is not running"
    fi
else
    echo -e "${RED}✗${NC} Flintlock not installed"
fi
echo ""

# Network Configuration
echo "5. Checking Network Configuration..."
IFACE=$(ip -br link show | grep -v lo | grep UP | head -1 | awk '{print $1}')
if [ -n "$IFACE" ]; then
    echo -e "${GREEN}✓${NC} Primary interface: $IFACE"
else
    echo -e "${RED}✗${NC} No network interface found"
fi
echo ""

# Summary
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo ""

PASS=0
FAIL=0

# Count checks
if grep -qE '(vmx|svm)' /proc/cpuinfo; then ((PASS++)); else ((FAIL++)); fi
if ls /dev/kvm &>/dev/null; then ((PASS++)); else ((FAIL++)); fi
if lsmod | grep -q kvm; then ((PASS++)); else ((FAIL++)); fi
if [ -f /usr/local/bin/firecracker ]; then ((PASS++)); else ((FAIL++)); fi
if [ -f /usr/local/bin/cloud-hypervisor ]; then ((PASS++)); else ((FAIL++)); fi
if [ -f /usr/local/bin/flintlock ]; then ((PASS++)); else ((FAIL++)); fi
if systemctl is-active --quiet flintlock 2>/dev/null; then ((PASS++)); else ((FAIL++)); fi

echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All checks passed! 🎉${NC}"
    echo "The hypervisor setup is complete and operational."
    exit 0
else
    echo -e "${YELLOW}Some checks failed.${NC}"
    echo "Please review the output above and fix any issues."
    exit 1
fi
