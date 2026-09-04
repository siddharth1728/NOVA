"""Models for process inspection and supervised termination."""

from pydantic import BaseModel, Field


class ProcessInfo(BaseModel):
    """Structured telemetry describing an active host process."""

    pid: int = Field(description="Process identifier")
    name: str = Field(description="Executable name (e.g. python.exe)")
    exe: str | None = Field(default=None, description="Absolute executable binary path")
    cpu_percent: float = Field(default=0.0, description="Recent CPU consumption percentage")
    memory_percent: float = Field(default=0.0, description="Resident memory percentage")
    memory_mb: float = Field(default=0.0, description="Resident memory in Megabytes")
    status: str = Field(default="running", description="Process execution status")
    parent_pid: int | None = Field(default=None, description="Parent process identifier")
    created_at: str | None = Field(default=None, description="Process start timestamp")


class ProcessFilter(BaseModel):
    """Criteria to filter process listings."""

    name_substring: str | None = Field(default=None, description="Filter by process name pattern")
    min_memory_mb: float | None = Field(default=None, description="Minimum memory usage filter")
    min_cpu_percent: float | None = Field(default=None, description="Minimum CPU usage filter")
    limit: int = Field(default=100, description="Max records to return")
    sort_by: str = Field(default="memory", description="Sort order: memory, cpu, or name")


class ProcessStopResult(BaseModel):
    """Result of attempting to terminate a process."""

    pid: int
    name: str
    success: bool
    message: str | None = None
