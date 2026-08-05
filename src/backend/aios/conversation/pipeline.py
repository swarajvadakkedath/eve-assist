"""ConversationPipeline v2 — mediates every user input before it reaches the LLM.

Pipeline:
  User (voice / chat / overlay)
    → ConversationPipeline
      → Input validation & sanitisation
      → Identity injection (always "EVE", never "Hermes")
      → Context enrichment (desktop state, memory, vision)
      → Intent detection & routing
      → Hermes agent delegation (reasoning, planning, skills)
      → Response post-processing (strip Hermes identity, add EVE personality)
      → Voice personality adaptation (TTS formatting)
      → Output to user

The pipeline wraps the existing ConversationManager (Phase A) and adds
the mediation layer on top.  No Phase A code is modified.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import uuid4

from aios.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pipeline models
# ---------------------------------------------------------------------------

class PipelineStage(str):
    """Stage names for pipeline events."""
    INPUT = "input"
    VALIDATE = "validate"
    IDENTITY = "identity"
    CONTEXT = "context"
    INTENT = "intent"
    DELEGATE = "delegate"
    POST_PROCESS = "post_process"
    OUTPUT = "output"


@dataclass
class PipelineContext:
    """Mutable context that flows through the pipeline."""
    pipeline_id: str = ""
    conversation_id: str = ""
    user_input: str = ""
    source: str = "chat"  # "chat" | "voice" | "overlay" | "api"
    intent: str = "conversation"
    context: dict = field(default_factory=dict)
    memories: list = field(default_factory=list)
    tools_available: list = field(default_factory=list)
    delegation: bool = False
    hermes_plan: Any = None
    response: str = ""
    response_events: list = field(default_factory=list)
    error: str | None = None
    metadata: dict = field(default_factory=dict)
    start_time: float = 0.0
    stage_timings: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.pipeline_id:
            self.pipeline_id = uuid4().hex
        if not self.start_time:
            self.start_time = time.monotonic()

    def record_stage(self, stage: str) -> None:
        self.stage_timings[stage] = (time.monotonic() - self.start_time) * 1000

    @property
    def total_latency_ms(self) -> float:
        return (time.monotonic() - self.start_time) * 1000


@dataclass
class PipelineEvent:
    """Event emitted during pipeline processing for streaming UI feedback."""
    stage: str
    event_type: str  # "started" | "completed" | "error"
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Pipeline hooks — the ONLY place business logic lives
# ---------------------------------------------------------------------------

class PipelineHooks:
    """Abstract hooks for pipeline stages.

    VoiceOS and the chat UI implement these hooks.  The pipeline itself
    contains zero business logic — it only orchestrates the hooks.
    """

    async def validate_input(self, ctx: PipelineContext) -> PipelineContext:
        """Validate and sanitise user input.  Return ctx (possibly modified)."""
        return ctx

    async def inject_identity(self, ctx: PipelineContext) -> PipelineContext:
        """Inject EVE identity into the context.  Must NEVER expose "Hermes"."""
        return ctx

    async def enrich_context(self, ctx: PipelineContext) -> PipelineContext:
        """Gather context from the unified Context Engine.

        Pulls all relevant context into the pipeline without the LLM
        ever accessing OS services directly.
        """
        context_engine = ctx.context.get("_context_engine")
        if context_engine is not None:
            try:
                execution_ctx = await context_engine.snapshot()
                ctx.context["execution_context"] = execution_ctx.to_dict()
                ctx.context["active_app"] = execution_ctx.window.active_app
                ctx.context["active_file"] = execution_ctx.window.active_file
                ctx.context["active_window"] = execution_ctx.window.active_window
                ctx.context["activity"] = execution_ctx.window.activity.value
                if execution_ctx.workspace.current_project:
                    ctx.context["project"] = execution_ctx.workspace.current_project.path
                    ctx.context["project_type"] = execution_ctx.workspace.current_project.type
                if execution_ctx.git.current_branch:
                    ctx.context["git_branch"] = execution_ctx.git.current_branch
                if execution_ctx.clipboard.has_content:
                    ctx.context["clipboard_available"] = True
                if execution_ctx.voice.is_active:
                    ctx.context["voice_active"] = True
                ctx.context["provider_health"] = execution_ctx.provider_health.overall_health
                ctx.context["context_version"] = execution_ctx.version
            except Exception:
                pass
        ctx.record_stage(PipelineStage.CONTEXT)
        return ctx

    async def detect_intent(self, ctx: PipelineContext) -> PipelineContext:
        """Classify user intent (conversation, question, tool, planning, etc.)."""
        return ctx

    async def delegate_to_hermes(self, ctx: PipelineContext) -> PipelineContext:
        """Optionally delegate to Hermes for reasoning/planning.
        Returns ctx with hermes_delegation, hermes_plan set."""
        return ctx

    async def post_process_response(self, ctx: PipelineContext) -> PipelineContext:
        """Strip any Hermes identity from response, add EVE personality."""
        return ctx

    async def adapt_for_voice(self, ctx: PipelineContext) -> PipelineContext:
        """Format response for TTS (remove markdown, code blocks, etc.)."""
        return ctx


# ---------------------------------------------------------------------------
# Default hooks — identity sanitisation + basic intent detection
# ---------------------------------------------------------------------------

# Patterns that should never appear in EVE responses
_HERMES_PATTERNS = [
    "hermes", "nous research", "nousresearch", "hermes-agent",
    "i am hermes", "my name is hermes", "i'm hermes",
]

# Identity replacement — when these appear in output, replace with EVE
_IDENTITY_REPLACEMENTS = {
    "hermes": "eve",
    "Hermes": "EVE",
    "HERMES": "EVE",
    "nous research": "eve ai",
    "Nous Research": "EVE AI",
    "NousResearch": "EVE AI",
}


class DefaultPipelineHooks(PipelineHooks):
    """Built-in hooks that enforce EVE identity and basic intent detection."""

    async def validate_input(self, ctx: PipelineContext) -> PipelineContext:
        ctx.user_input = ctx.user_input.strip()
        if not ctx.user_input:
            ctx.error = "Empty input"
        ctx.record_stage(PipelineStage.VALIDATE)
        return ctx

    async def inject_identity(self, ctx: PipelineContext) -> PipelineContext:
        """Ensure system prompt and context never mention Hermes."""
        # Strip any leaked Hermes references from context
        for key in ("system_prompt", "persona", "identity"):
            val = ctx.context.get(key, "")
            if isinstance(val, str):
                for pattern, replacement in _IDENTITY_REPLACEMENTS.items():
                    val = val.replace(pattern, replacement)
                ctx.context[key] = val
        ctx.metadata["identity"] = "eve"
        ctx.record_stage(PipelineStage.IDENTITY)
        return ctx

    async def detect_intent(self, ctx: PipelineContext) -> PipelineContext:
        """Basic keyword intent detection."""
        text = ctx.user_input.lower()
        intent = "conversation"
        if any(w in text for w in ("what", "who", "where", "when", "why", "how")):
            intent = "question"
        elif any(w in text for w in ("run", "execute", "open", "launch")):
            intent = "tool_execution"
        elif any(w in text for w in ("plan", "organize", "create a project")):
            intent = "planning"
        elif any(w in text for w in ("research", "analyze", "compare")):
            intent = "research"
        ctx.intent = intent
        ctx.record_stage(PipelineStage.INTENT)
        return ctx

    async def post_process_response(self, ctx: PipelineContext) -> PipelineContext:
        """Sanitise response — remove any Hermes references, add EVE personality."""
        if ctx.response:
            for pattern, replacement in _IDENTITY_REPLACEMENTS.items():
                ctx.response = ctx.response.replace(pattern, replacement)
        ctx.record_stage(PipelineStage.POST_PROCESS)
        return ctx


# ---------------------------------------------------------------------------
# ConversationPipeline
# ---------------------------------------------------------------------------

class ConversationPipeline:
    """Mediates every user input before it reaches the LLM.

    Wraps the existing ConversationManager and adds the pipeline layer.
    The pipeline itself contains NO business logic — all logic lives in
    the injected PipelineHooks.
    """

    def __init__(
        self,
        conversation_manager: Any | None = None,
        hooks: PipelineHooks | None = None,
        event_bus: Any | None = None,
        context_engine: Any | None = None,
    ):
        self._manager = conversation_manager
        self._hooks = hooks or DefaultPipelineHooks()
        self._event_bus = event_bus
        self._context_engine = context_engine

    # ── Main pipeline entry points ─────────────────────────────────

    async def process_message(
        self,
        conversation_id: str,
        content: str,
        *,
        source: str = "chat",
        context: dict | None = None,
    ) -> dict:
        """Non-streaming pipeline: input → validation → context → LLM → response."""
        ctx = PipelineContext(
            conversation_id=conversation_id,
            user_input=content,
            source=source,
            context=context or {},
        )
        if self._context_engine is not None:
            ctx.context["_context_engine"] = self._context_engine

        # Stage 1: Validate
        ctx = await self._hooks.validate_input(ctx)
        if ctx.error:
            return self._error_response(ctx)

        # Stage 2: Identity
        ctx = await self._hooks.inject_identity(ctx)

        # Stage 3: Context enrichment
        ctx = await self._hooks.enrich_context(ctx)

        # Stage 4: Intent detection
        ctx = await self._hooks.detect_intent(ctx)

        # Stage 5: Optional Hermes delegation
        ctx = await self._hooks.delegate_to_hermes(ctx)

        # Stage 6: Delegate to ConversationManager
        ctx = await self._delegate_to_manager(ctx)
        if ctx.error:
            return self._error_response(ctx)

        # Stage 7: Post-process (strip Hermes, add personality)
        ctx = await self._hooks.post_process_response(ctx)

        # Stage 8: Voice adaptation if source is voice
        if source == "voice":
            ctx = await self._hooks.adapt_for_voice(ctx)

        ctx.record_stage(PipelineStage.OUTPUT)

        return {
            "conversation_id": ctx.conversation_id,
            "response": ctx.response,
            "intent": ctx.intent,
            "pipeline_id": ctx.pipeline_id,
            "latency_ms": ctx.total_latency_ms,
            "stage_timings": ctx.stage_timings,
            "source": source,
            "metadata": ctx.metadata,
        }

    async def stream_message(
        self,
        conversation_id: str,
        content: str,
        *,
        source: str = "chat",
        context: dict | None = None,
    ) -> AsyncIterator[dict]:
        """Streaming pipeline: yields events as stages complete."""
        ctx = PipelineContext(
            conversation_id=conversation_id,
            user_input=content,
            source=source,
            context=context or {},
        )
        if self._context_engine is not None:
            ctx.context["_context_engine"] = self._context_engine

        # Stage 1: Validate
        yield self._stage_event(PipelineStage.VALIDATE, "started", {"input_length": len(content)})
        ctx = await self._hooks.validate_input(ctx)
        if ctx.error:
            yield self._stage_event(PipelineStage.VALIDATE, "error", {"error": ctx.error})
            yield self._error_stream_event(ctx.error)
            return
        yield self._stage_event(PipelineStage.VALIDATE, "completed")

        # Stage 2: Identity
        yield self._stage_event(PipelineStage.IDENTITY, "started")
        ctx = await self._hooks.inject_identity(ctx)
        yield self._stage_event(PipelineStage.IDENTITY, "completed")

        # Stage 3: Context
        yield self._stage_event(PipelineStage.CONTEXT, "started")
        ctx = await self._hooks.enrich_context(ctx)
        yield self._stage_event(PipelineStage.CONTEXT, "completed", {
            "memory_count": len(ctx.memories),
            "tools_count": len(ctx.tools_available),
        })

        # Stage 4: Intent
        yield self._stage_event(PipelineStage.INTENT, "started")
        ctx = await self._hooks.detect_intent(ctx)
        yield self._stage_event(PipelineStage.INTENT, "completed", {"intent": ctx.intent})

        # Stage 5: Hermes delegation
        yield self._stage_event(PipelineStage.DELEGATE, "started")
        ctx = await self._hooks.delegate_to_hermes(ctx)
        yield self._stage_event(PipelineStage.DELEGATE, "completed", {
            "delegation": ctx.delegation,
        })

        # Stage 6: Delegate to ConversationManager (streaming)
        if self._manager is not None:
            try:
                async for event in self._manager.stream_message(conversation_id, content):
                    # Post-process each event through hooks
                    if event.get("type") == "token" and "data" in event:
                        token_text = event["data"].get("token", "")
                        # Identity sanitise token stream
                        for pattern, replacement in _IDENTITY_REPLACEMENTS.items():
                            token_text = token_text.replace(pattern, replacement)
                        event["data"]["token"] = token_text
                    yield event
            except Exception as exc:
                ctx.error = str(exc)
                yield self._error_stream_event(str(exc))
                return
        else:
            yield self._error_stream_event("No conversation manager available")
            return

        # Stage 7: Post-process marker
        yield self._stage_event(PipelineStage.POST_PROCESS, "completed")
        ctx.record_stage(PipelineStage.OUTPUT)

    # ── Internal ───────────────────────────────────────────────────

    async def _delegate_to_manager(self, ctx: PipelineContext) -> PipelineContext:
        """Send validated input to ConversationManager and capture response."""
        if self._manager is None:
            ctx.error = "No conversation manager available"
            return ctx
        try:
            response = await self._manager.send_message(ctx.conversation_id, ctx.user_input)
            ctx.response = getattr(response, "content", str(response))
            ctx.record_stage(PipelineStage.DELEGATE)
        except Exception as exc:
            ctx.error = str(exc)
        return ctx

    def _error_response(self, ctx: PipelineContext) -> dict:
        return {
            "conversation_id": ctx.conversation_id,
            "response": "",
            "error": ctx.error,
            "intent": ctx.intent,
            "pipeline_id": ctx.pipeline_id,
            "latency_ms": ctx.total_latency_ms,
            "stage_timings": ctx.stage_timings,
            "source": ctx.source,
        }

    def _stage_event(self, stage: str, event_type: str, data: dict | None = None) -> dict:
        return {
            "type": "pipeline_stage",
            "data": {
                "stage": stage,
                "event_type": event_type,
                "data": data or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _error_stream_event(self, error: str) -> dict:
        return {
            "type": "error",
            "data": {"error": error, "recoverable": True},
        }
