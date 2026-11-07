"""Bayesian Knowledge Tracing. Parameters are illustrative defaults, NOT calibrated."""
from __future__ import annotations

PRIOR = 0.3
SLIP = 0.1
GUESS = 0.2
LEARN = 0.1


def bkt_update(p: float, correct: bool, slip: float = SLIP, guess: float = GUESS, learn: float = LEARN) -> float:
    if correct:
        numerator = p * (1 - slip)
        denominator = numerator + (1 - p) * guess
    else:
        numerator = p * slip
        denominator = numerator + (1 - p) * (1 - guess)
    posterior = numerator / denominator
    return posterior + (1 - posterior) * learn


def replay(answers: list[bool], prior: float = PRIOR) -> float:
    p = prior
    for a in answers:
        p = bkt_update(p, a)
    return p


def evidence_strength(n: int) -> str:
    if n <= 0:
        return "none"
    if n == 1:
        return "weak"
    if n <= 3:
        return "moderate"
    return "strong"
