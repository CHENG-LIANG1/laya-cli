"""Command-line interface for running Laya typed decisions with JSON I/O."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import __version__

MODEL_ID = "convaiinnovations/laya"
CHECKPOINTS = {
    "english": None,
    "multilingual": "multilingual",
    "typed-decisions": "typed-decisions",
}


class CliError(ValueError):
    """An input or configuration error suitable for a concise CLI response."""


def _read_payload(args: argparse.Namespace) -> dict[str, Any]:
    sources = sum(
        value is not None
        for value in (args.input_json, args.input_file)
    )
    if sources > 1:
        raise CliError("use only one of --input-json or --input-file")

    if args.input_json is not None:
        raw = args.input_json
    elif args.input_file is not None:
        raw = Path(args.input_file).read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    else:
        raise CliError("provide --input-json, --input-file, or JSON on stdin")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliError(f"invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}") from exc

    if not isinstance(payload, dict):
        raise CliError("input must be a JSON object")
    return payload


def _validate_payload(payload: Mapping[str, Any]) -> None:
    if "state" not in payload:
        raise CliError("missing required field: state")
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise CliError("questions must be a non-empty JSON object")


def _resolve_checkpoint(args: argparse.Namespace, payload: Mapping[str, Any] | None = None) -> str:
    requested = None if payload is None else payload.get("checkpoint")
    checkpoint = requested or args.checkpoint or os.environ.get("LAYA_CLI_CHECKPOINT", "multilingual")
    if checkpoint not in CHECKPOINTS:
        allowed = ", ".join(CHECKPOINTS)
        raise CliError(f"unsupported checkpoint {checkpoint!r}; choose one of: {allowed}")
    return str(checkpoint)


def _resolve_device(args: argparse.Namespace, payload: Mapping[str, Any] | None = None) -> str | None:
    requested = None if payload is None else payload.get("device")
    device = requested or args.device or os.environ.get("LAYA_CLI_DEVICE", "auto")
    if device not in {"auto", "cpu", "cuda"}:
        raise CliError("device must be auto, cpu, or cuda")
    return None if device == "auto" else str(device)


def _load_agent(checkpoint: str, device: str | None):
    import laya

    return laya.load(
        MODEL_ID,
        subfolder=CHECKPOINTS[checkpoint],
        device=device,
    )


def _emit_json(value: Mapping[str, Any], *, stream=None) -> None:
    json.dump(
        value,
        stream or sys.stdout,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    (stream or sys.stdout).write("\n")


def _cmd_decide(args: argparse.Namespace) -> int:
    payload = _read_payload(args)
    _validate_payload(payload)
    checkpoint = _resolve_checkpoint(args, payload)
    device = _resolve_device(args, payload)
    agent = _load_agent(checkpoint, device)
    result = agent.predict(payload["state"], payload["questions"])
    if isinstance(result, dict):
        result.setdefault("laya_cli", {})
        result["laya_cli"].update(
            {
                "checkpoint": checkpoint,
                "device": device or "auto",
                "cli_version": __version__,
            }
        )
    _emit_json(result)
    return 0


def _cmd_prepare(args: argparse.Namespace) -> int:
    checkpoint = _resolve_checkpoint(args)
    device = _resolve_device(args)
    _load_agent(checkpoint, device)
    _emit_json(
        {
            "ok": True,
            "model": MODEL_ID,
            "checkpoint": checkpoint,
            "device": device or "auto",
            "message": "checkpoint downloaded and load verified",
        }
    )
    return 0


def _cmd_health(args: argparse.Namespace) -> int:
    details: dict[str, Any] = {
        "ok": True,
        "cli_version": __version__,
        "python": sys.version.split()[0],
    }
    if args.check_dependencies:
        try:
            import laya
            import torch

            details.update(
                {
                    "laya_version": getattr(laya, "__version__", "unknown"),
                    "torch_version": getattr(torch, "__version__", "unknown"),
                    "cuda_available": bool(torch.cuda.is_available()),
                }
            )
        except Exception as exc:  # noqa: BLE001 - health must report import failures as JSON
            details.update({"ok": False, "dependency_error": str(exc)})
    _emit_json(details)
    return 0 if details["ok"] else 1


def _add_model_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--checkpoint",
        choices=tuple(CHECKPOINTS),
        help="checkpoint to load; defaults to multilingual",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        help="execution device; defaults to automatic selection",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="laya-cli",
        description="Run Laya typed decisions with stable JSON input and output.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    decide = subparsers.add_parser("decide", help="run a typed decision")
    decide.add_argument("--input-json", help="request JSON as a command-line value")
    decide.add_argument("--input-file", help="path to a UTF-8 request JSON file")
    _add_model_options(decide)
    decide.set_defaults(handler=_cmd_decide)

    prepare = subparsers.add_parser("prepare", help="download and verify a checkpoint")
    _add_model_options(prepare)
    prepare.set_defaults(handler=_cmd_prepare)

    health = subparsers.add_parser("health", help="check the CLI runtime")
    health.add_argument(
        "--check-dependencies",
        action="store_true",
        help="also import Laya and PyTorch and report CUDA availability",
    )
    health.set_defaults(handler=_cmd_health)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except CliError as exc:
        _emit_json({"ok": False, "error": str(exc), "error_type": "input"}, stream=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - connector needs a machine-readable terminal error
        _emit_json(
            {
                "ok": False,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            stream=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
