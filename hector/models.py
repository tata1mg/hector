# TODO: add module docstring, for auto documentation
# TODO: move to pydantic/mgspec models
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CovReportTotals:
    covered_lines: int
    num_statements: int
    percent_covered: float
    percent_covered_display: str
    missing_lines: int
    excluded_lines: int


@dataclass
class CovReport:
    meta: Dict[str, Dict[str, Any]]
    files: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    totals: CovReportTotals = field(default_factory=CovReportTotals)

    def __post_init__(self):
        if isinstance(self.totals, dict):
            # Filter dict to only include fields defined in CovReportTotals
            # This rejects extra keys like 'percent_statements_covered'
            valid_fields = set(CovReportTotals.__dataclass_fields__.keys())
            filtered_totals = {k: v for k, v in self.totals.items() if k in valid_fields}
            self.totals = CovReportTotals(**filtered_totals)

    @property
    def overall_coverage(self):
        return self.totals.percent_covered


@dataclass
class DiffCovReport:
    report_name: str
    diff_name: str
    total_num_lines: int
    total_num_violations: int
    total_percent_covered: int
    num_changed_lines: int
    src_stats: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.src_stats = dict(
            sorted(
                self.src_stats.items(),
                key=lambda item: item[1]["percent_covered"],
            )
        )

    @property
    def diff_coverage(self):
        return self.total_percent_covered

    @property
    def lines_covered(self):
        return self.lines_changed - self.lines_missed

    @property
    def lines_changed(self):
        return self.total_num_lines

    @property
    def lines_missed(self):
        return self.total_num_violations
