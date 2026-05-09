from typing import List, Dict


class ShortTermMemory:
    """短期记忆，基于对话历史列表"""

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.memories: Dict[int, List[Dict]] = {}

    def add_message(self, user_id: int, role: str, content: str):
        if user_id not in self.memories:
            self.memories[user_id] = []
        self.memories[user_id].append({"role": role, "content": content})
        if len(self.memories[user_id]) > self.window_size * 2:
            self.memories[user_id] = self.memories[user_id][-self.window_size * 2:]

    def get_history(self, user_id: int) -> List[Dict]:
        return self.memories.get(user_id, [])

    def get_context_string(self, user_id: int) -> str:
        history = self.get_history(user_id)
        if not history:
            return ""
        lines = []
        for msg in history[-6:]:
            prefix = "用户" if msg["role"] == "user" else "AI"
            lines.append(f"{prefix}: {msg['content'][:100]}")
        return "\n".join(lines)

    def clear_memory(self, user_id: int):
        if user_id in self.memories:
            del self.memories[user_id]
