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
        active_key = api_key or self.api_key
        if not active_key:
            return "[Error: GEMINI_API_KEY missing. Please set your key in the Web UI sidebar or .env file.]"

        try:
            import google.generativeai as genai
            import base64
            import io
            from PIL import Image

            genai.configure(api_key=active_key)
            
            # Prepare contents payload (text prompt + images)
            contents = [user_prompt]
            if images:
                for img_item in images:
                    try:
                        if isinstance(img_item, str):
                            # Assume base64 string
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

            # Unique list of active, valid Gemini API model names supported by your key
            raw_candidates = [self.model_name, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest", "gemini-3.5-flash"]
            candidates = []
            for c in raw_candidates:
                if c and c not in candidates:
                    candidates.append(c)
            
            last_error = None
            for model_candidate in candidates:
                clean_name = model_candidate.replace("models/", "")
                try:
                    model = genai.GenerativeModel(
                        model_name=clean_name,
                        system_instruction=system_prompt
                    )
                    response = model.generate_content(contents)
                    if response and hasattr(response, "text") and response.text:
                        return response.text
                except Exception as model_err:
                    err_str = str(model_err)
                    print(f"[Gemini Warning] Model {clean_name} failed: {err_str}")
                    last_error = err_str
                    # Continue trying next candidate model in list since each model has separate quota buckets
                    continue

            if "429" in str(last_error) or "quota" in str(last_error).lower():
                return (
                    "⚠️ **Gemini API Quota Limit Reached (HTTP 429)**\n\n"
                    "Your free Gemini API key has temporarily reached Google's quota limit for today.\n\n"
                    "**Solutions**:\n"
                    "1. Switch to **Groq API** in the left sidebar under *LLM Provider* for instant responses with zero rate limits.\n"
                    "2. Add your own custom Gemini API Key in the *API Key Settings* sidebar accordion."
                )

            return f"[Gemini API Error: {last_error or 'Could not generate response with available Gemini models.'}]"
        except Exception as e:
            return f"[Gemini Error: {str(e)}]"
