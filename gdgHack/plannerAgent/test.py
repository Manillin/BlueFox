import json
import base64

payload_dict = {"message": "Test minimale inlineData per ADK /run_sse"}
json_string = json.dumps(payload_dict)
base64_bytes = base64.b64encode(json_string.encode('utf-8'))
base64_string = base64_bytes.decode('utf-8')

print(f"Stringa JSON originale: {json_string}")
print(f"Stringa codificata in Base64: {base64_string}")

curl - X POST http: // localhost: 8000/run_sse \
- H "Content-Type: application/json" \
- d '{
  "app_name": "plannerAgent",
  "user_id": "django_user_curl",
  "session_id": "planner_session_curl_minimal_test",
  "new_message": {
    "parts": [
      {
        "inlineData": {
          "mimeType": "application/json",
          "data": "eyJtZXNzYWdlIjogIlRlc3QgbWluaW1hbGUgaW5saW5lRGF0YSBwZXIgQURLIC9ydW5fc3NlIn0="
        }
      }
    ],
    "role": "user"
  },
  "streaming": false
}'



curl -X POST http://localhost:/users/curl_user/sessions/curl_session \
      -H "Content-Type: application/json" \
      -d '{}'