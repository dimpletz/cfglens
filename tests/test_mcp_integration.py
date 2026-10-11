"""Real stdio MCP integration coverage (requires the optional MCP extra)."""

import json
import os
import shutil
import sys

import anyio
import pytest

pytest.importorskip("mcp")
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _result_data(result):
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    text = next(block.text for block in result.content if hasattr(block, "text"))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def test_stdio_server_discovery_comparison_errors_and_filesystem_access(tmp_path):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    malformed = tmp_path / "malformed.yaml"
    before.write_text(
        "databaseUrl: 2024-01-02\n"
        "items: !!set {b: null, a: null}\n"
        "nested: {password: SYNTHETIC_MCP_BEFORE}\n",
        encoding="utf-8",
    )
    after.write_text(
        "databaseUrl: 2024-01-03\n"
        "items: !!set {a: null, c: null}\n"
        "nested: {password: SYNTHETIC_MCP_AFTER}\n",
        encoding="utf-8",
    )
    malformed.write_text("password: [SYNTHETIC_MCP_ERROR\n", encoding="utf-8")

    installed_server = shutil.which("cfglens-mcp")
    parameters = StdioServerParameters(
        command=installed_server or sys.executable,
        args=[] if installed_server else ["-m", "cfglens.mcp_server"],
        env=os.environ.copy(),
    )

    async def exercise_server():
        async with stdio_client(parameters) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert [tool.name for tool in tools.tools] == ["compare_configs"]
            assert "show_values" not in tools.tools[0].inputSchema["properties"]

            arguments = {
                "before_path": str(before),
                "after_path": str(after),
            }
            first = await session.call_tool("compare_configs", arguments)
            repeated = await session.call_tool("compare_configs", arguments)
            response = _result_data(first)
            assert response == _result_data(repeated)
            serialized = json.dumps(response, allow_nan=False)
            assert "SYNTHETIC_MCP_" not in serialized
            assert "[REDACTED]" in serialized
            assert any(item["before_type"] == "date" for item in response["changes"])
            assert any(item["before_type"] == "set" for item in response["changes"])

            invalid = await session.call_tool(
                "compare_configs",
                {
                    "before_path": str(malformed),
                    "after_path": str(after),
                    "format": "yaml",
                },
            )
            error_data = _result_data(invalid)
            error_text = (
                error_data
                if isinstance(error_data, str)
                else json.dumps(error_data, allow_nan=False)
            )
            assert invalid.isError
            assert "SYNTHETIC_MCP_ERROR" not in error_text

            inaccessible = await session.call_tool(
                "compare_configs",
                {
                    "before_path": str(tmp_path / "not-readable.json"),
                    "after_path": str(after),
                },
            )
            assert inaccessible.isError
            inaccessible_data = _result_data(inaccessible)
            inaccessible_text = (
                inaccessible_data
                if isinstance(inaccessible_data, str)
                else json.dumps(inaccessible_data, allow_nan=False)
            )
            assert "not-readable.json" in inaccessible_text

    anyio.run(exercise_server)
