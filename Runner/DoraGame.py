import pygame
from sys import exit
import os

pygame.init()
screen = pygame.display.set_mode((800, 400))
pygame.display.set_caption('Runner')
clock = pygame.time.Clock()
test_font = pygame.font.Font(None, 35)

script_dir = os.path.dirname(__file__)

skyImage_path = os.path.join(script_dir, 'Graphics', 'Sky.png')
groundImage_path = os.path.join(script_dir, 'Graphics', 'ground.png')
snail_path = os.path.join(script_dir, 'Graphics', 'Snail', 'snail1.png')

ground_surface = pygame.image.load(groundImage_path)
sky_surface = pygame.image.load(skyImage_path)
text_surface = test_font.render('test', True, 'purple')
snail_surface = pygame.image.load(snail_path)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    screen.blit(sky_surface, (0, 0))
    screen.blit(ground_surface, (0, 300))
    screen.blit(text_surface, (210, 0))
    screen.blit(snail_surface, (600, 250))

    pygame.display.update()
    clock.tick(60)
