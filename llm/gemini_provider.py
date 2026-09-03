import config
from .base import BaseLLMProvider

class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini API Provider adapter."""

    def __init__(self, api_key: str = None, model_name: str = config.GEMINI_MODEL):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_name = model_name
        self._client = None

        if not self.api_key:
            print("[Warning] GEMINI_API_KEY not set. Gemini generations will require an API key.")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai = genai
            except Exception as e:
                print(f"[Error] Failed to initialize Gemini client: {e}")

    @property
    def provider_name(self) -> str:
        return "Google Gemini API"

    def generate_answer(self, system_prompt: str, user_prompt: str, api_key: str = None, images: list = None) -> str:
        active_key_raw = api_key or self.api_key
        if not active_key_raw:
            return "[Error: GEMINI_API_KEY missing. Please set your key in the Web UI sidebar or .env file.]"

        # Support comma-separated API keys for rotation/failover (e.g. key1,key2,key3)
        keys = [k.strip() for k in active_key_raw.split(",") if k.strip()]
        
        import google.generativeai as genai
        import base64
        import io
        from PIL import Image

        last_error = None

        for active_key in keys:
            try:
                genai.configure(api_key=active_key)
                
                # Prepare contents payload (text prompt + images)
                contents = [user_prompt]
                if images:
                    for img_item in images:
                        try:
                            if isinstance(img_item, str):
                                b64_data = img_item.split(",")[-1]
                                img_bytes = base64.b64decode(b64_data)
                                pil_img = Image.open(io.BytesIO(img_bytes))
                                contents.append(pil_img)
                            elif isinstance(img_item, dict) and "data" in img_item:
                                b64_data = img_item["data"].split(",")[-1]
                                img_bytes = base64.b64decode(b64_data)
                                pil_img = Image.open(io.BytesIO(img_bytes))
                                contents.append(pil_img)
                        except Exception as img_err:
                            print(f"[Warning] Failed to decode image attachment: {img_err}")

                # List of active Gemini model candidates (prioritize highly available Flash tiers, avoid Pro preview limit:0)
                raw_candidates = [self.model_name, "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.6-flash", "gemini-3.7-flash"]
                candidates = []
                for c in raw_candidates:
                    if c and c not in candidates:
                        candidates.append(c)
                
                for model_candidate in candidates:
                    clean_name = model_candidate.replace("models/", "")
                    try:
                        model = genai.GenerativeModel(
                            model_name=clean_name,
                            system_instruction=system_prompt
                        )
                        response = model.generate_content(contents, request_options={"timeout": 20.0})
                        if response and hasattr(response, "text") and response.text:
                            return response.text
                    except Exception as model_err:
                        err_str = str(model_err)
                        print(f"[Gemini Warning] Model {clean_name} with key ...{active_key[-6:]} failed: {err_str}")
                        last_error = err_str
                        # Try next model candidate if overloaded (503) or rate-limited on specific model
                        continue
            except Exception as key_err:
                last_error = str(key_err)
                print(f"[Gemini Key Error] Key ...{active_key[-6:]} failed: {key_err}")
                continue

        if "503" in str(last_error) or "unavailable" in str(last_error).lower():
            return "⚠️ **Gemini API Overloaded (HTTP 503)**\n\nGoogle's servers are currently experiencing high demand. Please try again in a few moments or switch to a different provider (like Cohere or OpenRouter)."

        if "429" in str(last_error) or "quota" in str(last_error).lower():
            return (
                "⚠️ **Gemini API Rate Limit / Quota Exceeded (HTTP 429)**\n\n"
                "Google Gemini has temporarily rate-limited requests on this key (often due to per-minute limits or high demand).\n\n"
                "**Solution**: Please wait 30–60 seconds, or switch to **Cohere** or **OpenRouter** in the left sidebar."
            )

        return f"[Gemini API Error: {last_error or 'Could not generate response with available Gemini models.'}]"
