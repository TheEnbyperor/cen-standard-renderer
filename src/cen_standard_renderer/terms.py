import pathlib
import yaml
from . import ir
from . import markdown_parser

def load_term_definitions(path: pathlib.Path) -> list[ir.TermDefinition]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []

    raw_terms = data.get("terms", []) if isinstance(data, dict) else data
    if not isinstance(raw_terms, list):
        raise ValueError(f"{path}: terms must be a YAML sequence")

    terms, seen = [], set()
    for i, raw in enumerate(raw_terms, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: term {i} must be a mapping")

        identifier = str(raw.get("id", "")).strip()
        term = str(raw.get("term", "")).strip()
        definition = str(raw.get("definition", "")).strip()

        if not identifier or not term or not definition:
            raise ValueError(f"{path}: term {i} requires id, term and definition")
        if identifier in seen:
            raise ValueError(f"{path}: duplicate term identifier: {identifier}")
        seen.add(identifier)

        def strings(name):
            value = raw.get(name, []) or []
            return [value] if isinstance(value, str) else [str(x) for x in value]

        terms.append(ir.TermDefinition(
            identifier, term, definition, strings("admitted_terms"),
            str(raw["source"]) if raw.get("source") else None
        ))

    return terms


def generate_terms_and_definitions(parser: markdown_parser.MarkdownParser, terms: list[ir.TermDefinition]) -> list[
    ir.Block]:
    if not terms:
        return []

    generated: list[ir.Block] = [
        ir.Heading(1, [ir.Text("Terms and definitions")], "terms-and-definitions"),
        ir.Paragraph([ir.Text(
            "For the purposes of this document, the following terms and definitions apply."
        )]),
    ]

    for term in terms:
        generated.append(ir.Heading(ir.HEADING_LEVEL_TERM, parser.parse_inlines(term.term), term.identifier))

        if term.admitted_terms:
            text = []
            for i, a in enumerate(term.admitted_terms):
                if i != 0:
                    text.append(ir.Text(", "))
                text.extend(parser.parse_inlines(a))
            generated.append(ir.Paragraph(text))

        generated.append(ir.Paragraph(parser.parse_inlines(term.definition)))

        if term.source:
            generated.append(ir.Paragraph(
                [ir.Text("SOURCE: ")] + parser.parse_inlines(term.source)
            ))

    return generated