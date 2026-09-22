import dataclasses

HEADING_LEVEL_TERM = -1


@dataclasses.dataclass
class Inline:
    pass


@dataclasses.dataclass
class SoftBreak(Inline):
    pass


@dataclasses.dataclass
class HardBreak(Inline):
    pass

@dataclasses.dataclass
class Text(Inline):
    text: str


@dataclasses.dataclass
class Code(Inline):
    text: str


@dataclasses.dataclass
class Strong(Inline):
    children: list[Inline]


@dataclasses.dataclass
class Emphasis(Inline):
    children: list[Inline]


@dataclasses.dataclass
class Link(Inline):
    children: list[Inline]
    destination: str


@dataclasses.dataclass
class ASN1Reference(Inline):
    name: str
    ref_id: str


@dataclasses.dataclass
class Block:
    pass


@dataclasses.dataclass
class Paragraph(Block):
    children: list[Inline]


@dataclasses.dataclass
class Blockquote(Block):
    children: list[Block]


@dataclasses.dataclass
class Heading(Block):
    level: int
    children: list[Inline]
    identifier: str | None = None


@dataclasses.dataclass
class CodeBlock(Block):
    text: str
    language: str | None = None


@dataclasses.dataclass
class BulletList(Block):
    items: list[list[Block]]


@dataclasses.dataclass
class OrderedList(Block):
    items: list[list[Block]]


@dataclasses.dataclass
class Directive(Block):
    name: str
    attributes: dict[str, str]
    identifier: str | None
    blocks: list[Block]


@dataclasses.dataclass
class SpecialBlock(Block):
    kind: str
    blocks: list[Block]


@dataclasses.dataclass
class ASN1Type(Block):
    ref: str


@dataclasses.dataclass
class Document:
    metadata: dict
    blocks: list[Block]

@dataclasses.dataclass
class TermDefinition:
    identifier: str
    term: str
    definition: str
    admitted_terms: list[str] = dataclasses.field(default_factory=list)
    source: str | None = None