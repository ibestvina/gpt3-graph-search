# GPT Graph Search

This repository generates random graphs and generates prompts that ask GPT-3 to find paths through the graph. GPT-3's
response is parsed and we try to automatically determine if the response is correct, or if not, why.

You should expose an environment variable `OPENAI_API_KEY=-<key>` before you run this code.

```bash
python3 -m pip install -r requirements.txt
python3 src/main.py
```


# Changes in this fork

1. Model changed from text-davinci-002 to code-davinci-002 (codex)
2. Instead of using an explanation of how tasks work, 3 examples are given (few-shot prompting): two with paths, and one to show what to output when there is no path present
3. Changed the output so that it has to specify edges, instead of nodes, it is traversing. This helps GPT to avoid using nonexistent edges.
