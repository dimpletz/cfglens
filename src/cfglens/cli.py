import argparse
import json
import sys

from .core import ConfigError, _terminal_safe_text, compare, load_config


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare configuration files safely")
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument(
        "--format",
        choices=["json", "yaml", "toml", "env"],
        help="Force both input formats",
    )
    parser.add_argument("--output", choices=["human", "json"], default="human")
    parser.add_argument(
        "--show-values",
        action="store_true",
        help="UNSAFE: may expose secrets in output",
    )
    args = parser.parse_args(argv)
    try:
        changes = compare(
            load_config(args.before, args.format),
            load_config(args.after, args.format),
            show_values=args.show_values,
        )
    except ConfigError as exc:
        print(_terminal_safe_text(f"cfglens: {exc}"), file=sys.stderr)
        return 2
    if args.output == "json":
        try:
            output = json.dumps(
                {"changes": changes, "count": len(changes)},
                indent=2,
                ensure_ascii=True,
                allow_nan=False,
            )
        except (TypeError, ValueError, OverflowError):
            print("cfglens: Could not encode comparison as JSON", file=sys.stderr)
            return 2
        print(output)
    else:
        if not changes:
            print("No changes")
        for c in changes:
            print(
                f"{c['change'].upper():12} "
                f"{_terminal_safe_text(c['path'])} "
                f"({c['before_type']} -> {c['after_type']})"
            )
            before = _terminal_safe_text(repr(c["before"]))
            after = _terminal_safe_text(repr(c["after"]))
            print(f"  before: {before}  after: {after}")
        print(f"{len(changes)} change(s)")
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
