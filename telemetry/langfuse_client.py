import os
from typing import Optional, Dict, Any

class LangfuseTelemetry:
    """
    Manages Langfuse tracing, latency metrics, prompt tracking, and quality evaluation.
    Fails open gracefully if Langfuse is not configured.
    """

    def __init__(self):
        self.client = None
        self.enabled = False
        try:
            import config
            public_key = getattr(config, "LANGFUSE_PUBLIC_KEY", os.getenv("LANGFUSE_PUBLIC_KEY", ""))
            secret_key = getattr(config, "LANGFUSE_SECRET_KEY", os.getenv("LANGFUSE_SECRET_KEY", ""))
            host = getattr(config, "LANGFUSE_HOST", os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"))

            if public_key and secret_key:
                from langfuse import Langfuse
                self.client = Langfuse(
                    public_key=public_key,
                    secret_key=secret_key,
                    host=host
                )
                self.enabled = True
                print("[Langfuse] Observability client initialized successfully.")
        except Exception as e:
            print(f"[Langfuse Note] Telemetry disabled or not configured: {e}")
            self.enabled = False

    def create_trace(self, name: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Creates a top-level execution trace."""
        if not self.enabled or not self.client:
            return DummyTrace()
        try:
            return self.client.trace(
                name=name,
                user_id=user_id,
                metadata=metadata or {}
            )
        except Exception as e:
            print(f"[Langfuse Warning] Failed to create trace: {e}")
            return DummyTrace()

    def log_score(self, trace_id: str, name: str, value: float, comment: Optional[str] = None):
        """Logs an evaluation score or user feedback rating to Langfuse."""
        if not self.enabled or not self.client or not trace_id:
            return
        try:
            self.client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment
            )
        except Exception as e:
            print(f"[Langfuse Warning] Failed to log score: {e}")


class DummyTrace:
    """Fallback dummy trace when Langfuse is disabled."""
    def __init__(self):
        self.id = "trace-local"

    def span(self, *args, **kwargs):
        return DummySpan()

    def generation(self, *args, **kwargs):
        return DummySpan()

    def update(self, *args, **kwargs):
        pass


class DummySpan:
    """Fallback dummy span."""
    def end(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass
