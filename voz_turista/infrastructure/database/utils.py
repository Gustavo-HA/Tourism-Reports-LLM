import pandas as pd


def read_restmex_dataframe(parquet_path: str) -> pd.DataFrame:
    """Obtener y validar el dataset RESTMEX a partir del archivo Parquet."""
    df = pd.read_parquet(parquet_path)

    # Validar columnas requeridas
    required_cols = {"text", "Lugar", "Tipo", "Pueblo", "Calificacion", "FechaEstadia"}
    missing = required_cols.difference(set(df.columns))
    if missing:
        raise ValueError(
            f"Faltan columnas requeridas en el archivo Parquet: {sorted(missing)}"
        )

    return df
