from __future__ import annotations

import argparse
import json
from typing import Any

from app.services.backup_restore import BackupRestoreService
from app.services import m5_entropy_audit, m5_longrun_simulation, m5_retrieval_benchmark


def _print_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup")
    backup_subparsers = backup_parser.add_subparsers(dest="backup_command", required=True)

    create_parser = backup_subparsers.add_parser("create")
    create_parser.add_argument("--output", required=False)

    validate_parser = backup_subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True)

    verify_parser = backup_subparsers.add_parser("verify-backup")
    verify_parser.add_argument("--input", required=True)

    restore_parser = backup_subparsers.add_parser("restore")
    restore_parser.add_argument("--input", required=True)

    search_parser = subparsers.add_parser("search")
    search_subparsers = search_parser.add_subparsers(dest="search_command", required=True)
    rebuild_parser = search_subparsers.add_parser("rebuild-index")
    rebuild_parser.add_argument("--workspace-id", required=False)

    m5_parser = subparsers.add_parser("m5")
    m5_subparsers = m5_parser.add_subparsers(dest="m5_command", required=True)

    retrieval_parser = m5_subparsers.add_parser("retrieval-benchmark")
    retrieval_parser.add_argument("--output-dir", required=False)
    retrieval_parser.add_argument(
        "--trigger",
        choices=m5_retrieval_benchmark.REGRESSION_TRIGGERS,
        default="manual",
    )
    retrieval_parser.add_argument("--set-baseline", action="store_true")

    longrun_parser = m5_subparsers.add_parser("longrun-simulation")
    longrun_parser.add_argument("--cycles", type=int, default=28)
    longrun_parser.add_argument("--restore-every", type=int, default=7)
    longrun_parser.add_argument("--output-dir", required=False)

    entropy_parser = m5_subparsers.add_parser("entropy-audit")
    entropy_parser.add_argument("--output-dir", required=False)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    service = BackupRestoreService()

    if args.command == "backup" and args.backup_command == "create":
        summary = service.create_backup(output_dir=args.output)
        _print_payload(summary.__dict__)
        return 0
    if args.command == "backup" and args.backup_command == "validate":
        _print_payload(service.validate_backup(input_dir=args.input))
        return 0
    if args.command == "backup" and args.backup_command == "verify-backup":
        _print_payload(service.verify_backup(input_dir=args.input))
        return 0
    if args.command == "backup" and args.backup_command == "restore":
        _print_payload(service.restore_backup(input_dir=args.input))
        return 0
    if args.command == "search" and args.search_command == "rebuild-index":
        _print_payload(service.rebuild_search_index(workspace_id=args.workspace_id))
        return 0
    if args.command == "m5" and args.m5_command == "retrieval-benchmark":
        from pathlib import Path

        output_dir = Path(args.output_dir) if args.output_dir else None
        _print_payload(
            m5_retrieval_benchmark.write_reports(
                output_dir=output_dir,
                trigger=args.trigger,
                set_baseline=args.set_baseline,
            )
        )
        return 0
    if args.command == "m5" and args.m5_command == "longrun-simulation":
        from pathlib import Path

        output_dir = Path(args.output_dir) if args.output_dir else None
        _print_payload(
            m5_longrun_simulation.write_reports(
                cycles=args.cycles,
                restore_every=args.restore_every,
                output_dir=output_dir,
            )
        )
        return 0
    if args.command == "m5" and args.m5_command == "entropy-audit":
        from pathlib import Path

        output_dir = Path(args.output_dir) if args.output_dir else None
        _print_payload(m5_entropy_audit.write_reports(output_dir=output_dir))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
