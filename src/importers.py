from __future__ import annotations
import hashlib
from io import BytesIO
import pandas as pd

ALIASES = {
    "Fara Ciencias": "Ciencias", "Fara Cuidados": "Cuidados",
    "Fara Actividades": "Actividades Fara", "Fara Juguetes": "Ropa y artículos Fara",
}

def _read_csv(data: bytes) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-16", "latin1"):
        try:
            return pd.read_csv(BytesIO(data), encoding=encoding, sep=None, engine="python")
        except (UnicodeError, pd.errors.ParserError):
            continue
    raise ValueError("No fue posible reconocer la codificación del CSV.")

def parse_alzex(data: bytes, filename: str) -> pd.DataFrame:
    df = _read_csv(data)
    required = {"Descripción", "Fecha", "Suma", "Categoría"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError("Faltan columnas de Alzex: " + ", ".join(sorted(missing)))
    split = df["Categoría"].fillna("Sin clasificar").astype(str).str.split(":", n=1, expand=True)
    out = pd.DataFrame({
        "description": df["Descripción"].fillna("").astype(str).str.strip(),
        "movement_date": pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce"),
        "amount": pd.to_numeric(df["Suma"], errors="coerce").fillna(0),
        "category": split[0].replace(ALIASES).str.strip(),
        "subcategory": split[1].fillna("").str.strip() if split.shape[1] > 1 else "",
        "family_member": df.get("Miembro de la Familia", ""),
        "tag": df.get("Etiqueta", ""), "account": df.get("Cuenta", ""),
        "source_file": filename,
    }).dropna(subset=["movement_date"])
    out["amount"] = out["amount"].abs()
    def fingerprint(r):
        raw = "|".join([r["movement_date"].strftime("%Y-%m-%d"), f'{r["amount"]:.2f}', r["description"].lower(), str(r["account"]).lower()])
        return hashlib.sha256(raw.encode()).hexdigest()
    out["fingerprint"] = out.apply(fingerprint, axis=1)
    out["movement_date"] = out["movement_date"].dt.strftime("%Y-%m-%d")
    return out.drop_duplicates("fingerprint")

def load_budget(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=0)
    raw = raw.iloc[:, :3].copy(); raw.columns = ["category", "detail", "monthly_budget"]
    raw["category"] = raw["category"].ffill().astype(str).str.replace("\n", " / ", regex=False).str.strip()
    raw["detail"] = raw["detail"].fillna("").astype(str).str.strip()
    raw["monthly_budget"] = pd.to_numeric(raw["monthly_budget"], errors="coerce")
    return raw.dropna(subset=["monthly_budget"]).query("monthly_budget > 0 and detail != ''")

def load_extraordinary(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=0, header=None)
    left = raw.iloc[:, :3].copy(); left.columns = ["month", "concept", "amount"]
    left["amount"] = pd.to_numeric(left["amount"], errors="coerce")
    return left.dropna(subset=["concept", "amount"])
