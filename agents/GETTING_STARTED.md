# Getting Started with Strands Agent Framework Team

This guide will help you set up and run the Strands Agent Framework team for your Hetzner hypervisor setup.

## Prerequisites

1. **Python 3.9+** installed
2. **SSH access** to your Hetzner server configured (see `.ssh/config`)
3. **API keys** for your chosen LLM provider (OpenAI, Anthropic, or AWS Bedrock)
4. **Git repository** cloned and up to date

## Quick Setup

### Step 1: Install Dependencies

```bash
cd /Users/franksimpson/CascadeProjects/hetzner-hypervisor-setup/agents

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
# Copy the template
cp .env.template .env

# Edit with your API keys
nano .env  # or use your preferred editor
```

**Example `.env` file:**
```bash
# Use Anthropic Claude (recommended for infrastructure tasks)
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Or use OpenAI
# OPENAI_API_KEY=sk-your-openai-key-here

# Or use AWS Bedrock
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Step 3: Verify SSH Connection

```bash
# Test your SSH connection
ssh hetzner1

# If it works, you're good. If not, configure SSH:
nano ~/.ssh/config
```

**SSH Config should look like:**
```
Host hetzner1
    HostName your.server.ip.address
    User root
    IdentityFile ~/.ssh/your_key
    StrictHostKeyChecking no
```

### Step 4: Configure Settings (Optional)

Review and modify `agents/config.yaml` to customize:
- Model provider and settings
- Team configurations
- Parallelization settings
- Logging levels
- Error handling behavior

```bash
nano config.yaml
```

## Running the Orchestrator

### Option 1: Dry Run (Recommended First)

Preview the execution plan without actually running anything:

```bash
python orchestrator.py --dry-run
```

This will show you:
- All phases and teams
- Dependencies between teams
- Estimated duration
- Execution order

### Option 2: Full Automated Execution

Run the complete workflow from start to finish:

```bash
python orchestrator.py
```

The orchestrator will:
1. Execute teams in proper dependency order
2. Run parallel teams where possible
3. Track progress and save checkpoints
4. Handle errors and rollbacks
5. Display real-time status updates

### Option 3: Phase-by-Phase Execution

Execute one phase at a time for more control:

```bash
# Phase 1: Foundation (Security)
python orchestrator.py --phase 1

# Phase 2: Core Services (Container + Monitoring)
python orchestrator.py --phase 2

# Phase 3: Kubernetes
python orchestrator.py --phase 3

# And so on...
```

### Option 4: Resume from Checkpoint

If execution stops or fails, resume from where you left off:

```bash
# Resume from last checkpoint
python orchestrator.py --resume

# Or resume from a specific team
python orchestrator.py --resume-from team_delta
```

## Monitoring Progress

### Real-Time Status

```bash
# Check current status
python orchestrator.py --status
```

Output example:
```
┌────────────────────┬────────┐
│ Metric             │ Value  │
├────────────────────┼────────┤
│ Total Teams        │ 12     │
│ Completed          │ 3      │
│ Running            │ 2      │
│ Failed             │ 0      │
│ Pending            │ 7      │
│ Progress           │ 25.0%  │
└────────────────────┴────────┘
```

### View Logs

```bash
# Main orchestrator log
tail -f logs/orchestrator.log

# Team-specific logs
tail -f logs/team_alpha.log
tail -f logs/team_bravo.log

# All logs
tail -f logs/*.log
```

## Error Handling & Recovery

### Rollback to Previous Phase

```bash
# Rollback to Phase 3
python orchestrator.py --rollback 3
```

### Nuclear Reset (Full Server Rebuild)

If things go seriously wrong:

```bash
python orchestrator.py --nuclear-reset
```

**This will:**
1. Prompt you to reset the server in Hetzner console
2. Wait for you to reinstall Ubuntu 24.04
3. Clear all state and checkpoints
4. Prepare for fresh start

Then manually:
1. Log into Hetzner console
2. Reset server
3. Install Ubuntu 24.04 LTS
4. Press Enter in the terminal
5. Re-run the workflow

## Understanding the Workflow

### Phase Breakdown

**Phase 1: Foundation** (2-3 hours)
- Team Alpha: Security Baseline
- No parallelization (critical path)

**Phase 2: Core Services** (2-4 hours)
- Team Bravo: Container Runtime ∥ Team Charlie: Monitoring
- These run in parallel!

**Phase 3: Kubernetes** (4-6 hours)
- Team Delta: Kubernetes Setup
- No parallelization

**Phase 4: Infrastructure** (3-4 hours)
- Team Echo-Network ∥ Team Echo-Storage
- Run in parallel

**Phase 5: Production Ready** (4-6 hours)
- Team Foxtrot ∥ Team Golf-Backup ∥ Team Golf-Performance
- Three-way parallel execution!

**Phase 6: Advanced Features** (4-6 hours)
- Team Charlie-Advanced ∥ Team Golf-MultiTenancy ∥ Team Golf-DevEx
- Three-way parallel execution!

**Total Time:** ~22 hours (vs 29 hours if sequential)

### Team Coordination

Teams automatically:
- Check dependencies before starting
- Wait for prerequisite teams to complete
- Run in parallel when possible
- Signal completion when done
- Save checkpoints after each phase

## Customization

### Modify Team Behavior

Edit `orchestrator.py` to customize:
- System prompts for each team
- Task descriptions
- Priority calculations
- Error handling strategies

### Add Custom Tools

Create tools in `agents/tools/` directory:

```python
# agents/tools/ssh_executor.py
from strands import tool

@tool
def execute_ssh_command(command: str, host: str = "hetzner1") -> str:
    """Execute a command on remote server via SSH"""
    # Implementation here
    pass
```

### Adjust Parallelization

Edit `config.yaml`:

```yaml
workflow:
  max_parallel_teams: 3  # Increase for more parallelization
  enable_parallel_execution: true
```

## Troubleshooting

### Issue: "API key not found"

**Solution:** Check your `.env` file has the correct API key:
```bash
cat .env | grep API_KEY
```

### Issue: "SSH connection failed"

**Solution:** Test SSH manually:
```bash
ssh hetzner1
```

If it fails, check:
- Server is running
- IP address is correct in `~/.ssh/config`
- SSH key has correct permissions: `chmod 600 ~/.ssh/your_key`

### Issue: "Module not found"

**Solution:** Ensure you're in the virtual environment:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Team failed verification"

**Solution:**
1. Check team log: `cat logs/team_<name>.log`
2. SSH to server and manually verify: `ssh hetzner1`
3. Review the step documentation: `docs/steps/step-XX-*.md`
4. Fix issues manually, then resume

### Issue: "Workflow stuck"

**Solution:**
1. Check status: `python orchestrator.py --status`
2. View logs: `tail -f logs/orchestrator.log`
3. Kill and resume: Ctrl+C, then `python orchestrator.py --resume`

## Best Practices

1. **Always start with dry-run** to understand the execution plan
2. **Monitor logs** during execution to catch issues early
3. **Take Hetzner snapshots** before starting each phase
4. **Test SSH connectivity** before running the orchestrator
5. **Use checkpoints** - don't skip the state saving
6. **Review verification** results after each team completes
7. **Keep API keys secure** - never commit `.env` file

## Advanced Usage

### Custom Invocation State

Share data across all agents:

```python
from agents.orchestrator import HypervisorOrchestrator

orchestrator = HypervisorOrchestrator()

custom_state = {
    "deployment_id": "prod-2024",
    "environment": "production",
    "custom_param": "value"
}

orchestrator.execute_full_workflow(invocation_state=custom_state)
```

### Programmatic Control

Use the orchestrator as a library:

```python
from agents.orchestrator import HypervisorOrchestrator

# Initialize
orch = HypervisorOrchestrator("agents/config.yaml")

# Execute specific actions
orch.execute_phase(1)
status = orch.get_status()
orch.checkpoint("after_security")

# Resume later
orch.resume_from_team("team_delta")
```

## Next Steps

After successful execution:
1. Review all team logs for warnings
2. Run manual verification on the server
3. Test Kubernetes cluster functionality
4. Deploy a test workload
5. Monitor metrics in Grafana
6. Document any customizations made

## Support & Resources

- **Strands Documentation:** https://strandsagents.com
- **Project README:** `../README.md`
- **Step Documentations:** `../docs/steps/`
- **Team Plan:** `../AGENT_TEAMS_PLAN.md`
- **Workflow Docs:** https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/workflow/

---

**Ready to orchestrate your infrastructure?** 🚀

Run: `python orchestrator.py --dry-run`
