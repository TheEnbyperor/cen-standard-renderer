import argparse
import json
import pathlib
from . import markdown_parser
from . import docx_renderer
from . import utils
from . import terms
from . import ir
from . import standard


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compile Markdown source for a CEN-style standard to DOCX"
    )
    ap.add_argument("input", type=pathlib.Path)
    ap.add_argument("-o", "--output", type=pathlib.Path, required=True)
    ap.add_argument(
        "--template", type=pathlib.Path,
        help="DOCX template/reference document containing CEN styles",
    )
    ap.add_argument(
        "--asn1", type=pathlib.Path,
        help="JSON file compiled from ASN.1 modules",
    )
    ap.add_argument(
        "--check", action="store_true",
        help="Parse, number and validate without writing a DOCX",
    )
    args = ap.parse_args()

    parser = markdown_parser.MarkdownParser()

    if args.asn1:
        with open(args.asn1, "r") as f:
            asn1_data = json.load(f)
    else:
        asn1_data = None

    src = standard.StandardSource.load(args.input, parser)

    if asn1_data:
        utils.render_asn1_docs(parser, asn1_data)

    if args.check:
        print("OK")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    renderer = docx_renderer.DocxRenderer(args.template, asn1_data)
    renderer.render(src, args.output)


if __name__ == "__main__":
    main()