# Strands Agent Framework - Architecture Overview

## System Design

This multi-agent system uses the **Workflow pattern** from Strands Agents SDK to orchestrate a complex, dependency-heavy infrastructure deployment with parallel execution optimization.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                        │
│  - Workflow coordination                                     │
│  - Dependency resolution                                     │
│  - State management                                          │
│  - Progress tracking                                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─► Phase 1: Foundation
                 │   └─► Team Alpha (Security)
                 │
                 ├─► Phase 2: Core Services (Parallel)
                 │   ├─► Team Bravo (Containers)
                 │   └─► Team Charlie (Monitoring)
                 │
                 ├─► Phase 3: Kubernetes
                 │   └─► Team Delta (K8s Setup)
                 │
                 ├─► Phase 4: Infrastructure (Parallel)
                 │   ├─► Team Echo-Network
                 │   └─► Team Echo-Storage
                 │
                 ├─► Phase 5: Production Ready (3x Parallel)
                 │   ├─► Team Foxtrot (HA)
                 │   ├─► Team Golf-Backup
                 │   └─► Team Golf-Performance
                 │
                 └─► Phase 6: Advanced Features (3x Parallel)
                     ├─► Team Charlie-Advanced
                     ├─► Team Golf-MultiTenancy
                     └─► Team Golf-DevEx
```

## Component Breakdown

### 1. Orchestrator (`orchestrator.py`)
**Role:** Central coordinator using Strands Workflow tool

**Responsibilities:**
- Create workflow tasks from team configuration
- Manage task dependencies (DAG)
- Execute teams in parallel where possible
- Track state and checkpoints
- Handle errors and rollbacks
- Monitor progress and display status

**Key Methods:**
- `execute_full_workflow()` - Run complete deployment
- `execute_phase(n)` - Run specific phase
- `resume_workflow()` - Resume from checkpoint
- `rollback_to_phase(n)` - Rollback to earlier state
- `nuclear_reset()` - Full server rebuild

### 2. Team Agents

Each team is a specialized agent with:
- **System Prompt**: Expertise definition (security, containers, K8s, etc.)
- **Task Description**: What to do (references step documentation)
- **Dependencies**: Which teams must complete first
- **Tools**: SSH execution, verification, coordination
- **State**: Shared via invocation_state

**Team Specializations:**
- **Alpha**: Security (TLS, firewall, SSH hardening)
- **Bravo**: Container runtime (containerd, snapshotter)
- **Charlie**: Monitoring (Prometheus, Grafana, basic & advanced)
- **Delta**: Kubernetes (control plane, Flintlock)
- **Echo**: Infrastructure (network CNI + storage PV)
- **Foxtrot**: High availability (multi-node, failover)
- **Golf**: Operations (backup, performance, multi-tenancy, DevEx)

### 3. Utilities (`utils/`)

**StateManager** (`state_manager.py`):
- Persist workflow state to `state/workflow_state.json`
- Track completed/failed teams
- Support checkpointing and recovery
- Maintain history of last 10 states

**Logger** (`logger.py`):
- Orchestrator-level logging
- Per-team logging (`logs/team_*.log`)
- Configurable levels (DEBUG, INFO, WARNING, ERROR)
- Rich console formatting support

**ModelFactory** (`model_factory.py`):
- Create LLM instances from config
- Support OpenAI, Anthropic, Bedrock, Ollama
- Load API keys from environment
- Configure temperature, max_tokens, etc.

### 4. Configuration (`config.yaml`)

**Structure:**
```yaml
project: {...}        # Project metadata
ssh: {...}           # SSH connection settings
models: {...}        # LLM provider configs
teams: {...}         # Team definitions with dependencies
workflow: {...}      # Workflow execution settings
execution: {...}     # Retry, checkpoint settings
logging: {...}       # Log levels and files
monitoring: {...}    # Metrics tracking
error_handling: {...} # Rollback, continue-on-error
verification: {...}  # Auto-verify settings
state: {...}         # State persistence
notifications: {...} # Optional webhooks
```

### 5. Tools (`tools/`)

**Placeholder for:**
- SSH command execution
- Remote file operations
- Verification script running
- Team coordination signals
- Hetzner API integration

**Future Implementation:**
```python
@tool
def execute_remote_command(cmd: str, host: str) -> str:
    """Execute command via SSH"""

@tool
def verify_step(step_number: int) -> bool:
    """Run verification script"""

@tool
def signal_completion(team_id: str, status: str):
    """Signal team completion"""
```

## Data Flow

### 1. Initialization
```
User runs orchestrator.py
  ↓
Load config.yaml
  ↓
Setup logger, state_manager
  ↓
Create model from factory
  ↓
Initialize coordinator agent with workflow tool
  ↓
Restore previous state (if exists)
```

### 2. Workflow Execution
```
Create workflow tasks from team config
  ↓
Filter out completed teams
  ↓
Generate task descriptions + system prompts
  ↓
Calculate priorities based on phase/deps
  ↓
Submit tasks to workflow tool
  ↓
Workflow tool resolves dependencies
  ↓
Execute tasks (parallel where possible)
  ↓
Monitor progress, update state
  ↓
Save checkpoints after each phase
```

### 3. State Management
```
Task starts → Update running_teams
  ↓
Task completes → Add to completed_teams
  ↓
Save to state/workflow_state.json
  ↓
Backup to history
  ↓
Can restore on failure/restart
```

### 4. Error Handling
```
Task fails → Log error
  ↓
Check error_handling.continue_on_error
  ↓
If false: Stop workflow
  ↓
If rollback_on_failure: Revert changes
  ↓
User can:
  - Resume from checkpoint
  - Rollback to phase
  - Nuclear reset (full rebuild)
```

## Parallel Execution Strategy

### Dependency Graph (DAG)
```
Alpha (Phase 1) - No deps
  ↓
├─► Bravo (Phase 2) - Depends on Alpha
│   ∥ (runs parallel with Charlie)
└─► Charlie (Phase 2) - Depends on Alpha
     ↓
Delta (Phase 3) - Depends on Bravo + Charlie
  ↓
├─► Echo-Network (Phase 4) - Depends on Delta
│   ∥ (runs parallel)
└─► Echo-Storage (Phase 4) - Depends on Delta
     ↓
├─► Foxtrot (Phase 5) - Depends on Echo-*
│   ∥ (runs parallel with Golf-Backup + Golf-Perf)
├─► Golf-Backup (Phase 5) - Depends on Echo-*
│   ∥
└─► Golf-Performance (Phase 5) - Depends on Echo-*
     ↓
├─► Charlie-Advanced (Phase 6) - Depends on Phase 5
│   ∥ (runs parallel with Golf-Multi + Golf-DevEx)
├─► Golf-MultiTenancy (Phase 6) - Depends on Phase 5
│   ∥
└─► Golf-DevEx (Phase 6) - Depends on Phase 5
```

### Time Optimization
- **Sequential**: 3 + 4 + 6 + 4 + 6 + 6 = ~29 hours
- **Parallel**: 3 + max(2,2) + 6 + max(3,3) + max(4,3,3) + max(4,4,4) = ~22 hours
- **Savings**: 24%+ reduction

### Controlled Parallelism
```yaml
workflow:
  max_parallel_teams: 3  # Limit concurrent execution
  enable_parallel_execution: true
```

Benefits:
- Resource management (don't overwhelm server)
- API rate limiting (LLM calls)
- Easier monitoring and debugging

## Shared Context Pattern

### Invocation State
All agents share context via `invocation_state`:

```python
shared_state = {
    "ssh_host": "hetzner1",
    "user": "root",
    "project_path": "/root/hetzner-hypervisor-setup",
    "current_phase": 2,
    "completed_teams": ["alpha", "bravo"],
    "verification_results": {
        "alpha": {"passed": true, "time": "2024-01-15T10:30:00"},
        "bravo": {"passed": true, "time": "2024-01-15T12:45:00"}
    },
    "ssh_connection": connection_pool_object,
    "deployment_id": "prod-2024-01-15"
}
```

### Benefits
- Agents can access shared infrastructure state
- No data in LLM prompts (security)
- Connection pooling for efficiency
- Cross-team coordination

## Monitoring & Observability

### Logs
```
logs/
├── orchestrator.log          # Main workflow log
├── team_alpha.log           # Security team
├── team_bravo.log           # Container team
├── team_charlie.log         # Monitoring team
├── team_delta.log           # K8s team
├── team_echo_network.log    # Network team
├── team_echo_storage.log    # Storage team
├── team_foxtrot.log         # HA team
├── team_golf_backup.log     # Backup team
├── team_golf_performance.log # Performance team
├── team_charlie_advanced.log # Advanced monitoring
├── team_golf_multitenancy.log # Multi-tenancy
└── team_golf_devex.log      # DevEx team
```

### State Snapshots
```
state/
└── workflow_state.json
    ├── current: {...}        # Latest state
    └── history: [...]        # Last 10 states
```

### Metrics (Optional)
```
logs/
└── metrics.json
    └── {
        "total_duration": 22.5,
        "teams": [
            {"id": "alpha", "duration": 2.3, "status": "complete"},
            {"id": "bravo", "duration": 2.1, "status": "complete"},
            ...
        ]
    }
```

## Security Considerations

1. **API Keys**: Stored in `.env`, never in code or config
2. **SSH Keys**: Use SSH agent or key-based auth
3. **Secrets**: Never logged or passed to LLM prompts
4. **State Files**: Local only, not committed to git
5. **Logs**: May contain sensitive data, keep secure

## Extensibility

### Adding New Teams
1. Add to `config.yaml` teams section
2. Define dependencies
3. Create step documentation in `docs/steps/`
4. Add system prompt in `orchestrator.py`
5. Test in isolation

### Adding Custom Tools
1. Create tool in `agents/tools/`
2. Use `@tool` decorator
3. Add to agent's tool list
4. Access via `agent.tool.your_tool()`

### Integrating External Services
1. Add credentials to `.env`
2. Create client in utils
3. Pass via invocation_state
4. Use in tool implementations

## Best Practices

1. **Always dry-run first**: Understand the plan
2. **Monitor logs**: Catch issues early
3. **Checkpoint frequently**: Enable recovery
4. **Test SSH**: Verify connectivity
5. **Incremental phases**: Don't rush
6. **Verify results**: Check after each team
7. **Document customizations**: Track changes

## Performance Tuning

### Model Selection
- **OpenAI GPT-4**: Best general capability
- **Anthropic Claude**: Best for infrastructure/operations
- **AWS Bedrock**: Best for enterprise/compliance
- **Ollama**: Best for local/privacy

### Temperature Settings
- Lower (0.0-0.2): Deterministic, infrastructure tasks
- Medium (0.3-0.7): Creative problem-solving
- Higher (0.8-1.0): Brainstorming, exploration

### Parallel Teams
- More parallel: Faster but harder to debug
- Less parallel: Slower but more stable
- Monitor resource usage

## Future Enhancements

1. **Real-time Web Dashboard**: Track progress visually
2. **Slack/Discord Integration**: Notifications
3. **Metrics Export**: Prometheus/Grafana
4. **A2A Protocol**: Direct agent-to-agent communication
5. **Tool Provider Pattern**: Managed tool lifecycle
6. **Multi-Server Support**: Deploy to multiple servers
7. **Rollback Automation**: Automatic recovery
8. **Performance Profiling**: Optimize bottlenecks

---

**Architecture designed for:**
- ✅ Scalability (12+ teams, 6 phases)
- ✅ Reliability (checkpoints, rollbacks)
- ✅ Efficiency (parallel execution)
- ✅ Observability (comprehensive logging)
- ✅ Maintainability (clear structure, documentation)
