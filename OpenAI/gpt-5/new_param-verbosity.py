# gpt5_demo.py
import os
import sys
import pdb
import argparse
import traceback
import functools
from typing import Optional

import pandas as pd
from openai import OpenAI
from rich import print as rich_print
from dotenv import find_dotenv, load_dotenv

pd.set_option('display.max_colwidth', None)

def debug_on_error(func):
    """Decorator to run pdb.post_mortem when an exception occurs."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Catch any exception and launch pdb in post-mortem mode
            rich_print(f"[red]Exception occurred in {func.__name__}:[/red]")
            rich_print(f"[red]Error: {e}[/red]")
            rich_print(f"[red]Traceback: {traceback.format_exc()}[/red]")
            pdb.post_mortem()
            raise  # Re-raise the exception after post-mortem inspection
    return wrapper

def make_client():
    """
    Create a genai.Client. The SDK will auto-pick GOOGLE_API_KEY (or GEMINI_API_KEY).
    If you prefer, pass api_key=... explicitly.
    """
    rich_print("[yellow]Creating a OpenAI Client[/yellow]")
    load_dotenv(find_dotenv())
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    return OpenAI(api_key=OPENAI_API_KEY)

def compare_verbosity(client: OpenAI, question: str) -> None:

    data = []
    for verbosity in ["low", "medium", "high"]:
        response = client.responses.create(
            model="gpt-5-mini",
            input=question,
            text={"verbosity": verbosity}
        )

        # Extract text
        output_text = ""
        for item in response.output:
            if hasattr(item, "content") and item.content:
                for content in item.content:
                    if hasattr(content, "text"):
                        output_text += content.text

        usage = response.usage
        """
            ResponseUsage(
                input_tokens=19,
                input_tokens_details=InputTokensDetails(cached_tokens=0),
                output_tokens=1580,
                output_tokens_details=OutputTokensDetails(reasoning_tokens=1152),
                total_tokens=1599
            )
        """

        # calculate tokens
        num_reasoning_tokens = usage.output_tokens_details.reasoning_tokens
        num_total_tokens = usage.output_tokens
        num_non_reasoning_tokens = num_total_tokens - num_reasoning_tokens

        # append data
        data.append({
            "Verbosity": verbosity,
            "Sample Output": output_text,
            "Reasoning Tokens": num_reasoning_tokens,
            "Non-Reasoning Tokens": num_non_reasoning_tokens,
            "Total Tokens": num_total_tokens
        })

    return data

@debug_on_error
def main() -> None:
    client = make_client()

    rich_print("[green]Compare the difference Verbosity parameters.[/green]")
    
    question = "Compare the difference between New Jeans and Le Sserafim."
    
    data = compare_verbosity(client, question)

    # Create DataFrame
    df = pd.DataFrame(data)
    _ = df.pop("Sample Output")
    print(df)

if __name__ == "__main__":
    main()
