from __future__ import annotations

import argparse
import json
from typing import Any

from app.services.backup_restore import BackupRestoreService


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

    restore_parser = backup_subparsers.add_parser("restore")
    restore_parser.add_argument("--input", required=True)

    search_parser = subparsers.add_parser("search")
    search_subparsers = search_parser.add_subparsers(dest="search_command", required=True)
    rebuild_parser = search_subparsers.add_parser("rebuild-index")
    rebuild_parser.add_argument("--workspace-id", required=False)

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
    if args.command == "backup" and args.backup_command == "restore":
        _print_payload(service.restore_backup(input_dir=args.input))
        return 0
    if args.command == "search" and args.search_command == "rebuild-index":
        _print_payload(service.rebuild_search_index(workspace_id=args.workspace_id))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())