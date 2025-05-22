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
        print("An error occurred during Graphiti operations:")
        raise  # Re-raise the exception after logging
    episodes = [
        {
            "name": "CustomerProfile",
            "episode_body": '{\\"company\\": {\\"name\\": \\"Acme Technologies\\"}, }',
            "source": "json",
            "source_description": "CRM data",
        },
        {
            "name": "CustomerConversation",
            "episode_body": "user: What's your return policy?\nassistant: You can return items within 30 days.",
            "source": EpisodeType.text,
            "source_description": "chat transcript",
            "group_id": "some_arbitrary_string",
        },
    ]

    # Add episodes to the graph
    for i, episode in enumerate(episodes[1:2]):
        await graphiti.add_episode(
            name=episode["name"],
            episode_body=(
                episode["episode_body"]
                if isinstance(episode["episode_body"], str)
                else json.dumps(episode["episode_body"])
            ),
            source=episode["source"],
            source_description=episode["source_description"],
            reference_time=datetime.now(timezone.utc),
        )
        print(f"Added episode: ({episode['name']})")


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

            print(f"Calling 'add_memory' with arguments: {arguments}")

            response = await client.call_tool("add_memory", arguments)

            print(f"Received response: {response}")

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
                    "name": "CustomerProfile",
                    "episode_body": '{\\"company\\": {\\"name\\": \\"Acme Technologies\\"}, }',
                    "source": "json",
                    "source_description": "CRM data",
                },
                {
                    "name": "CustomerConversation",
                    "episode_body": "user: What's your return policy?\nassistant: You can return items within 30 days.",
                    "source": EpisodeType.text,
                    "source_description": "chat transcript",
                    "group_id": "some_arbitrary_string",
                },
            ]

            for i, episode in enumerate(episodes):
                resp = await add_graphiti_episode(
                    GRAPHITI_SERVER_URL,
                    name=episode["name"],
                    episode_body=(
                        episode["episode_body"]
                        if isinstance(episode["episode_body"], str)
                        else json.dumps(episode["episode_body"])
                    ),
                    source=episode["source"],
                    source_description=episode["source_description"],
                    group_id="test_graph_group",
                    uuid=str(uuid.uuid4()),
                )
                print(f"Added episode: {episode['name']}")
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


if __name__ == "__main__":
    print(f"Attempting to connect to Graphiti server at {GRAPHITI_SERVER_URL}")
    asyncio.run(cli_menu())
