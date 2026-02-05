"""
Shared logging utilities for pipeline modules.

Provides:
- Progress tracking with progress bars
- Timing and performance monitoring
- Structured logging with levels
- Error reporting with context
"""

import time
import sys
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List


class ProgressTracker:
    """Track progress of long-running operations."""
    
    def __init__(self, total: int, name: str = "Processing"):
        self.total = total
        self.name = name
        self.current = 0
        self.start_time = None
        self.last_update = 0
    
    def start(self):
        """Start timing."""
        self.start_time = time.time()
        self.current = 0
        self.last_update = 0
    
    def update(self, count: int = 1, force: bool = False):
        """Update progress."""
        self.current = min(self.current + count, self.total)
        
        # Only update display every 0.5 seconds unless forced
        elapsed = time.time() - self.start_time
        if force or (elapsed - self.last_update >= 0.5):
            self._print_progress()
            self.last_update = elapsed
    
    def finish(self):
        """Mark as complete and show final stats."""
        self.current = self.total
        self._print_progress(final=True)
        elapsed = time.time() - self.start_time
        return elapsed
    
    def _print_progress(self, final: bool = False):
        """Print progress bar."""
        if self.total == 0:
            return
        
        percent = (self.current / self.total) * 100
        bar_length = 40
        filled = int(bar_length * self.current / self.total)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        elapsed = time.time() - self.start_time
        
        if self.current > 0 and percent < 100:
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate
            time_str = f"ETA {remaining:.0f}s"
        else:
            time_str = f"{elapsed:.1f}s"
        
        status = f"\r{self.name}: [{bar}] {percent:.1f}% ({self.current}/{self.total}) {time_str}"
        
        if final:
            status += f" - DONE\n"
            sys.stdout.write(status)
            sys.stdout.flush()
        else:
            sys.stdout.write(status)
            sys.stdout.flush()


class Timer:
    """Simple timer for performance monitoring."""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
        print(f"  ✓ {self.name}: {self.elapsed:.2f}s")


@contextmanager
def timer_context(name: str = "Operation"):
    """Context manager for timing a block of code."""
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        print(f"  ✓ {name}: {elapsed:.2f}s")


def print_header(text: str, width: int = 60):
    """Print formatted header."""
    print("\n" + "=" * width)
    print(text)
    print("=" * width + "\n")


def print_section(text: str):
    """Print formatted section header."""
    print(f"\n## {text}\n")


def print_success(text: str):
    """Print success message."""
    print(f"✓ {text}")


def print_warning(text: str):
    """Print warning message."""
    print(f"⚠ {text}")


def print_error(text: str):
    """Print error message."""
    print(f"✗ {text}")


def print_info(text: str):
    """Print info message."""
    print(f"ℹ {text}")


class Logger:
    """Structured logger for pipeline operations."""
    
    def __init__(self, name: str, level: str = "INFO"):
        self.name = name
        self.level = level
        self.messages: List[dict] = []
    
    def info(self, msg: str, **kwargs):
        """Log info message."""
        self._log("INFO", msg, kwargs)
        print_info(msg)
    
    def warning(self, msg: str, **kwargs):
        """Log warning message."""
        self._log("WARNING", msg, kwargs)
        print_warning(msg)
    
    def error(self, msg: str, **kwargs):
        """Log error message."""
        self._log("ERROR", msg, kwargs)
        print_error(msg)
    
    def success(self, msg: str, **kwargs):
        """Log success message."""
        self._log("SUCCESS", msg, kwargs)
        print_success(msg)
    
    def debug(self, msg: str, **kwargs):
        """Log debug message."""
        if self.level in ["DEBUG", "VERBOSE"]:
            self._log("DEBUG", msg, kwargs)
            print(f"🔧 {msg}")
    
    def _log(self, level: str, msg: str, context: dict):
        """Internal logging."""
        self.messages.append({
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": msg,
            "context": context
        })
    
    def get_summary(self) -> dict:
        """Get summary of logged messages."""
        levels = {}
        for msg in self.messages:
            level = msg["level"]
            levels[level] = levels.get(level, 0) + 1
        return levels


def print_stats(stats: dict, name: str = "Statistics"):
    """Print statistics in table format."""
    print(f"\n{name}:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """Format duration to human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"
