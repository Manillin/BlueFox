from google.adk.agents import Agent
from google.adk.tools import google_search


root_agent = Agent(
    model='gemini-2.0-flash',
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='''you are a very polite agent, greet the user and ask for his name, 
    if the user asks for specific things you can use google search feature, if you are unable to do so please tell the user''',
    tools=[google_search]
)
