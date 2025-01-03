import asyncio
from typing import Optional
from loguru import logger
from lmos_openai_types import CreateChatCompletionRequest
import mcp.types
import json

from mcp_clients.McpClientManager import ClientManager
from tool_mappers import mcp2openai


async def chat_completion_add_tools(request: CreateChatCompletionRequest):
    request.tools = []

    for _, session in ClientManager.get_clients():
        # if session is None, then the client is not running
        if session.session is None:
            logger.error(f"session is `None` for {session.name}")
            continue

        tools = await session.session.list_tools()
        for tool in tools.tools:
            request.tools.append(mcp2openai(tool))

    return request


async def call_tool(
    tool_call_name: str, tool_call_json: str, timeout: Optional[int] = None
) -> Optional[mcp.types.CallToolResult]:
    if tool_call_name == "" or tool_call_name is None:
        logger.error("tool call name is empty")
        return None

    if tool_call_json is None:
        logger.error("tool call json is empty")
        return None

    session = await ClientManager.get_client_from_tool(tool_call_name)

    if session is None:
        logger.error(f"session is `None` for {tool_call_name}")
        return None

    try:
        tool_call_args = json.loads(tool_call_json)
    except json.JSONDecodeError:
        logger.error(f"failed to decode json for {tool_call_name}")
        return None

    # try to call the tool
    try:
        async with asyncio.timeout(timeout):
            tool_call_result = await session.call_tool(
                name=tool_call_name,
                arguments=tool_call_args,
            )

    except asyncio.TimeoutError:
        logger.error(f"timed out calling {tool_call_name}")
        return None

    except mcp.McpError as e:
        logger.error(f"error calling {tool_call_name}: {e}")
        return mcp.types.CallToolResult(
            content=[
                mcp.types.TextContent(
                    type="text", text=f"Error calling {tool_call_name}: {e}"
                )
            ],
            isError=True,
        )

    return tool_call_result
