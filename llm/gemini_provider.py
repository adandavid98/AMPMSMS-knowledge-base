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

            # Try primary model (gemini-3.6-flash), fallback to gemini-2.5-flash
            for model_candidate in [self.model_name, "gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_candidate,
                        system_instruction=system_prompt
                    )
                    response = model.generate_content(contents)
                    return response.text
                except Exception:
                    continue
            return "[Gemini Error: Could not generate response with available Gemini models.]"
        except Exception as e:
            return f"[Gemini Error: {str(e)}]"
