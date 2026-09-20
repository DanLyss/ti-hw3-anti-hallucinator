from src.prompt_builder import build_prompt


def test_prompt_contains_description_and_indexed_alphabet():
    prompt = build_prompt("тестовое описание языка", ("a", "b", "c"))
    assert "тестовое описание языка" in prompt
    assert "0 -> 'a'" in prompt
    assert "1 -> 'b'" in prompt
    assert "2 -> 'c'" in prompt
    assert "n\nm" in prompt  # спецификация формата присутствует


def test_prompt_is_stable_for_same_input():
    prompt1 = build_prompt("desc", ("0", "1"))
    prompt2 = build_prompt("desc", ("0", "1"))
    assert prompt1 == prompt2
