import dataclasses
import pathlib
import yaml
from . import ir, markdown_parser, terms, utils


@dataclasses.dataclass
class StandardSource:
    metadata: dict

    introduction: list[ir.Block]
    scope: list[ir.Block]
    terms: list[ir.Block]

    sections: list[ir.Document]

    @classmethod
    def load(cls, manifest_path: pathlib.Path, parser: markdown_parser.MarkdownParser) -> "StandardSource":
        root = manifest_path.parent
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)

        with open(root / manifest["introduction"], "r") as f:
            introduction = parser.parse(f.read()).blocks
        with open(root / manifest["scope"], "r") as f:
            scope = parser.parse(f.read()).blocks
        term_defs = terms.load_term_definitions(root / manifest["terms"])
        term_blocks = terms.generate_terms_and_definitions(parser, term_defs)
        sections: list[ir.Document] = []

        for filename in manifest["sections"]:
            with open(root / filename, "r") as f:
                sec = parser.parse(f.read())
                utils.validate_block_identifiers(sec)
                utils.validate_requirements_language(sec.blocks)
                sections.append(sec)

        return cls(
            metadata={
                key: value for key, value in manifest.items()
                if key not in {"introduction", "scope", "terms", "sections"}
            },
            introduction=introduction,
            scope=scope,
            terms=term_blocks,
            sections=sections
        )