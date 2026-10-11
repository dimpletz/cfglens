"""Optional stdio MCP server. Install cfglens[mcp] to enable."""

from .core import compare, load_config


def main():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit(
            'Install optional dependency: pip install "cfglens[mcp]"'
        ) from exc
    server = FastMCP("CfgLens")

    @server.tool()
    def compare_configs(
        before_path: str, after_path: str, format: str | None = None
    ) -> dict:
        """Compare two local config files; sensitive values are redacted."""
        changes = compare(
            load_config(before_path, format), load_config(after_path, format)
        )
        return {"count": len(changes), "changes": changes}

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
