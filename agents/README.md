# Strands Agent Framework Team

This directory contains the Strands Agent Framework implementation for orchestrating the Hetzner hypervisor setup using a multi-agent workflow pattern.

## Architecture Overview

This implementation uses the **Workflow pattern** from Strands Agents SDK, which is optimal for:
- **Structured processes** with clear dependencies
- **Parallel execution** where tasks are independent
- **DAG-based orchestration** (Directed Acyclic Graph)
- **Specialized agent expertise** for different infrastructure domains

## Agent Team Structure

### 🎯 **Orchestrator Agent** (`orchestrator.py`)
The main coordinator that manages the entire workflow, tracking progress, handling failures, and ensuring proper dependency resolution.

### 🔐 **Team Alpha - Security Agent** (`team_alpha.py`)
- **Specialization**: Security baseline, TLS, SSH hardening
- **Phase**: 1 (Foundation)
- **Dependencies**: None (starts immediately)
- **Duration**: 2-3 hours

### 🐳 **Team Bravo - Container Agent** (`team_bravo.py`)
- **Specialization**: Containerd, snapshotter, OCI images
- **Phase**: 2 (Core Services)
- **Dependencies**: Team Alpha
- **Parallel With**: Team Charlie
- **Duration**: 2-4 hours

### 📊 **Team Charlie - Monitoring Agent** (`team_charlie.py`)
- **Specialization**: Prometheus, Grafana, node_exporter
- **Phase**: 2 (Core Services) & 6 (Advanced)
- **Dependencies**: Team Alpha (basic), All teams (advanced)
- **Parallel With**: Team Bravo (Phase 2)
- **Duration**: 2-3 hours (basic), 4-5 hours (advanced)

### ☸️ **Team Delta - Kubernetes Agent** (`team_delta.py`)
- **Specialization**: K8s control plane, Flintlock runtime
- **Phase**: 3 (Foundation)
- **Dependencies**: Team Bravo, Team Charlie
- **Duration**: 4-6 hours

### 🌐 **Team Echo - Infrastructure Agent** (`team_echo.py`)
- **Specialization**: Networking (CNI), Storage (PV/PVC)
- **Phase**: 4 (Infrastructure)
- **Dependencies**: Team Delta
- **Sub-teams**: Echo-1 (Network), Echo-2 (Storage) - can run parallel
- **Duration**: 3-4 hours each

### 🛡️ **Team Foxtrot - HA Agent** (`team_foxtrot.py`)
- **Specialization**: High availability, failover, health checks
- **Phase**: 5 (Production Readiness)
- **Dependencies**: Team Echo (both sub-teams)
- **Parallel With**: Team Golf-1, Golf-2
- **Duration**: 4-6 hours

### ⚡ **Team Golf - Operations Agent** (`team_golf.py`)
- **Specialization**: Backup, performance, multi-tenancy, DevEx
- **Phase**: 5-6 (Production & Advanced)
- **Dependencies**: Varies by sub-team
- **Sub-teams**: Golf-1 (Backup), Golf-2 (Performance), Golf-3 (Multi-tenancy), Golf-4 (DevEx)
- **Duration**: 3-6 hours each

## Workflow Execution Model

```
Phase 1: Foundation (2-3h)
┌─────────────────┐
│  Team Alpha     │ (Security Baseline)
└────────┬────────┘
         │
         ↓
Phase 2: Core Services (Max 2-4h)
┌──────────────┐    ┌──────────────┐
│ Team Bravo   │    │ Team Charlie │
│ (Container)  │    │ (Monitoring) │
└──────┬───────┘    └──────┬───────┘
       └────────┬───────────┘
                ↓
Phase 3: Kubernetes Foundation (4-6h)
┌─────────────────┐
│  Team Delta     │ (K8s Setup)
└────────┬────────┘
         ↓
Phase 4: Infrastructure (Max 3-4h)
┌──────────────┐    ┌──────────────┐
│ Echo-1       │    │ Echo-2       │
│ (Network)    │    │ (Storage)    │
└──────┬───────┘    └──────┬───────┘
       └────────┬───────────┘
                ↓
Phase 5: Production Ready (Max 4-6h)
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Foxtrot  │  │ Golf-1   │  │ Golf-2   │
│ (HA)     │  │ (Backup) │  │ (Perf)   │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     └─────────────┴─────────────┘
                   ↓
Phase 6: Advanced Features (Max 4-6h)
┌──────────┐  ┌──────────┐  ┌──────────┐
│Charlie-2 │  │ Golf-3   │  │ Golf-4   │
│(Full Mon)│  │(MultiTen)│  │ (DevEx)  │
└──────────┘  └──────────┘  └──────────┘
```

**Total Time**: ~22 hours (vs 29 hours sequential)
**Time Savings**: 24%+ through parallel execution

## Key Features

### 1. **Dependency Management**
- Automatic dependency resolution based on task graph
- Parallel execution of independent tasks
- Wait/block mechanisms for dependent tasks

### 2. **State Management**
- Shared invocation_state across all agents
- SSH connection pooling
- Progress tracking and checkpointing
- Rollback capabilities

### 3. **Error Handling**
- Automatic retries with exponential backoff
- Task-level error isolation
- Rollback procedures per step
- Nuclear option: full server rebuild

### 4. **Monitoring & Observability**
- Real-time progress tracking
- Task completion signals
- Duration metrics
- Verification results

## Files Structure

```
agents/
├── README.md                    # This file
├── orchestrator.py              # Main workflow coordinator
├── config.yaml                  # Configuration settings
├── requirements.txt             # Python dependencies
├── team_alpha.py               # Security baseline agent
├── team_bravo.py               # Container runtime agent
├── team_charlie.py             # Monitoring agent
├── team_delta.py               # Kubernetes agent
├── team_echo.py                # Infrastructure agent (network + storage)
├── team_foxtrot.py             # High availability agent
├── team_golf.py                # Operations agent (backup + perf + multi-tenancy + devex)
├── tools/
│   ├── __init__.py
│   ├── ssh_executor.py         # SSH command execution tool
│   ├── verification.py         # Step verification tool
│   └── coordination.py         # Team coordination signals
└── utils/
    ├── __init__.py
    ├── state_manager.py        # Shared state management
    └── logger.py               # Enhanced logging
```

## Quick Start

### Option 1: Docker (Recommended for Production)

```bash
# Navigate to agents directory
cd /Users/franksimpson/CascadeProjects/hetzner-hypervisor-setup/agents

# Configure environment
cp .env.template .env
# Edit .env with your API keys

# Build and run
docker-compose build
docker-compose run --rm orchestrator python orchestrator.py --dry-run
docker-compose run --rm orchestrator python orchestrator.py

# See DOCKER.md for full documentation
```

### Option 2: Native Python

```bash
# Navigate to project
cd /Users/franksimpson/CascadeProjects/hetzner-hypervisor-setup

# Install dependencies
pip install -r agents/requirements.txt

# Configure settings (edit SSH host, API keys, etc.)
nano agents/config.yaml

# Run the orchestrator
python agents/orchestrator.py

# Or run specific phases
python agents/orchestrator.py --phase 1
python agents/orchestrator.py --phase 2-4
python agents/orchestrator.py --resume-from team_delta
```

## Configuration

Edit `config.yaml` to customize:
- SSH connection details
- LLM model providers (OpenAI, Anthropic, etc.)
- Parallelization settings
- Retry policies
- Logging levels

## Usage Examples

### Full Automated Execution
```python
from agents.orchestrator import HypervisorOrchestrator

orchestrator = HypervisorOrchestrator()
results = orchestrator.execute_full_workflow()
print(f"Completed in {results['duration']} hours")
```

### Phase-by-Phase Execution
```python
orchestrator = HypervisorOrchestrator()

# Phase 1: Foundation
orchestrator.execute_phase(1)

# Phase 2: Core Services (parallel)
orchestrator.execute_phase(2)

# Continue...
```

### Recovery from Failure
```python
orchestrator = HypervisorOrchestrator()

# Resume from last checkpoint
orchestrator.resume_workflow()

# Or resume from specific team
orchestrator.resume_from_team('team_delta')
```

## Monitoring Progress

The orchestrator provides real-time updates via:
- Console logging with rich formatting
- Progress percentage tracking
- Task status dashboard
- Completion signals

Example output:
```
✅ [ALPHA] COMPLETE - Phase 1 - Duration: 2.3h - No issues
🚀 [BRAVO] STARTING - Phase 2 - Dependencies: Alpha ✓
🚀 [CHARLIE] STARTING - Phase 2 - Dependencies: Alpha ✓
⏳ [BRAVO] RUNNING - Installing containerd...
⏳ [CHARLIE] RUNNING - Deploying Prometheus...
✅ [BRAVO] COMPLETE - Phase 2 - Duration: 2.1h - No issues
✅ [CHARLIE] COMPLETE - Phase 2 - Duration: 2.0h - No issues
🚀 [DELTA] STARTING - Phase 3 - Dependencies: Bravo ✓, Charlie ✓
```

## Best Practices

1. **Test in dry-run mode first**: `orchestrator.execute_full_workflow(dry_run=True)`
2. **Take snapshots before each phase**: Hetzner console snapshots
3. **Monitor SSH connection**: Ensure stable connectivity
4. **Review logs after each phase**: Check for warnings
5. **Commit changes to git**: After successful phase completion

## Troubleshooting

### Agent Hangs
- Check SSH connectivity: `ssh hetzner1`
- Review agent logs: `tail -f logs/team_*.log`
- Increase timeout settings in `config.yaml`

### Dependency Errors
- Verify previous phase completed: `orchestrator.check_status()`
- Review dependency matrix in AGENT_TEAMS_PLAN.md
- Manual intervention may be needed

### Rollback Needed
```python
orchestrator.rollback_to_phase(3)  # Rollback to Phase 3
orchestrator.nuclear_reset()        # Full server rebuild
```

## Advanced Features

### Custom Tools Integration
Agents can use custom tools for:
- SSH command execution
- File editing on remote server
- Verification script running
- Git operations
- Hetzner API calls

### State Sharing
All agents share context through `invocation_state`:
```python
shared_state = {
    "ssh_host": "hetzner1",
    "user": "root",
    "project_path": "/root/hetzner-hypervisor-setup",
    "current_phase": 2,
    "completed_teams": ["alpha", "bravo"],
    "verification_results": {...}
}
```

### Parallel Optimization
Fine-tune parallelization:
```yaml
parallelization:
  max_concurrent_teams: 3
  phase_2_parallel: true
  phase_4_parallel: true
  phase_5_parallel: true
  phase_6_parallel: true
```

## Contributing

When adding new agents or modifying workflows:
1. Follow the existing agent template pattern
2. Update dependency matrix
3. Add verification steps
4. Document rollback procedures
5. Test in isolation before integration

## Deployment Options

### 🐳 Docker Deployment
**Recommended for:** Production, CI/CD, Team collaboration

**Benefits:**
- Isolated environment
- Reproducible builds
- Easy deployment
- Resource limits
- Version control

**Quick Start:**
```bash
docker-compose build
docker-compose run --rm orchestrator python orchestrator.py --dry-run
```

See **[DOCKER.md](DOCKER.md)** for complete Docker deployment guide.

### 🚀 Firecracker Deployment
**Recommended for:** Local testing, Hypervisor testing, Lightweight isolation

**Benefits:**
- Minimal overhead (5-10MB per VM vs 50-100MB Docker)
- Full VM isolation
- Boot in 100-500ms
- Perfect for testing Flintlock/hypervisor workflows
- Aligned with project's microVM focus

**Quick Start:**
```bash
./firecracker/setup-tap.sh
./firecracker/launch-agent-vm.sh
ssh -i firecracker/ssh/id_rsa ubuntu@172.15.0.2
```

See **[FIRECRACKER.md](FIRECRACKER.md)** for complete Firecracker deployment guide.

### 🐍 Native Python
**Recommended for:** Local development, Quick testing, Custom integration

**Quick Start:**
```bash
pip install -r requirements.txt
python orchestrator.py --dry-run
```

See **[GETTING_STARTED.md](GETTING_STARTED.md)** for native setup guide.

## Support

For issues or questions:
- Check the main project README
- Review AGENT_TEAMS_PLAN.md for team coordination
- Read DOCKER.md for containerized deployment
- Consult Strands documentation: https://strandsagents.com
- Create GitHub issue with logs

---

**Ready to orchestrate your infrastructure deployment!** 🚀
