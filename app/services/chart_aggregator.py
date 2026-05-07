import pandas as pd
import numpy as np
from typing import Any, Optional, Dict, List


def _safe_float(val: Any) -> Any:
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        return None
    return val


def _df_to_serializable(df: pd.DataFrame) -> List[Dict[str, Any]]:
    records = df.to_dict(orient="records")
    clean = []
    for row in records:
        clean_row: Dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, (np.integer,)):
                v = int(v)
            elif isinstance(v, (np.floating,)):
                v = _safe_float(float(v))
            elif isinstance(v, pd.Timestamp):
                v = v.strftime("%Y-%m-%d")
            clean_row[str(k)] = v
        clean.append(clean_row)
    return clean


def aggregate_bar(
    df: pd.DataFrame, x_axis: str, y_axis: Optional[str], aggregation: str
) -> Dict[str, Any]:
    df = df.dropna(subset=[x_axis])

    if aggregation == "count" or not y_axis:
        result = df.groupby(x_axis).size().reset_index(name="value")
        result = result.sort_values("value", ascending=False).head(15)
        data = _df_to_serializable(result.rename(columns={x_axis: "name"}))
        return {"data": data, "x_key": "name", "y_keys": ["value"], "chart_type": "bar"}

    df = df.dropna(subset=[y_axis])
    agg_func = {"sum": "sum", "avg": "mean"}.get(aggregation, "sum")
    result = df.groupby(x_axis)[y_axis].agg(agg_func).reset_index()
    result.columns = ["name", "value"]
    result = result.sort_values("value", ascending=False).head(15)
    data = _df_to_serializable(result)
    return {"data": data, "x_key": "name", "y_keys": ["value"], "chart_type": "bar"}


def aggregate_line(
    df: pd.DataFrame, x_axis: str, y_axis: Optional[str], aggregation: str
) -> Dict[str, Any]:
    df = df.dropna(subset=[x_axis])
    if y_axis:
        df = df.dropna(subset=[y_axis])

    # Try to convert to datetime
    if not pd.api.types.is_datetime64_any_dtype(df[x_axis]):
        try:
            df = df.copy()
            df[x_axis] = pd.to_datetime(df[x_axis])
        except Exception:
            pass

    agg_func = {"sum": "sum", "avg": "mean", "count": "count"}.get(aggregation, "sum")

    if not y_axis:
        result = df.groupby(x_axis).size().reset_index(name="value")
    else:
        result = df.groupby(x_axis)[y_axis].agg(agg_func).reset_index()
        result.columns = [x_axis, "value"]

    result = result.sort_values(x_axis)

    # Resample if too many points
    if len(result) > 100:
        result = result.iloc[::max(1, len(result) // 100)]

    # Convert datetime to string
    if pd.api.types.is_datetime64_any_dtype(result[x_axis]):
        result = result.copy()
        result[x_axis] = result[x_axis].dt.strftime("%Y-%m-%d")

    result = result.rename(columns={x_axis: "name"})
    data = _df_to_serializable(result)
    return {"data": data, "x_key": "name", "y_keys": ["value"], "chart_type": "line"}


def aggregate_pie(
    df: pd.DataFrame, x_axis: str, y_axis: Optional[str], aggregation: str
) -> Dict[str, Any]:
    df = df.dropna(subset=[x_axis])

    if not y_axis or aggregation == "count":
        counts = df[x_axis].value_counts()
    else:
        df = df.dropna(subset=[y_axis])
        agg_func = {"sum": "sum", "avg": "mean"}.get(aggregation, "sum")
        counts = df.groupby(x_axis)[y_axis].agg(agg_func).sort_values(ascending=False)

    top = counts.head(7)
    other_val = counts.iloc[7:].sum() if len(counts) > 7 else 0

    rows: List[Dict[str, Any]] = [
        {"name": str(k), "value": _safe_float(float(v))} for k, v in top.items()
    ]
    if other_val > 0:
        rows.append({"name": "Otros", "value": _safe_float(float(other_val))})

    return {"data": rows, "x_key": "name", "y_keys": ["value"], "chart_type": "pie"}


def aggregate_scatter(df: pd.DataFrame, x_axis: str, y_axis: str) -> Dict[str, Any]:
    df = df.dropna(subset=[x_axis, y_axis])

    if len(df) > 1000:
        df = df.sample(1000, random_state=42)

    result = df[[x_axis, y_axis]].copy()
    result.columns = pd.Index(["x", "y"])
    data = _df_to_serializable(result)
    return {"data": data, "x_key": "x", "y_keys": ["y"], "chart_type": "scatter"}


def get_chart_data(
    df: pd.DataFrame, chart_type: str, parameters: Dict[str, Any]
) -> Dict[str, Any]:
    x_axis = parameters.get("x_axis", "")
    y_axis = parameters.get("y_axis")
    aggregation = parameters.get("aggregation", "none")

    if not x_axis or x_axis not in df.columns:
        raise ValueError(f"Columna x_axis '{x_axis}' no encontrada")
    if y_axis and y_axis not in df.columns:
        raise ValueError(f"Columna y_axis '{y_axis}' no encontrada")

    if chart_type == "bar":
        return aggregate_bar(df, x_axis, y_axis, aggregation)
    elif chart_type == "line":
        return aggregate_line(df, x_axis, y_axis, aggregation)
    elif chart_type == "pie":
        return aggregate_pie(df, x_axis, y_axis, aggregation)
    elif chart_type == "scatter":
        if not y_axis:
            raise ValueError("scatter requiere y_axis")
        return aggregate_scatter(df, x_axis, y_axis)
    else:
        raise ValueError(f"Tipo de gráfico no soportado: {chart_type}")
