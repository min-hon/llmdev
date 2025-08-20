import sys
import os
import uuid
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import Annotated
from typing_extensions import TypedDict
from flask import Flask, render_template, request, make_response, session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
app.secret_key = 'your_secret_key'

load_dotenv(".env")
os.environ['OPENAI_API_KEY'] = os.environ['API_KEY']

MODEL_NAME = "gpt-4o-mini" 
memory = MemorySaver()
graph = None

class State(TypedDict):
    messages: Annotated[list, add_messages]

def build_graph(model_name, memory):
    graph_builder = StateGraph(State)
    llm = ChatOpenAI(model=model_name)

    tool = TavilySearchResults(max_results=2)
    tools = [tool]
    llm_with_tools = llm.bind_tools(tools)
    
    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}
    
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools))
    graph_builder.add_conditional_edges("chatbot", tools_condition,)
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.set_entry_point("chatbot")
    
    return graph_builder.compile(checkpointer=memory)

def stream_graph_updates(graph: StateGraph, user_message: str, thread_id):
    role = "あなたは犬です。犬らしく答えてください。"

    graph.invoke(
        {"messages": [("system", role), ("user", user_message)]},
        {"configurable": {"thread_id": thread_id}},
        stream_mode="values"
    )

def get_bot_response(user_message, memory, thread_id):
    global graph
    if graph is None:
        graph = build_graph(MODEL_NAME, memory)

    return stream_graph_updates(graph, user_message, thread_id)

def get_messages_list(memory, thread_id):
    messages = []
    memories = memory.get({"configurable": {"thread_id": thread_id}})['channel_values']['messages']
    for message in memories:
        if isinstance(message, HumanMessage):
            messages.append({'class': 'user-message', 'text': message.content.replace('\n', '<br>')})
        elif isinstance(message, AIMessage) and message.content != "":
            messages.append({'class': 'bot-message', 'text': message.content.replace('\n', '<br>')})
    return messages

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'thread_id' not in session:
        session['thread_id'] = str(uuid.uuid4())
    
    def default_view():
        memory.storage.clear()
        return make_response(render_template('index.html', messages=[]))

    if request.method == 'GET':
        return default_view()
    elif request.form.get('_action') == 'RESET':
        session.pop('thread_id', None)
        return default_view()

    user_message = request.form['user_message']
    
    get_bot_response(user_message, memory, session['thread_id'])

    messages = get_messages_list(memory, session['thread_id'])

    return make_response(render_template('index.html', messages=messages))

if __name__ == '__main__':
    app.run(debug=True)