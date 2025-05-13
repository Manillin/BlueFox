from google.adk.agents import Agent
import datetime


def get_current_time():
    now = datetime.datetime.now().strftime("%H:%M:%S")
    return now


root_agent = Agent(
    model='gemini-2.0-flash-001',
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge and ask the name of the user if not provided.',
    tools=[get_current_time],
)
