"""单元测试: core/security.py — JWT + bcrypt 密码"""

import time
from datetime import timedelta
from unittest.mock import patch

import pytest

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
)


class TestVerifyPassword:
    """密码验证"""

    def test_correct_password(self):
        hashed = get_password_hash("admin123")
        assert verify_password("admin123", hashed) is True

    def test_wrong_password(self):
        hashed = get_password_hash("admin123")
        assert verify_password("wrong", hashed) is False

    def test_empty_password(self):
        hashed = get_password_hash("secret")
        assert verify_password("", hashed) is False


class TestGetPasswordHash:
    """密码哈希"""

    def test_returns_string(self):
        h = get_password_hash("test")
        assert isinstance(h, str)

    def test_unique_per_call(self):
        """两次哈希结果不同（salt 随机）"""
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2

    def test_verifiable(self):
        h = get_password_hash("mypass")
        assert verify_password("mypass", h) is True


class TestCreateAccessToken:
    """JWT 生成"""

    def test_returns_string(self):
        token = create_access_token(data={"sub": "user1"})
        assert isinstance(token, str)

    def test_contains_payload(self):
        token = create_access_token(data={"sub": "u1", "role": "admin"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "u1"
        assert payload["role"] == "admin"

    def test_has_exp(self):
        token = create_access_token(data={"sub": "u1"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token(
            data={"sub": "u1"}, expires_delta=timedelta(minutes=1)
        )
        payload = decode_token(token)
        assert payload is not None


class TestDecodeToken:
    """JWT 解析"""

    def test_valid_token(self):
        token = create_access_token(data={"sub": "u1"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "u1"

    def test_invalid_token(self):
        assert decode_token("not.a.jwt") is None

    def test_empty_token(self):
        assert decode_token("") is None

    def test_expired_token(self):
        token = create_access_token(
            data={"sub": "u1"}, expires_delta=timedelta(seconds=-1)
        )
        assert decode_token(token) is None
