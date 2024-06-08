
import os
import uuid

from langchain.globals import set_debug
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from typing import Annotated
from typing import TypedDict
from langgraph.graph.message import AnyMessage, add_messages

from mistake_memory import MistakeMemory

os.environ['TOKENIZERS_PARALLELISM'] = 'true'

set_debug(True)

llm = OllamaFunctions(model="codellama", format="json", temperature=0)
mistakeMemory = MistakeMemory()

combined_prompt = PromptTemplate.from_template((
            """You are a coding assistant. Ensure any code or test you provide can be executed with all required imports and variables \n
            defined. Structure your answer: 1) a prefix describing the code solution, 2) the imports, 3) the tests to check corectness of your solution and invocation of these tests, 4) the functioning code block.
            Adhere to these pieces of advice based on commonly occuring errors: {advice}
            Human: {question}
            AI: """))

# Data model
class test_code(BaseModel):
    """Code output"""

    prefix: str = Field(description="Description of the problem and approach")
    imports: str = Field(description="Code block import statements")
    code: str = Field(description="Code block not including import statements")
    tests: str = Field(description="Test code block not including import statements")
    description = "Schema for code solutions to questions about LCEL."

structured_llm = llm.with_structured_output(test_code)
code_gen_chain = combined_prompt | structured_llm

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        error : Binary flag for control flow to indicate whether test error was tripped
        messages : With user question, error messages, reasoning
        generation : Code solution
        iterations : Number of tries
    """

    error: str
    messages: Annotated[list[AnyMessage], add_messages]
    generation: str
    iterations: int


### Parameters
max_iterations = 3

### Nodes
def generate(state: GraphState):
    """
    Generate a code solution

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation
    """

    print("---GENERATING CODE SOLUTION---")

    # State
    messages = state["messages"]
    iterations = state["iterations"]
    state["error"]

    # Solution
    code_solution = code_gen_chain.invoke({"question": question, "advice": mistakeMemory.get_top_n_advice(3)})

    messages += [
        (
            "assistant",
            f"Here is my attempt to solve the problem: {code_solution.prefix} \n Imports: {code_solution.imports} \n Test: {code_solution.tests} \n Code: {code_solution.code}",
        )
    ]

    # Increment
    iterations = iterations + 1
    return {"generation": code_solution, "messages": messages, "iterations": iterations}

def code_check(state: GraphState):
    """
    Check code

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, error
    """

    print("---CHECKING CODE---")

    # State
    messages = state["messages"]
    code_solution = state["generation"]
    iterations = state["iterations"]

    # Get solution components
    imports = code_solution.imports
    tests = code_solution.tests
    code = code_solution.code

    # Check imports
    try:
        exec(imports)
    except Exception as e:
        print("---CODE IMPORT CHECK: FAILED---")
        error_message = [("user", f"Your solution failed the import test. Here is the error: {e}. Reflect on this error and your prior attempt to solve the problem. (1) State what you think went wrong with the prior solution and (2) try to solve this problem again. Return the FULL SOLUTION. Use the code tool to structure the output with a prefix, imports, test and code block:")]
        messages += error_message
        return {
            "generation": code_solution,
            "messages": messages,
            "iterations": iterations,
            "error": "yes",
        }

    # Check execution
    try:
        combined_code = f"{imports}\n{code}\n{tests}"
        # Use a shared scope for exec
        global_scope = {}
        exec(combined_code, global_scope)
    except Exception as e:
        print("---CODE BLOCK CHECK: FAILED---")
        mistakeMemory.remember_mistake(e)
        error_message = [("user", f"Your solution failed the code execution test or unit test: {e}) Reflect on this error and your prior attempt to solve the problem. (1) State what you think went wrong with the prior solution and (2) try to solve this problem again. Return the FULL SOLUTION. Use the code tool to structure the output with a prefix, imports, test and code block:")]
        messages += error_message
        return {
            "generation": code_solution,
            "messages": messages,
            "iterations": iterations,
            "error": "yes",
        }

    # No errors
    print("---NO CODE TEST FAILURES---")
    return {
        "generation": code_solution,
        "messages": messages,
        "iterations": iterations,
        "error": "no",
    }

### Conditional edges

def decide_to_finish(state: GraphState):
    """
    Determines whether to finish.

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """
    error = state["error"]
    iterations = state["iterations"]

    if error == "no" or iterations == max_iterations:
        print("---DECISION: FINISH---")
        return "end"
    else:
        print("---DECISION: RE-TRY SOLUTION---")
        return "generate"

### Utilities
def _print_event(event: dict, _printed: set, max_length=1500):
    current_state = event.get("dialog_state")
    if current_state:
        print("Currently in: ", current_state[-1])
    message = event.get("messages")
    if message:
        if isinstance(message, list):
            message = message[-1]
        if message.id not in _printed:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... (truncated)"
            print(msg_repr)
            _printed.add(message.id)

builder = StateGraph(GraphState)

# Define the nodes
builder.add_node("generate", generate)  # generation solution
builder.add_node("check_code", code_check)  # check code

# Build graph
builder.set_entry_point("generate")
builder.add_edge("generate", "check_code")
builder.add_conditional_edges(
    "check_code",
    decide_to_finish,
    {
        "end": END,
        "generate": "generate",
    },
)

stateMemory = SqliteSaver.from_conn_string(":memory:")
graph = builder.compile(checkpointer=stateMemory)

# Util functions
def run_graph(question):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    _printed = set()
    events = graph.stream({"messages": [("user", question)], "iterations": 0}, config, stream_mode="values")
    for event in events:
        _print_event(event, _printed)
    return event['generation']

_printed = set()
thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        # Checkpoints are accessed by thread_id
        "thread_id": thread_id,
    }
}

if __name__ == "__main__":
    question = "Write a Python program that prints 'Hello, World!' to the console."
    events = graph.stream(
        {"messages": [("user", question)], "iterations": 0}, config, stream_mode="values"
    )
    for event in events:
        _print_event(event, _printed)
