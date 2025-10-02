"""AI behavior implementation for semi-auto shooter."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class Personality(Enum):
    AGGRESSIVE = "Aggressive"
    PRUDENT = "Prudent"
    SKITTISH = "Skittish"


class Action(Enum):
    NORMAL_SHOT = "normal_shot"
    STRONG_ATTACK = "strong_attack"
    APPROACH = "approach"
    KEEP_DISTANCE = "keep_distance"
    EVADE = "evade"
    STEP = "step"
    SPECIAL = "special"


BASE_WEIGHTS: Dict[Action, float] = {
    Action.NORMAL_SHOT: 25,
    Action.STRONG_ATTACK: 10,
    Action.APPROACH: 20,
    Action.KEEP_DISTANCE: 20,
    Action.EVADE: 15,
    Action.STEP: 5,
    Action.SPECIAL: 5,
}


@dataclass
class OrderBias:
    values: Dict[Action, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for action in Action:
            self.values.setdefault(action, 0.0)

    def __getitem__(self, action: Action) -> float:
        return self.values[action]

    def set_bias(self, action: Action, value: float) -> None:
        self.values[action] = value

    def scale(self, factor: float) -> None:
        for key in self.values:
            self.values[key] *= factor


@dataclass
class AIContext:
    threat_level: float
    target_score: float
    distance: float
    energy: float
    heat: float
    special: float
    hp_ratio: float
    sync: float
    cooldown_ready: bool


@dataclass
class AIChoice:
    action: Action
    delay: float


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(value, maximum))


class AIController:
    """Decides which action the partner AI should perform."""

    def __init__(
        self,
        personality: Personality = Personality.AGGRESSIVE,
        order_bias: OrderBias | None = None,
        base_delay: float = 0.35,
    ) -> None:
        self.personality = personality
        self.order_bias = order_bias or OrderBias()
        self.base_delay = base_delay
        self._rng = random.Random()
        self._rng.seed()

    def set_personality(self, personality: Personality) -> None:
        self.personality = personality

    def set_order_bias(self, bias: OrderBias) -> None:
        self.order_bias = bias

    def think(self, ctx: AIContext) -> AIChoice:
        weights = {action: weight for action, weight in BASE_WEIGHTS.items()}

        # 状況バイアス
        if ctx.threat_level > 0.7:
            weights[Action.EVADE] += 40
            weights[Action.STEP] += 15
        if ctx.energy < 20:
            weights[Action.STRONG_ATTACK] -= 30
        if ctx.heat > 70:
            weights[Action.NORMAL_SHOT] -= 20
            weights[Action.STRONG_ATTACK] -= 20
            weights[Action.EVADE] += 20
        if ctx.hp_ratio < 0.3:
            weights[Action.KEEP_DISTANCE] += 20
        if ctx.special >= 100:
            weights[Action.SPECIAL] += 15

        # 指示バイアス
        for action in Action:
            weights[action] += self.order_bias[action]

        # 性格補正
        if self.personality == Personality.AGGRESSIVE:
            weights[Action.NORMAL_SHOT] *= 1.3
            weights[Action.STRONG_ATTACK] *= 1.3
            weights[Action.EVADE] *= 0.7
            weights[Action.KEEP_DISTANCE] *= 0.8
        elif self.personality == Personality.PRUDENT:
            weights[Action.EVADE] *= 1.3
            weights[Action.KEEP_DISTANCE] *= 1.1
            weights[Action.NORMAL_SHOT] *= 0.8
            weights[Action.STRONG_ATTACK] *= 0.7
        elif self.personality == Personality.SKITTISH:
            weights[Action.KEEP_DISTANCE] += 20
            weights[Action.SPECIAL] -= 15
            weights[Action.APPROACH] *= 0.7
            weights[Action.NORMAL_SHOT] *= 0.8

        if not ctx.cooldown_ready:
            weights[Action.STEP] = 0

        # Clamp negatives to zero to avoid misbehavior
        for action in weights:
            weights[action] = max(0.0, weights[action])

        # Weighted choice
        choice = self._weighted_choice(weights)
        delay = self.base_delay * (1 - clamp(ctx.sync, 0.0, 0.9))
        delay += self._rng.uniform(-0.08, 0.08)
        delay = max(0.05, delay)
        return AIChoice(action=choice, delay=delay)

    def _weighted_choice(self, weights: Dict[Action, float]) -> Action:
        total = sum(weights.values())
        if total <= 0:
            return Action.KEEP_DISTANCE
        target = self._rng.uniform(0, total)
        cumulative = 0.0
        for action, weight in weights.items():
            cumulative += weight
            if target <= cumulative:
                return action
        return Action.KEEP_DISTANCE


def bias_from_instruction(name: str) -> OrderBias:
    """Return pre-defined bias sets for quick toggles."""
    name = name.lower()
    bias = OrderBias()
    if name == "aggressive":
        bias.set_bias(Action.NORMAL_SHOT, 25)
        bias.set_bias(Action.STRONG_ATTACK, 35)
        bias.set_bias(Action.APPROACH, 15)
    elif name == "defensive":
        bias.set_bias(Action.EVADE, 30)
        bias.set_bias(Action.KEEP_DISTANCE, 25)
        bias.set_bias(Action.STEP, 20)
    elif name == "focus":
        bias.set_bias(Action.NORMAL_SHOT, 10)
        bias.set_bias(Action.STRONG_ATTACK, 10)
    elif name == "special":
        bias.set_bias(Action.SPECIAL, 45)
    elif name == "balanced":
        pass
    else:
        raise ValueError(f"Unknown instruction '{name}'")
    return bias
