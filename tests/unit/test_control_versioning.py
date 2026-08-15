from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from apps.api.app.database import Base
from apps.api.app.db_models import ControlRow
from apps.api.app.service import register_control
from engine.aml.controls import load_control

ROOT = Path(__file__).resolve().parents[2]


def test_same_control_version_cannot_change_definition():
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    source = load_control(ROOT / "controls/AML-RMF-001.yaml")
    with Session(database) as session:
        register_control(session, source)
        session.commit()
        changed = source.model_copy(update={"severity": "critical"})
        with pytest.raises(ValueError, match="increment its version"):
            register_control(session, changed)


def test_new_control_version_preserves_runtime_toggle():
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    source = load_control(ROOT / "controls/AML-RMF-001.yaml")
    with Session(database) as session:
        active = register_control(session, source)
        state = session.get(ControlRow, source.id)
        state.enabled = False
        session.commit()
        newer = source.model_copy(update={"version": source.version + 1})
        resolved = register_control(session, newer)
        assert active.enabled is True
        assert resolved.enabled is False
