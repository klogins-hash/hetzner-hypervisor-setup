# Step 01: Security Baseline

**Team**: Alpha
**Phase**: 1
**Priority**: HIGH
**Duration**: 2-3 hours
**Prerequisites**: None
**Blocks**: All other teams

---

## Objective

Establish a secure foundation for the entire infrastructure by:
- Generating TLS certificates for Flintlock
- Configuring firewall rules
- Hardening SSH access
- Disabling Flintlock insecure mode

---

## Prerequisites

✅ Base installation complete (`scripts/install-all.sh` has run)
✅ SSH access to server (`ssh hetzner1`)
✅ Root privileges
✅ Firecracker, Cloud Hypervisor, and Flintlock installed

---

## Tasks

### Task 1: Generate TLS Certificates (30 min)

**Objective**: Create TLS certificates for Flintlock gRPC API

```bash
# SSH into server
ssh hetzner1

# Create certificate directory
mkdir -p /etc/flintlock/certs
cd /etc/flintlock/certs

# Generate self-signed certificate (válid for 1 year)
openssl req -x509 -newkey rsa:4096 \
  -keyout key.pem \
  -out cert.pem \
  -days 365 \
  -nodes \
  -subj "/CN=flintlock.local/O=HetznerInfra"

# Set proper permissions
chmod 600 key.pem
chmod 644 cert.pem

# Verify certificates
openssl x509 -in cert.pem -text -noout | grep "Subject:"
```

**Verification**:
```bash
ls -l /etc/flintlock/certs/
# Should show key.pem and cert.pem
```

---

### Task 2: Configure Firewall (30 min)

**Objective**: Set up UFW firewall with proper rules

```bash
# Install UFW if not present
apt-get update && apt-get install -y ufw

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (critical!)
ufw allow 22/tcp comment 'SSH'

# Allow Flintlock gRPC
ufw allow 9090/tcp comment 'Flintlock gRPC'

# Enable firewall (will prompt for confirmation)
ufw enable

# Check status
ufw status verbose
```

**Verification**:
```bash
ufw status numbered
# Should show rules for ports 22 and 9090
```

---

### Task 3: Harden SSH Access (30 min)

**Objective**: Disable password authentication, enforce key-only access

**⚠️ WARNING**: Do this ONLY if you have SSH key access configured!

```bash
# Backup SSH config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Edit SSH config
cat >> /etc/ssh/sshd_config << 'EOF'

# Security hardening
PasswordAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
ChallengeResponseAuthentication no
UsePAM no
EOF

# Test configuration
sshd -t

# If test passes, restart SSH
systemctl restart sshd

# Verify from another terminal (don't close current session yet!)
# ssh hetzner1 should work with keys, fail with password
```

**Verification**:
```bash
sshd -T | grep -i passwordauthentication
# Should show: passwordauthentication no
```

---

### Task 4: Update Flintlock Service with TLS (45 min)

**Objective**: Reconfigure Flintlock to use TLS instead of insecure mode

```bash
# Stop Flintlock service
systemctl stop flintlock

# Backup current service file
cp /etc/systemd/system/flintlock.service /etc/systemd/system/flintlock.service.backup

# Update service configuration
cat > /etc/systemd/system/flintlock.service << 'EOF'
[Unit]
Description=Flintlock MicroVM Management Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/flintlock run \
  --grpc-endpoint=0.0.0.0:9090 \
  --firecracker-bin=/usr/local/bin/firecracker \
  --cloudhypervisor-bin=/usr/local/bin/cloud-hypervisor \
  --default-provider=firecracker \
  --parent-iface=enp6s0 \
  --bridge-name=flkbr0 \
  --tls-cert=/etc/flintlock/certs/cert.pem \
  --tls-key=/etc/flintlock/certs/key.pem
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Start Flintlock with TLS
systemctl start flintlock

# Check status
systemctl status flintlock
```

**Verification**:
```bash
systemctl is-active flintlock
# Should show: active

# Check it's using TLS
journalctl -u flintlock -n 20 | grep -i tls

# Verify port is listening
ss -tln | grep 9090
```

---

### Task 5: Install fail2ban (15 min)

**Objective**: Add intrusion prevention system

```bash
# Install fail2ban
apt-get install -y fail2ban

# Enable and start
systemctl enable fail2ban
systemctl start fail2ban

# Check status
fail2ban-client status
```

**Verification**:
```bash
systemctl is-active fail2ban
# Should show: active
```

---

## Verification Checklist

Run these commands to verify all tasks completed successfully:

```bash
# 1. Certificates exist
[ -f /etc/flintlock/certs/cert.pem ] && echo "✅ TLS cert exists" || echo "❌ TLS cert missing"

# 2. Firewall is active
ufw status | grep -q "Status: active" && echo "✅ Firewall active" || echo "❌ Firewall inactive"

# 3. SSH hardened
grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config && echo "✅ SSH hardened" || echo "❌ SSH not hardened"

# 4. Flintlock using TLS
systemctl status flintlock | grep -q "active (running)" && echo "✅ Flintlock running" || echo "❌ Flintlock not running"

# 5. fail2ban active
systemctl is-active fail2ban > /dev/null && echo "✅ fail2ban active" || echo "❌ fail2ban inactive"
```

**All checks should show ✅**

---

## Rollback Procedures

If something goes wrong, follow these steps:

### Rollback TLS Configuration
```bash
systemctl stop flintlock
cp /etc/systemd/system/flintlock.service.backup /etc/systemd/system/flintlock.service
systemctl daemon-reload
systemctl start flintlock
```

### Rollback SSH Configuration
```bash
cp /etc/ssh/sshd_config.backup /etc/ssh/sshd_config
systemctl restart sshd
```

### Disable Firewall
```bash
ufw disable
```

### Nuclear Option - Full Rebuild
```bash
# On local machine
ssh hetzner1
# In Hetzner console: Reset server, install Ubuntu 24.04
git clone https://github.com/klogins-hash/hetzner-hypervisor-setup.git
cd hetzner-hypervisor-setup
sudo bash scripts/install-all.sh
```

---

## Troubleshooting

### Issue: Flintlock won't start with TLS

**Symptoms**: `systemctl status flintlock` shows failed state

**Solution**:
```bash
# Check logs
journalctl -u flintlock -n 50

# Verify certificate permissions
ls -l /etc/flintlock/certs/

# Test certificate validity
openssl x509 -in /etc/flintlock/certs/cert.pem -noout -dates
```

### Issue: Locked out of SSH

**Prevention**: Always keep one SSH session open while testing!

**Solution**: Use Hetzner console/KVM access to fix SSH config

### Issue: Firewall blocking connections

**Solution**:
```bash
# Check UFW logs
tail -f /var/log/ufw.log

# Add missing rule
ufw allow [port]/tcp
```

---

## Success Criteria

✅ TLS certificates generated and valid
✅ Firewall active with proper rules
✅ SSH password authentication disabled
✅ Flintlock running with TLS enabled
✅ fail2ban installed and active
✅ All verification checks pass

---

## Completion Signal

Once all tasks are complete and verified, post this message:

```
✅ TEAM ALPHA COMPLETE
Phase: 1
Duration: [X hours]
Issues: None
Next Teams Can Start: Team Bravo, Team Charlie
Security baseline established. TLS enabled. System hardened.
```

---

## Next Steps

After Team Alpha completes, the following teams can start in parallel:
- **Team Bravo**: Container Runtime (Step 02)
- **Team Charlie**: Basic Monitoring (Step 03)

---

## References

- [Flintlock TLS Configuration](https://github.com/liquidmetal-dev/flintlock/tree/main/docs)
- [UFW Guide](https://help.ubuntu.com/community/UFW)
- [SSH Hardening Best Practices](https://www.ssh.com/academy/ssh/sshd_config)
- [fail2ban Documentation](https://www.fail2ban.org/wiki/index.php/Main_Page)
