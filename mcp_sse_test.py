import argparse
import asyncio
import json
import os
import time  # For polling
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastmcp import Client
from fastmcp.client import SSETransport
from mcp.types import TextContent  # Need this for parsing response

GRAPHITI_SERVER_URL = os.environ.get("GRAPHITI_SERVER_URL", "http://localhost:8000/sse")


async def add_graphiti_episode(
    server_url: str,
    name: str,
    episode_body: str,
    group_id: str | None = None,
    source: str = "text",
    source_description: str = "",
    uuid: str | None = None,
) -> Dict[str, Any]:
    try:
        # The Client will infer the transport based on the URL
        client = Client(SSETransport(server_url))

        # Use the client as an async context manager to connect and manage the session
        async with client:
            print(f"Connected to Graphiti server at {server_url}")

            # Prepare the arguments for the 'add_episode' tool
            # Note: The server code expects a dict, so we pass a dict.
            # FastMCP handles the JSON-RPC parameter mapping.

            arguments: Dict[str, Any] = {
                "name": name,
                "episode_body": episode_body,
                "source": source,
                "source_description": source_description,
            }
            if group_id is not None:
                arguments["group_id"] = group_id
            if uuid is not None:
                arguments["uuid"] = uuid

            print(f"Calling 'add_episode' with arguments: {arguments}")

            response = await client.call_tool("add_episode", arguments)

            # The response will be the raw JSON-RPC result value.
            # We expect it to be a dict like {'message': ...} or {'error': ...}.

            print(f"Received response: {response}")

            # if isinstance(response, dict) and "error" in response:
            #     print(f"Server returned an error: {response['error']}")
            #     # Depending on how you want to handle errors, you might raise an exception
            #     # raise Exception(f"Server error: {response['error']}")
            #     return response
            # elif isinstance(response, dict) and "message" in response:
            #     print(f"Server returned success: {response['message']}")
            #     return response
            # else:
            #     print(f"Unexpected server response format: {response}")
            #     # Or handle unexpected response format
            #     raise ValueError(f"Unexpected server response format: {response}")

    except Exception as e:
        print(f"An error occurred: {e}")
        raise


async def cli_menu():
    parser = argparse.ArgumentParser(description="Interact with Graphiti server.")
    parser.add_argument(
        "--action",
        choices=["add", "search", "clear"],
        help="Choose an action: add, search, or clear",
    )
    parser.add_argument("--name", help="Name for add_episode")
    parser.add_argument("--episode_body", help="Episode body for add_episode")
    parser.add_argument("--source", default="text", help="Source for add_episode")
    parser.add_argument(
        "--source_description", default="", help="Source description for add_episode"
    )
    parser.add_argument("--group_id", default="test_graph_group", help="Group ID")
    parser.add_argument("--uuid", help="UUID for add_episode")
    parser.add_argument("--query", help="Query for search_nodes")

    args = parser.parse_args()

    if args.action == "add":
        if not args.name or not args.episode_body:
            print("Name and episode_body are required for add action.")
            return
        await add_graphiti_episode(
            GRAPHITI_SERVER_URL,
            name=args.name,
            episode_body=args.episode_body,
            source=args.source,
            source_description=args.source_description,
            group_id=args.group_id,
            uuid=args.uuid,
        )
    elif args.action == "search":
        if not args.query:
            print("Query is required for search action.")
            return
        await search_graphiti_episode(GRAPHITI_SERVER_URL, args.query)
    elif args.action == "clear":
        await clear_db(GRAPHITI_SERVER_URL)
    else:
        print("Please specify an action: add, search, or clear")


async def search_graphiti_episode(
    server_url: str,
    query: str,
) -> Dict[str, Any]:
    try:
        client = Client(SSETransport(server_url))

        async with client:
            print(f"Connected to Graphiti server at {server_url}")

            arguments: Dict[str, Any] = {
                "query": query,
                "group_ids": [],
                "max_nodes": 10,
                "center_node_uuid": "",
                "entity": "",
            }

            print(f"Calling 'search_episode' with arguments: {arguments}")

            response = await client.call_tool("search_nodes", arguments)
            print(f"Received response: {response}")

    except Exception as e:
        print(f"An error occurred: {e}")
        raise


async def clear_db(server_url: str):
    client = Client(SSETransport(server_url))
    async with client:
        resp = await client.call_tool("clear_graph")


async def main():
    episodes = [
        # {
        #     "content": "Kamala Harris is the Attorney General of California. She was previously "
        #     "the district attorney for San Francisco.",
        #     "type": "message",
        #     "description": "podcast transcript",
        # },
        {
            "content": "As AG, Harris was in office from January 3, 2011 – January 3, 2017",
            "type": "message",
            "description": "podcast transcript",
        },
        # {
        #     "content": {
        #         "name": "Gavin Newsom",
        #         "position": "Governor",
        #         "state": "California",
        #         "previous_role": "Lieutenant Governor",
        #         "previous_location": "San Francisco",
        #     },
        #     "type": EpisodeType.json,
        #     "description": "podcast metadata",
        # },
        # {
        #     "content": {
        #         "name": "Gavin Newsom",
        #         "position": "Governor",
        #         "term_start": "January 7, 2019",
        #         "term_end": "Present",
        #     },
        #     "type": EpisodeType.json,
        #     "description": "podcast metadata",
        # },
    ]
    for i, episode in enumerate(episodes):
        resp = await add_graphiti_episode(
            GRAPHITI_SERVER_URL,
            name=f"Freakonomics Radio {i}",
            episode_body=(
                episode["content"]
                if isinstance(episode["content"], str)
                else json.dumps(episode["content"])
            ),
            source=episode["type"],
            source_description=episode["description"],
            group_id="test_graph_group",
            uuid=str(uuid.uuid4()),
        )
        print(f"Added episode: Freakonomics Radio {i}")
        print(resp)

    # (You can add calls for search_nodes etc. here using the updated functions)
    response = await search_graphiti_episode(
        GRAPHITI_SERVER_URL,
        "Kamala Harris is the Attorney General of California.",
    )
    print("search response is ", response)
    await clear_db(GRAPHITI_SERVER_URL)


if __name__ == "__main__":
    print(f"Attempting to connect to Graphiti server at {GRAPHITI_SERVER_URL}")
    # asyncio.run(main())
    asyncio.run(cli_menu())
