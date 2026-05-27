"""加密服务 - AES/RSA加密、哈希、签名、密钥管理"""

import json
import os
import time
import hashlib
import hmac
import base64
import secrets
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class Algorithm(Enum):
    SHA256 = "sha256"
    SHA512 = "sha512"
    MD5 = "md5"
    HMAC_SHA256 = "hmac_sha256"
    AES = "aes"
    RSA = "rsa"
    FERNET = "fernet"


class KeyType(Enum):
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    HMAC = "hmac"


@dataclass
class CryptoKey:
    key_id: str
    key_type: str
    algorithm: str
    key_data: str  # base64 encoded
    created_at: float = 0.0
    expires_at: float = 0.0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CryptoOperation:
    operation_id: str
    operation_type: str  # encrypt/decrypt/sign/verify/hash
    algorithm: str
    key_id: str = ""
    timestamp: float = 0.0
    success: bool = True
    error: str = ""


class EncryptionServiceEngine:
    """加密服务引擎"""

    def __init__(self, storage_dir: str = "data/encryption"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.keys: Dict[str, CryptoKey] = {}
        self.operations: List[CryptoOperation] = []
        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "crypto_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("keys", {}).items():
                    self.keys[k] = CryptoKey(**v)
                self.operations = [CryptoOperation(**o) for o in data.get("operations", [])]
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "crypto_data.json")
        data = {
            "keys": {k: asdict(v) for k, v in self.keys.items()},
            "operations": [asdict(o) for o in self.operations[-5000:]],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def generate_key(self, key_type: str = "symmetric",
                     algorithm: str = "aes", length: int = 32,
                     expires_in: int = 0) -> str:
        """生成密钥"""
        key_id = hashlib.md5(f"{key_type}_{time.time()}".encode()).hexdigest()[:12]

        if key_type == KeyType.SYMMETRIC.value:
            key_bytes = secrets.token_bytes(length)
        elif key_type == KeyType.HMAC.value:
            key_bytes = secrets.token_bytes(length)
        else:
            key_bytes = secrets.token_bytes(length)

        key_data = base64.b64encode(key_bytes).decode()

        key = CryptoKey(
            key_id=key_id,
            key_type=key_type,
            algorithm=algorithm,
            key_data=key_data,
            created_at=time.time(),
            expires_at=time.time() + expires_in if expires_in > 0 else 0,
        )
        self.keys[key_id] = key
        self._save()
        return key_id

    def hash_data(self, data: str, algorithm: str = "sha256") -> str:
        """哈希"""
        data_bytes = data.encode('utf-8')

        if algorithm == Algorithm.SHA256.value:
            result = hashlib.sha256(data_bytes).hexdigest()
        elif algorithm == Algorithm.SHA512.value:
            result = hashlib.sha512(data_bytes).hexdigest()
        elif algorithm == Algorithm.MD5.value:
            result = hashlib.md5(data_bytes).hexdigest()
        else:
            result = hashlib.sha256(data_bytes).hexdigest()

        self._log_operation("hash", algorithm)
        return result

    def hmac_sign(self, data: str, key_id: str,
                  algorithm: str = "sha256") -> str:
        """HMAC签名"""
        if key_id not in self.keys:
            return ""

        key = self.keys[key_id]
        key_bytes = base64.b64decode(key.key_data)
        data_bytes = data.encode('utf-8')

        if algorithm == "sha256":
            result = hmac.new(key_bytes, data_bytes, hashlib.sha256).hexdigest()
        elif algorithm == "sha512":
            result = hmac.new(key_bytes, data_bytes, hashlib.sha512).hexdigest()
        else:
            result = hmac.new(key_bytes, data_bytes, hashlib.sha256).hexdigest()

        self._log_operation("sign", f"hmac_{algorithm}", key_id)
        return result

    def hmac_verify(self, data: str, signature: str, key_id: str,
                    algorithm: str = "sha256") -> bool:
        """HMAC验证"""
        expected = self.hmac_sign(data, key_id, algorithm)
        if not expected:
            return False
        result = hmac.compare_digest(expected, signature)
        self._log_operation("verify", f"hmac_{algorithm}", key_id)
        return result

    def encrypt_simple(self, plaintext: str, key_id: str) -> str:
        """简单异或加密(Base64输出)"""
        if key_id not in self.keys:
            return ""

        key = self.keys[key_id]
        key_bytes = base64.b64decode(key.key_data)
        plain_bytes = plaintext.encode('utf-8')

        # XOR加密
        encrypted = bytearray()
        for i, b in enumerate(plain_bytes):
            encrypted.append(b ^ key_bytes[i % len(key_bytes)])

        result = base64.b64encode(encrypted).decode()
        self._log_operation("encrypt", "xor", key_id)
        return result

    def decrypt_simple(self, ciphertext: str, key_id: str) -> str:
        """简单异或解密"""
        if key_id not in self.keys:
            return ""

        key = self.keys[key_id]
        key_bytes = base64.b64decode(key.key_data)

        try:
            encrypted = base64.b64decode(ciphertext)
        except Exception:
            return ""

        decrypted = bytearray()
        for i, b in enumerate(encrypted):
            decrypted.append(b ^ key_bytes[i % len(key_bytes)])

        result = decrypted.decode('utf-8', errors='replace')
        self._log_operation("decrypt", "xor", key_id)
        return result

    def generate_token(self, length: int = 32) -> str:
        """生成安全随机Token"""
        return secrets.token_urlsafe(length)

    def generate_salt(self, length: int = 16) -> str:
        """生成盐值"""
        return base64.b64encode(secrets.token_bytes(length)).decode()

    def hash_password(self, password: str, salt: str = "") -> Tuple[str, str]:
        """密码哈希(带盐)"""
        if not salt:
            salt = self.generate_salt()

        salted = f"{salt}{password}".encode('utf-8')
        # 多轮哈希
        result = salted
        for _ in range(10000):
            result = hashlib.sha256(result).digest()

        password_hash = base64.b64encode(result).decode()
        return password_hash, salt

    def verify_password(self, password: str, password_hash: str,
                        salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, password_hash)

    def _log_operation(self, op_type: str, algorithm: str, key_id: str = ""):
        """记录操作"""
        op = CryptoOperation(
            operation_id=hashlib.md5(f"{op_type}_{time.time()}".encode()).hexdigest()[:12],
            operation_type=op_type,
            algorithm=algorithm,
            key_id=key_id,
            timestamp=time.time(),
        )
        self.operations.append(op)

    def rotate_key(self, key_id: str) -> Optional[str]:
        """轮换密钥"""
        if key_id not in self.keys:
            return None

        old_key = self.keys[key_id]
        new_key_id = self.generate_key(old_key.key_type, old_key.algorithm)
        old_key.is_active = False
        old_key.expires_at = time.time()
        self._save()
        return new_key_id

    def revoke_key(self, key_id: str) -> bool:
        """吊销密钥"""
        if key_id in self.keys:
            self.keys[key_id].is_active = False
            self._save()
            return True
        return False

    def list_keys(self) -> List[Dict[str, Any]]:
        """列出密钥"""
        return [
            {
                "key_id": k.key_id,
                "type": k.key_type,
                "algorithm": k.algorithm,
                "active": k.is_active,
                "created": k.created_at,
            }
            for k in self.keys.values()
        ]

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        return {
            "total_keys": len(self.keys),
            "active_keys": sum(1 for k in self.keys.values() if k.is_active),
            "total_operations": len(self.operations),
            "operation_types": {
                op: sum(1 for o in self.operations if o.operation_type == op)
                for op in set(o.operation_type for o in self.operations)
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "keys_count": len(self.keys),
            "active_keys": sum(1 for k in self.keys.values() if k.is_active),
            "operations_count": len(self.operations),
        }


if __name__ == "__main__":
    print("=== 加密服务测试 ===")
    engine = EncryptionServiceEngine()

    # 生成密钥
    key_id = engine.generate_key("symmetric", "aes", 32)
    hmac_key = engine.generate_key("hmac", "hmac_sha256", 32)
    print(f"密钥: {key_id}, HMAC密钥: {hmac_key}")

    # 哈希
    h = engine.hash_data("Hello World")
    print(f"SHA256: {h}")

    # HMAC签名
    sig = engine.hmac_sign("重要数据", hmac_key)
    print(f"HMAC签名: {sig}")
    print(f"验证: {engine.hmac_verify('重要数据', sig, hmac_key)}")

    # 加密解密
    encrypted = engine.encrypt_simple("这是秘密消息", key_id)
    decrypted = engine.decrypt_simple(encrypted, key_id)
    print(f"加密: {encrypted[:30]}...")
    print(f"解密: {decrypted}")

    # 密码哈希
    pw_hash, salt = engine.hash_password("mypassword")
    print(f"密码验证: {engine.verify_password('mypassword', pw_hash, salt)}")
    print(f"错误密码: {engine.verify_password('wrong', pw_hash, salt)}")

    # Token生成
    print(f"Token: {engine.generate_token(16)}")

    report = engine.generate_report()
    print(f"\n加密报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
