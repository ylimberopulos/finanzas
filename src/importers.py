from __future__ import annotations
import hashlib
from io import BytesIO
import pandas as pd

ALIASES = {
    "Fara Ciencias": "Ciencias", "Fara Cuidados": "Cuidados",
    "Fara Actividades": "Actividades Fara", "Fara Juguetes": "Ropa y artículos Fara",
}
MONTHS_ES = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5,
             "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9,
             "Octubre": 10, "Noviembre": 11, "Diciembre": 12}

def normalize_category(value: str) -> str:
    text = str(value).replace("\n", " / ").strip().split(" / ")[0].strip()
    aliases = {"Compras Personales": "Compras personales", "Ropa y Articulos Fara": "Ropa y artículos Fara",
        "Fara Ciencias": "Ciencias", "Fara Cuidados": "Cuidados", "Fara Actividades": "Actividades Fara",
        "Fara Juguetes": "Ropa y artículos Fara", "Ropa y Art Fara": "Ropa y artículos Fara",
        "Bienes Inmuebles": "Bienes inmuebles"}
    return aliases.get(text, text)

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
        "category": split[0].replace(ALIASES).map(normalize_category),
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
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw.iloc[:, :3].copy(); raw.columns = ["category", "detail", "monthly_budget"]
    raw["category"] = raw["category"].ffill().map(normalize_category)
    raw["detail"] = raw["detail"].fillna("").astype(str).str.strip()
    raw["monthly_budget"] = pd.to_numeric(raw["monthly_budget"], errors="coerce")
    return raw.dropna(subset=["monthly_budget"]).query("monthly_budget > 0 and detail != ''")

def load_compiled_monthly(path: str, year: int = 2026) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=0)
    raw.columns = [str(c).strip() for c in raw.columns]
    category = raw.iloc[:, 0].ffill().map(normalize_category)
    detail = raw.iloc[:, 1].fillna("").astype(str).str.strip()
    records = []
    for month_name, month_num in MONTHS_ES.items():
        if month_name not in raw.columns: continue
        values = pd.to_numeric(raw[month_name], errors="coerce").fillna(0)
        valid = (~detail.str.lower().isin(["", "gasto mensual", "total acumulados"])) & (values != 0)
        for cat, subcat, value in zip(category[valid], detail[valid], values[valid]):
            records.append({"year": year, "month": month_num, "month_name": month_name,
                            "category": cat, "subcategory": subcat or "Sin detalle",
                            "amount": abs(float(value)), "source": "Consolidado"})
    return pd.DataFrame(records)

def load_extraordinary(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=0, header=None)
    left = raw.iloc[:, :3].copy(); left.columns = ["month", "concept", "amount"]
    left["amount"] = pd.to_numeric(left["amount"], errors="coerce")
    return left.dropna(subset=["concept", "amount"])
