"""
Audit logging for compliance and debugging.

Logs:
- Pipeline executions
- Data modifications
- User actions
- System events

WHY: Audit logs are essential for:
- Compliance (GDPR, SOX, etc.)
- Debugging pipeline issues
- Security monitoring
- Performance analysis
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from config.pipeline_config import LOG_FILE

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Enterprise audit logger for compliance and monitoring.
    
    Logs structured events with timestamps and metadata.
    """
    
    def __init__(self, log_file: Path = None):
        """
        Initialize audit logger.
        
        Args:
            log_file: Path to audit log file
        """
        self.log_file = log_file or Path(LOG_FILE).parent / "audit.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _write_event(self, event: Dict[str, Any]):
        """
        Write event to audit log.
        
        Args:
            event: Event dictionary
        """
        event["timestamp"] = datetime.now().isoformat()
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
    
    def log_pipeline_start(self, config: Dict[str, Any]):
        """
        Log pipeline execution start.
        
        Args:
            config: Pipeline configuration
        """
        self._write_event({
            "event_type": "pipeline_start",
            "config": config,
        })
        logger.info("Audit: Pipeline started")
    
    def log_pipeline_end(self, status: str, summary: Dict[str, Any]):
        """
        Log pipeline execution end.
        
        Args:
            status: "success" or "failure"
            summary: Execution summary
        """
        self._write_event({
            "event_type": "pipeline_end",
            "status": status,
            "summary": summary,
        })
        logger.info(f"Audit: Pipeline ended with status {status}")
    
    def log_file_processed(
        self,
        filename: str,
        stage: str,
        rows_in: int,
        rows_out: int,
        metadata: Dict[str, Any] = None
    ):
        """
        Log file processing event.
        
        Args:
            filename: Name of file processed
            stage: Pipeline stage
            rows_in: Input row count
            rows_out: Output row count
            metadata: Additional metadata
        """
        self._write_event({
            "event_type": "file_processed",
            "filename": filename,
            "stage": stage,
            "rows_in": rows_in,
            "rows_out": rows_out,
            "metadata": metadata or {},
        })
        logger.debug(f"Audit: Processed {filename} at {stage}")
    
    def log_quarantine(
        self,
        filename: str,
        row_count: int,
        reasons: Dict[str, int]
    ):
        """
        Log data quarantine event.
        
        Args:
            filename: Source filename
            row_count: Number of rows quarantined
            reasons: Dictionary of quarantine reasons and counts
        """
        self._write_event({
            "event_type": "quarantine",
            "filename": filename,
            "row_count": row_count,
            "reasons": reasons,
        })
        logger.warning(f"Audit: Quarantined {row_count} rows from {filename}")
    
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """
        Log error event.
        
        Args:
            error: Exception that occurred
            context: Context information
        """
        self._write_event({
            "event_type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
        })
        logger.error(f"Audit: Error logged - {error}")
    
    def log_quality_metrics(self, metrics: Dict[str, Any]):
        """
        Log quality metrics for monitoring.
        
        Args:
            metrics: Quality metrics dictionary
        """
        self._write_event({
            "event_type": "quality_metrics",
            "metrics": metrics,
        })
        logger.debug("Audit: Quality metrics logged")
    
    def get_recent_events(self, event_type: str = None, limit: int = 100) -> list:
        """
        Retrieve recent audit events.
        
        Args:
            event_type: Filter by event type (None = all types)
            limit: Maximum number of events to return
        
        Returns:
            List of event dictionaries
        """
        if not self.log_file.exists():
            return []
        
        events = []
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event_type is None or event.get("event_type") == event_type:
                        events.append(event)
                except json.JSONDecodeError:
                    continue
        
        # Return most recent events
        return events[-limit:]


# Global audit logger instance
_global_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger."""
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()
    return _global_audit_logger
