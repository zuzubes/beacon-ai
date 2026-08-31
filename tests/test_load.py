import pandas as pd

from src.load import build_interim_tables, load_china, load_india, load_startup_funding_dataset


def test_load_china_decodes_gb18030_correctly():
    df = load_china()
    assert len(df) == 15304
    assert df.loc[0, "company"] == "新浪微博"


def test_load_india_reads_all_rows():
    df = load_india()
    assert len(df) == 5074
    assert "startup" in df.columns


def test_load_startup_funding_dataset_reads_all_rows():
    df = load_startup_funding_dataset()
    assert len(df) == 2000
    assert "Country" in df.columns


def test_build_interim_tables_writes_three_clean_csvs(tmp_path):
    build_interim_tables(output_dir=tmp_path)

    china = pd.read_csv(tmp_path / "china_clean.csv")
    india = pd.read_csv(tmp_path / "india_clean.csv")
    us = pd.read_csv(tmp_path / "us_clean.csv")

    for df in (china, india, us):
        assert list(df.columns) == [
            "company",
            "country",
            "sector",
            "round",
            "amount_usd",
            "amount_precision",
            "year",
            "quarter",
        ]
    assert (china["country"] == "China").all()
    assert (india["country"] == "India").all()
    assert (us["country"] == "United States").all()
    assert len(us) == 240
