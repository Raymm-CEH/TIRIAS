import tempfile
import unittest
from pathlib import Path

from tirias.memory import LocalMemory


class MemoryTests(unittest.TestCase):
    def test_remember_recall_and_forget(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = LocalMemory(Path(folder) / "memory.db")
            memory.remember("preferred_editor", "vim")
            self.assertEqual(memory.recall("preferred_editor"), "vim")
            self.assertTrue(memory.forget("preferred_editor"))
            self.assertIsNone(memory.recall("preferred_editor"))

    def test_memory_persists_between_instances(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.db"
            LocalMemory(path).remember("theme", "dark")
            self.assertEqual(LocalMemory(path).recall("theme"), "dark")

    def test_memory_rejects_invalid_or_oversized_values(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = LocalMemory(Path(folder) / "memory.db")
            with self.assertRaises(ValueError):
                memory.remember("", "value")
            with self.assertRaises(ValueError):
                memory.remember("key", "x" * 501)

    def test_memory_lists_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = LocalMemory(Path(folder) / "memory.db")
            memory.remember("z", "last")
            memory.remember("a", "first")
            self.assertEqual(memory.list_keys(), ["a", "z"])


if __name__ == "__main__":
    unittest.main()
