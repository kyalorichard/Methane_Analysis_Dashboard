import io
import json
import zipfile

import numpy as np
import pandas as pd
from docx import Document
from pypdf import PdfReader

from analysis_engine.scientific_reports import build_scientific_report


def sample_data():
    rng = np.random.default_rng(17)
    rows = []
    for animal in range(1, 13):
        group = "Control" if animal <= 6 else "Treatment"
        for visit in range(3):
            rows.append({"animal": f"A{animal:02d}", "group": group,
                         "methane_index": float(20 + (group == "Treatment") * 2 + visit * .4 + rng.normal()),
                         "body_weight": float(35 + animal + visit * .2)})
    df = pd.DataFrame(rows)
    df.loc[0, "methane_index"] = np.nan
    return df


def test_builds_word_pdf_zip_and_machine_readable_tables():
    result = build_scientific_report(sample_data(), outcome="methane_index", animal_id="animal",
        group_col="group", covariates=["body_weight"], study_title="Pilot methane study",
        dataset_name="pilot.csv", species="Sheep", protocol_notes="Portable chamber; protocol v2.")
    assert result["docx"].startswith(b"PK")
    assert result["pdf"].startswith(b"%PDF")
    assert result["zip"].startswith(b"PK")
    assert result["manifest"]["analysis_unit"].startswith("animal")
    assert result["manifest"]["source_rows"] == 36
    doc = Document(io.BytesIO(result["docx"]))
    text = " ".join(p.text for p in doc.paragraphs)
    assert "Pilot methane study" in text
    assert "Interpretation and limitations" in text
    pdf = PdfReader(io.BytesIO(result["pdf"]))
    pdf_text = " ".join(page.extract_text() or "" for page in pdf.pages)
    assert "Pilot methane study" in pdf_text
    with zipfile.ZipFile(io.BytesIO(result["zip"])) as archive:
        names = set(archive.namelist())
        assert "report/scientific_report.docx" in names
        assert "report/scientific_report.pdf" in names
        assert "report/manifest.json" in names
        assert "tables/outcome_summary.csv" in names
        assert "figures/outcome_distribution.png" in names
        json.loads(archive.read("report/manifest.json"))


def test_rejects_missing_outcome_and_too_few_valid_values():
    df = sample_data()
    try:
        build_scientific_report(df, outcome="absent")
    except ValueError as exc:
        assert "not present" in str(exc)
    else:
        raise AssertionError("Missing outcome should be rejected")
    df["sparse"] = [1.0, np.nan] + [np.nan] * (len(df) - 2)
    try:
        build_scientific_report(df, outcome="sparse")
    except ValueError as exc:
        assert "three finite" in str(exc)
    else:
        raise AssertionError("Insufficient outcome observations should be rejected")


def test_rejects_invalid_animal_or_group_selection():
    df = sample_data()
    for kwargs in ({"animal_id": "missing"}, {"group_col": "missing"}):
        try:
            build_scientific_report(df, outcome="methane_index", **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid selected column should be rejected")
