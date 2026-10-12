"""Command line interface: get, set, delete, has, glob, flatten and unflatten over JSON."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import NoReturn

from ._commands import CliError, run
from ._errors import DotreachError
from ._version import __version__

_EPILOG = """\
examples:
  echo '{"user": {"name": "Ada", "roles": ["admin"]}}' > data.json
  dotreach get user.name data.json              prints "Ada"
  dotreach get user.name --raw data.json        prints Ada (no JSON quotes)
  dotreach get user.age --default 0 data.json   prints 0 instead of failing
  dotreach has user.roles.0 data.json           no output, exit 0 if present, 1 if not
  dotreach set user.age 36 data.json            VALUE is JSON when valid, else a string
  dotreach set user.city Paris -i data.json     edit the file in place
  dotreach set tags.0 new --create-lists data.json
  dotreach delete user.roles.-1 data.json
  dotreach glob 'user.*' data.json              every match, as {"path": value}
  dotreach flatten data.json                    {"user.name": "Ada", "user.roles.0": "admin"}
  dotreach flatten data.json | dotreach unflatten --create-lists
  curl -s https://example.com/api | dotreach get items.0.id

FILE defaults to standard input ("-"). Results go to stdout as JSON. Errors go to
stderr with exit code 1; "has" also exits 1 when the path is absent.
"""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _common(sub: argparse.ArgumentParser, *, writes: bool = False) -> None:
    sub.add_argument("file", nargs="?", default="-", help="JSON file to read (default: stdin)")
    sub.add_argument("--sep", default=".", help="path separator (default: '.')")
    sub.add_argument(
        "--escape", action="store_true", help="treat '\\.' in a path as a literal separator"
    )
    sub.add_argument("--indent", type=int, default=2, help="JSON indent, 0 for compact")
    if writes:
        sub.add_argument(
            "-i", "--in-place", action="store_true", help="write the result back to FILE"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="dotreach",
        description="Get, set and delete values in JSON by dotted path.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"dotreach {__version__}")
    subs = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    get = subs.add_parser("get", help="print the value at PATH")
    get.add_argument("path", help="dotted path, for example user.roles.0")
    get.add_argument("--default", metavar="JSON", help="print this instead of failing")
    get.add_argument("--raw", action="store_true", help="print a string result without quotes")
    _common(get)

    has = subs.add_parser("has", help="exit 0 if PATH exists, 1 if not")
    has.add_argument("path", help="dotted path to test")
    _common(has)

    put = subs.add_parser("set", help="set PATH to VALUE and print the document")
    put.add_argument("path", help="dotted path; missing dicts are created")
    put.add_argument("value", help="JSON value; text that is not valid JSON is a string")
    put.add_argument("--string", action="store_true", help="always treat VALUE as a string")
    put.add_argument(
        "--create-lists", action="store_true", help="integer segments build lists and append"
    )
    _common(put, writes=True)

    rm = subs.add_parser("delete", help="remove PATH and print the document")
    rm.add_argument("path", help="dotted path to remove")
    rm.add_argument("--missing-ok", action="store_true", help="do not fail if PATH is absent")
    _common(rm, writes=True)

    glob = subs.add_parser("glob", help="print every match of a '*' / '**' pattern")
    glob.add_argument("pattern", help="'*' matches one level, '**' any number of levels")
    _common(glob)

    flat = subs.add_parser("flatten", help="print a one-level {path: value} object")
    _common(flat)

    unflat = subs.add_parser("unflatten", help="rebuild nesting from a {path: value} object")
    unflat.add_argument("--create-lists", action="store_true", help="integer segments build lists")
    _common(unflat)
    return parser


def _parse(parser: argparse.ArgumentParser, argv: Sequence[str] | None) -> argparse.Namespace:
    # Before Python 3.12, argparse will not fill an optional trailing positional (FILE)
    # that follows option flags, so a lone leftover argument is taken as FILE here.
    args, extra = parser.parse_known_args(argv)
    if len(extra) == 1 and args.file == "-" and (extra[0] == "-" or extra[0][:1] != "-"):
        args.file = extra[0]
    elif extra:
        parser.error(f"unrecognized arguments: {' '.join(extra)}")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface and return its exit code.

    Returns ``0`` on success, ``1`` on any error (message on stderr) and ``1`` from
    ``has`` when the path is absent.
    """
    args = _parse(_build_parser(), argv)
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    try:
        return run(args)
    except (CliError, DotreachError, ValueError, OSError) as error:
        print(f"dotreach: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
