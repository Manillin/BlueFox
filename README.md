# Project Title: AI-Powered Study Assistant

This project utilizes Django to create a simple web application that interacts with Google's Agent Development Kit (ADK). It leverages Gemini models through various AI agents to assist users in their studies.

## Core Technologies

*   **Django:** A high-level Python web framework used for the web application backend.
*   **Google ADK:** The Agent Development Kit is used to build and manage AI agents.
*   **Gemini:** Google's multimodal AI model powers the intelligence of the agents.

## Features

The web application provides an interface to interact with specialized AI agents designed to help with different aspects of studying:

1.  **Rubber Duck Debugger Agent**
2.  **Study Planner Agent**

## Agents in Detail

### 1. Rubber Duck Debugger Agent

*   **Purpose:** The Rubber Duck agent, named "RubberDuck" acts as a virtual listener. It helps users think through problems (especially programming or logical ones) by encouraging them to articulate their thoughts. The agent doesn't provide direct solutions but guides the user to discover solutions themselves.
*   **Implementation:**
    *   The agent is implemented using the Google ADK (`Agent` class).
    *   It is configured with specific instructions to listen carefully, ask open-ended questions, avoid direct problem-solving, maintain patience, and rephrase user statements if helpful.
    *   It can use Google Search for simple factual lookups if the user is stuck on a definition or syntax, but not for solving the core logical problem.
    *   The agent is designed to respond in the language the user uses.
*   **Input:** The primary input is the user's textual explanation of the problem they are facing or the topic they want to think through out loud. The interaction is conversational.


### 2. Study Planner Agent

*   **Purpose:** The Study Planner Agent assists users in creating a structured study plan based on provided material (e.g., a PDF document) and a desired study duration.
*   **Implementation:** This agent is a sequential workflow composed of four sub-agents:
    1.  `SetupPlannerStateAgent`:
        *   This agent initializes the process.
        *   It receives the initial input (PDF text, study duration, user preferences) from the web application. This data is typically passed as a Base64 encoded JSON string within the `/run_sse` request payload.
        *   It decodes and parses this input, saving the PDF text content, study duration in days, and user preferences into the session state for subsequent agents.
    2.  `ContentAnalyzerAgent`:
        *   Takes the PDF text and user preferences from the session state.
        *   Analyzes the material to identify main topics and key sub-topics suitable for the given study duration.
        *   Outputs a structured JSON list of these topics and sub-topics.
    3.  `TimeEstimatorAgent`:
        *   Receives the JSON list of topics, the total study duration, and user preferences.
        *   Estimates a reasonable amount of study time for each topic and sub-topic.
        *   Distributes the estimated time across the specified number of study days.
        *   Outputs a detailed study schedule as a JSON string, listing tasks and estimated times per day.
    4.  `RoadmapFormatterAgent`:
        *   Takes the JSON study schedule.
        *   Formats it into a clear, human-readable, and motivating study plan using Markdown.
        *   Includes an encouraging opening and a motivational closing, potentially personalized based on user preferences.
*   **Input:** The primary input for the Study Planner Agent is a JSON object, usually sent from the web application to the ADK server. This JSON object should contain:
    *   `pdf_text_content` (String): The full text content extracted from the study material (e.g., a PDF).
    *   `study_duration_days` (Integer): The total number of days the user wants the study plan to cover.
    *   `user_preferences` (String, Optional): Any specific preferences the user has for the study plan (e.g., "focus more on practical examples," "prefer shorter study sessions").

    *Example JSON Input (as part of the ADK `/run_sse` call,  Base64 encoded):*
    ```json
    {
      "pdf_text_content": "The complete text from the PDF document about calculus...",
      "study_duration_days": 14,
      "user_preferences": "I prefer to study in the mornings and want a review session every 3 days."
    }
    ```

## Web Application Usage

1.  **Access the Web App:** Open the Django web application in your browser.
2.  **Select an Agent:** The interface should allow you to choose between the "Rubber Duck Debugger" and the "Study Planner Agent."
3.  **Interact with Rubber Duck:**
    *   If you select the Rubber Duck Debugger, a chat interface will likely appear.
    *   Start typing your problem or the thoughts you want to process.
    *   The agent will respond by asking questions to help you elaborate.
4.  **Use the Study Planner:**
    *   If you select the Study Planner Agent, you will likely need to provide:
        *   The text content of your study material (e.g., by uploading a PDF which the backend processes, or pasting text).
        *   The number of days you want the study plan to span.
        *   Optionally, any specific preferences for your study plan.
    *   Submit the information. The agent will process it and return a formatted study plan.

## ADK Server Setup (Conceptual Guide)

Setting up the Google ADK server involves running the ADK application that hosts your defined agents. The specifics can vary based on your project structure, but here's a general outline:

1.  **Prerequisites:**
    *   Python installed.
    *   Google Cloud SDK initialized and configured with a project that has the Vertex AI API enabled.
    *   Authentication set up (e.g., via `gcloud auth application-default login`).
    *   `google-cloud-aiplatform` and `google-adk` Python libraries installed. Your `Pipfile` suggests you are using `pipenv`.

2.  **Navigate to ADK Agent Directory:**
    Open your terminal and navigate to the directory containing your ADK agent definitions (e.g., `adk_agents/` or `BlueFox/agents/` depending on which set of agents you intend to run).

3.  **Set Environment Variables (if necessary):**
    You might need to set environment variables, such as `GOOGLE_CLOUD_PROJECT` if not already configured.

4.  **Run the ADK Server:**
    The command to run the ADK server typically uses `google-adk serve`. You'll need to point it to the directory containing your agent's Python module(s).

    *   **If your agents are structured with an `agent.py` file that defines a `root_agent`:**
        ```bash
        cd path/to/your/agent_directory # e.g., cd adk_agents/rubber_duck_agent
        google-adk serve .
        ```
        Or, if running from a parent directory:
        ```bash
        google-adk serve path.to.your.agent_module
        # Example: If your rubber_duck_agent is in adk_agents/rubber_duck_agent/agent.py
        # and you are in the project root:
        # google-adk serve adk_agents.rubber_duck_agent
        ```

    *   **For the Planner Agent (which seems to be in `BlueFox/agents/plannerAgent/`):**
        Assuming your project root is `BlueFox/` or its parent, and `BlueFox` is in your `PYTHONPATH` or you `cd` into `BlueFox`:
        ```bash
        # Assuming BlueFox is the root for this context
        cd BlueFox
        google-adk serve agents.plannerAgent
        # or from the absolute project root:
        # google-adk serve BlueFox.agents.plannerAgent
        ```
        The exact module path will depend on your `PYTHONPATH` and how Python resolves imports from your current working directory.

5.  **Specify Host and Port (Optional):**
    You can specify the host and port:
    ```bash
    google-adk serve . --host 0.0.0.0 --port 8080
    ```

6.  **Accessing the Server:**
    Once running, the ADK server will typically be available at `http://localhost:8000` (or the port you specified). The Django application will then make requests to this ADK server (e.g., to `http://localhost:8000/run_sse`).

**Note:** Ensure your Django application's settings are configured to point to the correct ADK server address and port. The `run_sse_payload.json` file in your `BlueFox` directory seems to be an example of the payload structure sent to the ADK server's `/run_sse` endpoint.

This README provides a general overview. You may need to adjust file paths and commands based on your exact project setup and how you manage your Python environments. 