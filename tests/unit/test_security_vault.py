"""
Unit Tests for AES-256 Security Vault.
"""

import pytest
from jarvis.security.vault import AESVault
from jarvis.core.exceptions import VaultError


def test_vault_store_and_retrieve_secret():
    vault = AESVault(master_password="secret-password-key")
    service = "openai_api_key"
    raw_secret = "sk-proj-1234567890abcdef"

    assert vault.store_secret(service, raw_secret) is True
    retrieved = vault.get_secret(service)
    assert retrieved == raw_secret


def test_vault_nonexistent_secret():
    vault = AESVault(master_password="secret-password-key")
    assert vault.get_secret("nonexistent_service") is None


def test_vault_delete_secret():
    vault = AESVault(master_password="secret-password-key")
    vault.store_secret("service_x", "secret_value")
    assert vault.delete_secret("service_x") is True
    assert vault.get_secret("service_x") is None
