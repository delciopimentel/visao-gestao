import io
import re
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Visão de Gestão", page_icon="📊", layout="wide")

# =========================================================
# CONFIG
# =========================================================
APP_TITLE = "Visão de Gestão"
APP_SUBTITLE = (
    "Transforme exportações do seu ERP em apoio direto à decisão: "
    "vendas, clientes, custos e faturação."
)

EXPECTED_VENDAS = ["Data", "Cliente", "Total"]
EXPECTED_BALANCETE = ["Conta", "Descricao", "Saldo"]
EXPECTED_FOLHA = ["Data", "Tipo", "Categoria", "Valor"]
EXPECTED_CLIENTES = ["Cliente"]

SUGESTOES_FILE = Path("sugestoes_utilizadores.csv")

COUNTRY_OPTIONS = ["Automático", "Portugal", "Angola"]

CATEGORIA_TO_CLASSE = {
    "compras": "61",
    "mercadoria": "61",
    "mercadorias": "61",
    "materias": "61",
    "matérias": "61",
    "materiasprimas": "61",
    "matériasprimas": "61",
    "fornecimentos": "62",
    "servicos": "62",
    "serviços": "62",
    "aguaeluz": "62",
    "águaeluz": "62",
    "renda": "62",
    "rendas": "62",
    "transporte": "62",
    "transportes": "62",
    "marketing": "62",
    "salarios": "63",
    "salários": "63",
    "pessoal": "63",
    "amortizacoes": "64",
    "amortizações": "64",
    "juros": "68",
    "financeiros": "68",
    "outros": "69",
}

# =========================================================
# STYLE
# =========================================================
st.markdown(
    """
    <style>
        .stApp {
            background: #f5f7fb;
        }

        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }

        .hero {
            padding: 1.4rem 1.6rem;
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 22px;
            background: linear-gradient(135deg, #ffffff, #eef4ff);
            margin-bottom: 1.2rem;
            box-shadow: 0 8px 24px rgba(15,23,42,0.06);
        }

        .hero h1 {
            margin: 0;
            font-size: 2.1rem;
            font-weight: 800;
            color: #172033;
        }

        .hero p {
            margin-top: 0.55rem;
            margin-bottom: 0;
            font-size: 1rem;
            color: #475569;
        }

        .section-panel {
            background: #ffffff;
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 22px;
            padding: 1.15rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 6px 18px rgba(15,23,42,0.05);
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 800;
            color: #172033;
            margin-bottom: 0.25rem;
        }

        .section-subtitle {
            font-size: 0.92rem;
            color: #64748b;
            margin-bottom: 0.9rem;
        }

        .kpi-box {
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 22px;
            padding: 1.05rem;
            background: #ffffff;
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
            min-height: 125px;
            position: relative;
            overflow: hidden;
        }

        .kpi-box:before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            height: 100%;
            width: 5px;
            background: #2563eb;
        }

        .kpi-icon {
            font-size: 1.3rem;
            margin-bottom: 0.25rem;
        }

        .kpi-label {
            font-size: 0.86rem;
            color: #64748b;
            margin-bottom: 0.35rem;
            font-weight: 600;
        }

        .kpi-value {
            font-size: 1.7rem;
            font-weight: 850;
            color: #172033;
            line-height: 1.1;
        }

        .kpi-sub {
            font-size: 0.85rem;
            color: #64748b;
            margin-top: 0.45rem;
        }

        .alert-box {
            border-radius: 18px;
            padding: 0.95rem 1rem;
            margin-bottom: 0.75rem;
            border: 1px solid rgba(15,23,42,0.08);
            background: white;
            box-shadow: 0 4px 12px rgba(15,23,42,0.04);
        }

        .alert-red {
            background: #fff5f5;
            border-color: rgba(239,68,68,0.26);
        }

        .alert-yellow {
            background: #fffbeb;
            border-color: rgba(245,158,11,0.28);
        }

        .alert-green {
            background: #f0fdf4;
            border-color: rgba(34,197,94,0.28);
        }

        .alert-title {
            font-weight: 800;
            margin-bottom: 0.25rem;
            font-size: 0.96rem;
            color: #172033;
        }

        .alert-text {
            font-size: 0.94rem;
            color: #334155;
        }

        .template-box {
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 20px;
            padding: 1rem;
            background: white;
            margin-bottom: 1rem;
            box-shadow: 0 6px 18px rgba(15,23,42,0.05);
        }
    </style>
    """,
    unsafe_allow_html=True,
)
# =========================================================
# HELPERS
# =========================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        str(c)
        .strip()
        .replace(" ", "")
        .replace("_", "")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "")
        .replace("/", "")
        .lower()
        for c in df.columns
    ]
    return df


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return (
        str(value)
        .strip()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .lower()
    )


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    filename = uploaded_file.name.lower()
    content = uploaded_file.getvalue()

    if filename.endswith(".csv"):
        for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                return pd.read_csv(
                    io.BytesIO(content),
                    sep=None,
                    engine="python",
                    dtype=str,
                    encoding=enc,
                )
            except Exception:
                pass

        raise ValueError("Não foi possível ler o CSV. Verifique separador e encoding.")

    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        return pd.read_excel(io.BytesIO(content), dtype=str)

    raise ValueError("Formato não suportado. Use CSV ou Excel.")


def clean_number(series: pd.Series) -> pd.Series:
    s = (
        series.astype(str)
        .str.replace("€", "", regex=False)
        .str.replace("AOA", "", regex=False)
        .str.replace("Kz", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(s, errors="coerce")


def dataframe_to_csv_download(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")


def standardize_vendas(df: pd.DataFrame) -> pd.DataFrame:
    raw = normalize_columns(df)

    rename_map = {
        "data": "Data",
        "datadoc": "Data",
        "datadocumento": "Data",
        "cliente": "Cliente",
        "entidade": "Cliente",
        "codcliente": "Cliente",
        "nomecliente": "Cliente",
        "documento": "Documento",
        "numdoc": "Documento",
        "numerodocumento": "Documento",
        "tipodoc": "Documento",
        "total": "Total",
        "totaldocumento": "Total",
        "valor": "Total",
        "valortotal": "Total",
        "totalliquido": "Total",
        "totallíquido": "Total",
        "totaliliquido": "Total",
        "totalilíquido": "Total",
    }

    raw = raw.rename(columns={c: rename_map.get(c, c) for c in raw.columns})
    cols = [c for c in ["Data", "Cliente", "Documento", "Total"] if c in raw.columns]
    out = raw[cols].copy()

    if "Data" in out.columns:
        out["Data"] = pd.to_datetime(out["Data"], dayfirst=True, errors="coerce")

    if "Total" in out.columns:
        out["Total"] = clean_number(out["Total"])

    if "Documento" not in out.columns:
        out["Documento"] = "N/D"

    out = out.dropna(subset=[c for c in ["Data", "Cliente", "Total"] if c in out.columns])
    return out


def standardize_balancete(df: pd.DataFrame) -> pd.DataFrame:
    raw = normalize_columns(df)

    rename_map = {
        "conta": "Conta",
        "contasnc": "Conta",
        "codigo": "Conta",
        "descricao": "Descricao",
        "descrição": "Descricao",
        "descricaoconta": "Descricao",
        "descriçãoconta": "Descricao",
        "contadescricao": "Descricao",
        "contadescrição": "Descricao",
        "saldo": "Saldo",
        "saldofinal": "Saldo",
        "valor": "Saldo",
        "debito": "Debito",
        "débito": "Debito",
        "credito": "Credito",
        "crédito": "Credito",
    }

    raw = raw.rename(columns={c: rename_map.get(c, c) for c in raw.columns})

    if "Saldo" not in raw.columns and {"Debito", "Credito"}.issubset(set(raw.columns)):
        raw["Saldo"] = clean_number(raw["Debito"]) - clean_number(raw["Credito"])

    cols = [c for c in ["Conta", "Descricao", "Saldo"] if c in raw.columns]
    out = raw[cols].copy()

    if "Saldo" in out.columns:
        out["Saldo"] = clean_number(out["Saldo"])

    if "Descricao" not in out.columns:
        out["Descricao"] = "N/D"

    if "Conta" in out.columns:
        out["Conta"] = out["Conta"].astype(str).str.strip()

    out = out.dropna(subset=[c for c in ["Conta", "Saldo"] if c in out.columns])
    return out


def standardize_folha(df: pd.DataFrame) -> pd.DataFrame:
    raw = normalize_columns(df)

    rename_map = {
        "data": "Data",
        "tipo": "Tipo",
        "categoria": "Categoria",
        "descricao": "Descricao",
        "descrição": "Descricao",
        "valor": "Valor",
        "montante": "Valor",
        "total": "Valor",
    }

    raw = raw.rename(columns={c: rename_map.get(c, c) for c in raw.columns})
    cols = [c for c in ["Data", "Tipo", "Categoria", "Descricao", "Valor"] if c in raw.columns]
    out = raw[cols].copy()

    if "Data" in out.columns:
        out["Data"] = pd.to_datetime(out["Data"], dayfirst=True, errors="coerce")

    if "Valor" in out.columns:
        out["Valor"] = clean_number(out["Valor"])

    if "Descricao" not in out.columns:
        out["Descricao"] = "N/D"

    if "Tipo" in out.columns:
        out["Tipo"] = out["Tipo"].astype(str).str.strip().str.lower()
        out["Tipo"] = out["Tipo"].replace(
            {
                "receita": "proveito",
                "receitas": "proveito",
                "proveito": "proveito",
                "proveitos": "proveito",
                "venda": "proveito",
                "vendas": "proveito",
                "custo": "custo",
                "custos": "custo",
                "despesa": "custo",
                "despesas": "custo",
                "gasto": "custo",
                "gastos": "custo",
            }
        )

    if "Categoria" in out.columns:
        out["Categoria"] = out["Categoria"].astype(str).str.strip()

    out = out.dropna(subset=[c for c in ["Data", "Tipo", "Categoria", "Valor"] if c in out.columns])
    return out


def standardize_clientes(df: pd.DataFrame) -> pd.DataFrame:
    raw = normalize_columns(df)

    rename_map = {
        "cliente": "Cliente",
        "nomecliente": "Cliente",
        "entidade": "Cliente",
        "codcliente": "CodigoCliente",
        "codigo": "CodigoCliente",
        "nif": "NIF",
        "nifcliente": "NIF",
        "segmento": "Segmento",
        "regiao": "Regiao",
        "região": "Regiao",
        "pais": "Pais",
        "país": "Pais",
        "email": "Email",
        "telefone": "Telefone",
    }

    raw = raw.rename(columns={c: rename_map.get(c, c) for c in raw.columns})
    cols = [c for c in ["Cliente", "CodigoCliente", "NIF", "Segmento", "Regiao", "Pais", "Email", "Telefone"] if c in raw.columns]

    out = raw[cols].copy()

    if "Cliente" in out.columns:
        out["Cliente"] = out["Cliente"].astype(str).str.strip()

    return out.dropna(subset=[c for c in ["Cliente"] if c in out.columns])


def folha_to_balancete(df_folha: pd.DataFrame) -> pd.DataFrame:
    if df_folha.empty:
        return pd.DataFrame(columns=["Conta", "Descricao", "Saldo"])

    df = df_folha.copy()
    df["Categoria_norm"] = df["Categoria"].apply(normalize_text)

    custos = df[df["Tipo"] == "custo"].copy()
    custos["Conta"] = custos["Categoria_norm"].map(CATEGORIA_TO_CLASSE).fillna("69")
    custos["Descricao"] = custos["Categoria"]

    bal_custos = (
        custos.groupby(["Conta", "Descricao"], as_index=False)["Valor"]
        .sum()
        .rename(columns={"Valor": "Saldo"})
    )

    return bal_custos


def validate_columns(df: pd.DataFrame, required_cols: list[str]) -> tuple[list[str], list[str]]:
    existing = list(df.columns)
    missing = [c for c in required_cols if c not in existing]
    return existing, missing


def classify_account_type(conta: str, descricao: str, pais: str = "Automático") -> str:
    conta = normalize_text(conta)
    descricao = normalize_text(descricao)

    if conta.startswith("6"):
        return "Custo"

    if conta.startswith("7"):
        return "Proveito"

    custo_keywords = [
        "custo", "custos", "gasto", "gastos", "despesa", "despesas",
        "fornecimento", "servico", "serviço", "salario", "salário",
        "pessoal", "renda", "energia", "agua", "água", "juros",
        "financeiro", "amortizacao", "amortização", "transporte",
        "marketing", "compras", "mercadorias",
    ]

    proveito_keywords = [
        "proveito", "proveitos", "venda", "vendas", "receita", "receitas",
        "servicoprestado", "serviçoprestado", "prestacao", "prestação",
        "faturacao", "faturação",
    ]

    for kw in custo_keywords:
        if kw in descricao:
            return "Custo"

    for kw in proveito_keywords:
        if kw in descricao:
            return "Proveito"

    return "Outro"


def safe_pct(current: float, base: float) -> float | None:
    if base is None or pd.isna(base) or base == 0:
        return None
    return ((current - base) / base) * 100


def sum_between(df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp) -> float:
    mask = (df["Data"] >= start_date) & (df["Data"] <= end_date)
    return float(df.loc[mask, "Total"].sum())


def date_bounds(reference_date: pd.Timestamp) -> dict:
    ref = pd.Timestamp(reference_date).normalize()

    week_start = ref - pd.Timedelta(days=ref.weekday())
    week_prev_start = week_start - pd.Timedelta(days=7)
    week_prev_end = ref - pd.Timedelta(days=7)

    month_start = ref.replace(day=1)
    prev_month_end = month_start - pd.Timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    same_day_prev_month = prev_month_start + pd.Timedelta(days=min(ref.day, prev_month_end.day) - 1)

    year_start = ref.replace(month=1, day=1)
    prev_year_same_day = ref - pd.DateOffset(years=1)
    prev_year_start = prev_year_same_day.replace(month=1, day=1)

    same_period_last_year_month_start = month_start - pd.DateOffset(years=1)
    same_period_last_year_month_end = ref - pd.DateOffset(years=1)

    return {
        "ref": ref,
        "week_start": week_start,
        "week_prev_start": week_prev_start,
        "week_prev_end": week_prev_end,
        "month_start": month_start,
        "prev_month_start": prev_month_start,
        "prev_month_same_day": same_day_prev_month,
        "year_start": year_start,
        "prev_year_start": prev_year_start,
        "prev_year_same_day": prev_year_same_day,
        "same_period_last_year_month_start": same_period_last_year_month_start,
        "same_period_last_year_month_end": same_period_last_year_month_end,
    }


def sanitize_user_feedback(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text[:500]


def validate_user_feedback(text: str) -> tuple[bool, str]:
    if not text:
        return False, "Escreva uma sugestão antes de enviar."

    if len(text) < 8:
        return False, "A sugestão é demasiado curta."

    blocked_patterns = [
        r"<script",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"<iframe",
        r"<img",
        r"powershell",
        r"cmd\.exe",
        r"bash -c",
        r"rm -rf",
        r"wget ",
        r"curl ",
        r"eval\(",
        r"exec\(",
        r"subprocess",
        r"os\.system",
    ]

    lowered = text.lower()
    for pattern in blocked_patterns:
        if re.search(pattern, lowered):
            return False, "A sugestão contém conteúdo não permitido."

    return True, ""


def save_user_feedback(page_name: str, feedback: str) -> None:
    row = pd.DataFrame(
        [
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "pagina": page_name,
                "sugestao": feedback,
            }
        ]
    )

    file_exists = SUGESTOES_FILE.exists()
    row.to_csv(
        SUGESTOES_FILE,
        mode="a",
        header=not file_exists,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )


def load_feedback() -> pd.DataFrame:
    if not SUGESTOES_FILE.exists():
        return pd.DataFrame(columns=["timestamp", "pagina", "sugestao"])

    try:
        df = pd.read_csv(SUGESTOES_FILE, sep=";", encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=["timestamp", "pagina", "sugestao"])

    for col in ["timestamp", "pagina", "sugestao"]:
        if col not in df.columns:
            df[col] = ""

    return df


def build_metrics(
    df_vendas: pd.DataFrame,
    df_bal: pd.DataFrame,
    df_folha: pd.DataFrame | None = None,
    df_clientes: pd.DataFrame | None = None,
    pais_classificacao: str = "Automático",
) -> dict:
    vendas = df_vendas.copy()
    bal = df_bal.copy()

    if df_clientes is not None and not df_clientes.empty and "Cliente" in df_clientes.columns:
        vendas = vendas.merge(df_clientes, on="Cliente", how="left")

    if "TipoConta" not in bal.columns:
        bal["TipoConta"] = bal.apply(
            lambda row: classify_account_type(
                row.get("Conta", ""),
                row.get("Descricao", ""),
                pais_classificacao,
            ),
            axis=1,
        )

    vendas["Dia"] = vendas["Data"].dt.date
    vendas["Mes_Ordem"] = vendas["Data"].dt.to_period("M").dt.to_timestamp()
    vendas["Mes"] = vendas["Data"].dt.strftime("%b %Y")
    vendas["Ano"] = vendas["Data"].dt.year
    vendas["Semana_Ordem"] = vendas["Data"].dt.to_period("W-MON").apply(lambda r: r.start_time)
    vendas["Semana_Label"] = vendas["Semana_Ordem"].dt.strftime("%d %b %Y")

    faturacao_total = float(vendas["Total"].sum()) if not vendas.empty else 0.0
    reference_date = (
        pd.Timestamp(vendas["Data"].max()).normalize()
        if not vendas.empty
        else pd.Timestamp.today().normalize()
    )
    bounds = date_bounds(reference_date)

    faturacao_diaria = vendas.groupby("Dia", as_index=False)["Total"].sum().sort_values("Dia")

    docs_diarios = (
        vendas.groupby("Dia", as_index=False)["Documento"]
        .count()
        .rename(columns={"Documento": "NumDocs"})
    )

    ticket_diario = faturacao_diaria.merge(docs_diarios, on="Dia", how="left")
    ticket_diario["TicketMedio"] = ticket_diario["Total"] / ticket_diario["NumDocs"].replace(0, pd.NA)

    faturacao_semanal = (
        vendas.groupby(["Semana_Ordem", "Semana_Label"], as_index=False)["Total"]
        .sum()
        .sort_values("Semana_Ordem")
    )

    faturacao_mensal = (
        vendas.groupby(["Mes_Ordem", "Mes"], as_index=False)["Total"]
        .sum()
        .sort_values("Mes_Ordem")
    )

    semana_atual = sum_between(vendas, bounds["week_start"], bounds["ref"])
    semana_anterior = sum_between(vendas, bounds["week_prev_start"], bounds["week_prev_end"])
    mtd = sum_between(vendas, bounds["month_start"], bounds["ref"])
    mtd_mes_anterior = sum_between(vendas, bounds["prev_month_start"], bounds["prev_month_same_day"])
    mtd_homologo = sum_between(
        vendas,
        bounds["same_period_last_year_month_start"],
        bounds["same_period_last_year_month_end"],
    )
    ytd = sum_between(vendas, bounds["year_start"], bounds["ref"])
    ytd_homologo = sum_between(vendas, bounds["prev_year_start"], bounds["prev_year_same_day"])

    var_semana = safe_pct(semana_atual, semana_anterior)
    var_mtd_mes_ant = safe_pct(mtd, mtd_mes_anterior)
    var_mtd_homologo = safe_pct(mtd, mtd_homologo)
    var_ytd_homologo = safe_pct(ytd, ytd_homologo)

    top_clientes = (
        vendas.groupby("Cliente", as_index=False)["Total"]
        .sum()
        .sort_values("Total", ascending=False)
        .head(10)
    )

    top_clientes["Perc_Faturacao"] = (
        (top_clientes["Total"] / faturacao_total) * 100 if faturacao_total else 0.0
    )

    top_clientes_mtd = vendas[
        (vendas["Data"] >= bounds["month_start"]) & (vendas["Data"] <= bounds["ref"])
    ].copy()

    top_clientes_mtd = (
        top_clientes_mtd.groupby("Cliente", as_index=False)["Total"]
        .sum()
        .sort_values("Total", ascending=False)
        .head(10)
        if not top_clientes_mtd.empty
        else pd.DataFrame(columns=["Cliente", "Total"])
    )

    if mtd and not top_clientes_mtd.empty:
        top_clientes_mtd["Perc_Faturacao"] = (top_clientes_mtd["Total"] / mtd) * 100
    elif not top_clientes_mtd.empty:
        top_clientes_mtd["Perc_Faturacao"] = 0.0

    total_top3 = float(top_clientes_mtd.head(3)["Total"].sum()) if not top_clientes_mtd.empty else 0.0
    pct_top3 = (total_top3 / mtd * 100) if mtd else 0.0

    bal_custos = bal[bal["TipoConta"] == "Custo"].copy()
    custos_total = float(bal_custos["Saldo"].sum()) if not bal_custos.empty else 0.0

    if not bal_custos.empty:
        bal_custos["Classe"] = bal_custos["Conta"].astype(str).str[:2]
        custos_por_classe = (
            bal_custos.groupby("Classe", as_index=False)["Saldo"]
            .sum()
            .sort_values("Saldo", ascending=False)
        )
    else:
        custos_por_classe = pd.DataFrame(columns=["Classe", "Saldo"])

    if custos_total and not custos_por_classe.empty:
        custos_por_classe["Perc_Custo"] = (custos_por_classe["Saldo"] / custos_total) * 100
    elif not custos_por_classe.empty:
        custos_por_classe["Perc_Custo"] = 0.0

    proveitos_folha = 0.0
    custos_folha = 0.0

    if df_folha is not None and not df_folha.empty:
        proveitos_folha = float(df_folha.loc[df_folha["Tipo"] == "proveito", "Valor"].sum())
        custos_folha = float(df_folha.loc[df_folha["Tipo"] == "custo", "Valor"].sum())

    resultado_estimado = faturacao_total - custos_total
    margem_estimada = (resultado_estimado / faturacao_total * 100) if faturacao_total else 0.0

    num_clientes = int(vendas["Cliente"].nunique()) if not vendas.empty else 0
    ticket_medio_global = (faturacao_total / len(vendas)) if len(vendas) else 0.0

    alertas = []

    if var_semana is not None:
        if var_semana >= 5:
            alertas.append({"level": "green", "title": "Semana atual", "text": f"A semana atual está {var_semana:.1f}% acima da semana anterior."})
        elif var_semana <= -5:
            alertas.append({"level": "red", "title": "Semana atual", "text": f"A semana atual está {abs(var_semana):.1f}% abaixo da semana anterior."})
        else:
            alertas.append({"level": "yellow", "title": "Semana atual", "text": "A semana atual está próxima do ritmo da semana anterior."})

    if var_mtd_homologo is not None:
        if var_mtd_homologo >= 5:
            alertas.append({"level": "green", "title": "MTD vs homólogo", "text": f"O mês até agora está {var_mtd_homologo:.1f}% acima do mesmo período do ano anterior."})
        elif var_mtd_homologo <= -5:
            alertas.append({"level": "red", "title": "MTD vs homólogo", "text": f"O mês até agora está {abs(var_mtd_homologo):.1f}% abaixo do mesmo período do ano anterior."})

    if pct_top3 >= 70:
        alertas.append({"level": "red", "title": "Dependência de clientes", "text": f"{pct_top3:.1f}% da faturação do mês depende dos 3 principais clientes."})
    elif pct_top3 >= 50:
        alertas.append({"level": "yellow", "title": "Dependência de clientes", "text": f"{pct_top3:.1f}% da faturação do mês depende dos 3 principais clientes."})

    if not custos_por_classe.empty:
        top_classe = str(custos_por_classe.iloc[0]["Classe"])
        top_classe_pct = float(custos_por_classe.iloc[0]["Perc_Custo"])
        alertas.append({"level": "yellow" if top_classe_pct >= 45 else "green", "title": "Estrutura de custos", "text": f"A maior fatia dos custos está na classe {top_classe} ({top_classe_pct:.1f}%)."})

    return {
        "reference_date": reference_date,
        "semana_atual": semana_atual,
        "semana_anterior": semana_anterior,
        "var_semana": var_semana,
        "mtd": mtd,
        "mtd_mes_anterior": mtd_mes_anterior,
        "mtd_homologo": mtd_homologo,
        "var_mtd_mes_ant": var_mtd_mes_ant,
        "var_mtd_homologo": var_mtd_homologo,
        "ytd": ytd,
        "ytd_homologo": ytd_homologo,
        "var_ytd_homologo": var_ytd_homologo,
        "resultado_estimado": resultado_estimado,
        "margem_estimada": margem_estimada,
        "faturacao_diaria": faturacao_diaria,
        "faturacao_semanal": faturacao_semanal,
        "faturacao_mensal": faturacao_mensal,
        "ticket_diario": ticket_diario,
        "ticket_medio_global": ticket_medio_global,
        "top_clientes": top_clientes,
        "top_clientes_mtd": top_clientes_mtd,
        "pct_top3": pct_top3,
        "num_clientes": num_clientes,
        "custos_total": custos_total,
        "custos_por_classe": custos_por_classe,
        "proveitos_folha": proveitos_folha,
        "custos_folha": custos_folha,
        "pais_classificacao": pais_classificacao,
        "alertas": alertas,
    }


def kpi_card(label: str, value: str, subtitle: str = "", icon: str = "📊") -> None:
    st.markdown(
        f"""
        <div class='kpi-box'>
            <div class='kpi-icon'>{icon}</div>
            <div class='kpi-label'>{label}</div>
            <div class='kpi-value'>{value}</div>
            <div class='kpi-sub'>{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def alert_card(level: str, title: str, text: str) -> None:
    css = {"red": "alert-red", "yellow": "alert-yellow", "green": "alert-green"}.get(level, "alert-yellow")

    st.markdown(
        f"""
        <div class='alert-box {css}'>
            <div class='alert-title'>{title}</div>
            <div class='alert-text'>{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def add_kpi_notes() -> None:
    with st.expander("O que significam estes indicadores?"):
        st.markdown(
            """
            - **Semana Atual**: soma das vendas desde segunda-feira até à última data disponível nos dados.
            - **MTD**: vendas acumuladas no mês até à última data disponível.
            - **YTD**: vendas acumuladas no ano até à última data disponível.
            - **Homólogo**: comparação com o mesmo período do ano anterior.
            - **Ticket Médio**: valor médio por documento de venda.
            """
        )


def add_costs_input_notes() -> None:
    with st.expander("Não tem balancete?"):
        st.markdown(
            """
            Pode carregar uma **folha simples de custos/proveitos** com estas colunas:

            - **Data**
            - **Tipo**: `Custo` ou `Proveito`
            - **Categoria**
            - **Descricao**
            - **Valor**

            A app transforma os custos numa estrutura resumida semelhante a um balancete de gestão.
            """
        )


def fmt_value(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "Sem base"
    return f"{x:,.2f}"


def fmt_pct(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "Sem base"
    return f"{x:.1f}%"


def render_feedback_box(page_name: str) -> None:
    st.markdown("### Sugestões")
    st.caption("Diga o que gostaria de ver na análise. Exemplo: vendas por hora, previsão de imposto ou comparação por produto.")

    feedback_key = f"feedback_{page_name}"
    button_key = f"send_feedback_{page_name}"

    feedback = st.text_area(
        "O que gostaria de analisar ou melhorar?",
        key=feedback_key,
        max_chars=500,
        placeholder="Exemplo: Gostaria de ver vendas por hora e uma estimativa simples do imposto.",
    )

    if st.button("Enviar sugestão", key=button_key, use_container_width=True):
        clean = sanitize_user_feedback(feedback)
        is_valid, message = validate_user_feedback(clean)

        if not is_valid:
            st.warning(message)
        else:
            save_user_feedback(page_name, clean)
            st.success("Sugestão registada com sucesso.")


def template_download_card(title: str, description: str, df: pd.DataFrame, file_name: str) -> None:
    st.markdown(f"### {title}")
    st.caption(description)
    st.dataframe(df, use_container_width=True)
    st.download_button(
        f"Descarregar {title}",
        data=dataframe_to_csv_download(df),
        file_name=file_name,
        mime="text/csv",
        use_container_width=True,
    )


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("## Visão de Gestão")

    pagina = st.radio(
        "Páginas",
        [
            "Resumo de Vendas",
            "Clientes",
            "Custos",
            "Faturação",
            "Templates e exemplos",
            "Backoffice de Sugestões",
        ],
    )

    st.divider()
    st.markdown("### Configuração")

    pais_classificacao = st.selectbox(
        "País / regra contabilística",
        COUNTRY_OPTIONS,
        index=0,
    )

    st.divider()
    st.markdown("### Carregar ficheiros")

    st.info("📥 Se não tiver os ficheiros no formato certo, vá à página 'Templates e exemplos', descarregue o template e preencha.")

    vendas_file = st.file_uploader("Ficheiro de Vendas", type=["csv", "xlsx", "xls"])

    origem_custos = st.radio(
        "Origem dos custos",
        ["Balancete", "Folha de custos/proveitos"],
    )

    if origem_custos == "Balancete":
        bal_file = st.file_uploader("Balancete", type=["csv", "xlsx", "xls"])
        folha_file = None
    else:
        folha_file = st.file_uploader("Folha de custos/proveitos", type=["csv", "xlsx", "xls"])
        bal_file = None

    clientes_file = st.file_uploader("Clientes (opcional)", type=["csv", "xlsx", "xls"])

    st.divider()
    st.markdown("### Colunas mínimas")
    st.code("Vendas: Data | Cliente | Total")
    st.caption("Documento é recomendado, mas opcional.")

    if origem_custos == "Balancete":
        st.code("Balancete: Conta | Descricao | Saldo")
    else:
        st.code("Folha: Data | Tipo | Categoria | Descricao | Valor")

    st.code("Clientes: Cliente | NIF | Segmento | Regiao")


# =========================================================
# HEADER
# =========================================================
st.markdown(
    f"""
    <div class='hero'>
        <h1>{APP_TITLE}</h1>
        <p>{APP_SUBTITLE}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# LOAD + VALIDATE
# =========================================================
vendas_std = None
bal_std = None
folha_std = None
clientes_std = None
m = None

tem_origem_custos = (
    (origem_custos == "Balancete" and bal_file is not None)
    or (origem_custos == "Folha de custos/proveitos" and folha_file is not None)
)

if vendas_file is not None and tem_origem_custos:
    try:
        vendas_raw = read_uploaded_file(vendas_file)
        vendas_std = standardize_vendas(vendas_raw)

        if clientes_file is not None:
            clientes_raw = read_uploaded_file(clientes_file)
            clientes_std = standardize_clientes(clientes_raw)
            _, missing_c = validate_columns(clientes_std, EXPECTED_CLIENTES)
            if missing_c:
                st.warning(f"O ficheiro de Clientes foi carregado, mas faltam colunas: {', '.join(missing_c)}")
                clientes_std = None

        _, missing_v = validate_columns(vendas_std, EXPECTED_VENDAS)

        if missing_v:
            st.error(f"Faltam colunas em Vendas: {', '.join(missing_v)}. Use o template disponível em 'Templates e exemplos'.")
        else:
            if origem_custos == "Balancete":
                bal_raw = read_uploaded_file(bal_file)
                bal_std = standardize_balancete(bal_raw)

                _, missing_b = validate_columns(bal_std, EXPECTED_BALANCETE)

                if missing_b:
                    st.error(f"Faltam colunas em Balancete: {', '.join(missing_b)}. Use o template disponível em 'Templates e exemplos'.")
                else:
                    m = build_metrics(
                        vendas_std,
                        bal_std,
                        df_clientes=clientes_std,
                        pais_classificacao=pais_classificacao,
                    )
                    st.success(
                        f"Ficheiros carregados com sucesso. Última data disponível: "
                        f"{m['reference_date'].strftime('%d/%m/%Y')}"
                    )

            else:
                folha_raw = read_uploaded_file(folha_file)
                folha_std = standardize_folha(folha_raw)

                _, missing_f = validate_columns(folha_std, EXPECTED_FOLHA)

                if missing_f:
                    st.error(f"Faltam colunas na Folha de custos/proveitos: {', '.join(missing_f)}. Use o template disponível em 'Templates e exemplos'.")
                else:
                    bal_std = folha_to_balancete(folha_std)

                    m = build_metrics(
                        vendas_std,
                        bal_std,
                        df_folha=folha_std,
                        df_clientes=clientes_std,
                        pais_classificacao=pais_classificacao,
                    )
                    st.success(
                        f"Ficheiros carregados com sucesso. Última data disponível: "
                        f"{m['reference_date'].strftime('%d/%m/%Y')}"
                    )

    except Exception as e:
        st.error(f"Erro ao processar ficheiros: {e}")

else:
    if pagina != "Backoffice de Sugestões" and pagina != "Templates e exemplos":
        st.info(
            "Carregue o ficheiro de Vendas e a origem de custos escolhida na barra lateral "
            "para ver as páginas de análise."
        )


# =========================================================
# PAGES
# =========================================================
if pagina == "Resumo de Vendas":
    st.markdown("## Resumo de Vendas")
    st.markdown("Indicadores principais do período atual e comparações úteis para decisão.")
    add_kpi_notes()
    add_costs_input_notes()

    if m is None:
        st.warning("Carregue os ficheiros para visualizar esta página.")
    else:
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            kpi_card("Semana Atual", fmt_value(m["semana_atual"]), f"Vs semana anterior: {fmt_pct(m['var_semana'])}", "📅")
        with c2:
            kpi_card("MTD", fmt_value(m["mtd"]), f"Vs mesmo período ano anterior: {fmt_pct(m['var_mtd_homologo'])}", "📈")
        with c3:
            kpi_card("YTD", fmt_value(m["ytd"]), f"Vs mesmo período ano anterior: {fmt_pct(m['var_ytd_homologo'])}", "🏁")
        with c4:
            kpi_card("Ticket Médio", fmt_value(m["ticket_medio_global"]), "Valor médio por documento", "🧾")

        st.markdown("### Alertas de gestão")

        if m["alertas"]:
            for alerta in m["alertas"]:
                alert_card(alerta["level"], alerta["title"], alerta["text"])
        else:
            st.info("Sem alertas relevantes para os dados carregados.")

        st.markdown(
            """
            <div class='section-panel'>
                <div class='section-title'>Evolução recente</div>
                <div class='section-subtitle'>Últimos dias disponíveis nos ficheiros carregados.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        g1, g2 = st.columns(2)

        with g1:
            df_plot = m["faturacao_diaria"].copy().tail(14)

            if len(df_plot) <= 12:
                fig1 = px.line(df_plot, x="Dia", y="Total", markers=True, text=df_plot["Total"].round(0))
                fig1.update_traces(textposition="top center")
            else:
                fig1 = px.line(df_plot, x="Dia", y="Total", markers=True)

            fig1.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Dia",
                yaxis_title="Faturação",
            )
            st.plotly_chart(fig1, use_container_width=True)

        with g2:
            df_ticket = m["ticket_diario"].copy().tail(14)
            fig2 = px.bar(df_ticket, x="Dia", y="TicketMedio", text=df_ticket["TicketMedio"].round(0))
            fig2.update_traces(textposition="outside")
            fig2.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Dia",
                yaxis_title="Ticket Médio",
            )
            st.plotly_chart(fig2, use_container_width=True)

        render_feedback_box("Resumo de Vendas")
elif pagina == "Clientes":
    st.markdown("## Clientes")
    st.markdown("Carteira atual e concentração da faturação do mês até à data.")

    if m is None:
        st.warning("Carregue os ficheiros para visualizar esta página.")
    else:
        c1, c2 = st.columns(2)

        with c1:
            kpi_card("Número de Clientes", f"{m['num_clientes']}", "Clientes únicos", "👥")
        with c2:
            kpi_card("Dependência Top 3", fmt_pct(m["pct_top3"]), "Peso dos 3 principais clientes no mês", "⚠️")

        df_clientes = m["top_clientes_mtd"].copy()

        if not df_clientes.empty:
            df_clientes["Perc_Faturacao"] = df_clientes["Perc_Faturacao"].round(1)

            fig3 = px.bar(df_clientes, x="Cliente", y="Total", text=df_clientes["Total"].round(0))
            fig3.update_traces(textposition="outside")
            fig3.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Cliente",
                yaxis_title="Faturação",
            )
            st.plotly_chart(fig3, use_container_width=True)

            st.dataframe(
                df_clientes[["Cliente", "Total", "Perc_Faturacao"]]
                .rename(columns={"Total": "Valor", "Perc_Faturacao": "% Faturação"})
                .round(2),
                use_container_width=True,
            )
        else:
            st.info("Sem dados suficientes para top clientes do mês atual.")

        render_feedback_box("Clientes")
elif pagina == "Custos":
    st.markdown("## Custos")

    if origem_custos == "Balancete":
        st.markdown("Estrutura técnica de custos por classe do balancete.")
    else:
        st.markdown("Custos resumidos a partir da folha de custos/proveitos.")

    if m is None:
        st.warning("Carregue os ficheiros para visualizar esta página.")
    else:
        st.caption(
            f"Regra de classificação em uso: {m['pais_classificacao']}. "
            "Se a empresa usar um plano adaptado, esta leitura deve ser validada."
        )

        c1, c2 = st.columns(2)

        with c1:
            kpi_card("Custos Totais", fmt_value(m["custos_total"]), "Contas classificadas como custo", "💸")
        with c2:
            kpi_card("Margem Estimada", fmt_pct(m["margem_estimada"]), "Receita menos custos", "📊")

        if origem_custos == "Folha de custos/proveitos" and folha_std is not None:
            c3, c4 = st.columns(2)

            with c3:
                kpi_card("Proveitos na Folha", fmt_value(m["proveitos_folha"]), "Registos marcados como proveito", "🟢")
            with c4:
                kpi_card("Custos na Folha", fmt_value(m["custos_folha"]), "Registos marcados como custo", "🔴")

        if not m["custos_por_classe"].empty:
            g1, g2 = st.columns(2)

            with g1:
                fig4 = px.pie(m["custos_por_classe"], names="Classe", values="Saldo")
                fig4.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig4, use_container_width=True)

            with g2:
                df_custos = m["custos_por_classe"].copy()
                df_custos["Perc_Custo"] = df_custos["Perc_Custo"].round(1)

                fig5 = px.bar(df_custos, x="Classe", y="Saldo", text=df_custos["Saldo"].round(0))
                fig5.update_traces(textposition="outside")
                fig5.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_title="Classe",
                    yaxis_title="Custo",
                )
                st.plotly_chart(fig5, use_container_width=True)

            st.dataframe(
                df_custos[["Classe", "Saldo", "Perc_Custo"]]
                .rename(columns={"Saldo": "Valor", "Perc_Custo": "% Custo"})
                .round(2),
                use_container_width=True,
            )
        else:
            st.warning("Não foram encontrados custos suficientes para análise.")

        if origem_custos == "Folha de custos/proveitos" and folha_std is not None:
            st.markdown("### Detalhe da folha carregada")
            st.dataframe(folha_std.sort_values("Data", ascending=False), use_container_width=True)

        render_feedback_box("Custos")


elif pagina == "Faturação":
    st.markdown("## Faturação")
    st.markdown("Evolução semanal, mensal e acumulados até à data.")
    add_kpi_notes()

    if m is None:
        st.warning("Carregue os ficheiros para visualizar esta página.")
    else:
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            kpi_card("Mês até agora", fmt_value(m["mtd"]), f"Vs mês anterior: {fmt_pct(m['var_mtd_mes_ant'])}", "📈")
        with c2:
            kpi_card("Mês homólogo", fmt_value(m["mtd_homologo"]), "Mesmo período do ano anterior", "📅")
        with c3:
            kpi_card("Ano até agora", fmt_value(m["ytd"]), f"Vs homólogo: {fmt_pct(m['var_ytd_homologo'])}", "🏁")
        with c4:
            kpi_card("Ano homólogo", fmt_value(m["ytd_homologo"]), "Ano anterior até à mesma data", "📊")

        g1, g2 = st.columns(2)

        with g1:
            df_sem = m["faturacao_semanal"].copy().tail(12)
            fig6 = px.bar(df_sem, x="Semana_Label", y="Total", text=df_sem["Total"].round(0))
            fig6.update_traces(textposition="outside")
            fig6.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Semana",
                yaxis_title="Faturação",
            )
            st.plotly_chart(fig6, use_container_width=True)

        with g2:
            df_fat = m["faturacao_mensal"].copy()
            fig7 = px.bar(df_fat, x="Mes", y="Total", text=df_fat["Total"].round(0))
            fig7.update_traces(textposition="outside")
            fig7.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Mês",
                yaxis_title="Faturação",
            )
            st.plotly_chart(fig7, use_container_width=True)

        resumo = pd.DataFrame({
            "Indicador": [
                "Semana Atual",
                "Semana Anterior",
                "MTD",
                "MTD Homólogo",
                "YTD",
                "YTD Homólogo",
                "Variação Semana (%)",
                "Variação MTD Homólogo (%)",
                "Variação YTD Homólogo (%)",
            ],
            "Valor": [
                m["semana_atual"],
                m["semana_anterior"],
                m["mtd"],
                m["mtd_homologo"],
                m["ytd"],
                m["ytd_homologo"],
                m["var_semana"],
                m["var_mtd_homologo"],
                m["var_ytd_homologo"],
            ],
        })

        st.download_button(
            "Descarregar resumo CSV",
            data=dataframe_to_csv_download(resumo),
            file_name="resumo_analise.csv",
            mime="text/csv",
            use_container_width=True,
        )

        render_feedback_box("Faturação")
elif pagina == "Templates e exemplos":
    st.markdown("## Templates e exemplos")
    st.markdown("Descarregue os ficheiros base, preencha com os seus dados e depois carregue na barra lateral.")

    st.info(
        "Fluxo recomendado: 1) descarregar template → 2) preencher → 3) guardar em CSV/Excel → 4) carregar na app."
    )

    exemplo_vendas = pd.DataFrame(
        {
            "Data": ["01/04/2026", "02/04/2026", "03/04/2026", "04/04/2026"],
            "Cliente": ["Cliente A", "Cliente B", "Cliente A", "Cliente C"],
            "Documento": ["FT 1", "FT 2", "FT 3", "FT 4"],
            "Total": [1200.50, 850.00, 430.00, 2100.00],
        }
    )

    exemplo_bal = pd.DataFrame(
        {
            "Conta": ["61", "62", "63", "68", "71"],
            "Descricao": ["CMVMC", "Fornecimentos e serviços", "Gastos com pessoal", "Gastos financeiros", "Vendas"],
            "Saldo": [3500.00, 1800.00, 2200.00, 200.00, 9500.00],
        }
    )

    exemplo_clientes = pd.DataFrame(
        {
            "Cliente": ["Cliente A", "Cliente B", "Cliente C"],
            "NIF": ["123456789", "987654321", "501234567"],
            "Segmento": ["Empresa", "Particular", "Empresa"],
            "Regiao": ["Lisboa", "Porto", "Luanda"],
            "Pais": ["Portugal", "Portugal", "Angola"],
            "Email": ["clientea@email.com", "clienteb@email.com", "clientec@email.com"],
            "Telefone": ["910000001", "920000002", "930000003"],
        }
    )

    exemplo_folha = pd.DataFrame(
        {
            "Data": ["02/04/2026", "03/04/2026", "05/04/2026", "08/04/2026"],
            "Tipo": ["Custo", "Custo", "Proveito", "Custo"],
            "Categoria": ["Renda", "Água e luz", "Vendas diversas", "Salários"],
            "Descricao": ["Loja abril", "Energia", "Venda balcão", "Equipa"],
            "Valor": [500.00, 120.00, 950.00, 1200.00],
        }
    )

    tab1, tab2, tab3, tab4 = st.tabs(["Vendas", "Balancete", "Clientes", "Folha custos/proveitos"])

    with tab1:
        template_download_card(
            "Template de Vendas",
            "Obrigatório. Use este ficheiro para carregar documentos de venda/faturação.",
            exemplo_vendas,
            "template_vendas.csv",
        )
        st.markdown("**Colunas mínimas:** `Data`, `Cliente`, `Total`. A coluna `Documento` é recomendada, mas a app consegue preencher como `N/D`.")

    with tab2:
        template_download_card(
            "Template de Balancete",
            "Use quando tiver exportação contabilística ou estrutura de contas.",
            exemplo_bal,
            "template_balancete.csv",
        )
        st.markdown("**Colunas mínimas:** `Conta`, `Descricao`, `Saldo`. Contas começadas por 6 são tratadas como custos; contas começadas por 7 como proveitos.")

    with tab3:
        template_download_card(
            "Template de Clientes",
            "Opcional. Serve para enriquecer a análise por segmento, região, país ou outros atributos do cliente.",
            exemplo_clientes,
            "template_clientes.csv",
        )
        st.markdown("**Coluna mínima:** `Cliente`. O nome deve coincidir com o campo Cliente do ficheiro de Vendas.")

    with tab4:
        template_download_card(
            "Template de Folha custos/proveitos",
            "Alternativa ao balancete para pequenos negócios que registam receitas e despesas manualmente.",
            exemplo_folha,
            "template_folha_custos_proveitos.csv",
        )
        st.markdown("**Colunas mínimas:** `Data`, `Tipo`, `Categoria`, `Valor`. O `Tipo` deve ser `Custo` ou `Proveito`.")


elif pagina == "Backoffice de Sugestões":
    st.markdown("## Backoffice de Sugestões")
    st.markdown("Visão interna das sugestões enviadas pelos utilizadores.")

    df_feedback = load_feedback()

    c1, c2, c3 = st.columns(3)

    with c1:
        kpi_card("Total de Sugestões", f"{len(df_feedback)}", "Registos guardados")

    with c2:
        kpi_card(
            "Páginas com Sugestões",
            f"{df_feedback['pagina'].nunique() if not df_feedback.empty else 0}",
            "Áreas com feedback",
        )

    with c3:
        ultima_data = (
            pd.to_datetime(df_feedback["timestamp"], errors="coerce").max().strftime("%d/%m/%Y %H:%M")
            if not df_feedback.empty and pd.to_datetime(df_feedback["timestamp"], errors="coerce").notna().any()
            else "Sem dados"
        )
        kpi_card("Última Sugestão", ultima_data, "Mais recente")

    if df_feedback.empty:
        st.info("Ainda não existem sugestões registadas.")
    else:
        st.markdown("### Resumo por página")

        resumo_paginas = (
            df_feedback.groupby("pagina", as_index=False)
            .size()
            .rename(columns={"size": "Quantidade"})
            .sort_values("Quantidade", ascending=False)
        )

        fig_fb = px.bar(
            resumo_paginas,
            x="pagina",
            y="Quantidade",
            text="Quantidade",
        )

        fig_fb.update_traces(textposition="outside")
        fig_fb.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Página",
            yaxis_title="Sugestões",
        )

        st.plotly_chart(fig_fb, use_container_width=True)

        st.markdown("### Registos")

        st.dataframe(
            df_feedback.sort_values("timestamp", ascending=False),
            use_container_width=True,
        )

        st.download_button(
            "Descarregar sugestões CSV",
            data=dataframe_to_csv_download(df_feedback),
            file_name="sugestoes_utilizadores.csv",
            mime="text/csv",
            use_container_width=True,
        )
