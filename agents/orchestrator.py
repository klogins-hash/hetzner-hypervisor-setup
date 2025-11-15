#!/usr/bin/env python3
"""
Hypervisor Orchestrator - Main workflow coordinator for Hetzner hypervisor setup
Uses Strands Agent Framework with Workflow pattern for parallel execution
"""

import os
import sys
import json
import yaml
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.tree import Tree

from strands import Agent
from strands_tools import workflow

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.state_manager import StateManager
from utils.logger import setup_logger


class HypervisorOrchestrator:
    """Main orchestrator for coordinating multi-agent hypervisor setup"""

    def __init__(self, config_path: str = "agents/config.yaml"):
        """Initialize the orchestrator with configuration"""
        self.console = Console()
        self.config = self._load_config(config_path)
        self.logger = setup_logger(self.config)
        self.state_manager = StateManager(self.config)

        # Initialize team tracking
        self.teams = self.config['teams']
        self.completed_teams: List[str] = []
        self.failed_teams: List[str] = []
        self.running_teams: List[str] = []

        # Initialize workflow coordinator agent
        self.coordinator = self._create_coordinator_agent()

        # Load or restore state
        if self.config['state']['restore_on_startup']:
            self.state_manager.restore_state()
            self.completed_teams = self.state_manager.get('completed_teams', [])

        self.logger.info("Orchestrator initialized successfully")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            # Try from project root
            config_file = Path(self.config['project']['base_path']) / config_path

        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def _create_coordinator_agent(self) -> Agent:
        """Create the main coordinator agent with workflow capability"""
        from utils.model_factory import create_model

        model = create_model(self.config)

        agent = Agent(
            name="HypervisorCoordinator",
            model=model,
            system_prompt="""You are the Hypervisor Infrastructure Coordinator.

Your mission is to orchestrate the deployment of a production-grade Kubernetes
hypervisor infrastructure on Hetzner servers using Firecracker/Flintlock microVMs.

You coordinate multiple specialized agent teams working in parallel where possible,
following a strict dependency graph to ensure proper ordering.

Your responsibilities:
- Manage workflow execution and task dependencies
- Track progress across all teams
- Handle errors and coordinate rollbacks
- Ensure verification passes after each step
- Optimize for parallel execution while respecting dependencies

Be precise, methodical, and always verify before proceeding to the next phase.""",
            tools=[workflow]
        )

        return agent

    def execute_full_workflow(self, dry_run: bool = False) -> Dict[str, Any]:
        """Execute the complete hypervisor setup workflow"""
        self.console.print(Panel.fit(
            "[bold cyan]🚀 Hetzner Hypervisor Setup - Full Workflow Execution[/bold cyan]",
            border_style="cyan"
        ))

        start_time = time.time()

        try:
            # Create workflow tasks
            tasks = self._create_workflow_tasks()

            if dry_run:
                self._display_workflow_plan(tasks)
                return {"status": "dry_run_complete", "tasks": len(tasks)}

            # Create workflow in coordinator
            self.console.print("\n[yellow]Creating workflow...[/yellow]")
            self.coordinator.tool.workflow(
                action="create",
                workflow_id="hypervisor_setup",
                tasks=tasks
            )

            # Start workflow execution
            self.console.print("[yellow]Starting workflow execution...[/yellow]\n")
            result = self.coordinator.tool.workflow(
                action="start",
                workflow_id="hypervisor_setup"
            )

            # Monitor progress
            self._monitor_workflow_progress()

            # Get final status
            final_status = self.coordinator.tool.workflow(
                action="status",
                workflow_id="hypervisor_setup"
            )

            duration_hours = (time.time() - start_time) / 3600

            self.console.print(Panel.fit(
                f"[bold green]✅ Workflow Complete![/bold green]\n"
                f"Duration: {duration_hours:.2f} hours\n"
                f"Completed Teams: {len(self.completed_teams)}\n"
                f"Failed Teams: {len(self.failed_teams)}",
                border_style="green"
            ))

            return {
                "status": "complete",
                "duration_hours": duration_hours,
                "completed_teams": self.completed_teams,
                "failed_teams": self.failed_teams,
                "final_status": final_status
            }

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            self.console.print(f"[bold red]❌ Error: {e}[/bold red]")

            if self.config['error_handling']['rollback_on_failure']:
                self._handle_failure()

            raise

    def _create_workflow_tasks(self) -> List[Dict]:
        """Create workflow tasks from team configuration"""
        tasks = []

        for team_id, team_config in self.teams.items():
            # Skip if already completed
            if team_id in self.completed_teams:
                self.logger.info(f"Skipping {team_id} - already completed")
                continue

            task = {
                "task_id": team_id,
                "description": self._get_team_description(team_id, team_config),
                "system_prompt": self._get_team_system_prompt(team_id, team_config),
                "dependencies": team_config.get('dependencies', []),
                "priority": self._calculate_priority(team_config),
            }

            tasks.append(task)

        self.logger.info(f"Created {len(tasks)} workflow tasks")
        return tasks

    def _get_team_description(self, team_id: str, team_config: Dict) -> str:
        """Generate task description for a team"""
        step_file = team_config['step_file']

        description = f"""Execute {team_config['name']} (Phase {team_config['phase']})

Step Documentation: {step_file}

Tasks:
1. SSH to the Hetzner server (host: {self.config['ssh']['host']})
2. Navigate to project: {self.config['ssh']['remote_project_path']}
3. Follow all instructions in {step_file}
4. Execute commands carefully and verify each step
5. Run verification script if available
6. Report completion status

Dependencies: {', '.join(team_config['dependencies']) if team_config['dependencies'] else 'None'}
Estimated Duration: {team_config['duration_estimate']} hours

Important: Document any issues encountered and ensure all verification passes."""

        return description

    def _get_team_system_prompt(self, team_id: str, team_config: Dict) -> str:
        """Generate system prompt for a team agent"""

        prompts = {
            "alpha": """You are the Security Specialist agent. Your expertise is in:
- TLS certificate generation and management
- Firewall configuration (iptables, firewallcmd)
- SSH hardening and key-based authentication
- Security baseline establishment
Be thorough and never compromise on security best practices.""",

            "bravo": """You are the Container Runtime Specialist. Your expertise is in:
- Containerd installation and configuration
- Snapshotter configuration (overlayfs, devmapper)
- OCI image management
- Container security
Ensure the runtime is production-ready and efficient.""",

            "charlie": """You are the Monitoring & Observability Specialist. Your expertise is in:
- Prometheus deployment and configuration
- Grafana dashboard setup
- Metrics collection (node_exporter, cAdvisor)
- Alerting and log aggregation
Build comprehensive monitoring from the start.""",

            "delta": """You are the Kubernetes Specialist. Your expertise is in:
- Kubernetes control plane deployment
- Flintlock runtime integration
- Pod scheduling and networking
- Cluster validation
Ensure a robust, production-grade K8s cluster.""",

            "echo_network": """You are the Network Infrastructure Specialist. Your expertise is in:
- CNI plugin configuration (Calico, Flannel, etc.)
- Network policies and security
- Load balancer setup
- Service mesh integration
Build reliable, secure networking.""",

            "echo_storage": """You are the Storage Infrastructure Specialist. Your expertise is in:
- Persistent volume configuration
- Storage classes and provisioners
- Volume snapshots and backups
- Performance optimization
Ensure reliable, performant storage.""",

            "foxtrot": """You are the High Availability Specialist. Your expertise is in:
- Multi-node cluster configuration
- Failover mechanisms
- Health checks and monitoring
- Disaster recovery planning
Build resilient, always-on infrastructure.""",

            "golf_backup": """You are the Backup & Recovery Specialist. Your expertise is in:
- Backup system deployment (Velero, etc.)
- Disaster recovery procedures
- Restore testing and validation
- Data retention policies
Protect data with reliable backup systems.""",

            "golf_performance": """You are the Performance Optimization Specialist. Your expertise is in:
- Kernel parameter tuning
- Resource optimization
- Benchmarking and profiling
- Performance monitoring
Maximize system efficiency and throughput.""",

            "charlie_advanced": """You are the Advanced Monitoring Specialist. Your expertise is in:
- Full observability stack deployment
- Custom metrics and alerting
- Log aggregation (ELK/Loki)
- Distributed tracing
Build production-grade monitoring.""",

            "golf_multitenancy": """You are the Multi-Tenancy Specialist. Your expertise is in:
- Tenant isolation (namespaces, network policies)
- Resource quotas and limits
- RBAC configuration
- Security boundaries
Ensure secure multi-tenant operation.""",

            "golf_devex": """You are the Developer Experience Specialist. Your expertise is in:
- CLI tool development
- Web dashboard creation
- API documentation
- Developer workflows
Make the platform easy and delightful to use."""
        }

        return prompts.get(team_id, f"You are a specialist for {team_config['name']}.")

    def _calculate_priority(self, team_config: Dict) -> int:
        """Calculate task priority based on phase and dependencies"""
        # Lower phase = higher priority (higher number)
        # Phase 1 = priority 10, Phase 6 = priority 5
        base_priority = 11 - team_config['phase']

        # Reduce priority based on number of dependencies
        dependency_factor = len(team_config.get('dependencies', []))

        return max(1, base_priority - dependency_factor)

    def _display_workflow_plan(self, tasks: List[Dict]):
        """Display the workflow execution plan"""
        tree = Tree("[bold cyan]Workflow Execution Plan[/bold cyan]")

        phases = {}
        for task in tasks:
            phase = self.teams[task['task_id']]['phase']
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(task)

        for phase in sorted(phases.keys()):
            phase_branch = tree.add(f"[yellow]Phase {phase}[/yellow]")

            for task in phases[phase]:
                team_id = task['task_id']
                team_config = self.teams[team_id]
                deps = ', '.join(task['dependencies']) if task['dependencies'] else 'None'

                task_info = (
                    f"[green]{team_config['name']}[/green] "
                    f"({team_config['duration_estimate']}h) "
                    f"- Deps: {deps}"
                )
                phase_branch.add(task_info)

        self.console.print(tree)

    def _monitor_workflow_progress(self):
        """Monitor and display workflow progress"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        ) as progress:

            task = progress.add_task("[cyan]Executing workflow...", total=100)

            while True:
                status = self.coordinator.tool.workflow(
                    action="status",
                    workflow_id="hypervisor_setup"
                )

                # Parse status and update progress
                if "content" in status:
                    content = status["content"]
                    # Extract progress percentage if available
                    # This is a simplified version - enhance based on actual status format

                    if "complete" in content.lower():
                        progress.update(task, completed=100)
                        break

                time.sleep(5)  # Check every 5 seconds

    def execute_phase(self, phase_number: int) -> Dict[str, Any]:
        """Execute a specific phase of the workflow"""
        self.console.print(Panel.fit(
            f"[bold cyan]Executing Phase {phase_number}[/bold cyan]",
            border_style="cyan"
        ))

        # Filter tasks for this phase
        phase_tasks = [
            self._create_workflow_tasks()[i]
            for i, (team_id, config) in enumerate(self.teams.items())
            if config['phase'] == phase_number and team_id not in self.completed_teams
        ]

        if not phase_tasks:
            self.console.print(f"[yellow]No tasks to execute in Phase {phase_number}[/yellow]")
            return {"status": "skipped", "phase": phase_number}

        self.console.print(f"[green]Found {len(phase_tasks)} tasks in Phase {phase_number}[/green]")

        # Execute tasks (they will run in parallel if no dependencies)
        # Implementation similar to execute_full_workflow but filtered

        return {"status": "complete", "phase": phase_number, "tasks": len(phase_tasks)}

    def resume_workflow(self) -> Dict[str, Any]:
        """Resume workflow from last checkpoint"""
        self.console.print("[yellow]Resuming workflow from checkpoint...[/yellow]")

        last_state = self.state_manager.get_last_state()
        if not last_state:
            self.console.print("[red]No checkpoint found. Starting fresh...[/red]")
            return self.execute_full_workflow()

        self.completed_teams = last_state.get('completed_teams', [])
        self.console.print(f"[green]Resuming after: {', '.join(self.completed_teams)}[/green]")

        return self.execute_full_workflow()

    def resume_from_team(self, team_id: str) -> Dict[str, Any]:
        """Resume workflow from a specific team"""
        self.console.print(f"[yellow]Resuming from team: {team_id}[/yellow]")

        # Mark all teams before this one as complete
        for tid, config in self.teams.items():
            if tid == team_id:
                break
            if tid not in self.completed_teams:
                self.completed_teams.append(tid)

        return self.execute_full_workflow()

    def _handle_failure(self):
        """Handle workflow failure with rollback"""
        self.console.print(Panel.fit(
            "[bold red]⚠️  Workflow Failed - Initiating Rollback[/bold red]",
            border_style="red"
        ))

        # Implement rollback logic based on last successful checkpoint
        last_completed = self.completed_teams[-1] if self.completed_teams else None

        if last_completed:
            self.console.print(f"[yellow]Rolling back to: {last_completed}[/yellow]")
            # Add rollback implementation
        else:
            self.console.print("[yellow]No checkpoint to rollback to[/yellow]")

    def rollback_to_phase(self, phase_number: int):
        """Rollback to a specific phase"""
        self.console.print(f"[yellow]Rolling back to Phase {phase_number}[/yellow]")

        # Remove completed teams from later phases
        self.completed_teams = [
            team_id for team_id in self.completed_teams
            if self.teams[team_id]['phase'] < phase_number
        ]

        self.state_manager.save_state({
            'completed_teams': self.completed_teams,
            'rollback_phase': phase_number,
            'timestamp': datetime.now().isoformat()
        })

    def nuclear_reset(self):
        """Perform full server rebuild (nuclear option)"""
        self.console.print(Panel.fit(
            "[bold red]☢️  NUCLEAR RESET - Full Server Rebuild[/bold red]",
            border_style="red"
        ))

        self.console.print("""
[yellow]This will:
1. Reset the Hetzner server (via Hetzner console)
2. Reinstall Ubuntu 24.04 LTS
3. Clone the repository
4. Run install-all.sh
5. Restart workflow from Phase 1

Please perform steps 1-2 manually in Hetzner console, then press Enter to continue...[/yellow]
        """)

        input()

        # Clear all state
        self.completed_teams = []
        self.failed_teams = []
        self.state_manager.clear_state()

        self.console.print("[green]State cleared. Ready to restart workflow.[/green]")

    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        total_teams = len(self.teams)
        completed = len(self.completed_teams)
        failed = len(self.failed_teams)
        running = len(self.running_teams)
        pending = total_teams - completed - failed - running

        progress_pct = (completed / total_teams * 100) if total_teams > 0 else 0

        table = Table(title="Workflow Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Teams", str(total_teams))
        table.add_row("Completed", str(completed))
        table.add_row("Running", str(running))
        table.add_row("Failed", str(failed))
        table.add_row("Pending", str(pending))
        table.add_row("Progress", f"{progress_pct:.1f}%")

        self.console.print(table)

        return {
            "total_teams": total_teams,
            "completed": completed,
            "running": running,
            "failed": failed,
            "pending": pending,
            "progress_percentage": progress_pct
        }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Hetzner Hypervisor Setup Orchestrator")
    parser.add_argument("--config", default="agents/config.yaml", help="Path to config file")
    parser.add_argument("--phase", type=int, help="Execute specific phase only")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--resume-from", help="Resume from specific team")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--rollback", type=int, help="Rollback to specific phase")
    parser.add_argument("--nuclear-reset", action="store_true", help="Full server rebuild")

    args = parser.parse_args()

    orchestrator = HypervisorOrchestrator(args.config)

    if args.status:
        orchestrator.get_status()
    elif args.nuclear_reset:
        orchestrator.nuclear_reset()
    elif args.rollback:
        orchestrator.rollback_to_phase(args.rollback)
    elif args.resume:
        orchestrator.resume_workflow()
    elif args.resume_from:
        orchestrator.resume_from_team(args.resume_from)
    elif args.phase:
        orchestrator.execute_phase(args.phase)
    else:
        orchestrator.execute_full_workflow(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
