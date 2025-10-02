"""Game entities for the semi-auto shooter."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import pygame


Vec = pygame.math.Vector2


@dataclass
class Bullet:
    position: Vec
    velocity: Vec
    damage: float
    radius: int
    friendly: bool

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt

    def to_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.position.x - self.radius), int(self.position.y - self.radius), self.radius * 2, self.radius * 2)


@dataclass
class PlayerStats:
    hp: float = 100
    max_hp: float = 100
    energy: float = 100
    max_energy: float = 100
    heat: float = 0
    max_heat: float = 100
    special: float = 0
    max_special: float = 100


class Player:
    def __init__(self, position: Tuple[float, float]) -> None:
        self.position = Vec(position)
        self.velocity = Vec(0, 0)
        self.speed = 170
        self.stats = PlayerStats()
        self.radius = 18
        self.shot_timer = 0.0
        self.strong_timer = 0.0
        self.step_cooldown = 0.0
        self.invincible = 0.0

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
        self.position.x = max(30, min(610, self.position.x))
        self.position.y = max(40, min(440, self.position.y))
        self.stats.energy = min(self.stats.max_energy, self.stats.energy + 20 * dt)
        self.stats.heat = max(0, self.stats.heat - 15 * dt)
        self.stats.special = min(self.stats.max_special, self.stats.special + 5 * dt)
        if self.shot_timer > 0:
            self.shot_timer -= dt
        if self.strong_timer > 0:
            self.strong_timer -= dt
        if self.step_cooldown > 0:
            self.step_cooldown -= dt
        if self.invincible > 0:
            self.invincible -= dt

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.position.x - self.radius), int(self.position.y - self.radius), self.radius * 2, self.radius * 2)

    def take_damage(self, dmg: float) -> None:
        if self.invincible > 0:
            return
        self.stats.hp = max(0, self.stats.hp - dmg)

    def can_shoot(self) -> bool:
        return self.shot_timer <= 0

    def can_strong(self) -> bool:
        return self.strong_timer <= 0 and self.stats.energy >= 35

    def can_step(self) -> bool:
        return self.step_cooldown <= 0

    def shoot(self) -> List[Bullet]:
        if not self.can_shoot():
            return []
        self.shot_timer = 0.18
        self.stats.heat = min(self.stats.max_heat, self.stats.heat + 8)
        self.stats.energy = min(self.stats.max_energy, self.stats.energy + 5)
        bullet = Bullet(self.position.copy(), Vec(0, -420), 6, 4, True)
        return [bullet]

    def strong_attack(self) -> List[Bullet]:
        if not self.can_strong():
            return []
        self.strong_timer = 0.9
        self.stats.energy -= 35
        self.stats.heat = min(self.stats.max_heat, self.stats.heat + 25)
        bullets = []
        for offset in (-25, 0, 25):
            bullet_pos = self.position + Vec(offset, -5)
            bullets.append(Bullet(bullet_pos, Vec(0, -520), 22, 6, True))
        return bullets

    def step(self, direction: Vec) -> None:
        if not self.can_step():
            return
        self.position += direction * 120
        self.velocity = direction * 220
        self.step_cooldown = 1.6
        self.invincible = 0.35

    def use_special(self) -> List[Bullet]:
        if self.stats.special < self.stats.max_special:
            return []
        self.stats.special = 0
        self.stats.energy = max(0, self.stats.energy - 40)
        self.stats.heat = min(self.stats.max_heat, self.stats.heat + 40)
        bullets = []
        for angle in range(-45, 50, 15):
            rad = math.radians(angle)
            velocity = Vec(math.sin(rad) * 420, -math.cos(rad) * 420)
            bullets.append(Bullet(self.position.copy(), velocity, 18, 6, True))
        return bullets


class Enemy:
    def __init__(self, position: Tuple[float, float], hp: float, speed: float = 50) -> None:
        self.position = Vec(position)
        self.hp = hp
        self.speed = speed
        self.radius = 20
        self.shoot_timer = 0.0
        self.type = "boss"

    def update(self, dt: float, target: Vec) -> List[Bullet]:
        direction = (target - self.position)
        if direction.length() > 1:
            self.position += direction.normalize() * self.speed * dt * 0.4
        bullets: List[Bullet] = []
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = 0.75
            for offset in (-40, -10, 10, 40):
                start = self.position + Vec(offset, 20)
                velocity = Vec(offset * 0.9, 210)
                bullets.append(Bullet(start, velocity, 12, 6, False))
        return bullets

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.position.x - self.radius), int(self.position.y - self.radius), self.radius * 2, self.radius * 2)

    def take_damage(self, dmg: float) -> None:
        self.hp = max(0, self.hp - dmg)

    def alive(self) -> bool:
        return self.hp > 0
