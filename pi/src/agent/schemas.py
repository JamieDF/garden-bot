"""
Agent decision schemas - pydantic models double as JSON schemas
for structured output (llama-server response_format / tool calling).
"""

from typing import Literal

from pydantic import BaseModel, Field


class Decision(BaseModel):
    """What the agent concludes on each wake.

    Phase 0/1: narration only - action is whitelisted to none/speak.
    Phase 2 will widen the action literal to real tool calls.
    """

    mood: str = Field(description="One word for how the garden feels")
    observation: str = Field(description="What the sensors show, in a sentence")
    action: Literal["none", "speak"] = "none"
    speak: str = Field(
        default="", description="One short sentence to say out loud (max ~20 words)"
    )
