"""Main game loop for semi-auto shooter '指示と本能'."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pygame

from .ai import Action, AIContext, AIController, Personality, bias_from_instruction
from .entities import Bullet, Enemy, Player

WIDTH = 640
HEIGHT = 480
FPS = 60


@dataclass
class InputState:
    instruction: str = "balanced"
    personality: Personality = Personality.AGGRESSIVE


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("指示と本能 / Orders & Instinct")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("noto sans", 18)
        self.big_font = pygame.font.SysFont("noto sans", 28)
        self.player = Player((WIDTH / 2, HEIGHT - 80))
        self.enemy = Enemy((WIDTH / 2, 120), hp=1200)
        self.player_bullets: List[Bullet] = []
        self.enemy_bullets: List[Bullet] = []
        self.input_state = InputState()
        self.order_bias = bias_from_instruction("balanced")
        self.ai = AIController()
        self.ai.set_order_bias(self.order_bias)
        self.ai_timer = 0.0
        self.running = True

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_q:
                    self.set_instruction("balanced")
                elif event.key == pygame.K_w:
                    self.set_instruction("aggressive")
                elif event.key == pygame.K_e:
                    self.set_instruction("defensive")
                elif event.key == pygame.K_r:
                    self.set_instruction("focus")
                elif event.key == pygame.K_t:
                    self.set_instruction("special")
                elif event.key == pygame.K_1:
                    self.ai.set_personality(Personality.AGGRESSIVE)
                elif event.key == pygame.K_2:
                    self.ai.set_personality(Personality.PRUDENT)
                elif event.key == pygame.K_3:
                    self.ai.set_personality(Personality.SKITTISH)

    def set_instruction(self, name: str) -> None:
        self.order_bias = bias_from_instruction(name)
        self.input_state.instruction = name
        self.ai.set_order_bias(self.order_bias)

    def update(self, dt: float) -> None:
        self.ai_timer -= dt
        self.player.update(dt)
        new_enemy_bullets = self.enemy.update(dt, self.player.position)
        if new_enemy_bullets:
            self.enemy_bullets.extend(new_enemy_bullets)

        if self.ai_timer <= 0:
            ctx = self.build_context()
            choice = self.ai.think(ctx)
            self.ai_timer = max(0.05, choice.delay)
            self.execute_action(choice.action)

        self.update_bullets(dt)
        self.handle_collisions()
        self.player.velocity *= 0.85

    def build_context(self) -> AIContext:
        threat = self.calculate_threat_level()
        distance = (self.enemy.position - self.player.position).length()
        target_score = 1.0  # single boss
        energy = self.player.stats.energy
        heat = self.player.stats.heat
        special = self.player.stats.special
        hp_ratio = self.player.stats.hp / self.player.stats.max_hp
        sync = 0.35
        cooldown_ready = self.player.can_step()
        return AIContext(
            threat_level=threat,
            target_score=target_score,
            distance=distance,
            energy=energy,
            heat=heat,
            special=special,
            hp_ratio=hp_ratio,
            sync=sync,
            cooldown_ready=cooldown_ready,
        )

    def execute_action(self, action: Action) -> None:
        to_add: List[Bullet] = []
        if action == Action.NORMAL_SHOT:
            to_add = self.player.shoot()
        elif action == Action.STRONG_ATTACK and self.player.stats.energy >= 35:
            to_add = self.player.strong_attack()
        elif action == Action.APPROACH:
            direction = (self.enemy.position - self.player.position)
            if direction.length() > 1:
                self.player.velocity = direction.normalize() * self.player.speed
        elif action == Action.KEEP_DISTANCE:
            desired = 200
            direction = (self.player.position - self.enemy.position)
            if direction.length() == 0:
                direction = pygame.math.Vector2(1, 0)
            move = direction.normalize()
            current = (self.enemy.position - self.player.position).length()
            if current < desired:
                self.player.velocity = move * self.player.speed
            else:
                self.player.velocity = move.rotate(90) * self.player.speed * 0.3
        elif action == Action.EVADE:
            threat_vec = self.aggregate_threat_vector()
            if threat_vec.length() > 0:
                self.player.velocity = threat_vec.normalize() * self.player.speed
            else:
                self.player.velocity = pygame.math.Vector2(0, self.player.speed)
        elif action == Action.STEP:
            threat_vec = self.aggregate_threat_vector()
            direction = threat_vec.normalize() if threat_vec.length() > 0 else pygame.math.Vector2(0, -1)
            self.player.step(direction)
        elif action == Action.SPECIAL:
            to_add = self.player.use_special()
        if to_add:
            self.player_bullets.extend(to_add)

    def calculate_threat_level(self) -> float:
        radius = 64
        count = 0
        for bullet in self.enemy_bullets:
            if (bullet.position - self.player.position).length_squared() <= radius ** 2:
                count += 1
        return min(1.0, count / 10)

    def aggregate_threat_vector(self) -> pygame.math.Vector2:
        vec = pygame.math.Vector2(0, 0)
        radius = 160
        for bullet in self.enemy_bullets:
            offset = bullet.position - self.player.position
            dist = offset.length()
            if dist < radius and dist > 0:
                vec -= offset / dist
        return vec

    def update_bullets(self, dt: float) -> None:
        for bullet in self.player_bullets:
            bullet.update(dt)
        for bullet in self.enemy_bullets:
            bullet.update(dt)
        self.player_bullets = [b for b in self.player_bullets if -20 <= b.position.x <= WIDTH + 20 and b.position.y > -40]
        self.enemy_bullets = [b for b in self.enemy_bullets if -40 <= b.position.x <= WIDTH + 40 and b.position.y < HEIGHT + 60]


    def handle_collisions(self) -> None:
        enemy_rect = self.enemy.rect()
        for bullet in list(self.player_bullets):
            if enemy_rect.collidepoint(bullet.position):
                self.enemy.take_damage(bullet.damage)
                self.player_bullets.remove(bullet)
        player_rect = self.player.rect()
        for bullet in list(self.enemy_bullets):
            if player_rect.collidepoint(bullet.position):
                self.player.take_damage(bullet.damage)
                self.enemy_bullets.remove(bullet)

    def draw(self) -> None:
        self.screen.fill((10, 12, 20))
        pygame.draw.rect(self.screen, (50, 180, 255), self.player.rect(), border_radius=12)
        pygame.draw.rect(self.screen, (255, 80, 80), self.enemy.rect(), border_radius=18)

        for bullet in self.player_bullets:
            pygame.draw.circle(self.screen, (220, 220, 255), bullet.position, bullet.radius)
        for bullet in self.enemy_bullets:
            pygame.draw.circle(self.screen, (255, 200, 90), bullet.position, bullet.radius)

        self.draw_ui()
        pygame.display.flip()

    def draw_ui(self) -> None:
        stats = self.player.stats
        bars = [
            ("HP", stats.hp, stats.max_hp, (200, 60, 60)),
            ("EN", stats.energy, stats.max_energy, (80, 200, 200)),
            ("HT", stats.heat, stats.max_heat, (220, 150, 70)),
            ("SP", stats.special, stats.max_special, (120, 80, 220)),
        ]
        for i, (label, value, maximum, color) in enumerate(bars):
            x = 20
            y = HEIGHT - 150 + i * 28
            pygame.draw.rect(self.screen, (40, 40, 40), (x, y, 200, 18))
            width = int(200 * (value / maximum)) if maximum > 0 else 0
            pygame.draw.rect(self.screen, color, (x, y, width, 18))
            text = self.font.render(f"{label}: {value:5.1f}/{maximum:5.1f}", True, (230, 230, 230))
            self.screen.blit(text, (x + 210, y - 4))

        info_lines = [
            "[Q]バランス [W]突撃 [E]回避 [R]集中射撃 [T]必殺優先",
            "[1]猪突 [2]慎重 [3]臆病 / ESCで終了",
            f"指示: {self.input_state.instruction}  性格: {self.ai.personality.value}",
            f"ボスHP: {self.enemy.hp:5.0f}",
        ]
        for i, line in enumerate(info_lines):
            text = self.font.render(line, True, (240, 240, 240))
            self.screen.blit(text, (20, 20 + i * 22))


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
