import json
import pandas as pd
from scraper.utils import save_json, save_csv, save_excel


def test_save_and_load_json(tmp_path):
    rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    p = tmp_path / "out.json"
    save_json(rows, str(p))
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data == rows


def test_save_and_load_csv(tmp_path):
    rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    p = tmp_path / "out.csv"
    save_csv(rows, str(p))
    df = pd.read_csv(str(p))
    assert list(df.columns) == ["a", "b"]
    assert df.shape[0] == 2


def test_save_and_load_excel(tmp_path):
    rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    p = tmp_path / "out.xlsx"
    save_excel(rows, str(p))
    df = pd.read_excel(str(p))
    assert list(df.columns) == ["a", "b"]
    assert df.shape[0] == 2
