from pathlib import Path
from src.importers import parse_alzex, load_budget, load_extraordinary
ROOT=Path(__file__).parents[1]
def test_alzex():
    p=ROOT/'data/initial/alzex_julio_2026.csv';df=parse_alzex(p.read_bytes(),p.name)
    assert len(df)==123 and round(df.amount.sum(),2)==89872.53 and df.fingerprint.is_unique
def test_budget():
    df=load_budget(ROOT/'data/initial/ppto_2026_morus.xlsx');assert round(df.monthly_budget.sum())==124337
def test_extra():
    df=load_extraordinary(ROOT/'data/initial/gastos_no_programados.xlsx');assert round(df.amount.sum(),0)==340155
