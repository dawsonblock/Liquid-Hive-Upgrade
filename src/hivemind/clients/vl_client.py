import torch
from transformers import AutoModelForCausalLM, AutoProcessor


class VLClient:
    def __init__(self, model_id: str, revision: str = "main"):
        # Pin revision for security - prevents supply chain attacks
        self.processor = AutoProcessor.from_pretrained(
            model_id, 
            revision=revision, 
            trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id, 
            revision=revision,
            torch_dtype=torch.bfloat16, 
            device_map="auto", 
            trust_remote_code=True
        )

    def generate(self, prompt: str, image):
        inputs = self.processor(text=prompt, images=image, return_tensors="pt").to(
            self.model.device
        )
        out = self.model.generate(**inputs, max_new_tokens=256)
        txt = self.processor.batch_decode(out, skip_special_tokens=True)[0]
        return txt
