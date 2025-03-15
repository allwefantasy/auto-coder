"""
Module providing a singleton class to track run context (terminal or web mode).
"""
from enum import Enum, auto
from typing import Optional


class RunMode(Enum):
    """Enum representing different run modes for Auto-Coder."""
    TERMINAL = auto()
    WEB = auto()


class RunContext:
    """
    Singleton class to track whether Auto-Coder is running in terminal or web mode.
    
    Usage:
        from autocoder.run_context import get_run_context
        
        # Get current mode
        context = get_run_context()
        if context.mode == RunMode.WEB:
            # Do web-specific things
        
        # Set mode
        context.set_mode(RunMode.WEB)
    """
    _instance: Optional['RunContext'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RunContext, cls).__new__(cls)
            cls._instance._mode = RunMode.TERMINAL  # Default to terminal mode
        return cls._instance
    
    @property
    def mode(self) -> RunMode:
        """Get the current run mode."""
        return self._mode
    
    def set_mode(self, mode: RunMode) -> None:
        """Set the current run mode."""
        self._mode = mode
    
    def is_terminal(self) -> bool:
        """Check if running in terminal mode."""
        return self._mode == RunMode.TERMINAL
    
    def is_web(self) -> bool:
        """Check if running in web mode."""
        return self._mode == RunMode.WEB


def get_run_context() -> RunContext:
    """
    Get the singleton RunContext instance.
    
    Returns:
        RunContext: The singleton instance of RunContext
    """
    return RunContext() 