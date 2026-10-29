"""Acceptance checks, not the solution. The untouched FIFO starter should fail.

Run from the project folder: python challenge/check_stack.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.stack import HistoryBuffer
from backend.app import create_app
from database import db


class StackGoalTests(unittest.TestCase):
    def test_01_last_in_first_out(self):
        history = HistoryBuffer()
        for value in ["A", "B", "C"]:
            history.push(value)
        self.assertEqual([history.pop(), history.pop(), history.pop()], ["C", "B", "A"],
                         "The last recorded value must leave first.")

    def test_02_peek_reads_the_top_without_removal(self):
        history = HistoryBuffer(["A", "B", "C"])
        self.assertEqual(history.peek(), "C", "The top should be the newest value.")
        self.assertEqual(history.peek(), "C")
        self.assertEqual(history.size(), 3, "Peeking must not reduce the size.")

    def test_03_mixed_operations_follow_lifo(self):
        history = HistoryBuffer()
        history.push("A")
        history.push("B")
        self.assertEqual(history.pop(), "B")
        history.push("C")
        self.assertEqual(history.pop(), "C")
        self.assertEqual(history.pop(), "A")
        self.assertTrue(history.is_empty())

    def test_04_empty_pop_and_peek_are_explicit(self):
        history = HistoryBuffer()
        self.assertTrue(history.is_empty())
        self.assertEqual(history.size(), 0)
        with self.assertRaises(IndexError):
            history.pop()
        with self.assertRaises(IndexError):
            history.peek()

    def test_05_persistence_order_and_copy_are_preserved(self):
        original = ["A", "B", "C"]
        history = HistoryBuffer(original)
        exported = history.to_list()
        self.assertEqual(exported, ["A", "B", "C"])
        exported.append("external change")
        original.append("another external change")
        self.assertEqual(history.size(), 3, "The structure must own its storage.")
        restored = HistoryBuffer(history.to_list())
        self.assertEqual(restored.pop(), "C", "Reloading from SQLite must preserve the top.")

    def test_06_real_website_restores_latest_removed_item(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"TESTING": True, "SECRET_KEY": "challenge-tests-only",
                      "DATABASE": str(Path(directory) / "goal.sqlite3")}
            app = create_app(config)
            client = app.test_client()
            client.get("/")
            with client.session_transaction() as session:
                token = session["csrf_token"]
                owner = session["workspace_id"]
            ids = []
            for title in ["Challenge A", "Challenge B", "Challenge C"]:
                client.post("/items/new", data={"csrf_token": token, "title": title,
                            "description": "Keep my original fields", "category": "Challenge",
                            "status": "doing", "priority": "high", "due_date": ""})
                with app.app_context():
                    ids.append(db.get_db().execute("SELECT id FROM items WHERE workspace_id=? AND title=?",
                                                  (owner, title)).fetchone()["id"])
            for item_id in ids:
                client.post(f"/items/{item_id}/remove", data={"csrf_token": token})
            for expected_id in reversed(ids):
                # Use a fresh request each time: persistence is part of the goal.
                response = client.post("/recovery/restore", data={"csrf_token": token})
                self.assertEqual(response.status_code, 303)
                client.get("/recovery")
                with app.app_context():
                    item = db.get_item(owner, expected_id)
                    self.assertEqual(item["archived"], 0,
                                     "The Flask route must restore the ID returned by a LIFO pop.")
                    self.assertEqual(item["description"], "Keep my original fields")
                    self.assertEqual(item["status"], "doing")
                    self.assertEqual(item["priority"], "high")


if __name__ == "__main__":
    print("\nSTACK CHALLENGE CHECKS")
    print("The untouched starter is FIFO and intentionally fails LIFO checks.")
    print("Modify backend/stack.py, restart the server, and run this checker again.\n")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StackGoalTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("\nAll Stack goal checks passed. Demonstrate and explain your solution too.")
    else:
        print("\nThe Stack goal is not complete yet. Review the failing behavior above.")
        print("This does not mean the website setup failed. Website checks are separate.")
    raise SystemExit(0 if result.wasSuccessful() else 1)
