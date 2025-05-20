import asyncio
import json
import logging
import os
import time  # For polling
import uuid
from datetime import datetime, timezone
from logging import INFO
from typing import Any, Dict, List

from fastmcp import Client
from fastmcp.client import SSETransport
from graphiti_core import Graphiti
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
from mcp.types import TextContent  # Need this for parsing response

GRAPHITI_SERVER_URL = os.environ.get("GRAPHITI_SERVER_URL", "http://localhost:8000/sse")


async def add_direct():
    """Initializes Graphiti with Gemini clients and builds indices."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or not api_key.strip():  # Added check for empty string
        print("GOOGLE_API_KEY environment variable must be set and not empty")
        raise ValueError(
            "GOOGLE_API_KEY environment variable must be set and not empty"
        )

    graphiti = None
    try:
        # Initialize Graphiti with Gemini clients
        graphiti = Graphiti(
            "bolt://localhost:7687",
            "neo4j",
            "demodemo",
            llm_client=GeminiClient(
                config=LLMConfig(api_key=api_key, model="gemini-2.0-flash")
            ),
            embedder=GeminiEmbedder(
                config=GeminiEmbedderConfig(
                    api_key=api_key, embedding_model="embedding-001"
                )
            ),
        )
        print("Graphiti initialized successfully")

        # Initialize the graph database with graphiti's indices. This only needs to be done once.
        print("Building indices and constraints...")
        await graphiti.build_indices_and_constraints()
        print("Indices and constraints built successfully")

        # Additional code will go here

    except Exception as e:
        print(
            "An error occurred during Graphiti operations:"
        )  # Logs the full traceback
        # You might want to handle specific exceptions differently here
        # For example:
        # except neo4j.exceptions.ServiceUnavailable as e:
        #     logger.error("Failed to connect to Neo4j database: %s", e)
        # except SomeGeminiAPIError as e:
        #     logger.error("Gemini API error: %s", e)
        raise  # Re-raise the exception after logging

    # Episodes list containing both text and JSON episodes
    episodes = [
        # {
        #     "content": "Kamala Harris is the Attorney General of California. She was previously "
        #     "the district attorney for San Francisco.",
        #     "type": EpisodeType.text,
        #     "description": "podcast transcript",
        # },
        {
            "content": "As AG, Harris was in office from January 3, 2011 – January 3, 2017",
            "type": EpisodeType.text,
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

    # Add episodes to the graph
    for i, episode in enumerate(episodes):
        await graphiti.add_episode(
            name=f"Freakonomics Radio {i}",
            episode_body=(
                episode["content"]
                if isinstance(episode["content"], str)
                else json.dumps(episode["content"])
            ),
            source=episode["type"],
            source_description=episode["description"],
            reference_time=datetime.now(timezone.utc),
        )
        print(f"Added episode: Freakonomics Radio {i} ({episode['type'].value})")


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


async def get_user_choice():
    print("\nChoose an action:")
    print("1. Add an episode")
    print("2. Search for nodes")
    print("3. Clear the graph")
    print("4. Exit")
    print("5. Add directly using gemini")

    while True:
        choice = input("Enter your choice (1-5): ")
        if choice in ["1", "2", "3", "4", "5"]:
            return choice
        else:
            print("Invalid choice. Please enter a number between 1 and 4.")


async def cli_menu():
    while True:
        choice = await get_user_choice()

        if choice == "1":
            # name = input("Enter episode name: ")
            # episode_body = input("Enter episode body: ")
            # source = input("Enter source (default: text): ") or "text"
            # source_description = input("Enter source description: ")
            # group_id = (
            #     input("Enter group ID (default: test_graph_group): ")
            #     or "test_graph_group"
            # )
            # uuid_str = input("Enter UUID (optional): ")
            # uuid_value = uuid_str if uuid_str else None
            # await add_graphiti_episode(
            #     GRAPHITI_SERVER_URL,
            #     name=name,
            #     episode_body=episode_body,
            #     source=source,
            #     source_description=source_description,
            #     group_id=group_id,
            #     uuid=uuid_value,
            # )

            episodes = [
                {
                    "content": "As AG, Harris was in office from January 3, 2011 – January 3, 2017",
                    "type": "message",
                    "description": "podcast transcript",
                }
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

        elif choice == "2":
            query = input("Enter your search query: ")
            await search_graphiti_episode(GRAPHITI_SERVER_URL, query)

        elif choice == "3":
            await clear_db(GRAPHITI_SERVER_URL)

        elif choice == "4":
            print("Exiting...")
            break
        elif choice == "5":
            await add_direct()


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
    asyncio.run(cli_menu())
