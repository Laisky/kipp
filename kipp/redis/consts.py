from __future__ import annotations

# Top-level namespace prefix for all kipp-managed Redis keys.
# All keys follow the pattern: "laisky/<domain>/<specific_key>"
KEY_PREFIX: str = "laisky/"

KEY_PREFIX_TASK: str = KEY_PREFIX + "tasks/"
KEY_PREFIX_TASK_LLM_STORM: str = KEY_PREFIX_TASK + "llm_storm/"
