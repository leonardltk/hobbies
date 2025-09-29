# GPT-5 usage
- https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide
- https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools
    - https://github.com/openai/openai-cookbook/blob/main/examples/gpt-5/gpt-5_new_params_and_tools.ipynb


# set up
```bash
uv init
uv add rich dotenv jupyterlab
uv add openai pandas

uv add xxx
uv add xxx
uv add xxx
uv add xxx
```

# Sample
```bash
uv run main.py \
    "Tell me what is Le Sserafim doing today." \
    --effort minimal \
    --verbosity low
```

# Parameters
## verbosity
https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools#1-verbosity-parameter
```bash
uv run new_param-verbosity.py
```
| Verbosity | Reasoning Tokens | Non-Reasoning Tokens | Total Tokens |
|-----------|------------------|----------------------|--------------|
| low       | 1088             | 546                  | 1634         |
| medium    | 1408             | 853                  | 2261         |
| high      | 1664             | 1167                 | 2831         |

## freeform-function-calling
https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools#2-freeform-function-calling
```bash
uv run new_param-freeform_function_calling.py
```
