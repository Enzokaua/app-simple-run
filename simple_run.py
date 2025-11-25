import pygame
import random
import sys
from typing import List

FPS = 60
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700
GROUND_Y = WINDOW_HEIGHT - 50
UNIT = 8
PLAYER_UNITS_W = 3   
PLAYER_UNITS_H = 10
PLAYER_W = PLAYER_UNITS_W * UNIT
PLAYER_H = PLAYER_UNITS_H * UNIT
GRAVITY = 0.8
JUMP_VELOCITY = -14
OBSTACLE_MIN_GAP = 300
OBSTACLE_MAX_GAP = 600
OBSTACLE_SPEED_START = 6
OBSTACLE_ACCEL = 0.02
JUMP_ANIMATION_TIME = 0.8

class GameWeights:
    def __init__(self):
        self.down_lock_time = 0.1
        self.gravity = GRAVITY
        self.auto_jump_distance = 140
    def adjust_weights(self, death_condition):
        if death_condition == "ground":
            self.down_lock_time = max(0.05, self.down_lock_time * 0.9)
        elif death_condition == "air":
            self.gravity = min(1.2, self.gravity * 1.1)
        elif death_condition == "early_jump":
            self.auto_jump_distance = max(100, self.auto_jump_distance * 1.05)
            self.gravity = min(1.2, self.gravity * 1.05)
        elif death_condition == "late_jump":
            self.auto_jump_distance = min(180, self.auto_jump_distance * 0.95)
            self.gravity = max(0.5, self.gravity * 0.95)
            self.down_lock_time = max(0.05, self.down_lock_time * 0.9)

def init_screen() -> pygame.Surface:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("SimpleRun")
    return screen
def draw_screen(screen: pygame.Surface, player_rect: pygame.Rect, obstacles: List[pygame.Rect], score: int):
    screen.fill((235, 235, 235))
    pygame.draw.rect(screen, (80, 80, 80), (0, GROUND_Y, WINDOW_WIDTH, WINDOW_HEIGHT - GROUND_Y))
    pygame.draw.rect(screen, (20, 20, 20), player_rect)
    for obs in obstacles:
        pygame.draw.rect(screen, (120, 20, 20), obs)
    font = pygame.font.SysFont("Arial", 20)
    score_surf = font.render(f"Points score: {score}", True, (0, 0, 0))
    screen.blit(score_surf, (10, 10))
    pygame.display.flip()

class Player:
    def __init__(self, x: int, y: int, weights: GameWeights):
        self.rect = pygame.Rect(x, y - PLAYER_H, PLAYER_W, PLAYER_H)
        self.vel_y = 0.0
        self.on_ground = True
        self.weights = weights
        self.auto_jump_distance = weights.auto_jump_distance
        self.down_lock_time = 0
        self.last_obstacle_id = None
        self.last_death_condition = None
    def analyze_death_condition(self, obstacle):
        if self.on_ground:
            return "ground"
        else:
            distance = obstacle.x - self.rect.right
            if distance < 50:
                return "late_jump"
            elif distance > 200:
                return "early_jump"
            else:
                return "air"
    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False
    def obstacle_verify(self, obstacles, obstacle_speed):
        for obs in obstacles:
            if obs.x > self.rect.x:
                distance = obs.x - self.rect.right
                if 0 < distance <= self.auto_jump_distance and self.on_ground:
                    self.jump()
                    self.last_obstacle_id = id(obs)
                if not self.on_ground and self.last_obstacle_id != id(obs):
                    min_distance, max_distance = self.calculate_dynamic_range(obstacle_speed)
                    
                    if min_distance < distance < max_distance:
                        if self.will_collide_if_continues(obs, obstacle_speed, distance):
                            self.force_down()
                            self.last_obstacle_id = id(obs)
                            break
                break
    def calculate_dynamic_range(self, obstacle_speed):
        distance_during_jump = obstacle_speed * JUMP_ANIMATION_TIME
        min_distance = distance_during_jump * 0.4
        max_distance = distance_during_jump * 0.9
        min_distance = max(min_distance, 80)
        max_distance = max(max_distance, 200)
        return min_distance, max_distance
    def will_collide_if_continues(self, obstacle, obstacle_speed, distancia):
        colision_time = distancia / obstacle_speed
        future_y = self.predict_future_position(colision_time)
        will_be_in_air = future_y < GROUND_Y - 10
        return will_be_in_air
    def predict_future_position(self, time):
        future_y = self.rect.y + self.vel_y * time + 0.5 * self.weights.gravity * time * time
        return future_y
    def update(self, obstacles, obstacle_speed, dt):
        if self.down_lock_time > 0:
            self.down_lock_time -= dt / 1000
            return            
        if self.on_ground:
            self.obstacle_verify(obstacles, obstacle_speed) 
        else:
            self.obstacle_verify(obstacles, obstacle_speed)
        self.vel_y += self.weights.gravity
        self.rect.y += int(self.vel_y)
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vel_y = 0
            self.on_ground = True
            self.last_obstacle_id = None
    def force_down(self):
        if not self.on_ground:
            self.rect.bottom = GROUND_Y
            self.vel_y = 0
            self.on_ground = True
            self.down_lock_time = self.weights.down_lock_time

class ObstacleManager:
    def __init__(self):
        self.obstacles: List[pygame.Rect] = []
        self.next_spawn_x = WINDOW_WIDTH + random.randint(OBSTACLE_MIN_GAP, OBSTACLE_MAX_GAP)
        self.speed = OBSTACLE_SPEED_START
        self.distance_travelled = 0.01
    def spawn_obstacle(self):
        height_units = random.choice([3, 4, 5, 6]) 
        width_units = random.choice([3, 4, 6])      
        w = width_units * UNIT
        h = height_units * UNIT
        x = WINDOW_WIDTH + 10
        y = GROUND_Y - h
        rect = pygame.Rect(x, y, w, h)
        self.obstacles.append(rect)
        self.next_spawn_x = x + random.randint(OBSTACLE_MIN_GAP, OBSTACLE_MAX_GAP)
    def update(self):
        for o in self.obstacles:
            o.x -= int(self.speed)
        self.obstacles = [o for o in self.obstacles if o.right > 0]
        if not self.obstacles:
            self.spawn_obstacle()
        else:
            last = max(self.obstacles, key=lambda r: r.x)
            if last.x < WINDOW_WIDTH - random.randint(OBSTACLE_MIN_GAP, OBSTACLE_MAX_GAP):
                self.spawn_obstacle()
        self.distance_travelled += self.speed
        self.speed += OBSTACLE_ACCEL
    def reset(self):
        self.obstacles.clear()
        self.next_spawn_x = WINDOW_WIDTH + random.randint(OBSTACLE_MIN_GAP, OBSTACLE_MAX_GAP)
        self.speed = OBSTACLE_SPEED_START
        self.distance_travelled = 0.0
    def clear(self):
        self.obstacles.clear()

def main():
    screen = init_screen()
    clock = pygame.time.Clock()
    game_weights = GameWeights()
    player = Player(80, GROUND_Y, game_weights)
    obstacles = ObstacleManager()
    score = 0
    running = True
    game_over = False
    death_obstacle = None
    while running:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                    if game_over:
                        player = Player(80, GROUND_Y, game_weights)
                        obstacles.reset()
                        score = 0
                        game_over = False
                        death_obstacle = None
                    else:
                        player.jump()
                elif event.key == pygame.K_DOWN:
                    player.force_down()                        
        if not game_over:
            player.update(obstacles.obstacles, obstacles.speed, dt)
            obstacles.update()
            for obs in obstacles.obstacles:
                if player.rect.colliderect(obs):
                    death_obstacle = obs
                    game_over = True
                    death_condition = player.analyze_death_condition(death_obstacle)
                    game_weights.adjust_weights(death_condition)
                    break
            score += int(obstacles.speed * 0.5)
        draw_screen(screen, player.rect, obstacles.obstacles, score)
        if game_over:
            print("Latest points: ", score, ". Readjusting taking action ...")
            obstacles.reset()
            score = 0
            game_over = False
            death_obstacle = None
            pygame.time.delay(300)
            continue
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()