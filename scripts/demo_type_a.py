from pathlib import Path

from attendance_gen.generation.layouts import TYPE_A_LAYOUT
from attendance_gen.generation.pdf_renderer import PdfRenderer
from attendance_gen.parsing.type_a_parser import TypeAParser
from attendance_gen.transformation.base import seed_from_bytes
from attendance_gen.transformation.type_a import TypeAStrategy

text = Path("tests/fixtures/a_r_25.txt").read_text(encoding="utf-8")
report = TypeAStrategy().transform(TypeAParser().parse(text), seed_from_bytes(text.encode()))
print(PdfRenderer().render(report, TYPE_A_LAYOUT, Path("data/output/a_r_25_sample.pdf")))