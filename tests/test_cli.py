from __future__ import annotations

import io
import json
import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from laya_cli import cli


class FakeAgent:
    def predict(self, state, questions):
        return {
            "answers": {"route": {"choice": "animation", "confidence": 0.9}},
            "seen_state": state,
            "question_count": len(questions),
        }


class CliTests(unittest.TestCase):
    def run_cli(self, argv, stdin=""):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(stdin)):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_decide_outputs_json_and_defaults_to_multilingual(self):
        calls = []
        fake_laya = types.SimpleNamespace(
            load=lambda model_id, subfolder=None, device=None: (
                calls.append((model_id, subfolder, device)) or FakeAgent()
            )
        )
        request = {
            "state": "手臂穿过衣服，需要返修。",
            "questions": {
                "route": {
                    "type": "choice",
                    "instructions": "属于哪个部门？",
                    "criteria": ["animation", "cfx"],
                }
            },
        }
        with patch.dict(sys.modules, {"laya": fake_laya}):
            code, stdout, stderr = self.run_cli(
                ["decide", "--input-json", json.dumps(request, ensure_ascii=False)]
            )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        result = json.loads(stdout)
        self.assertEqual(result["answers"]["route"]["choice"], "animation")
        self.assertEqual(result["laya_cli"]["checkpoint"], "multilingual")
        self.assertEqual(calls, [(cli.MODEL_ID, "multilingual", None)])

    def test_decide_accepts_stdin(self):
        fake_laya = types.SimpleNamespace(
            load=lambda model_id, subfolder=None, device=None: FakeAgent()
        )
        request = {"state": "hello", "questions": {"q": {"type": "noul"}}}
        with patch.dict(sys.modules, {"laya": fake_laya}):
            code, stdout, _ = self.run_cli(["decide"], json.dumps(request))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["seen_state"], "hello")

    def test_missing_questions_is_machine_readable(self):
        code, stdout, stderr = self.run_cli(
            ["decide", "--input-json", '{"state":"hello"}']
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("questions must be", json.loads(stderr)["error"])

    def test_prepare_loads_requested_checkpoint(self):
        calls = []
        fake_laya = types.SimpleNamespace(
            load=lambda model_id, subfolder=None, device=None: (
                calls.append((model_id, subfolder, device)) or FakeAgent()
            )
        )
        with patch.dict(sys.modules, {"laya": fake_laya}):
            code, stdout, stderr = self.run_cli(
                ["prepare", "--checkpoint", "typed-decisions", "--device", "cpu"]
            )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["ok"])
        self.assertEqual(calls, [(cli.MODEL_ID, "typed-decisions", "cpu")])


if __name__ == "__main__":
    unittest.main()
