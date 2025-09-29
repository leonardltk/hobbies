import os
import sys
import pdb
import argparse
import traceback
import functools
import subprocess
from typing import List, Optional

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

@debug_on_error
def main() -> None:
    client = make_client()

    rich_print("[green]Use freeform function calling.[/green]")
    
    response = client.responses.create(
        model="gpt-5-mini",
        input="Please use the code_exec tool to calculate the area of a circle with radius equal to the number of 'r's in strawberry",
        text={"format": {"type": "text"}},
        tools=[
            {
                "type": "custom",
                "name": "code_exec",
                "description": "Executes arbitrary python code",
            }
        ]
    )
    rich_print(response)
    """
        Response(
            id='resp_68c287b7bd688192916bfe7ca8a113bf040ad332fd793f3e',
            created_at=1757579191.0,
            error=None,
            incomplete_details=None,
            instructions=None,
            metadata={},
            model='gpt-5-mini-2025-08-07',
            object='response',
            output=[
                ResponseReasoningItem(
                    id='rs_68c287b82f448192bb8f5a21fa17ceed040ad332fd793f3e',
                    summary=[],
                    type='reasoning',
                    content=None,
                    encrypted_content=None,
                    status=None
                ),
                ResponseCustomToolCall(
                    call_id='call_OXPHq2QgimxInA3Vpime53uz',
                    input='# Python code to count \'r\'s in the word "strawberry" and compute area of a circle with that radius\nimport math\n\nword =
        "strawberry"\nradius = word.count(\'r\')\narea = math.pi * (radius ** 2)\n\n# Print results in a clear format\nprint(f"word: {word}")\nprint(f"radius
        (number of \'r\'s): {radius}")\nprint(f"area = pi * radius^2 = {area}")',
                    name='code_exec',
                    type='custom_tool_call',
                    id='ctc_68c287bca1cc8192b85da410d2835832040ad332fd793f3e',
                    status='completed'
                )
            ],
            parallel_tool_calls=True,
            temperature=1.0,
            tool_choice='auto',
            tools=[CustomTool(name='code_exec', type='custom', description='Executes arbitrary python code', format=Text(type='text'))],
            top_p=1.0,
            background=False,
            conversation=None,
            max_output_tokens=None,
            max_tool_calls=None,
            previous_response_id=None,
            prompt=None,
            prompt_cache_key=None,
            reasoning=Reasoning(effort='medium', generate_summary=None, summary=None),
            safety_identifier=None,
            service_tier='default',
            status='completed',
            text=ResponseTextConfig(format=ResponseFormatText(type='text'), verbosity='medium'),
            top_logprobs=0,
            truncation='disabled',
            usage=ResponseUsage(
                input_tokens=63,
                input_tokens_details=InputTokensDetails(cached_tokens=0),
                output_tokens=369,
                output_tokens_details=OutputTokensDetails(reasoning_tokens=256),
                total_tokens=432
            ),
            user=None,
            store=True
        )
    """
    rich_print(response.output)
    """
        [
            ResponseReasoningItem(
                id='rs_68c287b82f448192bb8f5a21fa17ceed040ad332fd793f3e',
                summary=[],
                type='reasoning',
                content=None,
                encrypted_content=None,
                status=None
            ),
            ResponseCustomToolCall(
                call_id='call_OXPHq2QgimxInA3Vpime53uz',
                input='# Python code to count \'r\'s in the word "strawberry" and compute area of a circle with that radius\nimport math\n\nword =
        "strawberry"\nradius = word.count(\'r\')\narea = math.pi * (radius ** 2)\n\n# Print results in a clear format\nprint(f"word: {word}")\nprint(f"radius
        (number of \'r\'s): {radius}")\nprint(f"area = pi * radius^2 = {area}")',
                name='code_exec',
                type='custom_tool_call',
                id='ctc_68c287bca1cc8192b85da410d2835832040ad332fd793f3e',
                status='completed'
            )
        ]
    """
    
    python_file = "./tmp/freeform_function_calling.py"
    with open(python_file, "w") as f_w:
        f_w.write(response.output[1].input)
    subprocess.run(["python", python_file])
    """
        word: strawberry
        radius (number of 'r's): 3
        area = pi * radius^2 = 28.274333882308138
        CompletedProcess(args=['python', 'freeform_function_calling.py'], returncode=0)
    """


if __name__ == "__main__":
    main()
