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
EXPECTED_BANCO = ["Data", "Descricao", "Tipo", "Valor"]

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
def standardize_banco(df: pd.DataFrame) -> pd.DataFrame:
    raw = normalize_columns(df)

    rename_map = {
        "data": "Data",
        "descricao": "Descricao",
        "descrição": "Descricao",
        "movimento": "Descricao",
        "historico": "Descricao",
        "histórico": "Descricao",
        "tipo": "Tipo",
        "entradaesaida": "Tipo",
        "debitocredito": "Tipo",
        "debitoCredito": "Tipo",
        "valor": "Valor",
        "montante": "Valor",
        "total": "Valor",
        "referencia": "Referencia",
        "referência": "Referencia",
        "documento": "Referencia",
    }

    raw = raw.rename(columns={c: rename_map.get(c, c) for c in raw.columns})
    cols = [c for c in ["Data", "Descricao", "Tipo", "Valor", "Referencia"] if c in raw.columns]
    out = raw[cols].copy()

    if "Data" in out.columns:
        out["Data"] = pd.to_datetime(out["Data"], dayfirst=True, errors="coerce")

    if "Valor" in out.columns:
        out["Valor"] = clean_number(out["Valor"])

    if "Descricao" not in out.columns:
        out["Descricao"] = "N/D"

    if "Referencia" not in out.columns:
        out["Referencia"] = "N/D"

    if "Tipo" in out.columns:
        out["Tipo"] = out["Tipo"].astype(str).str.strip().str.lower()
        out["Tipo"] = out["Tipo"].replace({
            "entrada": "entrada",
            "credito": "entrada",
            "crédito": "entrada",
            "recebimento": "entrada",
            "receita": "entrada",
            "saida": "saida",
            "saída": "saida",
            "debito": "saida",
            "débito": "saida",
            "pagamento": "saida",
            "despesa": "saida",
        })

    out = out.dropna(subset=[c for c in ["Data", "Tipo", "Valor"] if c in out.columns])
    return out

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
            lambda row: classify_account_type(row.get("Conta", ""), row.get("Descricao", ""), pais_classificacao),
            axis=1,
        )

    vendas["Dia"] = vendas["Data"].dt.date
    vendas["Mes_Ordem"] = vendas["Data"].dt.to_period("M").dt.to_timestamp()
    vendas["Mes"] = vendas["Data"].dt.strftime("%b %Y")
    vendas["Ano"] = vendas["Data"].dt.year
    vendas["Semana_Ordem"] = vendas["Data"].dt.to_period("W-MON").apply(lambda r: r.start_time)
    vendas["Semana_Label"] = vendas["Semana_Ordem"].dt.strftime("%d %b %Y")

    faturacao_total = float(vendas["Total"].sum()) if not vendas.empty else 0.0
    reference_date = pd.Timestamp(vendas["Data"].max()).normalize() if not vendas.empty else pd.Timestamp.today().normalize()
    bounds = date_bounds(reference_date)

    faturacao_diaria = vendas.groupby("Dia", as_index=False)["Total"].sum().sort_values("Dia")

    docs_diarios = vendas.groupby("Dia", as_index=False)["Documento"].count().rename(columns={"Documento": "NumDocs"})
    ticket_diario = faturacao_diaria.merge(docs_diarios, on="Dia", how="left")
    ticket_diario["TicketMedio"] = ticket_diario["Total"] / ticket_diario["NumDocs"].replace(0, pd.NA)

    faturacao_semanal = vendas.groupby(["Semana_Ordem", "Semana_Label"], as_index=False)["Total"].sum().sort_values("Semana_Ordem")
    faturacao_mensal = vendas.groupby(["Mes_Ordem", "Mes"], as_index=False)["Total"].sum().sort_values("Mes_Ordem")

    semana_atual = sum_between(vendas, bounds["week_start"], bounds["ref"])
    semana_anterior = sum_between(vendas, bounds["week_prev_start"], bounds["week_prev_end"])
    mtd = sum_between(vendas, bounds["month_start"], bounds["ref"])
    mtd_mes_anterior = sum_between(vendas, bounds["prev_month_start"], bounds["prev_month_same_day"])
    mtd_homologo = sum_between(vendas, bounds["same_period_last_year_month_start"], bounds["same_period_last_year_month_end"])
    ytd = sum_between(vendas, bounds["year_start"], bounds["ref"])
    ytd_homologo = sum_between(vendas, bounds["prev_year_start"], bounds["prev_year_same_day"])

    var_semana = safe_pct(semana_atual, semana_anterior)
    var_mtd_mes_ant = safe_pct(mtd, mtd_mes_anterior)
    var_mtd_homologo = safe_pct(mtd, mtd_homologo)
    var_ytd_homologo = safe_pct(ytd, ytd_homologo)

    top_clientes = vendas.groupby("Cliente", as_index=False)["Total"].sum().sort_values("Total", ascending=False).head(10)
    top_clientes["Perc_Faturacao"] = (top_clientes["Total"] / faturacao_total) * 100 if faturacao_total else 0.0

    top_clientes_mtd_base = vendas[(vendas["Data"] >= bounds["month_start"]) & (vendas["Data"] <= bounds["ref"])].copy()
    top_clientes_mtd = (
        top_clientes_mtd_base.groupby("Cliente", as_index=False)["Total"].sum().sort_values("Total", ascending=False).head(10)
        if not top_clientes_mtd_base.empty
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
        custos_por_classe = bal_custos.groupby("Classe", as_index=False)["Saldo"].sum().sort_values("Saldo", ascending=False)
        custos_por_classe["Perc_Custo"] = (custos_por_classe["Saldo"] / custos_total) * 100 if custos_total else 0.0
    else:
        custos_por_classe = pd.DataFrame(columns=["Classe", "Saldo", "Perc_Custo"])

    proveitos_folha = float(df_folha.loc[df_folha["Tipo"] == "proveito", "Valor"].sum()) if df_folha is not None and not df_folha.empty else 0.0
    custos_folha = float(df_folha.loc[df_folha["Tipo"] == "custo", "Valor"].sum()) if df_folha is not None and not df_folha.empty else 0.0

    resultado_estimado = faturacao_total - custos_total
    margem_estimada = (resultado_estimado / faturacao_total * 100) if faturacao_total else 0.0

    alertas = []

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
        "ticket_medio_global": faturacao_total / len(vendas) if len(vendas) else 0.0,
        "top_clientes": top_clientes,
        "top_clientes_mtd": top_clientes_mtd,
        "pct_top3": pct_top3,
        "num_clientes": int(vendas["Cliente"].nunique()) if not vendas.empty else 0,
        "custos_total": custos_total,
        "custos_por_classe": custos_por_classe,
        "proveitos_folha": proveitos_folha,
        "custos_folha": custos_folha,
        "pais_classificacao": pais_classificacao,
        "alertas": alertas,
    }


def build_bank_metrics(df_banco: pd.DataFrame, m: dict | None = None) -> dict:
    banco = df_banco.copy()

    entradas = float(banco.loc[banco["Tipo"] == "entrada", "Valor"].sum())
    saidas = float(banco.loc[banco["Tipo"] == "saida", "Valor"].sum())
    saldo_liquido = entradas - saidas

    banco["Mes_Ordem"] = banco["Data"].dt.to_period("M").dt.to_timestamp()
    banco["Mes"] = banco["Data"].dt.strftime("%b %Y")

    mensal = banco.groupby(["Mes_Ordem", "Mes", "Tipo"], as_index=False)["Valor"].sum().sort_values("Mes_Ordem")

    top_saidas = (
        banco[banco["Tipo"] == "saida"]
        .groupby("Descricao", as_index=False)["Valor"]
        .sum()
        .sort_values("Valor", ascending=False)
        .head(10)
    )

    diferenca_vs_vendas = None
    pct_diferenca_vs_vendas = None

    if m is not None:
        vendas_base = m.get("mtd", 0)
        diferenca_vs_vendas = entradas - vendas_base
        pct_diferenca_vs_vendas = safe_pct(entradas, vendas_base)

    alertas_banco = [{
        "level": "green" if saldo_liquido >= 0 else "red",
        "title": "Saldo bancário líquido",
        "text": "As entradas bancárias são superiores às saídas." if saldo_liquido >= 0 else "As saídas bancárias são superiores às entradas.",
    }]

    return {
        "entradas": entradas,
        "saidas": saidas,
        "saldo_liquido": saldo_liquido,
        "mensal": mensal,
        "top_saidas": top_saidas,
        "diferenca_vs_vendas": diferenca_vs_vendas,
        "pct_diferenca_vs_vendas": pct_diferenca_vs_vendas,
        "alertas_banco": alertas_banco,
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

def input_vendas_manual() -> pd.DataFrame:
    st.markdown("### Inserir vendas manualmente")

    default = pd.DataFrame({
        "Data": [pd.Timestamp.today().date()],
        "Cliente": [""],
        "Documento": [""],
        "Total": [0.0],
    })

    df = st.data_editor(
        default,
        num_rows="dynamic",
        use_container_width=True,
        key="manual_vendas",
    )

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce")
    df["Documento"] = df["Documento"].replace("", "N/D")

    return df.dropna(subset=["Data", "Cliente", "Total"])
def input_custos_manual() -> pd.DataFrame:
    st.markdown("### Inserir custos manualmente")

    default = pd.DataFrame({
        "Data": [pd.Timestamp.today().date()],
        "Tipo": ["Custo"],
        "Categoria": [""],
        "Descricao": [""],
        "Valor": [0.0],
    })

    df = st.data_editor(
        default,
        num_rows="dynamic",
        use_container_width=True,
        key="manual_custos",
    )

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Tipo"] = df["Tipo"].astype(str).str.lower()
    df["Categoria"] = df["Categoria"].astype(str)
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

    return df.dropna(subset=["Data", "Tipo", "Categoria", "Valor"])
def input_banco_manual() -> pd.DataFrame:
    st.markdown("### Inserir movimentos bancários")

    default = pd.DataFrame({
        "Data": [pd.Timestamp.today().date()],
        "Descricao": [""],
        "Tipo": ["Entrada"],
        "Valor": [0.0],
        "Referencia": [""],
    })

    df = st.data_editor(
        default,
        num_rows="dynamic",
        use_container_width=True,
        key="manual_banco",
    )

    return standardize_banco(df)



pais_classificacao = st.selectbox(
    "País / regra contabilística",
    COUNTRY_OPTIONS,
    index=0,
)
# =========================================================
# MENU PRINCIPAL
# =========================================================

m = st.session_state.get("m")
vendas_std = st.session_state.get("vendas_std")
folha_std = st.session_state.get("folha_std")
banco_std = st.session_state.get("banco_std")
bank_m = st.session_state.get("bank_m")

PAGINAS = [
    "Resumo de Vendas",
    "Clientes",
    "Custos",
    "Faturação",
    "Reconciliação Bancária",
    "Templates e exemplos",
    "Backoffice de Sugestões",
]

if "pagina" not in st.session_state:
    st.session_state.pagina = "Resumo de Vendas"

cols = st.columns(len(PAGINAS))

for col, nome in zip(cols, PAGINAS):

    with col:

        ativo = st.session_state.pagina == nome

        if st.button(
            nome,
            key=f"menu_{nome}",
            use_container_width=True,
            type="primary" if ativo else "secondary",
        ):

            st.session_state.pagina = nome
            st.rerun()

pagina = st.session_state.pagina

st.divider()
   
# =========================================================
# ESTADO GLOBAL
# =========================================================
# =========================================================
# PAGES
# =========================================================

if pagina == "Resumo de Vendas":

    st.markdown("## Resumo de Vendas")

    tab1, tab2 = st.tabs(["✍️ Inserção Manual", "📂 Importar Ficheiro"])

    with tab1:
        vendas_std = input_vendas_manual()

        folha_std = pd.DataFrame()
        bal_std = pd.DataFrame({
            "Conta": ["61"],
            "Descricao": ["Custos"],
            "Saldo": [0]
        })

        if st.button("Gerar análise manual"):
            if vendas_std.empty:
                st.warning("Insira pelo menos uma venda.")
            else:
                m = build_metrics(
                    vendas_std,
                    bal_std,
                    df_folha=folha_std,
                    pais_classificacao=pais_classificacao,
                )

                st.session_state["m"] = m
                st.session_state["vendas_std"] = vendas_std
                st.session_state["folha_std"] = folha_std
                st.success("Análise gerada com sucesso.")

    with tab2:
        vendas_file = st.file_uploader("Ficheiro de vendas", type=["csv", "xlsx", "xls"])

        if st.button("Gerar análise ficheiro"):
            if vendas_file is None:
                st.warning("Carregue o ficheiro de vendas.")
            else:
                try:
                    vendas_raw = read_uploaded_file(vendas_file)
                    vendas_std = standardize_vendas(vendas_raw)

                    folha_std = pd.DataFrame()
                    bal_std = pd.DataFrame({
                        "Conta": ["61"],
                        "Descricao": ["Custos"],
                        "Saldo": [0]
                    })

                    m = build_metrics(
                        vendas_std,
                        bal_std,
                        df_folha=folha_std,
                        pais_classificacao=pais_classificacao,
                    )

                    st.session_state["m"] = m
                    st.session_state["vendas_std"] = vendas_std
                    st.session_state["folha_std"] = folha_std
                    st.success("Análise gerada com sucesso.")

                except Exception as e:
                    st.error(f"Erro: {e}")

    m = st.session_state.get("m")

    if m is not None:
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            kpi_card("Semana Atual", fmt_value(m["semana_atual"]), f"Vs semana anterior: {fmt_pct(m['var_semana'])}", "📅")
        with c2:
            kpi_card("MTD", fmt_value(m["mtd"]), f"Vs homólogo: {fmt_pct(m['var_mtd_homologo'])}", "📈")
        with c3:
            kpi_card("YTD", fmt_value(m["ytd"]), f"Vs homólogo: {fmt_pct(m['var_ytd_homologo'])}", "🏁")
        with c4:
            kpi_card("Ticket Médio", fmt_value(m["ticket_medio_global"]), "Valor médio por documento", "🧾")

    st.markdown("### Evolução da faturação")

    g1, g2 = st.columns(2)

    with g1:
        df_plot = m["faturacao_diaria"].copy().tail(14)

        fig1 = px.line(
            df_plot,
            x="Dia",
            y="Total",
            markers=True,
            text=df_plot["Total"].round(0)
            )

        fig1.update_traces(textposition="top center")

        st.plotly_chart(
            fig1,
            use_container_width=True,
            key="grafico_faturacao_diaria"
            )

    with g2:
        df_ticket = m["ticket_diario"].copy().tail(14)

        df_ticket["TicketMedio"] = pd.to_numeric(
            df_ticket["TicketMedio"],
            errors="coerce"
            ).fillna(0)

        fig2 = px.bar(
            df_ticket,
            x="Dia",
            y="TicketMedio",
            text=df_ticket["TicketMedio"].round(0),
            )

        fig2.update_traces(textposition="outside")

        st.plotly_chart(
            fig2,
                use_container_width=True,
                key="grafico_ticket_medio"
            )
elif pagina == "Clientes":

    st.markdown("## Clientes")
    m = st.session_state.get("m")

    if m is None:
        st.warning("Insira vendas primeiro.")
    else:
        c1, c2 = st.columns(2)

        with c1:
            kpi_card("Número de Clientes", f"{m['num_clientes']}", "Clientes únicos", "👥")
        with c2:
            kpi_card("Dependência Top 3", fmt_pct(m["pct_top3"]), "Peso dos 3 principais clientes", "⚠️")

        st.dataframe(m["top_clientes"], use_container_width=True)


elif pagina == "Custos":

    st.markdown("## Custos")

    tab1, tab2 = st.tabs(["✍️ Inserção Manual", "📂 Importar Ficheiro"])

    with tab1:
        folha_std = input_custos_manual()

        if st.button("Atualizar custos manual"):
            atualizar_custos(folha_std)

    with tab2:
        folha_file = st.file_uploader("Ficheiro de custos", type=["csv", "xlsx", "xls"])

        if st.button("Importar custos"):
            if folha_file is None:
                st.warning("Carregue o ficheiro de custos.")
            else:
                folha_raw = read_uploaded_file(folha_file)
                folha_std = standardize_folha(folha_raw)
                atualizar_custos(folha_std)

elif pagina == "Faturação":

    st.markdown("## Faturação")
    m = st.session_state.get("m")

    if m is None:
        st.warning("Insira vendas primeiro.")
    else:
        df_mes = m["faturacao_mensal"].copy()
        fig = px.bar(df_mes, x="Mes", y="Total", text=df_mes["Total"].round(0))
        fig.update_traces(textposition="outside")
        st.plotly_chart(
        fig,
        use_container_width=True,
        key="grafico_faturacao_mensal"
)


elif pagina == "Reconciliação Bancária":

    st.markdown("## Reconciliação Bancária")

    tab1, tab2 = st.tabs(["✍️ Inserção Manual", "📂 Importar Ficheiro"])

    with tab1:
        banco_std = input_banco_manual()

        if st.button("Gerar análise bancária manual"):
            gerar_banco(banco_std)

    with tab2:
        banco_file = st.file_uploader("Extrato bancário", type=["csv", "xlsx", "xls"])

        if st.button("Importar extrato bancário"):
            if banco_file is None:
                st.warning("Carregue o extrato bancário.")
            else:
                banco_raw = read_uploaded_file(banco_file)
                banco_std = standardize_banco(banco_raw)
                gerar_banco(banco_std)

elif pagina == "Templates e exemplos":

    st.markdown("## Templates e exemplos")
    st.info("Aqui depois colocamos os botões para descarregar templates.")


elif pagina == "Backoffice de Sugestões":

    st.markdown("## Backoffice de Sugestões")
    df_feedback = load_feedback()
    st.dataframe(df_feedback, use_container_width=True)
