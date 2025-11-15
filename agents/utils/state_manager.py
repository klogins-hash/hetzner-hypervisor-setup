"""
State Manager - Handles workflow state persistence and recovery
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List


class StateManager:
    """Manages workflow state for checkpointing and recovery"""

    def __init__(self, config: Dict):
        """Initialize state manager with configuration"""
        self.config = config
        self.state_config = config.get('state', {})

        # Setup state directory and file
        base_path = Path(config['project']['base_path'])
        self.state_file = base_path / self.state_config.get('state_file', 'state/workflow_state.json')
        self.state_dir = self.state_file.parent

        # Create state directory if it doesn't exist
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state
        self.state: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

        # Load existing state if available
        if self.state_file.exists():
            self._load_state()

    def save_state(self, state_data: Dict[str, Any]):
        """Save current workflow state to disk"""
        if not self.state_config.get('persistence', True):
            return

        # Add timestamp
        state_data['timestamp'] = datetime.now().isoformat()
        state_data['version'] = self.config['project']['version']

        # Backup current state to history
        if self.state_config.get('backup_state', True) and self.state:
            self.history.append(self.state.copy())

        # Update current state
        self.state.update(state_data)

        # Write to file
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    'current': self.state,
                    'history': self.history[-10:]  # Keep last 10 states
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save state: {e}")

    def _load_state(self):
        """Load state from disk"""
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                self.state = data.get('current', {})
                self.history = data.get('history', [])
        except Exception as e:
            print(f"Warning: Failed to load state: {e}")
            self.state = {}
            self.history = []

    def restore_state(self) -> Optional[Dict[str, Any]]:
        """Restore state from checkpoint"""
        if self.state_config.get('restore_on_startup', True) and self.state:
            return self.state
        return None

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from current state"""
        return self.state.get(key, default)

    def set(self, key: str, value: Any):
        """Set value in current state"""
        self.state[key] = value
        self.save_state({key: value})

    def get_last_state(self) -> Optional[Dict[str, Any]]:
        """Get the most recent state"""
        return self.state if self.state else None

    def get_history(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get last n historical states"""
        return self.history[-n:]

    def clear_state(self):
        """Clear all state and history"""
        self.state = {}
        self.history = []

        # Remove state file
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete state file: {e}")

    def checkpoint(self, checkpoint_name: str, data: Dict[str, Any]):
        """Create a named checkpoint"""
        checkpoint_data = {
            'checkpoint_name': checkpoint_name,
            'timestamp': datetime.now().isoformat(),
            **data
        }
        self.save_state(checkpoint_data)

    def restore_checkpoint(self, checkpoint_name: str) -> Optional[Dict[str, Any]]:
        """Restore from a named checkpoint"""
        # Search history for matching checkpoint
        for state in reversed(self.history):
            if state.get('checkpoint_name') == checkpoint_name:
                self.state = state.copy()
                return state

        # Check current state
        if self.state.get('checkpoint_name') == checkpoint_name:
            return self.state

        return None

    def list_checkpoints(self) -> List[str]:
        """List all available checkpoint names"""
        checkpoints = []

        # Check current state
        if 'checkpoint_name' in self.state:
            checkpoints.append(self.state['checkpoint_name'])

        # Check history
        for state in self.history:
            if 'checkpoint_name' in state:
                name = state['checkpoint_name']
                if name not in checkpoints:
                    checkpoints.append(name)

        return checkpoints

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress metrics"""
        return {
            'completed_teams': self.state.get('completed_teams', []),
            'failed_teams': self.state.get('failed_teams', []),
            'current_phase': self.state.get('current_phase'),
            'last_update': self.state.get('timestamp'),
        }

    def mark_team_complete(self, team_id: str):
        """Mark a team as completed"""
        completed = self.state.get('completed_teams', [])
        if team_id not in completed:
            completed.append(team_id)
            self.save_state({'completed_teams': completed})

    def mark_team_failed(self, team_id: str, error: str = ""):
        """Mark a team as failed"""
        failed = self.state.get('failed_teams', [])
        if team_id not in failed:
            failed.append(team_id)
            self.save_state({
                'failed_teams': failed,
                'last_error': error,
                'failed_team': team_id
            })

    def get_completed_teams(self) -> List[str]:
        """Get list of completed teams"""
        return self.state.get('completed_teams', [])

    def get_failed_teams(self) -> List[str]:
        """Get list of failed teams"""
        return self.state.get('failed_teams', [])

    def is_team_completed(self, team_id: str) -> bool:
        """Check if a team has been completed"""
        return team_id in self.state.get('completed_teams', [])

    def is_team_failed(self, team_id: str) -> bool:
        """Check if a team has failed"""
        return team_id in self.state.get('failed_teams', [])
