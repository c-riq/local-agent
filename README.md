# local-agent

Alphacodium style local agent, with support for local documentation fetching and active memory of mistakes.

We used https://github.com/mistralai/cookbook/blob/main/third_party/langchain/langgraph_code_assistant_mistral.ipynb as a starting point and enhanced the system by:
- enabling local LLMs
- local documentation fetching
- long term memory for avoiding past mistakes
- agent writing unit tests before writing the actual code and running the tests in the evaluation step
