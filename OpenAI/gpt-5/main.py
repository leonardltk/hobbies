# gpt5_demo.py
import os
import sys
import pdb
import argparse
import traceback
import functools
from typing import Optional

from openai import OpenAI
from rich import print as rich_print
from dotenv import find_dotenv, load_dotenv

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

"""
Run:
    uv run main.py "Tell me what is Le Sserafim doing today." --effort medium --verbosity medium
"""


def make_client():
    """
    Create a genai.Client. The SDK will auto-pick GOOGLE_API_KEY (or GEMINI_API_KEY).
    If you prefer, pass api_key=... explicitly.
    """
    rich_print("[yellow]Creating a OpenAI Client[/yellow]")
    load_dotenv(find_dotenv())
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    return OpenAI(api_key=OPENAI_API_KEY)

def gpt5_answer(user_query: str, *, effort: str = "medium", verbosity: str = "low") -> str:
    """
    effort:    'minimal' | 'low' | 'medium' | 'high'
    verbosity: 'low' | 'medium' | 'high'   (controls how long the answer is)
    """
    client = make_client()

    # System/dev instructions reflect Cookbook guidance on:
    # - tool preambles (clear upfront plan & progress),
    # - calibrated eagerness (keep going unless unsafe),
    # - concise final output (verbosity control).
    system_instructions = (
        "<tool_preambles>\n"
            "- Begin by restating the user's goal in 1 sentence.\n"
            "- Outline a short plan (2-4 bullets) before any tool calls.\n"
            "- As you work, keep progress updates brief.\n"
            "- End with a concise summary of what you did.\n"
        "</tool_preambles>\n"
        "<persistence>\n"
            "- You are an agent. Keep going until the user's request is fully resolved.\n"
            "- If something is uncertain, make a reasonable assumption, proceed, and note it.\n"
            "- Only hand control back when the task is complete or if an explicit confirmation is required for a risky action.\n"
        "</persistence>\n"
        "<context_gathering>\n"
            "- Keep context gathering lightweight. Prefer acting over prolonged searching.\n"
            "- Stop once you have enough to proceed; avoid redundant steps.\n"
        "</context_gathering>\n"
        f"<verbosity target='{verbosity}'>Responses should match this target.</verbosity>"
    )

    # Responses API call
    resp = client.responses.create(
        model="gpt-5",
        # Cookbook suggests hierarchical instructions; we pass a system/dev block plus the user turn.
        input=[
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_query},
        ],
        reasoning={"effort": effort},          # Control "how hard it thinks"
        # temperature=0.2,                       # Favor determinism for docs/answers
        max_output_tokens=800,                 # Guardrail for cost/length
        # (Optional) You can set "verbosity": "low|medium|high" if available in your SDK version.
        # verbosity=verbosity,
    )

    # Be robust to SDK version quirks around resp.output_text:
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text.strip()

    # Fallback: join any text outputs
    chunks = []
    for item in getattr(resp, "output", []) or []:
        if getattr(item, "type", "") in ("message", "output_text", "reasoning"):  # prefer visible text
            content = getattr(item, "content", None)
            if isinstance(content, str):
                chunks.append(content)
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, str):
                        chunks.append(c)
                    elif isinstance(c, dict) and c.get("type") in ("text", "output_text"):
                        chunks.append(c.get("text", ""))
    return "\n".join(x for x in chunks if x).strip()

@debug_on_error
def main(argv: Optional[list[str]] = None) -> None:
    # parse arguments
    parser = argparse.ArgumentParser(description="Ask GPT-5 a question.")
    parser.add_argument("query", type=str, help="Your question for GPT-5")
    parser.add_argument("--effort", type=str, default=os.getenv("GPT5_EFFORT", "medium"), help="Reasoning effort: low, medium, high")
    parser.add_argument("--verbosity", type=str, default=os.getenv("GPT5_VERBOSITY", "low"), help="Verbosity: low, medium, high")
    args = parser.parse_args(argv)

    # get arguments
    query = args.query
    effort = args.effort
    verbosity = args.verbosity
    rich_print(f"[yellow]Query: {query}[/yellow]")
    rich_print(f"[yellow]Effort: {effort}[/yellow]")
    rich_print(f"[yellow]Verbosity: {verbosity}[/yellow]")

    # answer gpt5
    rich_print("[yellow]Answering GPT-5[/yellow]")
    answer_gpt5 = gpt5_answer(
        query,
        effort=effort,
        verbosity=verbosity,
    )
    rich_print(f"[green]Answer: {answer_gpt5}[/green]")
    rich_print("[green]Done[/green]")

    pdb.set_trace()

if __name__ == "__main__":
    main()
