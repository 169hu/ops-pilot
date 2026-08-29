"""纯 Python xxhash 兜底垫片（仅本机 AppLocker 策略拦截原生 xxhash DLL 时启用）。

背景：Windows「应用程序控制策略」拦截了 xxhash 的原生 _xxhash.pyd（机器级策略，
非代码问题）。依赖方实际只用两个能力：
  - langsmith/_internal/_uuid.py : `xxhash.xxh3_128(data).digest()`
  - langgraph/...                : `from xxhash import xxh3_128_hexdigest`
它们都只要求「对相同输入返回稳定输出」，不要求真实 XXH3 标准值。

因此本垫片在原生 import 失败时，以真实 module 注入 sys.modules['xxhash']，用 stdlib
hashlib 产出确定性摘要。在不受该策略限制的机器上真实 xxhash 正常加载，本垫片不生效。
"""
import hashlib
import sys
import types

try:
    import xxhash as _real  # noqa: F401
    _IS_REAL = True
except ImportError:
    _IS_REAL = False

_FIXED_SEED = b"ops-pilot-xxhash-fallback-seed"


def _digest_bytes(data: bytes) -> bytes:
    return hashlib.sha256(_FIXED_SEED + (data or b"")).digest()


def xxh3_128(data: bytes):
    class _D:
        def digest(self) -> bytes:
            return _digest_bytes(data)

        def hexdigest(self) -> str:
            return _digest_bytes(data).hex()

    return _D()


def xxh3_128_hexdigest(data: bytes) -> str:
    return _digest_bytes(data).hex()


def _install_if_blocked():
    if _IS_REAL:
        return
    mod = types.ModuleType("xxhash")
    mod.xxh3_128 = xxh3_128
    mod.xxh3_128_hexdigest = xxh3_128_hexdigest
    mod.__doc__ = ("纯 Python 兜底垫片（原生 DLL 被机器 AppLocker 拦截）")
    sys.modules["xxhash"] = mod


_install_if_blocked()