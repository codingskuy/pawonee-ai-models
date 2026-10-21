"""Fixture bersama uji pawonee-ai-models."""

import copy
import json
import sys
from pathlib import Path

import pytest

DASAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASAR / "eval"))


def muat(rel: str):
    return json.loads((DASAR / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def skema():
    return muat("models/schema.json")


@pytest.fixture(scope="session")
def bank_asli():
    return muat("models/bank_resep_grade2.json")


@pytest.fixture()
def bank(bank_asli):
    return copy.deepcopy(bank_asli)


@pytest.fixture(scope="session")
def referensi():
    return muat("models/referensi_bahan.json")
