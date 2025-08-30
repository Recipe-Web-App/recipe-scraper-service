"""Database monitoring and connection health service.

Provides background monitoring of database connectivity with automatic reconnection
attempts and health status tracking.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.db.session import check_database_health

_log = get_logger(__name__)


class DatabaseMonitor:
    """Background service for monitoring database health and connection status."""

    def __init__(self, check_interval: int = 30) -> None:
        """Initialize the database monitor.

        Args:
            check_interval: Seconds between health checks (default: 30)
        """
        self.check_interval = check_interval
        self.is_running = False
        self.task: asyncio.Task[None] | None = None
        self.last_check_time: datetime | None = None
        self.last_success_time: datetime | None = None
        self.consecutive_failures = 0
        self.is_healthy = False

    async def start(self) -> None:
        """Start the background database monitoring task."""
        if self.is_running:
            _log.warning("Database monitor is already running")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._monitor_loop())
        _log.info(
            "Database monitor started with {} second intervals", self.check_interval
        )

    async def stop(self) -> None:
        """Stop the background database monitoring task."""
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

        _log.info("Database monitor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop that runs database health checks."""
        _log.debug("Database monitor loop started")

        while self.is_running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                _log.debug("Database monitor loop cancelled")
                break
            except Exception as e:
                _log.error(
                    "Unexpected error in database monitor loop: {} ({})",
                    str(e),
                    type(e).__name__,
                    exc_info=True,
                )
                # Continue monitoring after unexpected errors
                await asyncio.sleep(min(self.check_interval, 10))

    async def _perform_health_check(self) -> None:
        """Perform a single database health check and update status."""
        self.last_check_time = datetime.now(tz=UTC)

        try:
            is_healthy = await check_database_health()

            if is_healthy:
                if not self.is_healthy:
                    # Database has recovered
                    _log.info(
                        "Database connection recovered after {} consecutive failures",
                        self.consecutive_failures,
                    )

                self.is_healthy = True
                self.last_success_time = self.last_check_time
                self.consecutive_failures = 0
            else:
                if self.is_healthy:
                    # Database became unhealthy
                    _log.warning("Database connection lost")

                self.is_healthy = False
                self.consecutive_failures += 1

                # Log periodic status updates for prolonged outages
                # Every ~5 minutes at 30s intervals
                if self.consecutive_failures % 10 == 0:
                    _log.warning(
                        "Database still unavailable after {} consecutive checks "
                        "(~{} minutes)",
                        self.consecutive_failures,
                        (self.consecutive_failures * self.check_interval) // 60,
                    )

        except Exception as e:
            _log.error(
                "Database health check failed with unexpected error: {} ({})",
                str(e),
                type(e).__name__,
                exc_info=True,
            )
            self.is_healthy = False
            self.consecutive_failures += 1

    def get_status(self) -> dict[str, Any]:
        """Get the current database monitoring status.

        Returns:
            Dict containing database health status and monitoring metrics
        """
        return {
            "is_healthy": self.is_healthy,
            "is_monitoring": self.is_running,
            "last_check_time": (
                self.last_check_time.isoformat() if self.last_check_time else None
            ),
            "last_success_time": (
                self.last_success_time.isoformat() if self.last_success_time else None
            ),
            "consecutive_failures": self.consecutive_failures,
            "check_interval_seconds": self.check_interval,
            "uptime_status": (
                "healthy"
                if self.is_healthy
                else f"degraded ({self.consecutive_failures} failures)"
            ),
        }


# Global database monitor instance
_database_monitor = DatabaseMonitor()


async def start_database_monitoring() -> None:
    """Start the global database monitoring service."""
    await _database_monitor.start()


async def stop_database_monitoring() -> None:
    """Stop the global database monitoring service."""
    await _database_monitor.stop()


def get_database_monitor_status() -> dict[str, Any]:
    """Get the current status of the database monitor.

    Returns:
        Dict containing database health status and monitoring metrics
    """
    return _database_monitor.get_status()
