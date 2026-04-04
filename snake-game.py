import json
import math
import random
from array import array
from pathlib import Path

import pygame


WINDOW_WIDTH = 980
WINDOW_HEIGHT = 760
MIN_WINDOW_SIZE = (620, 620)
GRID_COLUMNS = 20
GRID_ROWS = 20
FPS = 60

DIFFICULTIES = {
    "Easy": {"move_delay": 180, "accent": (74, 222, 128)},
    "Medium": {"move_delay": 135, "accent": (96, 165, 250)},
    "Hard": {"move_delay": 95, "accent": (251, 146, 60)},
}

BACKGROUND_COLOR = (16, 24, 32)
PANEL_COLOR = (24, 36, 48)
CARD_COLOR = (28, 43, 58)
GRID_DARK = (33, 48, 62)
GRID_LIGHT = (38, 57, 73)
SNAKE_HEAD = (52, 211, 153)
SNAKE_BODY = (16, 185, 129)
FOOD_COLOR = (248, 113, 113)
TEXT_COLOR = (241, 245, 249)
MUTED_TEXT = (148, 163, 184)
WARNING_COLOR = (251, 191, 36)
OVERLAY_COLOR = (0, 0, 0, 130)

HIGH_SCORE_FILE = Path(__file__).with_name("snake_high_scores.json")
SOUND_SAMPLE_RATE = 44100


pygame.mixer.pre_init(SOUND_SAMPLE_RATE, -16, 1, 512)
pygame.init()
pygame.display.set_caption("Snake Game")
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
clock = pygame.time.Clock()

title_font = pygame.font.SysFont("segoeui", 50, bold=True)
subtitle_font = pygame.font.SysFont("segoeui", 30, bold=True)
hud_font = pygame.font.SysFont("segoeui", 28, bold=True)
small_font = pygame.font.SysFont("segoeui", 22)


def load_high_scores() -> dict[str, int]:
    default_scores = {name: 0 for name in DIFFICULTIES}
    if not HIGH_SCORE_FILE.exists():
        return default_scores

    try:
        data = json.loads(HIGH_SCORE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_scores

    for difficulty in DIFFICULTIES:
        value = data.get(difficulty, 0)
        default_scores[difficulty] = value if isinstance(value, int) and value >= 0 else 0
    return default_scores


def save_high_scores(high_scores: dict[str, int]) -> None:
    try:
        HIGH_SCORE_FILE.write_text(json.dumps(high_scores, indent=2), encoding="utf-8")
    except OSError:
        pass


def build_tone(frequency: int, duration_ms: int, volume: float = 0.35) -> pygame.mixer.Sound | None:
    if not pygame.mixer.get_init():
        return None

    sample_count = int(SOUND_SAMPLE_RATE * duration_ms / 1000)
    samples = array("h")
    amplitude = int(32767 * max(0.0, min(volume, 1.0)))

    for sample_index in range(sample_count):
        envelope = 1 - (sample_index / max(1, sample_count)) * 0.35
        sample_value = int(amplitude * envelope * math.sin(2 * math.pi * frequency * sample_index / SOUND_SAMPLE_RATE))
        samples.append(sample_value)

    try:
        return pygame.mixer.Sound(buffer=samples.tobytes())
    except pygame.error:
        return None


def create_sound_bank() -> dict[str, pygame.mixer.Sound | None]:
    return {
        "select": build_tone(720, 70, 0.25),
        "start": build_tone(560, 150, 0.3),
        "eat": build_tone(900, 90, 0.28),
        "pause": build_tone(420, 110, 0.22),
        "game_over": build_tone(240, 360, 0.35),
        "record": build_tone(1040, 140, 0.3),
    }


def play_sound(name: str) -> None:
    sound = sound_bank.get(name)
    if sound_enabled and sound is not None:
        sound.play()


def compute_board(surface: pygame.Surface) -> tuple[pygame.Rect, int]:
    width, height = surface.get_size()
    board_size = max(320, min(width - 90, height - 220))
    cell_size = max(12, board_size // GRID_COLUMNS)
    board_size = cell_size * GRID_COLUMNS
    board_x = (width - board_size) // 2
    board_y = 130 + max(0, (height - 220 - board_size) // 2)
    return pygame.Rect(board_x, board_y, board_size, board_size), cell_size


def draw_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    center: tuple[int, int],
) -> None:
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)


def spawn_food(snake: list[tuple[int, int]]) -> tuple[int, int]:
    available_positions = [
        (x, y)
        for x in range(GRID_COLUMNS)
        for y in range(GRID_ROWS)
        if (x, y) not in snake
    ]
    return random.choice(available_positions)


def reset_game() -> tuple[list[tuple[int, int]], tuple[int, int], tuple[int, int], tuple[int, int], int]:
    snake = [(10, 10), (9, 10), (8, 10)]
    direction = (1, 0)
    next_direction = direction
    food = spawn_food(snake)
    score = 0
    return snake, direction, next_direction, food, score


def is_opposite(direction: tuple[int, int], next_direction: tuple[int, int]) -> bool:
    return direction[0] == -next_direction[0] and direction[1] == -next_direction[1]


def update_high_score(difficulty: str, score: int) -> bool:
    if score > high_scores[difficulty]:
        high_scores[difficulty] = score
        save_high_scores(high_scores)
        return True
    return False


def start_new_game() -> None:
    global snake, direction, next_direction, food, score, game_state, last_move_time, current_difficulty

    current_difficulty = difficulty_names[selected_difficulty_index]
    snake, direction, next_direction, food, score = reset_game()
    game_state = "playing"
    last_move_time = pygame.time.get_ticks()
    play_sound("start")


def draw_start_screen(surface: pygame.Surface, selected_name: str) -> tuple[dict[str, pygame.Rect], pygame.Rect]:
    surface.fill(BACKGROUND_COLOR)

    width, height = surface.get_size()
    draw_text(surface, "Snake Game", title_font, TEXT_COLOR, (width // 2, 88))
    draw_text(surface, "Choose a difficulty and press Enter to play", small_font, MUTED_TEXT, (width // 2, 126))

    card_width = min(220, width - 80)
    card_height = 115
    card_gap = 18
    total_height = len(difficulty_names) * card_height + (len(difficulty_names) - 1) * card_gap
    top = max(180, (height - total_height) // 2 - 20)

    option_rects: dict[str, pygame.Rect] = {}

    for index, difficulty_name in enumerate(difficulty_names):
        card_rect = pygame.Rect((width - card_width) // 2, top + index * (card_height + card_gap), card_width, card_height)
        is_selected = difficulty_name == selected_name
        accent = DIFFICULTIES[difficulty_name]["accent"]
        fill_color = accent if is_selected else CARD_COLOR
        border_color = TEXT_COLOR if is_selected else GRID_LIGHT

        pygame.draw.rect(surface, fill_color, card_rect, border_radius=20)
        pygame.draw.rect(surface, border_color, card_rect, width=2, border_radius=20)
        draw_text(surface, difficulty_name, subtitle_font, TEXT_COLOR, (card_rect.centerx, card_rect.y + 34))

        speed_label = f"Speed: {1000 // DIFFICULTIES[difficulty_name]['move_delay']} tiles/sec"
        best_label = f"Best score: {high_scores[difficulty_name]}"
        draw_text(surface, speed_label, small_font, TEXT_COLOR, (card_rect.centerx, card_rect.y + 68))
        draw_text(surface, best_label, small_font, MUTED_TEXT, (card_rect.centerx, card_rect.y + 92))
        option_rects[difficulty_name] = card_rect

    start_button = pygame.Rect((width - 220) // 2, top + total_height + 36, 220, 58)
    pygame.draw.rect(surface, PANEL_COLOR, start_button, border_radius=18)
    pygame.draw.rect(surface, TEXT_COLOR, start_button, width=2, border_radius=18)
    draw_text(surface, "Start Game", subtitle_font, TEXT_COLOR, start_button.center)

    instructions = [
        "↑/↓ or W/S: choose difficulty",
        "Enter / Space: start game",
        "M: toggle sound",
    ]
    for index, message in enumerate(instructions):
        draw_text(surface, message, small_font, MUTED_TEXT, (width // 2, height - 96 + index * 24))

    sound_label = "Sound: ON" if sound_enabled else "Sound: OFF"
    draw_text(surface, sound_label, small_font, WARNING_COLOR if sound_enabled else FOOD_COLOR, (width - 90, 34))
    return option_rects, start_button


def draw_game(
    surface: pygame.Surface,
    snake: list[tuple[int, int]],
    food: tuple[int, int],
    score: int,
    best_score: int,
    state: str,
    difficulty: str,
) -> None:
    surface.fill(BACKGROUND_COLOR)
    board_rect, cell_size = compute_board(surface)
    accent = DIFFICULTIES[difficulty]["accent"]

    header_rect = pygame.Rect(0, 0, surface.get_width(), 105)
    pygame.draw.rect(surface, PANEL_COLOR, header_rect)
    draw_text(surface, "Snake", title_font, TEXT_COLOR, (110, 52))

    difficulty_text = small_font.render(f"Difficulty: {difficulty}", True, accent)
    score_text = hud_font.render(f"Score: {score}", True, TEXT_COLOR)
    best_text = small_font.render(f"Best: {best_score}", True, TEXT_COLOR)
    sound_text = small_font.render(f"Sound: {'ON' if sound_enabled else 'OFF'}", True, WARNING_COLOR if sound_enabled else FOOD_COLOR)

    surface.blit(difficulty_text, (26, 74))
    surface.blit(score_text, (surface.get_width() - score_text.get_width() - 24, 18))
    surface.blit(best_text, (surface.get_width() - best_text.get_width() - 24, 50))
    surface.blit(sound_text, (surface.get_width() - sound_text.get_width() - 24, 78))

    pygame.draw.rect(surface, PANEL_COLOR, board_rect.inflate(18, 18), border_radius=16)
    pygame.draw.rect(surface, GRID_DARK, board_rect, border_radius=14)

    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            cell_rect = pygame.Rect(
                board_rect.x + column * cell_size,
                board_rect.y + row * cell_size,
                cell_size,
                cell_size,
            )
            color = GRID_LIGHT if (row + column) % 2 == 0 else GRID_DARK
            pygame.draw.rect(surface, color, cell_rect)

    food_rect = pygame.Rect(
        board_rect.x + food[0] * cell_size + 3,
        board_rect.y + food[1] * cell_size + 3,
        cell_size - 6,
        cell_size - 6,
    )
    pygame.draw.ellipse(surface, FOOD_COLOR, food_rect)

    for index, segment in enumerate(snake):
        segment_rect = pygame.Rect(
            board_rect.x + segment[0] * cell_size + 2,
            board_rect.y + segment[1] * cell_size + 2,
            cell_size - 4,
            cell_size - 4,
        )
        segment_color = SNAKE_HEAD if index == 0 else SNAKE_BODY
        pygame.draw.rect(surface, segment_color, segment_rect, border_radius=8)

    controls_text = "Move: Arrow Keys / WASD   •   P: Pause   •   R: Restart   •   Esc: Menu   •   M: Sound"
    draw_text(surface, controls_text, small_font, TEXT_COLOR, (surface.get_width() // 2, surface.get_height() - 30))

    if state in {"paused", "game_over"}:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))

        if state == "paused":
            draw_text(surface, "Paused", title_font, WARNING_COLOR, (surface.get_width() // 2, surface.get_height() // 2 - 24))
            draw_text(surface, "Press P to continue", small_font, TEXT_COLOR, (surface.get_width() // 2, surface.get_height() // 2 + 18))
        else:
            draw_text(surface, "Game Over", title_font, FOOD_COLOR, (surface.get_width() // 2, surface.get_height() // 2 - 50))
            draw_text(surface, f"Final Score: {score}", hud_font, TEXT_COLOR, (surface.get_width() // 2, surface.get_height() // 2 - 2))
            draw_text(surface, f"Best {difficulty}: {best_score}", small_font, accent, (surface.get_width() // 2, surface.get_height() // 2 + 34))
            draw_text(surface, "Press R / Enter to replay or Esc for menu", small_font, TEXT_COLOR, (surface.get_width() // 2, surface.get_height() // 2 + 68))


high_scores = load_high_scores()
save_high_scores(high_scores)
difficulty_names = list(DIFFICULTIES)
selected_difficulty_index = 1
current_difficulty = difficulty_names[selected_difficulty_index]
sound_enabled = True
sound_bank = create_sound_bank()

snake, direction, next_direction, food, score = reset_game()
game_state = "start"
last_move_time = pygame.time.get_ticks()
running = True

direction_map = {
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
}

menu_option_rects: dict[str, pygame.Rect] = {}
menu_start_rect = pygame.Rect(0, 0, 0, 0)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            new_width = max(event.w, MIN_WINDOW_SIZE[0])
            new_height = max(event.h, MIN_WINDOW_SIZE[1])
            screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game_state == "start":
            for index, difficulty_name in enumerate(difficulty_names):
                if menu_option_rects.get(difficulty_name, pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                    selected_difficulty_index = index
                    play_sound("select")
                    break
            if menu_start_rect.collidepoint(event.pos):
                start_new_game()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                sound_enabled = not sound_enabled
                if sound_enabled:
                    play_sound("select")

            if game_state == "start":
                if event.key in {pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a}:
                    selected_difficulty_index = (selected_difficulty_index - 1) % len(difficulty_names)
                    play_sound("select")
                elif event.key in {pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d}:
                    selected_difficulty_index = (selected_difficulty_index + 1) % len(difficulty_names)
                    play_sound("select")
                elif event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                    start_new_game()

            elif game_state in {"playing", "paused", "game_over"}:
                if event.key == pygame.K_ESCAPE:
                    game_state = "start"
                    play_sound("select")

                elif event.key == pygame.K_r:
                    snake, direction, next_direction, food, score = reset_game()
                    game_state = "playing"
                    last_move_time = pygame.time.get_ticks()
                    play_sound("start")

                elif event.key in {pygame.K_RETURN, pygame.K_SPACE} and game_state == "game_over":
                    snake, direction, next_direction, food, score = reset_game()
                    game_state = "playing"
                    last_move_time = pygame.time.get_ticks()
                    play_sound("start")

                elif event.key == pygame.K_p and game_state in {"playing", "paused"}:
                    game_state = "paused" if game_state == "playing" else "playing"
                    play_sound("pause")

                elif event.key in direction_map and game_state == "playing":
                    proposed_direction = direction_map[event.key]
                    if not is_opposite(direction, proposed_direction):
                        next_direction = proposed_direction

    if game_state == "playing":
        base_delay = DIFFICULTIES[current_difficulty]["move_delay"]
        move_delay = max(60, base_delay - score * 3)
        current_time = pygame.time.get_ticks()

        if current_time - last_move_time >= move_delay:
            last_move_time = current_time
            direction = next_direction

            new_head = (snake[0][0] + direction[0], snake[0][1] + direction[1])
            hit_wall = not (0 <= new_head[0] < GRID_COLUMNS and 0 <= new_head[1] < GRID_ROWS)
            hit_self = new_head in snake[:-1]

            if hit_wall or hit_self:
                game_state = "game_over"
                if update_high_score(current_difficulty, score):
                    play_sound("record")
                play_sound("game_over")
            else:
                snake.insert(0, new_head)
                if new_head == food:
                    score += 1
                    play_sound("eat")
                    if update_high_score(current_difficulty, score):
                        play_sound("record")
                    if len(snake) == GRID_COLUMNS * GRID_ROWS:
                        game_state = "game_over"
                    else:
                        food = spawn_food(snake)
                else:
                    snake.pop()

    if game_state == "start":
        menu_option_rects, menu_start_rect = draw_start_screen(screen, difficulty_names[selected_difficulty_index])
    else:
        draw_game(
            screen,
            snake,
            food,
            score,
            high_scores[current_difficulty],
            game_state,
            current_difficulty,
        )

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()


