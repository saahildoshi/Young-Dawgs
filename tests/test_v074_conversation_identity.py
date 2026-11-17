"""Protect conversation continuity when ChatGPT redirects an existing project chat."""
import pytest
from scripts.v074_trials import conversation_id

IDENTITY='6afbb12b-1020-83ea-85ba-d387a4969eee'


def test_project_path_preserves_original_conversation_identity():
    original=f'https://chatgpt.com/c/{IDENTITY}'
    observed=f'https://chatgpt.com/g/g-p-6adabe4175a48191b0a5bb4986ade2f1-pipeline-tests/c/{IDENTITY}'
    assert conversation_id(original)==conversation_id(observed)==IDENTITY


def test_another_chat_is_never_a_same_conversation_revision():
    assert conversation_id(f'https://chatgpt.com/c/{IDENTITY}')!=conversation_id('https://chatgpt.com/c/6afbb637-f198-83ea-b1e8-70ef3b1cb890')


def test_nonconversation_or_foreign_service_is_rejected():
    for url in ['https://chatgpt.com/','https://example.com/c/'+IDENTITY,'https://chatgpt.com/c/new']:
        with pytest.raises(ValueError):conversation_id(url)
