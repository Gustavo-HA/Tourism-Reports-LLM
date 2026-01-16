import re
import unicodedata

import pandas as pd


def normalize_town_name(town: str) -> str:
    """Normaliza nombres de pueblos a un formato estable (snake, ascii, minúsculas)."""
    text = str(town or "").strip().replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().replace(" ", "_")


def prepare_restmex_dataframe(csv_path: str) -> pd.DataFrame:
    """Limpia, valida y desduplica el CSV de restmex."""
    df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")

    required_cols = {"text", "Polarity", "Town", "Region", "Type"}
    missing = required_cols.difference(set(df.columns))
    if missing:
        raise ValueError(f"Faltan columnas requeridas en el CSV: {sorted(missing)}")

    df = df.copy()
    df["text"] = df["text"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df["text"] != ""]

    df["Polarity"] = pd.to_numeric(df["Polarity"], errors="coerce")
    df = df.dropna(subset=["Polarity", "Town", "Region", "Type"])

    df["TownNormalized"] = df["Town"].apply(normalize_town_name)

    before = len(df)
    df = df.drop_duplicates(subset=["text"])
    dropped = before - len(df)
    print(f"Registros tras limpieza: {len(df)} (duplicados descartados: {dropped})")
    return df
