"""Spielt die Alembic-Kette gegen ein Schemamodell durch — ohne Datenbank.

Zweck: das Zielschema der Migrationen maschinell verfuegbar machen, damit es
gegen die ORM-Metadaten diffbar ist. Ersetzt keinen Lauf gegen echtes
PostgreSQL — Raw-SQL (``op.execute``) wird bewusst ignoriert, weil es sich nicht
ohne DB interpretieren laesst. Bekannte Folgen davon stehen als KNOWN_ORM_GAPS
in ``test_schema_truth_0028_0029.py``.
"""
from __future__ import annotations

import contextlib
from typing import Any

import sqlalchemy as sa

Schema = dict[str, dict[str, Any]]


def _empty() -> dict[str, Any]:
    return {"columns": {}, "indexes": {}, "checks": {}, "uniques": {}, "fks": {}, "pk": []}


def _type_str(column_type: Any) -> str:
    try:
        return str(column_type.compile(dialect=sa.dialects.postgresql.dialect()))
    except Exception:  # noqa: BLE001 - Typen ohne PG-Compiler
        return str(column_type)


def _names(constraint: Any) -> list[str]:
    pending = getattr(constraint, "_pending_colargs", None)
    source = pending if pending else constraint.columns
    return [c if isinstance(c, str) else c.name for c in source]


class _FakeDialect:
    name = "postgresql"


class _FakeResult:
    def mappings(self):
        return self

    def all(self):
        return []

    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def scalar(self):
        return None

    def scalar_one(self):
        return 0

    def __iter__(self):
        return iter([])


class _FakeBind:
    dialect = _FakeDialect()

    def execute(self, *args, **kwargs):
        return _FakeResult()

    def exec_driver_sql(self, *args, **kwargs):
        return _FakeResult()


class _FakeContext:
    def __init__(self) -> None:
        self.dialect = _FakeDialect()

    @contextlib.contextmanager
    def autocommit_block(self):
        yield


class SchemaRecorder:
    """Nimmt Alembic-Operationen entgegen und pflegt daraus ``schema``."""

    def __init__(self) -> None:
        self.schema: Schema = {}

    def _table(self, name: str) -> dict[str, Any]:
        return self.schema.setdefault(name, _empty())

    # -- Tabellen ----------------------------------------------------------
    def create_table(self, name: str, *items: Any, **kwargs: Any) -> None:
        table = self._table(name)
        for item in items:
            if isinstance(item, sa.Column):
                table["columns"][item.name] = {
                    "type": _type_str(item.type),
                    "nullable": bool(item.nullable),
                }
                if item.primary_key is True:
                    table["pk"].append(item.name)
            elif isinstance(item, sa.PrimaryKeyConstraint):
                table["pk"] = _names(item)
            elif isinstance(item, sa.CheckConstraint):
                table["checks"][item.name] = str(item.sqltext)
            elif isinstance(item, sa.UniqueConstraint):
                table["uniques"][item.name] = _names(item)
            elif isinstance(item, sa.ForeignKeyConstraint):
                table["fks"][item.name] = {
                    "cols": _names(item),
                    "ondelete": item.ondelete,
                }

    def drop_table(self, name: str, **kwargs: Any) -> None:
        self.schema.pop(name, None)

    def rename_table(self, old: str, new: str, **kwargs: Any) -> None:
        if old in self.schema:
            self.schema[new] = self.schema.pop(old)

    # -- Spalten -----------------------------------------------------------
    def add_column(self, table: str, column: sa.Column, **kwargs: Any) -> None:
        self._table(table)["columns"][column.name] = {
            "type": _type_str(column.type),
            "nullable": bool(column.nullable),
        }

    def drop_column(self, table: str, column: str, **kwargs: Any) -> None:
        self._table(table)["columns"].pop(column, None)

    def alter_column(self, table: str, column: str, **kwargs: Any) -> None:
        entry = self._table(table)
        current = entry["columns"].setdefault(column, {"type": "?", "nullable": True})
        if kwargs.get("nullable") is not None:
            current["nullable"] = bool(kwargs["nullable"])
        if kwargs.get("type_") is not None:
            current["type"] = _type_str(kwargs["type_"])
        new_name = kwargs.get("new_column_name")
        if new_name:
            entry["columns"][new_name] = entry["columns"].pop(column)

    # -- Indizes und Constraints ------------------------------------------
    def create_index(
        self, name: str, table: str, columns: list[str], unique: bool = False, **kwargs: Any
    ) -> None:
        where = kwargs.get("postgresql_where")
        if where is None:
            where = kwargs.get("sqlite_where")
        self._table(table)["indexes"][name] = {
            "cols": [str(c) for c in columns],
            "unique": bool(unique),
            "where": str(where) if where is not None else None,
            "using": kwargs.get("postgresql_using"),
        }

    def drop_index(self, name: str, table_name: str | None = None, **kwargs: Any) -> None:
        if table_name:
            self._table(table_name)["indexes"].pop(name, None)
            return
        for table in self.schema.values():
            table["indexes"].pop(name, None)

    def create_check_constraint(self, name: str, table: str, condition: Any, **kwargs: Any) -> None:
        self._table(table)["checks"][name] = str(condition)

    def create_unique_constraint(
        self, name: str, table: str, columns: list[str], **kwargs: Any
    ) -> None:
        self._table(table)["uniques"][name] = list(columns)

    def create_foreign_key(
        self,
        name: str,
        table: str,
        referent: str,
        local_cols: list[str],
        remote_cols: list[str],
        **kwargs: Any,
    ) -> None:
        self._table(table)["fks"][name] = {
            "cols": list(local_cols),
            "ondelete": kwargs.get("ondelete"),
        }

    def drop_constraint(self, name: str, table: str | None = None, **kwargs: Any) -> None:
        if not table:
            return
        entry = self._table(table)
        entry["checks"].pop(name, None)
        entry["uniques"].pop(name, None)
        entry["fks"].pop(name, None)

    # -- bewusst wirkungslos ----------------------------------------------
    def execute(self, *args: Any, **kwargs: Any) -> None:
        """Raw-SQL laesst sich ohne DB nicht auswerten."""

    def bulk_insert(self, *args: Any, **kwargs: Any) -> None:
        """Daten sind fuer den Strukturvergleich irrelevant."""

    def get_bind(self) -> _FakeBind:
        return _FakeBind()

    def get_context(self) -> _FakeContext:
        return _FakeContext()

    def batch_alter_table(self, table: str, *args: Any, **kwargs: Any) -> "_BatchContext":
        return _BatchContext(self, table)


class _BatchContext:
    def __init__(self, recorder: SchemaRecorder, table: str) -> None:
        self._recorder = recorder
        self._table = table

    def __enter__(self) -> "_BatchOps":
        return _BatchOps(self._recorder, self._table)

    def __exit__(self, *exc_info: Any) -> bool:
        return False


class _BatchOps:
    def __init__(self, recorder: SchemaRecorder, table: str) -> None:
        self._recorder = recorder
        self._table = table

    def add_column(self, column, **kw):
        self._recorder.add_column(self._table, column, **kw)

    def drop_column(self, column, **kw):
        self._recorder.drop_column(self._table, column, **kw)

    def alter_column(self, column, **kw):
        self._recorder.alter_column(self._table, column, **kw)

    def create_index(self, name, columns, **kw):
        self._recorder.create_index(name, self._table, columns, **kw)

    def drop_index(self, name, **kw):
        self._recorder.drop_index(name, self._table, **kw)

    def create_check_constraint(self, name, condition, **kw):
        self._recorder.create_check_constraint(name, self._table, condition, **kw)

    def create_unique_constraint(self, name, columns, **kw):
        self._recorder.create_unique_constraint(name, self._table, columns, **kw)

    def create_foreign_key(self, name, referent, local_cols, remote_cols, **kw):
        self._recorder.create_foreign_key(
            name, self._table, referent, local_cols, remote_cols, **kw
        )

    def drop_constraint(self, name, **kw):
        self._recorder.drop_constraint(name, self._table, **kw)


class _FakeInspector:
    def __init__(self, recorder: SchemaRecorder) -> None:
        self._recorder = recorder

    def get_table_names(self, **kwargs):
        return list(self._recorder.schema)

    def has_table(self, table, **kwargs):
        return table in self._recorder.schema

    def get_columns(self, table, **kwargs):
        entry = self._recorder._table(table)
        return [
            {"name": name, "type": data["type"], "nullable": data["nullable"]}
            for name, data in entry["columns"].items()
        ]

    def get_indexes(self, table, **kwargs):
        entry = self._recorder._table(table)
        return [
            {"name": name, "column_names": data["cols"], "unique": data["unique"]}
            for name, data in entry["indexes"].items()
        ]

    def get_check_constraints(self, table, **kwargs):
        entry = self._recorder._table(table)
        return [{"name": name, "sqltext": text} for name, text in entry["checks"].items()]

    def get_unique_constraints(self, table, **kwargs):
        entry = self._recorder._table(table)
        return [{"name": name, "column_names": cols} for name, cols in entry["uniques"].items()]

    def get_foreign_keys(self, table, **kwargs):
        entry = self._recorder._table(table)
        return [{"name": name, "constrained_columns": data["cols"]} for name, data in entry["fks"].items()]

    def get_pk_constraint(self, table, **kwargs):
        return {"constrained_columns": self._recorder._table(table)["pk"]}


class _OpProxy:
    def __init__(self, recorder: SchemaRecorder) -> None:
        self._recorder = recorder

    def __getattr__(self, item: str) -> Any:
        return getattr(self._recorder, item)


def replay(modules: dict[str, Any], order: list[str]) -> Schema:
    """Fuehrt ``upgrade()`` aller Module in ``order`` gegen den Recorder aus."""
    recorder = SchemaRecorder()
    proxy = _OpProxy(recorder)
    inspector = _FakeInspector(recorder)

    original_inspect = sa.inspect

    def patched_inspect(obj, **kwargs):
        if isinstance(obj, (_FakeBind, _FakeDialect)):
            return inspector
        return original_inspect(obj, **kwargs)

    import alembic

    original_alembic_op = getattr(alembic, "op", None)
    sa.inspect = patched_inspect
    alembic.op = proxy
    try:
        for revision in order:
            module = modules[revision]
            module.op = proxy
            module_sa = getattr(module, "sa", None)
            if module_sa is not None:
                module_sa.inspect = patched_inspect
            module.upgrade()
    finally:
        sa.inspect = original_inspect
        if original_alembic_op is not None:
            alembic.op = original_alembic_op

    return recorder.schema
