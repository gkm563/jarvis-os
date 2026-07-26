"""
Memory System Package Initialization.
"""

from jarvis.memory.short_term import ShortTermMemory
from jarvis.memory.long_term import LongTermMemory
from jarvis.memory.vector_store import VectorMemoryStore

# Singletons
short_term_memory = ShortTermMemory()
long_term_memory = LongTermMemory()
vector_memory = VectorMemoryStore()

__all__ = [
    "ShortTermMemory",
    "LongTermMemory",
    "VectorMemoryStore",
    "short_term_memory",
    "long_term_memory",
    "vector_memory",
]
