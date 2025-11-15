"""
Logger - Enhanced logging for workflow orchestration
"""

import logging
import sys
from pathlib import Path
from typing import Dict
from datetime import datetime


def setup_logger(config: Dict) -> logging.Logger:
    """Setup and configure logger based on config"""
    log_config = config.get('logging', {})

    # Create logs directory
    base_path = Path(config['project']['base_path'])
    log_file = base_path / log_config.get('file', 'logs/orchestrator.log')
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger('HypervisorOrchestrator')
    logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatters
    formatter = logging.Formatter(
        log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (if enabled)
    if log_config.get('console_output', True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_config.get('level', 'INFO')))

        if log_config.get('rich_formatting', False):
            # Use simple formatter for console when using rich
            console_formatter = logging.Formatter('%(message)s')
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    logger.info(f"Logger initialized - Level: {log_config.get('level', 'INFO')}")
    logger.info(f"Log file: {log_file}")

    return logger


class TeamLogger:
    """Logger for individual team agents"""

    def __init__(self, team_id: str, config: Dict):
        """Initialize team-specific logger"""
        self.team_id = team_id
        self.config = config

        # Create team-specific log file
        base_path = Path(config['project']['base_path'])
        log_file = base_path / f"logs/team_{team_id}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(f'Team.{team_id}')
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self.logger.handlers.clear()

        # File handler
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def info(self, message: str):
        """Log info message"""
        self.logger.info(f"[{self.team_id}] {message}")

    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(f"[{self.team_id}] {message}")

    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(f"[{self.team_id}] {message}")

    def error(self, message: str):
        """Log error message"""
        self.logger.error(f"[{self.team_id}] {message}")

    def critical(self, message: str):
        """Log critical message"""
        self.logger.critical(f"[{self.team_id}] {message}")
