"""Explicit acceptance policy for FP16 NPU versus FP32 reference output.

Keep exact-token checks for short fixtures. For long fixtures, require identical
words (including accents, numbers and word boundaries), allowing only casing and
punctuation differences. Tensor checks remain independent of decoded text.
"""
import re
import unicodedata

POLICY = 'stream-lexical-v1'


def words(text):
    return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())


def accepted(result):
    return (
        result.get('frontend_parity') is True
        and result.get('lexical_equal') is True
        and (result.get('audio_samples', 0) > 640000 or result.get('tokens_equal') is True)
        and result.get('relative_l2_error', float('inf')) < 0.03
        and result.get('global_relative_l2_error', float('inf')) < 0.01
    )
