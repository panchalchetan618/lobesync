from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlmodel import Session, select

from lobesync.agent.nodes.commitment import _update_summary
from lobesync.agent.nodes.completion import completion_node
from lobesync.agent.nodes.executor import executor_node
from lobesync.config import config
from lobesync.db.database import get_engine, init_db
from lobesync.db.models import ChatSession, MessageRole, Task
from lobesync.db.repos.chat_repo import create_message
from lobesync.db.repos.checklist_repo import create_checklist
from lobesync.exceptions.checklist_exceptions import ChecklistHasPendingTasksError
from lobesync.services.checklist_service import delete_checklist_service


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "lobesync-test.db"
        self.original_cache = config._cache
        config._cache = {"DATABASE_URL": f"sqlite:///{self.database_path}"}
        init_db()

    def tearDown(self) -> None:
        engine = get_engine()
        engine.dispose()
        config._cache = self.original_cache
        self.temp_dir.cleanup()

    def test_atomic_plan_resolves_unique_step_ids_and_commits(self) -> None:
        state = {
            "plan": {
                "atomic_groups": [
                    [
                        {"id": "release", "tool": "create_checklist", "args": {"title": "Release"}},
                        {
                            "id": "write_tests",
                            "tool": "create_task",
                            "args": {"title": "Write tests", "checklist_id": "$release.id"},
                        },
                    ]
                ],
                "non_atomic": [],
            }
        }

        result = executor_node(state)

        self.assertEqual([entry["error"] for entry in result["execution_results"]], [None, None])
        with Session(get_engine()) as session:
            task = session.exec(select(Task)).one()
            self.assertEqual(task.title, "Write tests")
            self.assertIsNotNone(task.checklist_id)

    def test_invalid_plan_is_reported_without_crashing_executor(self) -> None:
        result = executor_node({"plan": {"atomic_groups": [], "non_atomic": ["not a step"]}})

        self.assertEqual(len(result["execution_results"]), 1)
        self.assertEqual(result["execution_results"][0]["tool"], "unknown")
        self.assertIn("Plan step must be an object", result["execution_results"][0]["error"])

    def test_pending_tasks_block_checklist_deletion(self) -> None:
        with Session(get_engine()) as session:
            checklist = create_checklist(session, "Release")
            session.commit()
            self.assertIsNotNone(checklist)
            session.refresh(checklist)

        executor_node(
            {
                "plan": {
                    "atomic_groups": [],
                    "non_atomic": [
                        {
                            "id": "task",
                            "tool": "create_task",
                            "args": {"title": "Write tests", "checklist_id": checklist.id},
                        }
                    ],
                }
            }
        )

        with Session(get_engine()) as session:
            with self.assertRaises(ChecklistHasPendingTasksError):
                delete_checklist_service(session, checklist.id)

    def test_summary_only_includes_new_messages(self) -> None:
        with Session(get_engine()) as session:
            chat_session = ChatSession(name="Lobesync")
            session.add(chat_session)
            session.flush()
            for index in range(10):
                create_message(session, chat_session.id, f"message {index}", MessageRole.USER)
            session.commit()
            session.refresh(chat_session)
            chat_session_id = chat_session.id

        prompts: list[str] = []
        with patch(
            "lobesync.agent.nodes.commitment._generate_summary",
            side_effect=lambda existing, messages: (
                prompts.append("|".join(message.content for message in messages)) or "summary"
            ),
        ):
            _update_summary(chat_session_id)
            with Session(get_engine()) as session:
                for index in range(10, 15):
                    create_message(session, chat_session_id, f"message {index}", MessageRole.USER)
                session.commit()
            _update_summary(chat_session_id)

        self.assertEqual(
            prompts,
            [
                "message 0|message 1|message 2|message 3|message 4",
                "message 5|message 6|message 7|message 8|message 9",
            ],
        )
        with Session(get_engine()) as session:
            summary_state = session.get(ChatSession, chat_session_id)
            self.assertEqual(summary_state.summary_message_count, 10)

    def test_completion_needs_no_model_and_includes_created_id(self) -> None:
        response = completion_node(
            {
                "execution_results": [
                    {
                        "tool": "create_task",
                        "result": {"id": 7, "title": "Write tests"},
                        "error": None,
                    }
                ]
            }
        )

        self.assertEqual(response["final_response"], 'Created task "Write tests" (ID: 7).')
