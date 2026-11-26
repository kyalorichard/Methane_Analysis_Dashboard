"""Generate manuscript-oriented Word/PDF reports from explicit descriptive analyses.

The generated documents are reporting aids, not publication approval or automated
scientific interpretation. Repeated-record summaries are animal-level only when
an animal identifier is explicitly supplied.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
import platform
import zipfile
from xml.sax.saxutils import escape as xml_escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak


def _safe(v):
    if isinstance(v, dict): return {str(k): _safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [_safe(x) for x in v]
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating, float)): return float(v) if np.isfinite(v) else None
    if isinstance(v, (np.bool_,)): return bool(v)
    if isinstance(v, (pd.Timestamp, datetime)): return v.isoformat()
    if pd.isna(v): return None
    return str(v) if not isinstance(v, (str, int, bool)) else v


def _table_frame(frame: pd.DataFrame, max_rows: int = 35, max_cols: int = 8) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    out = frame.iloc[:max_rows, :max_cols].copy().astype(object)
    for column in out.columns:
        out[column] = out[column].map(
            lambda value: "—" if pd.isna(value) or
            (isinstance(value, (float, np.floating)) and not np.isfinite(value)) else value
        )
    return out


def _figure_png(df: pd.DataFrame, outcome: str, group_col: str | None) -> bytes:
    values = pd.to_numeric(df[outcome], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    fig, ax = plt.subplots(figsize=(8.2, 4.5))
    ax.hist(values, bins=min(30, max(8, int(np.sqrt(len(values))))), edgecolor="black", linewidth=.35)
    ax.set_title(f"Distribution of {outcome}")
    ax.set_xlabel(outcome); ax.set_ylabel("Records")
    fig.tight_layout()
    buf = BytesIO(); fig.savefig(buf, format="png", dpi=180, bbox_inches="tight"); plt.close(fig)
    return buf.getvalue()


def _group_figure_png(df: pd.DataFrame, outcome: str, group_col: str | None) -> bytes | None:
    if not group_col or group_col not in df:
        return None
    plot = df[[group_col, outcome]].copy()
    plot[outcome] = pd.to_numeric(plot[outcome], errors="coerce")
    plot = plot.replace([np.inf, -np.inf], np.nan).dropna()
    levels = plot[group_col].drop_duplicates().tolist()
    if len(levels) < 2 or len(levels) > 20:
        return None
    data = [plot.loc[plot[group_col] == level, outcome].to_numpy() for level in levels]
    fig, ax = plt.subplots(figsize=(8.2, 4.5))
    ax.boxplot(data, tick_labels=[str(x)[:24] for x in levels], showfliers=True)
    ax.set_title(f"{outcome} by {group_col}"); ax.set_xlabel(group_col); ax.set_ylabel(outcome)
    ax.tick_params(axis="x", labelrotation=25)
    fig.tight_layout()
    buf = BytesIO(); fig.savefig(buf, format="png", dpi=180, bbox_inches="tight"); plt.close(fig)
    return buf.getvalue()


def _add_docx_table(doc, frame: pd.DataFrame, title: str):
    if frame.empty: return
    doc.add_heading(title, level=2)
    frame = _table_frame(frame)
    table = doc.add_table(rows=1, cols=len(frame.columns))
    table.style = "Light Shading Accent 1"
    for cell, name in zip(table.rows[0].cells, frame.columns):
        cell.text = str(name)
    for _, row in frame.iterrows():
        cells = table.add_row().cells
        for cell, value in zip(cells, row):
            cell.text = str(value)


def _pdf_table(frame: pd.DataFrame):
    frame = _table_frame(frame)
    if frame.empty: return None
    data = [[str(c) for c in frame.columns]] + [[str(v) for v in row] for row in frame.itertuples(index=False, name=None)]
    widths = [175 * mm / max(1, len(frame.columns))] * len(frame.columns)
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#23415c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7), ("LEADING", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#b8c3cc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f8")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def build_scientific_report(df: pd.DataFrame, *, outcome: str, animal_id: str | None = None,
                            group_col: str | None = None, covariates: list[str] | None = None,
                            study_title: str = "Methane phenotype study", dataset_name: str = "active_dataset",
                            species: str = "Not specified", protocol_notes: str = "") -> dict:
    """Return DOCX, PDF, ZIP, tables, manifest, and report figure bytes."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("A non-empty pandas DataFrame is required.")
    if outcome not in df:
        raise ValueError(f"Outcome '{outcome}' is not present in the dataset.")
    y = pd.to_numeric(df[outcome], errors="coerce").replace([np.inf, -np.inf], np.nan)
    if int(y.notna().sum()) < 3:
        raise ValueError("At least three finite numeric outcome observations are required.")
    if animal_id and animal_id not in df: raise ValueError("Selected animal identifier is not present.")
    if group_col and group_col not in df: raise ValueError("Selected group variable is not present.")
    from analysis_engine.publication import publication_tables
    tables = publication_tables(df, outcome, animal_id, group_col, covariates or [])
    fingerprint = hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values.tobytes()).hexdigest()
    generated = datetime.now(timezone.utc).isoformat()
    manifest = {
        "report_type": "methane-scientific-report", "report_version": 1,
        "generated_utc": generated, "study_title": study_title, "dataset_name": dataset_name,
        "species": species, "outcome": outcome, "animal_id": animal_id, "group_variable": group_col,
        "covariates": covariates or [], "source_rows": int(len(df)), "source_columns": int(df.shape[1]),
        "valid_outcome_records": int(y.notna().sum()), "missing_outcome_records": int(y.isna().sum()),
        "analysis_unit": tables["analysis_unit"], "analysis_n": int(tables["analysis_n"]),
        "dataset_fingerprint_sha256": fingerprint, "python_version": platform.python_version(),
        "pandas_version": pd.__version__, "protocol_notes": protocol_notes,
        "interpretation_status": "descriptive reporting; no causal or inferential claim generated",
    }
    limitations = [
        "This report presents descriptive summaries and exploratory Spearman associations; it does not establish causal effects.",
        "Where an animal identifier is supplied, animal-level summaries aggregate numeric variables by median and categorical variables by first observed value.",
        "Repeated observations must not be treated as independent animals. The analysis unit stated in this report should be checked against the study design.",
        "Concentration and area-under-the-curve signals are not methane mass flux (for example, g/day) without validated calibration.",
        "Phenotype definitions, units, instrument calibration, sampling protocol, exclusions and QC thresholds require investigator verification.",
        "No automatic significance claims are made. Select and report inferential models separately with their assumptions and diagnostics.",
    ]
    fig_png = _figure_png(df, outcome, group_col)
    group_fig_png = _group_figure_png(df, outcome, group_col)

    # Word report
    word = Document()
    sec = word.sections[0]; sec.top_margin = Inches(.7); sec.bottom_margin = Inches(.7)
    normal = word.styles["Normal"]; normal.font.name = "Arial"; normal.font.size = Pt(9)
    title = word.add_heading(study_title or "Scientific report", 0); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = word.add_paragraph("Methane phenotype analysis report"); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = word.add_paragraph(f"Generated (UTC): {generated}"); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    word.add_heading("Study metadata", level=1)
    for label, value in [("Dataset", dataset_name), ("Species", species), ("Outcome", outcome),
                         ("Source records", f"{len(df):,}"), ("Valid outcome records", f"{int(y.notna().sum()):,}"),
                         ("Missing outcome records", f"{int(y.isna().sum()):,}"),
                         ("Analysis unit", tables["analysis_unit"]), ("Analysis units", str(tables["analysis_n"]))]:
        word.add_paragraph(f"{label}: {value}")
    word.add_heading("Methods", level=1)
    word.add_paragraph("Outcome observations were coerced to numeric values; non-numeric and non-finite values were excluded from outcome summaries. Descriptive statistics include the mean, standard deviation, median, quartiles, minimum and maximum. Where an animal identifier was supplied, repeated observations were aggregated to animal-level medians for numeric variables and first-observed values for categorical variables before independent-unit group summaries and Spearman associations.")
    if protocol_notes: word.add_paragraph("Protocol and measurement notes: " + protocol_notes)
    else: word.add_paragraph("Protocol and measurement notes were not supplied. Add instrument model, calibration, sampling duration, units, phenotype definition, inclusion criteria and QC thresholds.")
    _add_docx_table(word, tables["outcome_summary"], "Primary outcome summary")
    _add_docx_table(word, tables["group_summary"], "Group-level descriptive summary")
    _add_docx_table(word, tables["spearman_correlations"], "Exploratory Spearman correlations")
    _add_docx_table(word, tables["descriptive_statistics"].head(35), "Dataset descriptive statistics (first 35 variables)")
    word.add_heading("Outcome distribution", level=1)
    word.add_picture(BytesIO(fig_png), width=Inches(6.2))
    if group_fig_png:
        word.add_heading(f"{outcome} by group", level=1)
        word.add_picture(BytesIO(group_fig_png), width=Inches(6.2))
    word.add_heading("Interpretation and limitations", level=1)
    for item in limitations: word.add_paragraph(item, style="List Bullet")
    word.add_heading("Reproducibility", level=1)
    word.add_paragraph(f"Dataset fingerprint (SHA-256): {fingerprint}")
    word.add_paragraph("This fingerprint identifies the dataframe content and row order; it is not a substitute for controlled archival storage of source data.")
    word_bytes = BytesIO(); word.save(word_bytes); docx_bytes = word_bytes.getvalue()

    # PDF report
    pdf_buf = BytesIO(); styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=18, leading=22, spaceAfter=8))
    styles.add(ParagraphStyle(name="SmallBody", parent=styles["BodyText"], fontSize=8, leading=11, spaceAfter=5))
    story = [Paragraph(xml_escape(study_title or "Scientific report"), styles["ReportTitle"]),
             Paragraph("Methane phenotype analysis report", styles["Heading2"]),
             Paragraph(f"Generated (UTC): {generated}", styles["SmallBody"]), Spacer(1, 5*mm),
             Paragraph("Study metadata", styles["Heading1"])]
    for label, value in [("Dataset", dataset_name), ("Species", species), ("Outcome", outcome),
                         ("Source records", f"{len(df):,}"), ("Valid outcome records", f"{int(y.notna().sum()):,}"),
                         ("Missing outcome records", f"{int(y.isna().sum()):,}"),
                         ("Analysis unit", tables["analysis_unit"]), ("Analysis units", str(tables["analysis_n"]))]:
        story.append(Paragraph(f"<b>{xml_escape(str(label))}:</b> {xml_escape(str(value))}", styles["SmallBody"]))
    story += [Spacer(1, 3*mm), Paragraph("Methods", styles["Heading1"]),
              Paragraph("Outcome values were coerced to numeric; non-numeric and non-finite values were excluded. Descriptive summaries report central tendency and spread. When an animal identifier is supplied, repeated records are collapsed to animal-level medians for numeric variables and first-observed categorical values for independent-unit summaries and exploratory Spearman associations.", styles["SmallBody"])]
    if protocol_notes:
        story.append(Paragraph("<b>Protocol notes:</b> " + xml_escape(protocol_notes), styles["SmallBody"]))
    else:
        story.append(Paragraph("<b>Protocol notes:</b> Not supplied. Add instrument calibration, sampling duration, units, phenotype definition, inclusion criteria and QC thresholds.", styles["SmallBody"]))
    for key, heading in [("outcome_summary", "Primary outcome summary"), ("group_summary", "Group-level descriptive summary"), ("spearman_correlations", "Exploratory Spearman correlations")]:
        t = _pdf_table(tables[key])
        if t: story.extend([Paragraph(heading, styles["Heading2"]), t, Spacer(1, 3*mm)])
    story += [Paragraph("Outcome distribution", styles["Heading1"]), Image(BytesIO(fig_png), width=165*mm, height=90*mm)]
    if group_fig_png:
        story += [Paragraph(f"{outcome} by group", styles["Heading1"]), Image(BytesIO(group_fig_png), width=165*mm, height=90*mm)]
    story.append(Paragraph("Interpretation and limitations", styles["Heading1"]))
    for item in limitations: story.append(Paragraph("&#8226; " + xml_escape(item), styles["SmallBody"]))
    story += [Paragraph("Reproducibility", styles["Heading1"]), Paragraph(f"Dataset fingerprint (SHA-256): {xml_escape(fingerprint)}", styles["SmallBody"])]
    SimpleDocTemplate(pdf_buf, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm).build(story)
    pdf_bytes = pdf_buf.getvalue()

    # Complete archive with documents, machine-readable tables and figure
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("report/scientific_report.docx", docx_bytes)
        z.writestr("report/scientific_report.pdf", pdf_bytes)
        z.writestr("report/manifest.json", json.dumps(_safe(manifest), indent=2, ensure_ascii=False))
        z.writestr("report/interpretation_limitations.md", "# Interpretation and limitations\n\n" + "\n".join(f"- {x}" for x in limitations))
        z.writestr("figures/outcome_distribution.png", fig_png)
        if group_fig_png: z.writestr("figures/outcome_by_group.png", group_fig_png)
        for name, frame in tables.items():
            if isinstance(frame, pd.DataFrame): z.writestr(f"tables/{name}.csv", frame.to_csv(index=False))
        z.writestr("tables/publication_tables.xlsx", __excel_bytes(tables))
    return {"docx": docx_bytes, "pdf": pdf_bytes, "zip": zip_buf.getvalue(), "manifest": manifest, "tables": tables, "figure_png": fig_png, "group_figure_png": group_fig_png}


def __excel_bytes(tables):
    b = BytesIO()
    with pd.ExcelWriter(b, engine="openpyxl") as writer:
        for name, frame in tables.items():
            if isinstance(frame, pd.DataFrame): frame.to_excel(writer, sheet_name=name[:31], index=False)
    return b.getvalue()
