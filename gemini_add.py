import json
import logging
import os
from datetime import datetime, timezone
from logging import INFO

from graphiti_core import Graphiti
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

# Configure logging

logging.basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# Google API key configuration
async def main():
    """Initializes Graphiti with Gemini clients and builds indices."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or not api_key.strip():  # Added check for empty string
        logger.error("GOOGLE_API_KEY environment variable must be set and not empty")
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
        logger.info("Graphiti initialized successfully")

        # Initialize the graph database with graphiti's indices. This only needs to be done once.
        logger.info("Building indices and constraints...")
        await graphiti.build_indices_and_constraints()
        logger.info("Indices and constraints built successfully")

        # Additional code will go here

    except Exception as e:
        logger.exception(
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
        {
            "content": "Kamala Harris is the Attorney General of California. She was previously "
            "the district attorney for San Francisco.",
            "type": EpisodeType.text,
            "description": "podcast transcript",
        },
        # {
        #     "content": "As AG, Harris was in office from January 3, 2011 – January 3, 2017",
        #     "type": EpisodeType.text,
        #     "description": "podcast transcript",
        # },
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


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
