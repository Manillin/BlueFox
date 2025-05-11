import json
import base64
from PyPDF2 import PdfReader
# import uuid # Decommenta se vuoi usare uuid.uuid4().hex per session_id


def extract_text_from_pdf(pdf_path):
    text_from_pdf = ""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_from_pdf += page_text + "\n"

        # Pulizia simile a quella in Django (opzionale ma per coerenza)
        text_from_pdf_cleaned = text_from_pdf.encode(
            'ascii', 'ignore').decode('utf-8', 'ignore')
        return text_from_pdf_cleaned.strip()
    except Exception as e:
        print(f"Errore durante l'estrazione del testo dal PDF: {e}")
        return None


# --- CONFIGURA QUI I TUOI DATI ---
# <--- MODIFICA QUESTO!
pdf_file_path = "/Users/chris/Desktop/EsamiM/AlgoOpt/DetailedProgram.pdf"
study_duration_days = 7  # Modifica se necessario
user_preferences = "Preferisco studiare la mattina."  # Modifica se necessario
# --- FINE CONFIGURAZIONE ---

extracted_pdf_text = extract_text_from_pdf(pdf_file_path)

if extracted_pdf_text is None:
    print("Non è stato possibile estrarre il testo dal PDF. Interruzione.")
else:
    print(
        f"Testo estratto dal PDF (prime 300 chars): {extracted_pdf_text[:300]}...")
    print(
        f"Lunghezza totale del testo estratto: {len(extracted_pdf_text)} caratteri")

    # Dati strutturati come nella view Django
    structured_input_data = {
        "pdf_text_content": extracted_pdf_text,
        "study_duration_days": study_duration_days,
        "user_preferences": user_preferences
    }

    # Serializza in JSON e codifica in Base64 (come fa _call_adk_run_specific_agent)
    input_data_json_string = json.dumps(structured_input_data)
    base64_encoded_data = base64.b64encode(
        input_data_json_string.encode('utf-8')).decode('utf-8')

    print(
        f"\nDati codificati in Base64 (prime 100 chars): {base64_encoded_data[:100]}...")

    # Semplice session_id per lo script
    session_id_for_curl = "curl_pdf_test_session_001"
    # Se hai import uuid, puoi usare (dopo aver decommentato l'import sopra):
    # session_id_for_curl = "curl_pdf_test_session_" + uuid.uuid4().hex

    curl_payload = {
        "app_name": "plannerAgent",
        "user_id": "curl_pdf_test_user",
        "session_id": session_id_for_curl,  # Usa il session_id semplice
        "new_message": {
            "parts": [
                {
                    "inlineData": {
                        "mimeType": "application/json",
                        "data": base64_encoded_data
                    }
                }
            ],
            "role": "user"
        },
        "streaming": False  # Mantieni False per ora, come fa Django
    }

    # Salva il payload in un file
    output_filename = "run_sse_payload_full.json"
    with open(output_filename, 'w') as f_out:
        json.dump(curl_payload, f_out, indent=2)

    print(f"\nPayload completo salvato in: {output_filename}")
    print("Ora puoi eseguire il seguente comando curl:")
    print(
        f"curl -X POST -H \"Content-Type: application/json\" -d @{output_filename} http://localhost:8000/run_sse -v")
