"""Ledger + analysis-runbook helpers. Files live in the data dir so the app is
self-contained; templates are seeded from packaged resources on first use.
"""

from importlib import resources


def ledger_path(cfg):
    return cfg.data_dir / "ledger.md"


def analyze_doc_path(cfg):
    return cfg.data_dir / "ANALYZE.md"


def _seed(cfg, resource_name: str, dest):
    if dest.exists():
        return
    try:
        text = resources.files("eagleeye.analysis").joinpath(resource_name).read_text()
    except Exception:
        text = ""
    dest.write_text(text)


def ensure_seeded(cfg):
    _seed(cfg, "ledger.template.md", ledger_path(cfg))
    _seed(cfg, "ANALYZE.template.md", analyze_doc_path(cfg))
