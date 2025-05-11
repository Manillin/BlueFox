from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
# Utile per testare POST da altri servizi locali, ma valuta la sicurezza
from django.views.decorators.csrf import csrf_exempt
import base64
import json
import requests
from PyPDF2 import PdfReader  # Importa PdfReader
import uuid  # Aggiunto per generare session ID unici
import traceback  # Per logging eccezioni

# Variabili globali per ADK (o meglio, da settings.py in un progetto reale)
ADK_BASE_URL = 'http://localhost:8000'
ADK_RUBBER_DUCK_APP_NAME = 'rubberAgent'  # Specifico per Rubber Duck
ADK_PLANNER_APP_NAME = 'plannerAgent'  # Specifico per Planner
ADK_USER_ID = 'django_user'  # Può essere comune o specifico
# Sessione fissa per Rubber Duck
ADK_RUBBER_DUCK_SESSION_ID = 'django_session_rubber_duck'

# --- Funzioni Helper per ADK ---


def _ensure_rubber_duck_adk_session():
    """Assicura che la sessione ADK per Rubber Duck esista, creandola se necessario."""
    session_url = f"{ADK_BASE_URL}/apps/{ADK_RUBBER_DUCK_APP_NAME}/users/{ADK_USER_ID}/sessions/{ADK_RUBBER_DUCK_SESSION_ID}"
    try:
        response = requests.get(session_url, timeout=10)
        if response.status_code == 200:
            print(
                f"ADK Session '{ADK_RUBBER_DUCK_SESSION_ID}' for {ADK_RUBBER_DUCK_APP_NAME} found.")
            return True
        elif response.status_code == 404:
            print(
                f"ADK Session '{ADK_RUBBER_DUCK_SESSION_ID}' for {ADK_RUBBER_DUCK_APP_NAME} not found, creating...")
            create_response = requests.post(session_url, json={}, timeout=10)
            create_response.raise_for_status()
            print(
                f"ADK Session '{ADK_RUBBER_DUCK_SESSION_ID}' for {ADK_RUBBER_DUCK_APP_NAME} created.")
            return True
        else:
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(
            f"Error ensuring ADK session for {ADK_RUBBER_DUCK_APP_NAME}: {e}")
        return False


def _call_adk_run_for_rubber_duck(payload):
    """Chiama l'endpoint /run dell'ADK specificamente per Rubber Duck Agent."""
    run_url = f"{ADK_BASE_URL}/run"
    # Assicura che il payload usi le costanti corrette per Rubber Duck
    payload['app_name'] = ADK_RUBBER_DUCK_APP_NAME
    payload['user_id'] = ADK_USER_ID
    payload['session_id'] = ADK_RUBBER_DUCK_SESSION_ID
    print(
        f"Sending payload to ADK ({run_url}) for {ADK_RUBBER_DUCK_APP_NAME}:")
    print(json.dumps(payload, indent=2))
    response = requests.post(run_url, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def _call_adk_run_specific_agent(
    structured_input_data: dict,
    agent_app_name: str,
    user_id: str,
    session_id: str
):
    run_url = f"{ADK_BASE_URL}/run_sse"
    input_data_json_string = json.dumps(structured_input_data)

    # Codifica la stringa JSON in Base64
    base64_encoded_data = base64.b64encode(
        input_data_json_string.encode('utf-8')).decode('utf-8')

    run_payload_structure = {
        "app_name": agent_app_name,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "parts": [
                {
                    "inlineData": {
                        "mimeType": "application/json",
                        "data": base64_encoded_data  # Usa la stringa codificata in Base64
                    }
                }
            ],
            "role": "user"
        },
        "streaming": False
    }
    print(
        f"Sending payload to ADK ({run_url}) for agent {agent_app_name} (session: {session_id}):")
    print(json.dumps(run_payload_structure, indent=2))
    response = requests.post(run_url, json=run_payload_structure, timeout=240)
    response.raise_for_status()
    return response.json()

# Create your views here.


def main_braynr_view(request):
    return HttpResponse("Ciao! Questa è la pagina principale di Braynr. Da qui potrai accedere alle varie feature.")


def rubber_duck_view(request):
    return render(request, 'braynr_demo/rubber_duck_page.html')


@csrf_exempt
def process_pdf_view(request):
    if request.method == 'POST':
        if not _ensure_rubber_duck_adk_session():  # Specifica per Rubber Duck
            return JsonResponse({'success': False, 'error': 'Could not ensure ADK session for Rubber Duck.'}, status=503)

        pdf_file_content = None
        source_of_context = "No PDF provided"

        if 'pdf_file' in request.FILES:
            pdf_file = request.FILES['pdf_file']
            source_of_context = f"PDF: {pdf_file.name}"
            print(
                f"PDF file received: {pdf_file.name}, type: {pdf_file.content_type}, size: {pdf_file.size}")
            try:
                pdf_reader = PdfReader(pdf_file)
                text_from_pdf_pages = [
                    page.extract_text() or "" for page in pdf_reader.pages]
                text_from_pdf_raw = "\n".join(text_from_pdf_pages)

                # ***** INIZIO MODIFICA PER PULIZIA TESTO *****
                # Tenta di normalizzare e pulire il testo da caratteri problematici
                text_from_pdf_cleaned = text_from_pdf_raw.encode(
                    'ascii', 'ignore').decode('utf-8')

                text_from_pdf = text_from_pdf_cleaned  # Usa il testo pulito
                # ***** FINE MODIFICA PER PULIZIA TESTO *****

                if not text_from_pdf.strip():
                    return JsonResponse({'success': False, 'error': 'Il PDF è vuoto o non è stato possibile estrarre testo (dopo pulizia).'}, status=400)
                print(
                    f"Testo estratto e PULITO dal PDF (prime 300 chars): {text_from_pdf[:300]}...")
            except Exception as e:
                print(f"Errore durante la lettura o pulizia del PDF: {e}")
                return JsonResponse({'success': False, 'error': f'Errore durante la lettura o pulizia del PDF: {e}'}, status=500)

        if not pdf_file_content:
            return JsonResponse({'success': False, 'error': 'No PDF file processed or PDF is empty.'}, status=400)

        # Ora invia questo contenuto all'agente ADK chiedendogli di "assimilarlo"
        # e rispondere con una conferma.
        message_to_agent = (
            "[PLEASE RESPOND IN ENGLISH AND USE PLAIN TEXT ONLY. NO MARKDOWN.]\n"
            "The user has uploaded a document for study. Please acknowledge that you have received and processed this document. "
            "You can refer to it as 'the provided study material'.\n"
            f"Document content (source: {source_of_context}):\n--- START OF STUDY MATERIAL ---\n{pdf_file_content}\n--- END OF STUDY MATERIAL ---"
        )

        payload_for_adk = {  # Non servono app_name, user_id, session_id qui, li aggiunge _call_adk_run_for_rubber_duck
            "new_message": {"parts": [{"text": message_to_agent}], "role": "user"},
            "streaming": False
        }

        try:
            response_data = _call_adk_run_for_rubber_duck(payload_for_adk)
            print(f"ADK response after PDF processing:")
            print(json.dumps(response_data, indent=2))

            agent_confirmation = "Agent did not provide a clear confirmation."  # Default
            if response_data and isinstance(response_data, list) and response_data[0].get('content') and \
               response_data[0]['content'].get('parts') and response_data[0]['content']['parts'][0].get('text'):
                agent_confirmation = response_data[0]['content']['parts'][0]['text']

            # Salviamo il testo del PDF nella sessione Django per non doverlo riprocessare.
            # NOTA: Per PDF molto grandi, questo potrebbe non essere ideale. Per PoC va bene.
            request.session['pdf_context_text'] = pdf_file_content
            request.session['pdf_source_of_context'] = source_of_context

            return JsonResponse({'success': True, 'agent_ready_message': agent_confirmation})
        except requests.exceptions.HTTPError as e:
            # ... gestione errori come prima ...
            error_msg = f"HTTP Error during ADK communication (PDF processing): {e}"
            # (codice gestione errore omesso per brevità, ma è simile a quello che avevi)
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
        except Exception as e:
            print(f"Generic error in process_pdf_view: {e}")
            return JsonResponse({'success': False, 'error': f'Internal server error: {str(e)}'}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method for PDF processing.'}, status=405)


@csrf_exempt
def process_rubber_duck_audio(request):
    if request.method == 'POST':
        # Manteniamo _ensure_rubber_duck_adk_session per rubberAgent se usa sessioni fisse
        # if not _ensure_rubber_duck_adk_session():
        #     return JsonResponse({'success': False, 'error': 'Could not ensure ADK session.'}, status=503)

        transcription = request.POST.get('transcription', '')
        if not transcription:
            return JsonResponse({'success': False, 'error': 'No transcription received.'}, status=400)

        # Recupera il contesto del PDF dalla sessione Django (se presente)
        # Questo presuppone che process_pdf_view sia stato chiamato prima per questa sessione.
        pdf_context_text = request.session.get(
            'pdf_context_text', 'No prior PDF context found in session.')
        source_of_context = request.session.get(
            'pdf_source_of_context', 'Unknown source')

        print(
            f"Using PDF context from session (source: {source_of_context}, first 100 chars): {pdf_context_text[:100]}...")
        print(f"Transcription received: {transcription}")

        message_to_agent = (
            "[PLEASE RESPOND IN ENGLISH AND USE PLAIN TEXT ONLY. NO MARKDOWN.]\n"
            f"The user is now providing their explanation based on the previously submitted study material (source: {source_of_context}). "
            "Please evaluate their understanding.\n"
            f"User's explanation:\n--- START OF USER EXPLANATION ---\n{transcription}\n--- END OF USER EXPLANATION ---"
            # Non inviamo di nuovo il pdf_context_text qui, l'agente dovrebbe averlo in memoria dalla chiamata precedente
            # Tuttavia, per l'ADK che non ha una vera memoria LLM persistente tra chiamate /run discrete
            # (a meno di non implementare un salvataggio stato più complesso nell'agente stesso),
            # potrebbe essere necessario re-inviare il contesto principale. Per ora, testiamo se la sessione ADK lo tiene.
            # Se non funziona, dovremo aggiungere qui:
            # f"Recall the study material:\n{pdf_context_text}\n\n"
        )

        # Usiamo la funzione helper aggiornata o una specifica se necessario
        # Per rubberAgent che usa ADK_RUBBER_DUCK_APP_NAME fisso:
        payload_for_rubber_agent = {
            "new_message": {"parts": [{"text": message_to_agent}], "role": "user"},
            "streaming": False
        }
        try:
            # Qui potremmo usare _call_adk_run_for_rubber_duck originale se non l'abbiamo rimossa,
            # o adattare _call_adk_run_specific_agent
            response_data = _call_adk_run_for_rubber_duck(
                payload_for_rubber_agent)
            print(f"ADK response after user explanation:")
            print(json.dumps(response_data, indent=2))

            agent_feedback = "No text feedback received or unexpected response structure."  # Default
            if response_data and isinstance(response_data, list) and response_data[0].get('content') and \
               response_data[0]['content'].get('parts') and response_data[0]['content']['parts'][0].get('text'):
                agent_feedback = response_data[0]['content']['parts'][0]['text']

            return JsonResponse({'success': True, 'agent_response': agent_feedback})
        except requests.exceptions.HTTPError as e:
            # ... gestione errori come prima ...
            error_msg = f"HTTP Error during ADK communication (explanation processing): {e}"
            # (codice gestione errore omesso per brevità)
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
        except Exception as e:
            print(f"Generic error in process_rubber_duck_audio: {e}")
            return JsonResponse({'success': False, 'error': f'Internal server error: {str(e)}'}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method for audio processing.'}, status=405)


def simplify_view(request):
    return HttpResponse("Ciao! Feature: Simplify Problem.")


def scheduler_view(request):
    return HttpResponse("Ciao! Feature: Scheduler.")

# --- Nuove View per il Planner ---


def planner_page_view(request):
    """Mostra la pagina HTML per l'interfaccia del Planner."""
    return render(request, 'braynr_demo/planner_page.html')


@csrf_exempt
def generate_study_plan_view(request):
    if request.method == 'POST':
        try:
            pdf_file = request.FILES.get('pdf_file')
            study_duration_days_str = request.POST.get('study_duration_days')
            user_preferences = request.POST.get(
                'user_preferences', 'Nessuna preferenza specifica fornita.')

            if not pdf_file:
                return JsonResponse({'success': False, 'error': 'File PDF non fornito.'}, status=400)
            if not study_duration_days_str:
                return JsonResponse({'success': False, 'error': 'Durata dello studio non fornita.'}, status=400)

            try:
                study_duration_days = int(study_duration_days_str)
                if study_duration_days <= 0:
                    raise ValueError(
                        "La durata dello studio deve essere positiva.")
            except ValueError as e:
                return JsonResponse({'success': False, 'error': f'Durata dello studio non valida: {e}'}, status=400)

            text_from_pdf = ""  # Inizializza text_from_pdf qui
            source_of_context = "No PDF provided"  # Inizializza anche questo per coerenza

            # Estrazione del testo dal PDF (solo se pdf_file esiste)
            # Questa logica era già protetta dal check if not pdf_file, ma l'inizializzazione sopra è più sicura.
            try:
                source_of_context = f"PDF: {pdf_file.name}"
                print(
                    f"PDF file received: {pdf_file.name}, type: {pdf_file.content_type}, size: {pdf_file.size}")
                pdf_reader = PdfReader(pdf_file)
                text_from_pdf_pages = [
                    page.extract_text() or "" for page in pdf_reader.pages]
                text_from_pdf_raw = "\n".join(text_from_pdf_pages)
                text_from_pdf_cleaned = text_from_pdf_raw.encode(
                    'ascii', 'ignore').decode('utf-8')
                text_from_pdf = text_from_pdf_cleaned  # Assegnazione corretta
                if not text_from_pdf.strip():
                    # Anche se il PDF non è vuoto ma non si estrae testo, consideralo un errore qui o gestiscilo.
                    print(
                        "Attenzione: Il PDF è stato processato ma non è stato estratto alcun testo.")
                    # Potresti voler restituire un errore qui se il testo è cruciale e vuoto.
                    # return JsonResponse({'success': False, 'error': 'Il PDF è vuoto o non è stato possibile estrarre testo (dopo pulizia).'}, status=400)
                print(
                    f"Testo estratto e PULITO dal PDF (prime 300 chars): {text_from_pdf[:300]}...")
            except Exception as e:
                print(f"Errore durante la lettura o pulizia del PDF: {e}")
                return JsonResponse({'success': False, 'error': f'Errore durante la lettura o pulizia del PDF: {e}'}, status=500)

            # Controllo aggiuntivo: se dopo tutto text_from_pdf è ancora vuoto e un PDF era atteso/necessario.
            if not text_from_pdf.strip() and pdf_file:  # Se un file è stato fornito ma il testo è vuoto
                return JsonResponse({'success': False, 'error': 'Il PDF fornito risulta vuoto o il testo non è stato estratto correttamente.'}, status=400)

            # NOTA: La sezione "TEST 1" è stata rimossa nei passaggi precedenti.
            # Ora si usa direttamente il payload completo.
            adk_input_for_planner_agent = {
                "pdf_text_content": text_from_pdf,
                "study_duration_days": study_duration_days,
                "user_preferences": user_preferences
            }

            # Rimuovo il print fuorviante del "TEST 1"
            print(
                f"Dati strutturati pronti per ADK Planner Agent: {json.dumps(adk_input_for_planner_agent, indent=2)}")

            planner_user_id = ADK_USER_ID
            planner_session_id = "planner_session_" + uuid.uuid4().hex

            print(
                f"Inviando richiesta a ADK Planner Agent ({ADK_PLANNER_APP_NAME}) via /run_sse ...")

            response_data = _call_adk_run_specific_agent(
                adk_input_for_planner_agent,
                ADK_PLANNER_APP_NAME,
                planner_user_id,
                planner_session_id
            )

            # La logica di estrazione della roadmap probabilmente restituirà un default o un errore,
            # dato che l'agente (se riceve questo input) non produrrà una roadmap completa.
            final_roadmap = "Roadmap non generata (DEBUG MODE - Test 1 inlineData minimale)."
            if response_data and isinstance(response_data, list):
                # Tentativo grezzo di vedere se c'è una risposta testuale dall'agente
                for event_item in reversed(response_data):
                    if event_item.get("author"):  # Qualsiasi autore
                        content_parts = event_item.get(
                            "content", {}).get("parts", [{}])
                        if content_parts and content_parts[0].get("text"):
                            final_roadmap = f"Risposta testuale agente (Debug Test 1): {content_parts[0]['text']}"
                            break

            print(f"Risultato (DEBUG Test 1): {final_roadmap[:500]}...")
            return JsonResponse({'success': True, 'roadmap': final_roadmap, 'debug_info': 'Test 1 - inlineData minimale'})

        except requests.exceptions.HTTPError as e:
            error_body = e.response.text if e.response else str(e)
            print(
                f"HTTPError durante la chiamata ADK per il planner ({e.request.url}): {e.response.status_code} - {error_body}")
            return JsonResponse({'success': False, 'error': f'Errore comunicazione con Agente Planner (Test 1): {e.response.status_code} - {error_body}'}, status=500)
        except Exception as e:
            print(f"Errore generico in generate_study_plan_view (Test 1): {e}")
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': f'Errore interno del server (Test 1): {str(e)}'}, status=500)

    return JsonResponse({'success': False, 'error': 'Metodo non valido. Richiesto POST.'}, status=405)

# Definisci le altre funzioni view per le tue feature qui
