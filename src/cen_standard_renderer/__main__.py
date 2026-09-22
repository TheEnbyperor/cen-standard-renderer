import argparse
import json
import pathlib
import os.path
import importlib.util
import zipimport
from . import markdown_parser
from . import docx_renderer
from . import utils
from . import standard


def find_template_folder(package_name: str, package_path: str = "templates") -> pathlib.Path:
    package_path = os.path.normpath(package_path).rstrip(os.path.sep)
    if package_path == os.path.curdir:
        package_path = ""
    elif package_path[:2] == os.path.curdir + os.path.sep:
        package_path = package_path[2:]

    spec = importlib.util.find_spec(package_name)
    assert spec is not None, "An import spec was not found for the package."
    loader = spec.loader
    assert loader is not None, "A loader was not found for the package."

    if isinstance(loader, zipimport.zipimporter):
        assert spec.submodule_search_locations is not None
        pkgdir = next(iter(spec.submodule_search_locations))
        return pathlib.Path(os.path.join(pkgdir, package_path).rstrip(os.path.sep))
    else:
        roots = []
        if spec.submodule_search_locations:
            roots.extend(spec.submodule_search_locations)
        elif spec.origin is not None:
            roots.append(os.path.dirname(spec.origin))
        assert roots
        for root in roots:
            root = os.path.join(root, package_path)

            if os.path.isdir(root):
                return pathlib.Path(root)

    raise ValueError("Templates not found")


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

    if args.template:
        template = args.template
    else:
        template = find_template_folder("cen_standard_renderer") / "cen.docx"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    renderer = docx_renderer.DocxRenderer(template, asn1_data)
    renderer.render(src, args.output)


if __name__ == "__main__":
    main()