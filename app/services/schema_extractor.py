import pandas as pd
from typing import Any, Dict, List


def extract_schema(df: pd.DataFrame) -> Dict[str, Any]:
    schema: Dict[str, Any] = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": [],
        "sample_rows": [],
    }

    # Try to convert string columns that look like dates
    for col in df.select_dtypes(include=["object"]).columns:
        try:
            converted = pd.to_datetime(df[col], infer_datetime_format=True)
            if converted.notna().sum() > len(df) * 0.7:
                df[col] = converted
        except Exception:
            pass

    for col in df.columns:
        dtype = str(df[col].dtype)
        col_info: Dict[str, Any] = {
            "name": col,
            "dtype": dtype,
            "null_count": int(df[col].isna().sum()),
            "cardinality": int(df[col].nunique()),
        }

        if pd.api.types.is_numeric_dtype(df[col]):
            desc = df[col].describe()
            col_info["stats"] = {
                "min": round(float(desc["min"]), 2) if not pd.isna(desc["min"]) else None,
                "max": round(float(desc["max"]), 2) if not pd.isna(desc["max"]) else None,
                "mean": round(float(desc["mean"]), 2) if not pd.isna(desc["mean"]) else None,
                "std": round(float(desc["std"]), 2) if not pd.isna(desc["std"]) else None,
            }
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            col_info["date_range"] = {
                "min": str(df[col].min()),
                "max": str(df[col].max()),
            }
        else:
            top_values = df[col].value_counts().head(5)
            col_info["top_values"] = {str(k): int(v) for k, v in top_values.items()}

        schema["columns"].append(col_info)

    # Sample rows (convert to serializable)
    sample = df.head(5).copy()
    for col in sample.select_dtypes(include=["datetime64"]).columns:
        sample[col] = sample[col].dt.strftime("%Y-%m-%d")
    schema["sample_rows"] = sample.fillna("").to_dict(orient="records")

    return schema


def schema_to_text(schema: Dict[str, Any]) -> str:
    lines: List[str] = [
        f"Dataset: {schema['total_rows']} filas, {schema['total_columns']} columnas\n",
        "Columnas:",
    ]
    for col in schema["columns"]:
        line = f"  - {col['name']} (tipo: {col['dtype']}, valores únicos: {col['cardinality']}, nulos: {col['null_count']})"
        if "stats" in col:
            s = col["stats"]
            line += f"\n    Estadísticas: min={s['min']}, max={s['max']}, media={s['mean']}, std={s['std']}"
        if "date_range" in col:
            line += f"\n    Rango de fechas: {col['date_range']['min']} a {col['date_range']['max']}"
        if "top_values" in col:
            top = ", ".join(f"{k}({v})" for k, v in list(col["top_values"].items())[:5])
            line += f"\n    Valores más frecuentes: {top}"
        lines.append(line)

    lines.append("\nMuestra de 5 filas:")
    for row in schema["sample_rows"]:
        lines.append(f"  {row}")

    return "\n".join(lines)
