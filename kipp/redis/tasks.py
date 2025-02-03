import uuid
import json
from datetime import datetime

from kipp.redis.utils import RedisUtils
from kipp.redis.consts import KEY_PREFIX_TASK_LLM_STORM


def add_llm_storm_task(rutils: RedisUtils, prompt: str, api_key: str) -> str:
    """Add a task to LLM Storm."""
    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "prompt": prompt,
        "api_key": api_key,
        "created_at": datetime.now().isoformat(),
    }
    key = KEY_PREFIX_TASK_LLM_STORM + task_id
    rutils.rpush(key, json.dumps(task))
    return task_id
