from collections.abc import Sequence

from attendance_gen.parsing.base_parser import BaseParser

MIN_CONFIDENCE = 0.3
MIN_MARGIN = 0.2


class UnknownReportTypeError(ValueError):
    """לא ניתן לזהות את סוג הדוח בביטחון מספיק."""


def classify(text: str, parsers: Sequence[BaseParser]) -> BaseParser:
    if not parsers:
        raise UnknownReportTypeError("no parsers registered")
    ranked = sorted(((p.score(text), p) for p in parsers), key=lambda x: x[0], reverse=True)
    best_score, best = ranked[0]
    runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
    if best_score < MIN_CONFIDENCE or best_score - runner_up < MIN_MARGIN:
        raise UnknownReportTypeError(
            f"ambiguous report type (best={best_score:.2f}, runner-up={runner_up:.2f})"
        )
    return best