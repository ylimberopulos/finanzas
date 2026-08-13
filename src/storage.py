from __future__ import annotations
import streamlit as st
from supabase import create_client

def client():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)

def fetch(table: str):
    db = client()
    if db is None: return []
    return db.table(table).select("*").execute().data or []

def insert_rows(table: str, rows: list[dict]):
    db = client()
    if db is None: raise RuntimeError("Configura SUPABASE_URL y SUPABASE_KEY en los secretos de la aplicación.")
    if not rows: return []
    return db.table(table).upsert(rows, on_conflict="fingerprint" if table == "movements" else None).execute().data or []

def insert_one(table: str, row: dict):
    db = client()
    if db is None: raise RuntimeError("Configura Supabase antes de guardar información.")
    return db.table(table).insert(row).execute().data
