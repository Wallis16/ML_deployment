import torch

from app.model import _prepare_model_inputs


def test_prepare_model_inputs_accepts_tensor() -> None:
    input_ids = torch.tensor([[1, 2, 3]])

    prepared_input_ids, attention_mask = _prepare_model_inputs(input_ids, "cpu", torch)

    assert torch.equal(prepared_input_ids, input_ids)
    assert torch.equal(attention_mask, torch.ones_like(input_ids))


def test_prepare_model_inputs_accepts_mapping_with_attention_mask() -> None:
    input_ids = torch.tensor([[1, 2, 3]])
    attention_mask = torch.tensor([[1, 1, 0]])

    prepared_input_ids, prepared_attention_mask = _prepare_model_inputs(
        {"input_ids": input_ids, "attention_mask": attention_mask},
        "cpu",
        torch,
    )

    assert torch.equal(prepared_input_ids, input_ids)
    assert torch.equal(prepared_attention_mask, attention_mask)
