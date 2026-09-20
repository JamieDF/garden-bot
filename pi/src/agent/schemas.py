"""
Agent decision schemas - pydantic models double as JSON schemas
for structured output (llama-server response_format / tool calling).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

ACTIONS = Literal[
    "none",       # do nothing
    "speak",      # just narrate
    "fan_on",     # turn a fan actuator on (manual)
    "fan_off",    # turn a fan actuator off (manual)
    "fan_auto",   # return a fan actuator to auto mode
    "water",      # run a pump actuator for duration_s seconds
    "alert",      # flag something for human attention
    "log_note",   # write a note to the journal (memory)
    "remember",   # store a persistent fact (fact_key + fact_value)
    "wait",       # explicitly decide to check again later
]


class Decision(BaseModel):
    """What the agent concludes on each wake.

    The model proposes; the deterministic safety layer in safety.py
    disposes - hardware actions are validated before executing.
    """

    mood: str = Field(description="One word for how the garden feels")
    observation: str = Field(description="What the sensors show, in a sentence")
    action: ACTIONS = "none"
    device: Optional[str] = Field(
        default=None,
        description="Actuator device name for fan_*/water actions",
    )
    duration_s: Optional[float] = Field(
        default=None, description="Seconds to run a pump for 'water'"
    )
    note: Optional[str] = Field(
        default=None, description="Text to journal for 'log_note'"
    )
    fact_key: Optional[str] = Field(
        default=None, description="Short label for 'remember' facts"
    )
    fact_value: Optional[str] = Field(
        default=None, description="Fact content for 'remember'"
    )
    speak: str = Field(
        default="", description="One short sentence to say out loud (max ~20 words)"
    )
