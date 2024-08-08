import pygame
import os
import random

pygame.init()

# Constants for screen size and colors
WIDTH, HEIGHT = 900, 500
RED = (255, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)

# Initialize the screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Load images
enemy_image_path = os.path.join('Assets', 'terror.png')
background_image_path = os.path.join('Assets', 'dust.png')
enemy_image = pygame.image.load(enemy_image_path).convert_alpha()
background_image = pygame.image.load(background_image_path).convert()

# Scale enemy image to the specified size
enemy_width, enemy_height = 200, 100  # Smaller size
enemy_image = pygame.transform.scale(enemy_image, (enemy_width, enemy_height))

# Predefined spawn points (x, y)
spawn_points = [(100, 350), (190, 300), (300, 350), (400, 250), (500, 300)]

# Font for displaying score
font = pygame.font.SysFont(None, 36)

class Game:
    def __init__(self):
        self.objects = []
        self.score = 0

    def spawn_object(self):
        # Choose a random spawn point
        x, y = random.choice(spawn_points)
        self.objects.append(Enemy(x, y, enemy_width, enemy_height, enemy_image))

    def update(self):
        # No need to update position since enemies are static
        pass

    def check_collisions(self, crosshair):
        for obj in self.objects[:]:
            if crosshair.get_rect().colliderect(obj.get_rect()):
                self.objects.remove(obj)
                self.score += 1
                print("Collision! Score:", self.score)

    def draw_score(self, WIN):
        score_text = font.render(f'Score: {self.score}', True, GREEN)
        WIN.blit(score_text, (10, 20))

class Enemy:
    def __init__(self, x, y, width, height, image):
        self.rect = pygame.Rect(x, y, width, height)
        self.image = image

    def draw(self, WIN):
        WIN.blit(self.image, (self.rect.x, self.rect.y))

    def get_rect(self):
        return self.rect

class Crosshair:
    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT / 2

    def draw(self, screen):
        # Draw the crosshair
        pygame.draw.line(screen, RED, (self.x - 30, self.y), (self.x + 30, self.y), 4)
        pygame.draw.line(screen, RED, (self.x, self.y - 30), (self.x, self.y + 30), 4)

    def get_rect(self):
        return pygame.Rect(self.x - 10, self.y - 10, 20, 20)

game = Game()
crosshair = Crosshair()

running = True
spawn_timer = 0
spawn_delay = 2000  # Spawn delay in milliseconds

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check for collisions when the mouse is clicked
            game.check_collisions(crosshair)

    # Update the crosshair position to the mouse position
    crosshair.x, crosshair.y = pygame.mouse.get_pos()

    # Spawn new objects with a certain delay
    if pygame.time.get_ticks() - spawn_timer > spawn_delay:
        game.spawn_object()
        spawn_timer = pygame.time.get_ticks()

    game.update()

    # Draw everything
    screen.blit(background_image, (0, 0))  # Draw the background
    for obj in game.objects:
        obj.draw(screen)

    crosshair.draw(screen)
    game.draw_score(screen)

    pygame.display.flip()

    clock.tick(60)

pygame.quit()
