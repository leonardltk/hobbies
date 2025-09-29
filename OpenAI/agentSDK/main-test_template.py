# gpt5_demo.py
import os
import sys
import pdb
import argparse
import traceback
import functools
from typing import Optional

from openai import OpenAI
from rich import print as rprint
from dotenv import find_dotenv, load_dotenv

from agents import Agent, Runner, function_tool
from agents import set_default_openai_key

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
    set_default_openai_key(os.getenv("OPENAI_API_KEY"))


@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny."


@debug_on_error
def main(argv: Optional[list[str]] = None) -> None:
    # answer gpt5
    rich_print("[yellow]Using Agent SDK[/yellow]")
    make_client()


    # v1
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant"
    )
    result = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
    print(result.final_output)


    # v2
    agent = Agent(
        name="WeatherAgent",
        instructions="You are good at giving the weather.",
        tools=[get_weather],
    )
    result = Runner.run_sync(agent, "What's the weather in Tokyo?")
    """
        RunResult(
            input="What's the weather in Tokyo?",
            new_items=[
                ToolCallItem(
                    agent=Agent(
                        name='WeatherAgent',
                        handoff_description=None,
                        tools=[
                            FunctionTool(
                                name='get_weather',
                                description='',
                                params_json_schema={'properties': {'city': {'title': 'City', 'type': 'string'}}, 'required': ['city'], 'title': 'get_weather_args', 'type': 'object', 'additionalProperties': False},
                                on_invoke_tool=<function function_tool.<locals>._create_function_tool.<locals>._on_invoke_tool at 0x7d67063efd80>,
                                strict_json_schema=True,
                                is_enabled=True
                            )
                        ],
                        mcp_servers=[],
                        mcp_config={},
                        instructions='You are good at giving the weather.',
                        prompt=None,
                        handoffs=[],
                        model=None,
                        model_settings=ModelSettings(
                            temperature=None,
                            top_p=None,
                            frequency_penalty=None,
                            presence_penalty=None,
                            tool_choice=None,
                            parallel_tool_calls=None,
                            truncation=None,
                            max_tokens=None,
                            reasoning=None,
                            verbosity=None,
                            metadata=None,
                            store=None,
                            include_usage=None,
                            response_include=None,
                            top_logprobs=None,
                            extra_query=None,
                            extra_body=None,
                            extra_headers=None,
                            extra_args=None
                        ),
                        input_guardrails=[],
                        output_guardrails=[],
                        output_type=None,
                        hooks=None,
                        tool_use_behavior='run_llm_again',
                        reset_tool_choice=True
                    ),
                    raw_item=ResponseFunctionToolCall(
                        arguments='{"city":"Tokyo"}',
                        call_id='call_MNyQiMkkpLOED5jgqaq13OdL',
                        name='get_weather',
                        type='function_call',
                        id='fc_68da9c959fc88193a2b336e069f5f97809b8871f49818978',
                        status='completed'
                    ),
                    type='tool_call_item'
                ),
                ToolCallOutputItem(
                    agent=Agent(),
                    raw_item={'call_id': 'call_MNyQiMkkpLOED5jgqaq13OdL', 'output': 'The weather in Tokyo is sunny.', 'type': 'function_call_output'},
                    output='The weather in Tokyo is sunny.',
                    type='tool_call_output_item'
                ),
                MessageOutputItem(
                    agent=Agent(),
                    raw_item=ResponseOutputMessage(
                        id='msg_68da9c96dc3c8193a18c99ef0de2864209b8871f49818978',
                        content=[
                            ResponseOutputText(annotations=[], text='The weather in Tokyo is currently sunny. If you need more details like temperature or forecast, let me know!', type='output_text', logprobs=[])
                        ],
                        role='assistant',
                        status='completed',
                        type='message'
                    ),
                    type='message_output_item'
                )
            ],
            raw_responses=[
                ModelResponse(
                    output=[
                        ResponseFunctionToolCall(
                            arguments='{"city":"Tokyo"}',
                            call_id='call_MNyQiMkkpLOED5jgqaq13OdL',
                            name='get_weather',
                            type='function_call',
                            id='fc_68da9c959fc88193a2b336e069f5f97809b8871f49818978',
                            status='completed'
                        )
                    ],
                    usage=Usage(
                        requests=1,
                        input_tokens=57,
                        input_tokens_details=InputTokensDetails(cached_tokens=0),
                        output_tokens=15,
                        output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
                        total_tokens=72
                    ),
                    response_id='resp_68da9c9409fc8193ac8b8716d34c317809b8871f49818978'
                ),
                ModelResponse(
                    output=[
                        ResponseOutputMessage(
                            id='msg_68da9c96dc3c8193a18c99ef0de2864209b8871f49818978',
                            content=[
                                ResponseOutputText(
                                    annotations=[],
                                    text='The weather in Tokyo is currently sunny. If you need more details like temperature or forecast, let me know!',
                                    type='output_text',
                                    logprobs=[]
                                )
                            ],
                            role='assistant',
                            status='completed',
                            type='message'
                        )
                    ],
                    usage=Usage(
                        requests=1,
                        input_tokens=87,
                        input_tokens_details=InputTokensDetails(cached_tokens=0),
                        output_tokens=24,
                        output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
                        total_tokens=111
                    ),
                    response_id='resp_68da9c9629e08193932fc7b33f27ea0c09b8871f49818978'
                )
            ],
            final_output='The weather in Tokyo is currently sunny. If you need more details like temperature or forecast, let me know!',
            input_guardrail_results=[],
            output_guardrail_results=[],
            context_wrapper=RunContextWrapper(
                context=None,
                usage=Usage(requests=2, input_tokens=144, input_tokens_details=InputTokensDetails(cached_tokens=0), output_tokens=39, output_tokens_details=OutputTokensDetails(reasoning_tokens=0), total_tokens=183)
            ),
            _last_agent=Agent(
                name='WeatherAgent',
                handoff_description=None,
                tools=[
                    FunctionTool(
                        name='get_weather',
                        description='',
                        params_json_schema={'properties': {'city': {'title': 'City', 'type': 'string'}}, 'required': ['city'], 'title': 'get_weather_args', 'type': 'object', 'additionalProperties': False},
                        on_invoke_tool=<function function_tool.<locals>._create_function_tool.<locals>._on_invoke_tool at 0x7d67063efd80>,
                        strict_json_schema=True,
                        is_enabled=True
                    )
                ],
                mcp_servers=[],
                mcp_config={},
                instructions='You are good at giving the weather.',
                prompt=None,
                handoffs=[],
                model=None,
                model_settings=ModelSettings(
                    temperature=None,
                    top_p=None,
                    frequency_penalty=None,
                    presence_penalty=None,
                    tool_choice=None,
                    parallel_tool_calls=None,
                    truncation=None,
                    max_tokens=None,
                    reasoning=None,
                    verbosity=None,
                    metadata=None,
                    store=None,
                    include_usage=None,
                    response_include=None,
                    top_logprobs=None,
                    extra_query=None,
                    extra_body=None,
                    extra_headers=None,
                    extra_args=None
                ),
                input_guardrails=[],
                output_guardrails=[],
                output_type=None,
                hooks=None,
                tool_use_behavior='run_llm_again',
                reset_tool_choice=True
            )
        )
    """
    print(result.final_output)


    # print
    rich_print("[green]Done[/green]")
    pdb.set_trace()

if __name__ == "__main__":
    main()
