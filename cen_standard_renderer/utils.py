import typing
import re
from . import ir, markdown_parser

FORBIDDEN_REQUIREMENTS_LANGUAGE = re.compile(r"\b(MUST|MUST NOT|REQUIRED)\b")
LOWERCASE_REQUIREMENTS_LANGUAGE = re.compile(r"\b(shall|shall not|should|should not|may|can)\b")


def walk_blocks(blocks: typing.Iterable[ir.Block]) -> typing.Iterable[ir.Block]:
    for block in blocks:
        yield block
        if isinstance(block, (ir.BulletList, ir.OrderedList)):
            for item in block.items:
                yield from walk_blocks(item)

def validate_block_identifiers(doc: ir.Document) -> None:
    seen_ids: set[str] = set()

    for block in walk_blocks(doc.blocks):
        if isinstance(block, ir.Heading):
            if block.identifier:
                if block.identifier in seen_ids:
                    raise ValueError(f"Duplicate identifier: {block.identifier}")
                seen_ids.add(block.identifier)

def block_text(block: ir.Block) -> typing.Iterable[str]:
    if isinstance(block, (ir.Paragraph, ir.Heading)):
        yield inline_plain_text(block.children)
    elif isinstance(block, ir.CodeBlock):
        return
    elif isinstance(block, (ir.BulletList, ir.OrderedList)):
        for item in block.items:
            for child in item:
                yield from block_text(child)

def inline_plain_text(inlines: typing.Sequence[ir.Inline]) -> str:
    out = []
    for inline in inlines:
        if isinstance(inline, (ir.Text, ir.Code)):
            out.append(inline.text)
        elif isinstance(inline, (ir.Strong, ir.Emphasis, ir.Link)):
            out.append(inline_plain_text(inline.children))
    return "".join(out)

def validate_requirements_language(blocks: typing.Iterable[ir.Block]) -> None:
    for block in walk_blocks(blocks):
        for text in block_text(block):
            for match in FORBIDDEN_REQUIREMENTS_LANGUAGE.finditer(text):
                print(f"warning: RFC-style normative keyword {match.group(0)!r} found")
            for match in LOWERCASE_REQUIREMENTS_LANGUAGE.finditer(text):
                print(f"warning: Lowercase normative keyword {match.group(0)!r} found")

def render_asn1_markdown(parser: markdown_parser.MarkdownParser, docs):
    out = []
    for doc in docs:
        if isinstance(doc, str):
            out.extend(parser.parse_blocks(doc))
    return out

def render_asn1_type_docs(parser: markdown_parser.MarkdownParser, asn1_type):
    kind = asn1_type.get("type")
    if kind in {"sequence", "choice"}:
        for component in asn1_type["components"].values():
            rendered = render_asn1_markdown(parser, component["doc"])
            validate_requirements_language(rendered)
            component["markdown_doc"] = rendered
            render_asn1_type_docs(parser, component["type"])
    elif kind == "enum":
        for value in asn1_type["values"]:
            rendered = render_asn1_markdown(parser, value["doc"])
            validate_requirements_language(rendered)
            value["markdown_doc"] = rendered
    elif kind in {"sequence_of", "set_of"}:
        render_asn1_type_docs(parser, asn1_type["inner_type"])

def render_asn1_object_class_docs(parser: markdown_parser.MarkdownParser, asn1_object_set):
    for field in asn1_object_set["fields"].values():
        rendered = render_asn1_markdown(parser, field["doc"])
        validate_requirements_language(rendered)
        field["markdown_doc"] = rendered

def render_asn1_object_set_docs(parser: markdown_parser.MarkdownParser, asn1_object_set):
    for member in asn1_object_set["members"]:
        rendered = render_asn1_markdown(parser, member["doc"])
        validate_requirements_language(rendered)
        member["markdown_doc"] = rendered

def render_asn1_docs(parser: markdown_parser.MarkdownParser, asn1_data):
    for assignment in asn1_data["assignments"].values():
        rendered = render_asn1_markdown(parser, assignment["doc"])
        validate_requirements_language(rendered)
        assignment["markdown_doc"] = rendered
        if assignment["assignment"]["assignment_type"] == "type":
            render_asn1_type_docs(parser, assignment["assignment"]["type"])
        elif assignment["assignment"]["assignment_type"] == "object_class":
            render_asn1_object_class_docs(parser, assignment["assignment"]["class"])
        elif assignment["assignment"]["assignment_type"] == "object_set":
            render_asn1_object_set_docs(parser, assignment["assignment"]["set"])