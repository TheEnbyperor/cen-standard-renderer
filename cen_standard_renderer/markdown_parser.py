import re
import yaml
import typing
import marko
import shlex
from . import ir

FRONT_MATTER = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)
HEADING_ID = re.compile(r"\s*{#([A-Za-z][A-Za-z0-9_.:-]*)}\s*$")
DIRECTIVE_OPEN = re.compile(r"^:::\s*([A-Za-z][A-Za-z0-9_-]*)(?:\s+{([^}]*)})?\s*$")
DIRECTIVE_ONE_LINE = re.compile(r"^:::\s*([A-Za-z][A-Za-z0-9_-]*)(?:\s+{([^}]*)})?\s*:::$")


class MarkdownParser:
    def __init__(self) -> None:
        self.md = marko.Markdown()

    def parse(self, source: str) -> ir.Document:
        metadata, body = split_front_matter(source)
        blocks = self.parse_blocks(body)
        return ir.Document(metadata=metadata, blocks=blocks)

    def parse_inlines(self, source: str) -> list[ir.Inline]:
        ast = self.md.parse(source)
        blocks = self._blocks(ast.children)
        if len(blocks) != 1 or not isinstance(blocks[0], ir.Paragraph):
            raise ValueError(f"Expected inline Markdown, got: {source!r}")
        return blocks[0].children

    def parse_blocks(self, source: str) -> list[ir.Block]:
        body, directives = extract_directives(source)
        ast = self.md.parse(body)
        blocks = self._expand_directives(self._blocks(ast.children), directives)
        return self._lower_directives(blocks)

    def _expand_directives(self, blocks, directives):
        out = []
        for block in blocks:
            if isinstance(block, ir.Paragraph) and len(block.children) == 1 and isinstance(block.children[0], ir.Text) \
                    and block.children[0].text in directives:
                name, raw_attrs, body = directives[block.children[0].text]
                ident, attrs = parse_directive_attributes(raw_attrs)
                inner = self.parse_blocks(body)
                out.append(ir.Directive(name, attrs, ident, inner))
            else:
                out.append(block)
        return out

    def _lower_directives(self, blocks):
        out = []
        for block in blocks:
            if not isinstance(block, ir.Directive):
                out.append(block)
                continue

            name = block.name.lower()
            if name in {"introduction", "scope"}:
                inner = self._lower_directives(block.blocks)
                out.append(ir.SpecialBlock(name, inner))
            elif name == "asn1-type":
                out.append(ir.ASN1Type(block.attributes["ref"]))
            else:
                raise SyntaxError(f"Unknown ::: directive: {block.name}")

        return out

    def _blocks(self, nodes: typing.Iterable) -> list[ir.Block]:
        result: list[ir.Block] = []

        for node in nodes:
            name = type(node).__name__

            if name == "BlankLine":
                pass

            elif name == "Paragraph":
                result.append(ir.Paragraph(self._inlines(node.children)))

            elif name == "Heading":
                inlines = self._inlines(node.children)
                identifier = None

                if inlines and isinstance(inlines[-1], ir.Text):
                    m = HEADING_ID.search(inlines[-1].text)
                    if m:
                        identifier = m.group(1)
                        inlines[-1].text = HEADING_ID.sub("", inlines[-1].text)
                        if not inlines[-1].text:
                            inlines.pop()

                result.append(ir.Heading(
                        level=node.level,
                        children=inlines,
                        identifier=identifier,
                ))

            elif name == "FencedCode":
                language = None
                lang = getattr(node, "lang", None)
                if lang:
                    language = str(lang).strip() or None
                result.append(ir.CodeBlock(
                    text=self._raw_text(node),
                    language=language,
                ))

            elif name == "CodeBlock":
                result.append(ir.CodeBlock(text=self._raw_text(node)))

            elif name == "Quote":
                result.append(ir.Blockquote(self._blocks(node.children)))

            elif name == "List":
                items = []
                for item in node.children:
                    items.append(self._blocks(item.children))
                if getattr(node, "ordered", False):
                    result.append(ir.OrderedList(items))
                else:
                    result.append(ir.BulletList(items))

            else:
                raise NotImplementedError(f"Markdown block {name} is not implemented yet")

        return result

    def _inlines(self, nodes: typing.Iterable) -> list[ir.Inline]:
        result: list[ir.Inline] = []

        for node in nodes:
            name = type(node).__name__

            if name in {"RawText", "Literal"}:
                result.append(ir.Text(str(node.children)))
            elif name == "LineBreak":
                if node.soft:
                    result.append(ir.SoftBreak())
                else:
                    result.append(ir.HardBreak())
            elif name == "CodeSpan":
                result.append(ir.Code(self._raw_text(node)))
            elif name == "StrongEmphasis":
                result.append(ir.Strong(self._inlines(node.children)))
            elif name == "Emphasis":
                result.append(ir.Emphasis(self._inlines(node.children)))
            elif name == "Link":
                result.append(ir.Link(
                    children=self._inlines(node.children),
                    destination=node.dest,
                ))
            else:
                children = getattr(node, "children", None)
                if isinstance(children, list):
                    result.extend(self._inlines(children))
                elif children is not None:
                    result.append(ir.Text(str(children)))
                else:
                    raise NotImplementedError(f"Markdown inline {name} is not implemented yet")

        return result

    @staticmethod
    def _raw_text(node) -> str:
        children = getattr(node, "children", "")
        if isinstance(children, str):
            return children
        if isinstance(children, list):
            return "".join(MarkdownParser._raw_text(x) for x in children)
        return str(children)


def split_front_matter(source: str) -> tuple[dict, str]:
    match = FRONT_MATTER.match(source)
    if not match:
        return {}, source

    metadata = yaml.safe_load(match.group(1)) or {}
    return metadata, source[match.end():]


def parse_directive_attributes(raw):
    ident, attrs = None, {}
    for token in shlex.split(raw or ""):
        if token.startswith("#"):
            ident = token[1:]
        elif "=" in token:
            k, v = token.split("=", 1)
            attrs[k] = v
        else:
            attrs[token] = "true"
    return ident, attrs


def extract_directives(source):
    lines, out, found = source.splitlines(keepends=True), [], {}
    i = serial = 0
    while i < len(lines):
        if m := DIRECTIVE_ONE_LINE.match(lines[i].rstrip("\r\n")):
            name, raw_attrs = m.groups()
            token = f"---DIRECTIVEPLACEHOLDER{serial}---"
            serial += 1
            found[token] = (name, raw_attrs, "")
            out.append(token + "\n\n")
            i += 1
            continue

        m = DIRECTIVE_OPEN.match(lines[i].rstrip("\r\n"))
        if not m:
            out.append(lines[i])
            i += 1
            continue

        name, raw_attrs = m.groups()
        depth, j, body, fence = 1, i + 1, [], None
        while j < len(lines):
            text = lines[j].rstrip("\r\n")
            fm = re.match(r"^\s*(```+|~~~+)", text)
            if fm:
                ch = fm.group(1)[0]
                fence = ch if fence is None else (None if fence == ch else fence)
                body.append(lines[j])
                j += 1
                continue

            if fence is None:
                if DIRECTIVE_OPEN.match(text):
                    depth += 1
                elif re.match(r"^:::\s*$", text):
                    depth -= 1
                    if depth == 0:
                        break

            body.append(lines[j])
            j += 1

        if depth:
            raise SyntaxError(f"Unclosed ::: {name} directive")

        token = f"---DIRECTIVEPLACEHOLDER{serial}---"
        serial += 1
        found[token] = (name, raw_attrs, "".join(body))
        out.append(token + "\n\n")
        i = j + 1

    return "".join(out), found