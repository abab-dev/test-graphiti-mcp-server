import csv
import os
from pprint import pprint
from typing import Any, Dict, List, Union

import litellm
import openai.types.chat  # Import chat types for type hinting
# Assuming 'studio_key' is defined in a 'utils.py' file
# from utils import studio_key
import tiktoken
# Ensure you have the necessary environment variables or a utils.py with studio_key
# For demonstration, I'll use a placeholder if studio_key is not available
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()
studio_key = os.environ["GEMINI_API_KEY"]


app = Flask(__name__)
# Configure your litellm credentials (if required for Google Gemini)
litellm.api_key = studio_key
os.environ["LITELLM_LOG"] = "DEBUG"  # Keep for debugging LiteLLM calls


# Define route for the Embeddings endpoint
@app.route("/embeddings", methods=["POST"])
def embeddings():
    try:
        # Parse the request payload
        payload = request.json
        print("Embeddings endpoint received payload:", payload)
        # Expects input as a list of strings or list of lists of integers
        input_data = payload.get("input", [])
        # model = payload.get(
        #     "model", "gemini/text-embedding-004"
        # )  # Default embedding model for LiteLLM

        model: str = "gemini/text-embedding-004"
        if not input_data:
            return jsonify({"error": "Input text is required"}), 400

        # Determine if input is tokens (list of lists of ints) or strings (list of strings)
        is_token_input = (
            isinstance(input_data, list)
            and input_data
            and isinstance(input_data[0], list)
            and input_data[0]
            and isinstance(input_data[0][0], int)
        )

        decoded_texts = []
        if is_token_input:
            # Initialize the tokenizer (Assuming a common tokenizer like GPT-4 for decoding tokens)
            # Note: Decoding tokens from one model might not be accurate for another model's tokenizer.
            # If your input tokens come from a specific model, use that model's tokenizer if available.
            # text-embedding-ada-002 is a common baseline.
            try:
                tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")
                decoded_texts = [
                    tokenizer.decode(token_list) for token_list in input_data
                ]
                print(f"Decoded string from tokens: {decoded_texts}")
            except Exception as e:
                print(
                    f"Warning: Could not decode tokens using tiktoken: {e}. Treating input as strings."
                )
                decoded_texts = input_data  # Fallback to treating as strings

        else:
            # Input is already a list of strings
            decoded_texts = input_data
            print(f"Input treated as strings: {decoded_texts}")

        # Use litellm to call the embedding model
        response = litellm.embedding(
            model=model,
            input=decoded_texts,  # LiteLLM expects a list of strings here
        )

        embeddings = [item.embedding for item in response.data]

        formatted_data = [
            {"object": "embedding", "embedding": emb, "index": i}
            for i, emb in enumerate(embeddings)
        ]

        return jsonify(
            {
                "object": "list",
                "model": model,
                "data": formatted_data,
                "usage": (
                    response.usage.model_dump() if response.usage else {}
                ),  # Include usage if available
            }
        )

    except Exception as e:
        # Handle errors
        print("Error in /embeddings:", e)
        return jsonify({"error": str(e)}), 500


# Define route for the Chat Completions endpoint
@app.route("/chat/completions", methods=["POST"])
def chat_completions():
    try:
        # Parse the request payload
        payload = request.json
        print("\nChat completions endpoint received payload:\n")
        print("-" * 80 + "\n")
        pprint(payload)

        # Extract required parameters
        messages: List[Dict[str, str]] = payload.get("messages")
        # model: str = payload.get(
        #     "model", "gemini/gemini-2.0-flash-lite"
        # )  # Default chat model
        model: str = "gemini/gemini-2.0-flash-lite"

        if not messages:
            return jsonify({"error": "Messages are required"}), 400

        # Optional parameters (mimicking OpenAI)
        temperature: float = payload.get("temperature", 1.0)
        max_tokens: int | None = payload.get("max_tokens")
        top_p: float = payload.get("top_p", 1.0)
        # Add other parameters as needed (e.g., stream, functions, tool_choice, etc.)
        # For simplicity, we'll start with basic ones.

        # Prepare messages for LiteLLM. LiteLLM usually accepts the same format
        # as OpenAI Chat Completions API (list of role/content dicts).
        # Ensure roles are valid (system, user, assistant, tool)
        valid_roles = ["system", "user", "assistant", "tool"]
        cleaned_messages = [msg for msg in messages if msg.get("role") in valid_roles]

        if not cleaned_messages:
            return (
                jsonify(
                    {
                        "error": "Valid messages with roles (system, user, assistant, tool) are required"
                    }
                ),
                400,
            )

        # Use litellm to call the chat completion model
        litellm_params: Dict[str, Any] = {
            "model": model,
            "messages": cleaned_messages,
            "temperature": temperature,
            "top_p": top_p,
            # Add other parameters like frequency_penalty, presence_penalty, stop, etc.
            # "stream": payload.get("stream", False), # Handle streaming if needed
        }
        if max_tokens is not None:
            litellm_params["max_tokens"] = max_tokens

        # If streaming is requested, we need to handle it differently
        if payload.get("stream", False):
            # LiteLLM can stream, but Flask needs to handle the stream response.
            # This requires using Flask's streaming capabilities or a library like flask-streaming.
            # For simplicity, let's implement non-streaming first.
            # Implementing streaming in Flask requires returning a generator or using a streaming extension.
            # We'll add a basic placeholder for streaming response.
            return (
                jsonify({"error": "Streaming is not yet implemented on this server"}),
                501,
            )

        # Non-streaming call
        response: openai.types.chat.ChatCompletion = litellm.completion(
            **litellm_params
        )

        # Format the response to mimic OpenAI's API
        # LiteLLM's response object is usually compatible with OpenAI's format
        # It should be a ChatCompletion object or similar dictionary structure
        formatted_response: Dict[str, Any] = (
            response.model_dump()
        )  # Use model_dump for Pydantic models

        return jsonify(formatted_response)

    except Exception as e:
        # Handle errors
        print("Error in /chat/completions:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Ensure you have LiteLLM and Flask installed:
    # pip install litellm flask openai tiktoken
    # Also install the necessary providers for LiteLLM (e.g., `pip install openai google-generativeai`)

    # Set the LITELLM_STUDIO_KEY environment variable, or define it in utils.py
    # export LITELLM_STUDIO_KEY='your_key_here'

    print("Starting Flask server...")
    app.run(port=5000, debug=True)
