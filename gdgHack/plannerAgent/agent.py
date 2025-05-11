from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.events import Event
from google.adk.agents.invocation_context import InvocationContext
from typing import AsyncGenerator
import json  # NECESSARIO per json.loads
import base64  # NECESSARIO per decodificare da Base64

# --- 1. Agente per Inizializzare lo Stato ---


class SetupPlannerStateAgent(BaseAgent):
    """
    Questo agente prende l'input iniziale (testo del PDF, durata)
    dalla chiamata /run_sse (strutturato in new_message.parts[0].inlineData.data, che è base64 encodato)
    e lo salva in session.state.
    """

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        input_payload = {}
        raw_base64_data = ""  # Per logging in caso di errore di decodifica base64
        json_string_data = ""  # Per logging in caso di errore di parsing JSON
        try:
            if ctx.data and hasattr(ctx.data, 'parts') and ctx.data.parts:
                part = ctx.data.parts[0]
                if hasattr(part, 'inline_data') and part.inline_data and \
                   hasattr(part.inline_data, 'data') and \
                   hasattr(part.inline_data, 'mime_type') and \
                   part.inline_data.mime_type == 'application/json':

                    raw_base64_data = part.inline_data.data
                    print(
                        f"SetupPlannerStateAgent: Received raw inlineData (expected base64): {raw_base64_data[:100]}...")

                    # Fase 1: Decodifica da Base64
                    json_string_data = base64.b64decode(
                        raw_base64_data).decode('utf-8')
                    print(
                        f"SetupPlannerStateAgent: Decoded base64 to JSON string: {json_string_data[:300]}...")

                    # Fase 2: Parsing del JSON
                    input_payload = json.loads(json_string_data)
                    print(
                        "SetupPlannerStateAgent: Successfully parsed decoded inlineData JSON string.")

                # Fallback se per errore arrivasse solo testo
                elif hasattr(part, 'text') and part.text:
                    print(
                        f"SetupPlannerStateAgent WARN: Received simple text in new_message part: {part.text[:300]}... (Previsto inlineData base64 per il planner)")
                    # Qui potresti anche tentare json.loads(part.text) se ti aspetti che il testo sia JSON diretto
                else:
                    print(
                        "SetupPlannerStateAgent ERRORE: new_message.parts[0] non contiene inlineData.data JSON (base64) con mimeType corretto, o text.")
            else:
                print(
                    "SetupPlannerStateAgent ERRORE: ctx.data non ha la struttura attesa (mancano parts o ctx.data è None).")

        except (base64.binascii.Error, UnicodeDecodeError) as b64_err:
            print(
                f"SetupPlannerStateAgent ERRORE: Fallimento nel decodificare base64 da inlineData.data: {b64_err}")
            print(
                f"Stringa base64 che ha causato l'errore (prime 100 chars): {raw_base64_data[:100]}")
        except json.JSONDecodeError as json_err:
            print(
                f"SetupPlannerStateAgent ERRORE: Fallimento nel parsing della stringa JSON (dopo decode base64): {json_err}")
            print(
                f"Stringa JSON (dopo decode base64) che ha causato l'errore: {json_string_data}")
        except Exception as e:
            print(
                f"SetupPlannerStateAgent ERRORE: Eccezione imprevista durante l'estrazione dei dati da ctx.data: {e}")

        # Estrai i dati dal payload ora deserializzato (o vuoto in caso di errore)
        pdf_text = input_payload.get('pdf_text_content', '')
        duration_days_raw = input_payload.get('study_duration_days', 0)
        duration_days = 0  # Default in caso di errore
        try:
            duration_days = int(duration_days_raw)
        except (ValueError, TypeError):
            print(
                f"SetupPlannerStateAgent ERRORE: study_duration_days ('{duration_days_raw}') non è un intero valido in input_payload. Uso 0.")

        user_preferences = input_payload.get(
            'user_preferences', 'Nessuna preferenza specifica fornita.')

        # Logica di validazione e salvataggio in session.state
        if not pdf_text or duration_days <= 0:
            print(
                f"SetupPlannerStateAgent ERRORE: Testo PDF (len: {len(pdf_text)}) o durata ({duration_days}) non validi. Lo stato potrebbe non essere completamente inizializzato.")
            # Salviamo comunque ciò che abbiamo, o valori vuoti/default
            ctx.session.state['pdf_text_content'] = pdf_text if pdf_text else ""
            ctx.session.state['study_duration_days'] = duration_days if duration_days > 0 else 0
        else:
            ctx.session.state['pdf_text_content'] = pdf_text
            ctx.session.state['study_duration_days'] = duration_days

        ctx.session.state['user_preferences'] = user_preferences

        print(
            f"SetupPlannerStateAgent: State Initialized: PDF length {len(ctx.session.state.get('pdf_text_content', ''))}, Duration {ctx.session.state.get('study_duration_days', 0)} days.")

        yield Event(author=self.name)  # Omesso 'data'


# --- 2. ContentAnalyzerAgent ---
content_analyzer_agent = LlmAgent(
    name="ContentAnalyzerAgent",
    model="gemini-1.5-flash-latest",
    instruction=(
        "You are an expert in analyzing study materials. "
        "Read the provided text from 'session.state.pdf_text_content'. "
        "Identify the main topics and key sub-topics. "
        "Also consider any 'session.state.user_preferences' if relevant for topic breakdown (e.g., focus areas). "
        "Output a structured list of these topics and sub-topics. "
        "The output MUST be a valid JSON string representing a list of dictionaries, where each dictionary has 'topic' and 'subtopics' keys. "
        "For example: [{'topic': 'Main Topic 1', 'subtopics': ['Subtopic 1.1', 'Subtopic 1.2']}, ...]. "
        "Focus on creating a breakdown suitable for a study plan of 'session.state.study_duration_days' days."
    ),
    output_key="analyzed_content_json_string"
)

# --- 3. TimeEstimatorAgent ---
time_estimator_agent = LlmAgent(
    name="TimeEstimatorAgent",
    model="gemini-1.5-flash-latest",
    instruction=(
        "You are a study planning assistant. "
        "You will receive a JSON string list of topics and sub-topics from 'session.state.analyzed_content_json_string', "
        "a total study duration in days from 'session.state.study_duration_days', "
        "and user preferences from 'session.state.user_preferences'. "
        "FIRST, parse the 'session.state.analyzed_content_json_string' into a list of topics. "
        "THEN, estimate a reasonable amount of study time (e.g., in hours or specific sessions) for each main topic and its sub-topics. "
        "Distribute the estimated time across the 'session.state.study_duration_days'. "
        "Consider 'session.state.user_preferences' for time allocation. "
        "Output a detailed study schedule as a valid JSON string. "
        "The JSON should be a list of dictionaries, each representing a day, with 'day_number', 'topics_covered' (list of strings), and 'estimated_time_details' (string). "
        "Example: [{'day_number': 1, 'topics_covered': ['Topic 1.1', 'Topic 1.2'], 'estimated_time_details': '2-3 hours, focus on core concepts'}, ...]."
    ),
    output_key="estimated_schedule_json_string"
)

# --- 4. RoadmapFormatterAgent ---
roadmap_formatter_agent = LlmAgent(
    name="RoadmapFormatterAgent",
    model="gemini-1.5-flash-latest",
    instruction=(
        "You are a friendly and encouraging study plan presenter. "
        "You will receive a detailed study schedule as a JSON string from 'session.state.estimated_schedule_json_string'. "
        "FIRST, parse this JSON string. "
        "THEN, format this schedule into a clear, human-readable, and motivating study plan. "
        "Use markdown for structuring the output (e.g., headings for days, bullet points for topics). "
        "Start with a brief encouraging message. End with a motivational closing. "
        "Refer to 'session.state.user_preferences' to make the tone more personal if applicable. "
        "The final output should be a single block of markdown text."
    ),
    output_key="final_study_roadmap"
)

# --- Sequenza degli Agenti ---
root_agent = SequentialAgent(
    name="PlannerSequentialWorkflow",
    agents=[
        SetupPlannerStateAgent(name="InputSetupAgent"),
        content_analyzer_agent,
        time_estimator_agent,
        roadmap_formatter_agent
    ]
)
