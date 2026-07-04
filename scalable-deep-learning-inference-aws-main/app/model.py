import os
import time
from dataclasses import dataclass
from threading import Lock

from app.metrics import MODEL_LOAD_TIME
from app.schemas import DeviceInfo, DeviceStatusResponse

DEFAULT_MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"


@dataclass
class GenerationResult:
    text: str
    tokens_generated: int
    first_token_latency_ms: int | None


class SmolLMGenerator:
    def __init__(self, model_id: str = DEFAULT_MODEL_ID) -> None:
        self.model_id = model_id
        self._tokenizer = None
        self._model = None
        self._device = "cpu"
        self._load_lock = Lock()
        self.load_time_seconds: float | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def load(self) -> None:
        if self.is_loaded:
            return

        with self._load_lock:
            if self.is_loaded:
                return

            if _mock_mode_enabled():
                self.load_time_seconds = 0.0
                MODEL_LOAD_TIME.set(0.0)
                return

            started = time.perf_counter()

            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if self._device == "cuda" else torch.float32

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=dtype,
            )
            self._model.to(self._device)
            self._model.eval()

            self.load_time_seconds = time.perf_counter() - started
            MODEL_LOAD_TIME.set(self.load_time_seconds)

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 100,
        temperature: float = 0.7,
    ) -> GenerationResult:
        self.load()

        if _mock_mode_enabled():
            mock_text = (
                "AWS ECS is a managed container orchestration service for "
                "running and scaling containerized workloads on AWS."
            )
            return GenerationResult(
                text=mock_text,
                tokens_generated=len(mock_text.split()),
                first_token_latency_ms=0,
            )

        import torch

        assert self._tokenizer is not None
        assert self._model is not None

        messages = [{"role": "user", "content": prompt}]
        if hasattr(self._tokenizer, "apply_chat_template"):
            encoded = self._tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
            )
        else:
            encoded = self._tokenizer(prompt, return_tensors="pt")

        input_ids, attention_mask = _prepare_model_inputs(encoded, self._device, torch)
        input_token_count = input_ids.shape[-1]
        do_sample = temperature > 0

        started = time.perf_counter()
        with torch.inference_mode():
            output_ids = self._model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                temperature=temperature if do_sample else None,
                do_sample=do_sample,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        if self._device == "cuda":
            torch.cuda.synchronize()

        generated_ids = output_ids[0][input_token_count:]
        text = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return GenerationResult(
            text=text,
            tokens_generated=len(generated_ids),
            first_token_latency_ms=elapsed_ms if len(generated_ids) else None,
        )

    def device_status(self) -> DeviceStatusResponse:
        try:
            import torch
        except ImportError:
            return DeviceStatusResponse(
                model_loaded=self.is_loaded,
                inference_device=self._device,
                cuda_available=False,
                gpu_count=0,
                devices=[],
                note="PyTorch is not installed.",
            )

        cuda_available = torch.cuda.is_available()
        gpu_count = torch.cuda.device_count() if cuda_available else 0
        devices = []

        for index in range(gpu_count):
            props = torch.cuda.get_device_properties(index)
            devices.append(
                DeviceInfo(
                    index=index,
                    name=torch.cuda.get_device_name(index),
                    total_memory_mb=round(props.total_memory / 1024 / 1024),
                )
            )

        note = None
        if _mock_mode_enabled():
            note = "Mock mode is enabled, so generation is not using the model."
        elif not self.is_loaded:
            note = "Model is not loaded yet. Call /generate to load it."

        return DeviceStatusResponse(
            model_loaded=self.is_loaded,
            inference_device=self._device,
            cuda_available=cuda_available,
            gpu_count=gpu_count,
            devices=devices,
            note=note,
        )


def _mock_mode_enabled() -> bool:
    return os.getenv("SMOLLM_MOCK", "").lower() in {"1", "true", "yes"}


def _prepare_model_inputs(encoded, device: str, torch):
    if hasattr(encoded, "to"):
        encoded = encoded.to(device)

    if hasattr(encoded, "keys"):
        input_ids = encoded["input_ids"]
        attention_mask = encoded.get("attention_mask")
    else:
        input_ids = encoded
        attention_mask = None

    if attention_mask is None:
        attention_mask = torch.ones_like(input_ids)

    return input_ids, attention_mask


generator = SmolLMGenerator(os.getenv("MODEL_ID", DEFAULT_MODEL_ID))
