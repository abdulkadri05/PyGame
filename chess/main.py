# Two-player chess in Python with Pygame.
#
# This file is intentionally written with a lot of comments.
# The goal is not only to make the game run, but also to make the logic readable
# while you are learning how a chess program is put together.

# Python 3.9 needs this so type hints like tuple[int, int] | None do not run
# as normal code at startup.
from __future__ import annotations

from dataclasses import dataclass

try:
    import pygame
except ImportError:
    raise SystemExit("Pygame is required to run this game.")


# ---------------------------------------------------------------------------
# Basic pygame setup
# ---------------------------------------------------------------------------

# Pygame needs to be initialized before we create windows, load fonts, or read
# events from the keyboard/mouse.
pygame.init()

# A chess board has 8 columns and 8 rows. In this program, each square is
# 100 pixels wide and 100 pixels tall.
BOARD_SIZE = 8
SQUARE_SIZE = 100

# The playable board is 800x800. The window is 1000x900 because we reserve:
# - 200 pixels on the right for captured pieces and game information
# - 100 pixels at the bottom for turn/status text
BOARD_PIXELS = BOARD_SIZE * SQUARE_SIZE
SIDE_PANEL_WIDTH = 200
BOTTOM_PANEL_HEIGHT = 100
WIDTH = BOARD_PIXELS + SIDE_PANEL_WIDTH
HEIGHT = BOARD_PIXELS + BOTTOM_PANEL_HEIGHT

# Create the game window. Everything we draw goes onto this `screen` surface.
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess 2-Player-Game")

# SysFont asks the operating system for a font. This is safer than Font("Arial"),
# because Font("Arial") tries to load a local file literally named "Arial".
font = pygame.font.SysFont("Arial", 22)
small_font = pygame.font.SysFont("Arial", 18)
big_font = pygame.font.SysFont("Arial", 42)

# The clock lets us limit the game loop to a steady frame rate.
clock = pygame.time.Clock()
FPS = 60


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

# Board coordinates are stored as (column, row).
# (0, 0) is the top-left square.
# (7, 7) is the bottom-right square.
#
# This board is drawn with white pieces starting at the top and moving downward.
# That is opposite from many chess diagrams, but it matches the starter code.
WHITE = "white"
BLACK = "black"

# Pawns move in different directions depending on color.
# White starts near row 1 and moves toward row 7.
# Black starts near row 6 and moves toward row 0.
PAWN_DIRECTIONS = {
    WHITE: 1,
    BLACK: -1,
}

# Pawns are allowed to move two squares only from their starting row.
PAWN_START_ROWS = {
    WHITE: 1,
    BLACK: 6,
}

# When a pawn reaches this row, it promotes.
PROMOTION_ROWS = {
    WHITE: 7,
    BLACK: 0,
}

# The pieces are listed in the same order as their images.
PIECE_TYPES = ["pawn", "queen", "king", "knight", "rook", "bishop"]

# The promotion menu allows the player to choose one of these pieces.
PROMOTION_CHOICES = ["queen", "rook", "bishop", "knight"]


@dataclass
class Move:
    """A single legal move.

    A normal move only needs `piece_index`, `start`, and `end`.

    Captures use `capture_square`. Most captures happen on the destination
    square, but en passant captures a pawn on a different square, so keeping
    this separate makes that special rule easier to handle.

    Castling moves also move a rook. For those moves, `rook_start` and
    `rook_end` tell us where the rook should move.
    """

    piece_index: int
    start: tuple[int, int]
    end: tuple[int, int]
    capture_square: tuple[int, int] | None = None
    rook_start: tuple[int, int] | None = None
    rook_end: tuple[int, int] | None = None
    promotion: bool = False
    en_passant: bool = False


# These global lists are the current game state.
#
# The piece at white_pieces[i] is located at white_locations[i].
# Its "has moved?" flag is stored at white_moved[i].
#
# Keeping the three lists aligned by index is important:
# index 0 in all three lists describes the same piece.
white_pieces = []
white_locations = []
white_moved = []
black_pieces = []
black_locations = []
black_moved = []

# Captured pieces are stored as names so we can draw them in the side panel.
captured_white_pieces = []
captured_black_pieces = []

# `current_turn` tells us whose move it is.
current_turn = WHITE

# `selected_index` is the index of the selected piece in the current player's
# piece list. None means no piece is selected.
selected_index = None

# Once a piece is selected, `legal_moves` stores where that piece may move.
legal_moves = []

# En passant only exists for one move immediately after a pawn moves two
# squares. This variable stores the square where an en passant capture may land.
en_passant_target = None

# If a pawn reaches the end of the board, we pause normal moving and show a
# promotion menu until the player chooses a new piece.
promotion_pending = None

# This becomes "checkmate" or "stalemate" when the game ends.
game_result = None


# ---------------------------------------------------------------------------
# Asset loading
# ---------------------------------------------------------------------------


def load_piece_images():
    """Load and scale all chess piece images.

    Pygame image loading returns a Surface. A Surface is basically an image
    that can be drawn onto the screen with screen.blit(...).
    """

    images = {WHITE: {}, BLACK: {}}
    small_images = {WHITE: {}, BLACK: {}}

    for color in (WHITE, BLACK):
        for piece in PIECE_TYPES:
            # Example path: assets/white queen.png
            path = f"assets/{color} {piece}.png"

            # Load the original image from disk.
            image = pygame.image.load(path)

            # Pawns are slightly smaller than the other pieces in your assets,
            # so we keep them at 65x65 and use 80x80 for the rest.
            board_size = (65, 65) if piece == "pawn" else (80, 80)

            # Store one image for the board and one smaller image for the
            # captured-piece list in the side panel.
            images[color][piece] = pygame.transform.scale(image, board_size)
            small_images[color][piece] = pygame.transform.scale(image, (36, 36))

    return images, small_images


piece_images, small_piece_images = load_piece_images()


# ---------------------------------------------------------------------------
# Game setup helpers
# ---------------------------------------------------------------------------


def reset_game():
    """Put every piece back in the starting position."""

    global white_pieces, white_locations, white_moved
    global black_pieces, black_locations, black_moved
    global captured_white_pieces, captured_black_pieces
    global current_turn, selected_index, legal_moves
    global en_passant_target, promotion_pending, game_result

    # Standard chess order from left to right is:
    # rook, knight, bishop, queen, king, bishop, knight, rook.
    back_row = ["rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook"]
    pawns = ["pawn"] * 8

    white_pieces = back_row[:] + pawns[:]
    white_locations = [(col, 0) for col in range(8)] + [(col, 1) for col in range(8)]
    white_moved = [False] * len(white_pieces)

    black_pieces = back_row[:] + pawns[:]
    black_locations = [(col, 7) for col in range(8)] + [(col, 6) for col in range(8)]
    black_moved = [False] * len(black_pieces)

    captured_white_pieces = []
    captured_black_pieces = []

    current_turn = WHITE
    selected_index = None
    legal_moves = []
    en_passant_target = None
    promotion_pending = None
    game_result = None


def make_state_copy():
    """Create a copy of the board state for move simulation.

    Chess move validation often asks: "If I make this move, will my king be in
    check?" To answer that safely, we copy the board, try the move on the copy,
    and inspect the result without changing the real game.
    """

    return {
        WHITE: {
            "pieces": white_pieces[:],
            "locations": white_locations[:],
            "moved": white_moved[:],
        },
        BLACK: {
            "pieces": black_pieces[:],
            "locations": black_locations[:],
            "moved": black_moved[:],
        },
        "en_passant_target": en_passant_target,
    }


def other_color(color):
    """Return the opponent color."""

    return BLACK if color == WHITE else WHITE


def current_lists(color):
    """Return the real piece/location/moved lists for a color."""

    if color == WHITE:
        return white_pieces, white_locations, white_moved
    return black_pieces, black_locations, black_moved


def in_bounds(square):
    """Return True if a square is inside the 8x8 board."""

    col, row = square
    return 0 <= col < BOARD_SIZE and 0 <= row < BOARD_SIZE


def piece_at(state, square, color=None):
    """Find the piece on a square.

    Returns a tuple: (piece_color, piece_index)
    Returns None if the square is empty.

    If `color` is passed, only that color's pieces are searched.
    """

    colors = [color] if color else [WHITE, BLACK]

    for piece_color in colors:
        locations = state[piece_color]["locations"]
        if square in locations:
            return piece_color, locations.index(square)

    return None


# ---------------------------------------------------------------------------
# Move generation
# ---------------------------------------------------------------------------


def sliding_moves(state, color, index, directions):
    """Generate moves for bishops, rooks, and queens.

    These pieces move in straight lines until they hit:
    - the edge of the board
    - one of their own pieces
    - an enemy piece, which they may capture
    """

    moves = []
    enemy = other_color(color)
    start = state[color]["locations"][index]

    for col_step, row_step in directions:
        col = start[0] + col_step
        row = start[1] + row_step

        while in_bounds((col, row)):
            square = (col, row)

            # Friendly pieces block movement.
            if piece_at(state, square, color):
                break

            # Enemy pieces can be captured, but movement stops there.
            if piece_at(state, square, enemy):
                moves.append(Move(index, start, square, capture_square=square))
                break

            # Empty square: this is a normal move, and the piece can keep going.
            moves.append(Move(index, start, square))
            col += col_step
            row += row_step

    return moves


def pawn_moves(state, color, index, attacks_only=False):
    """Generate pawn moves.

    Pawns are special:
    - They move forward into empty squares.
    - They capture diagonally.
    - They can move two squares from their starting row.
    - They can capture en passant after an enemy pawn moves two squares.
    - They promote when they reach the last row.

    `attacks_only=True` is used when checking whether a king is under attack.
    In that case, we only care about the diagonal capture squares.
    """

    moves = []
    enemy = other_color(color)
    start = state[color]["locations"][index]
    direction = PAWN_DIRECTIONS[color]

    # Pawns attack diagonally forward-left and forward-right.
    attack_squares = [
        (start[0] - 1, start[1] + direction),
        (start[0] + 1, start[1] + direction),
    ]

    for square in attack_squares:
        if not in_bounds(square):
            continue

        # When asking "what squares does this pawn attack?", the answer is the
        # diagonal squares whether or not an enemy is currently there.
        if attacks_only:
            moves.append(Move(index, start, square))
            continue

        # Normal diagonal capture.
        if piece_at(state, square, enemy):
            moves.append(Move(index, start, square, capture_square=square,
                              promotion=square[1] == PROMOTION_ROWS[color]))

        # En passant capture. The pawn lands on en_passant_target but captures
        # the pawn sitting one row behind that target square.
        if square == state["en_passant_target"]:
            captured_square = (square[0], start[1])
            if piece_at(state, captured_square, enemy):
                moves.append(Move(index, start, square, capture_square=captured_square,
                                  promotion=square[1] == PROMOTION_ROWS[color],
                                  en_passant=True))

    # Attack checks stop here because pawns do not attack straight forward.
    if attacks_only:
        return moves

    # One-square forward move.
    one_forward = (start[0], start[1] + direction)
    if in_bounds(one_forward) and not piece_at(state, one_forward):
        moves.append(Move(index, start, one_forward,
                          promotion=one_forward[1] == PROMOTION_ROWS[color]))

        # Two-square forward move from the starting row.
        two_forward = (start[0], start[1] + direction * 2)
        if start[1] == PAWN_START_ROWS[color] and not piece_at(state, two_forward):
            moves.append(Move(index, start, two_forward))

    return moves


def knight_moves(state, color, index):
    """Generate knight moves.

    Knights move in an L shape and can jump over other pieces.
    """

    moves = []
    enemy = other_color(color)
    start = state[color]["locations"][index]

    offsets = [
        (1, 2), (2, 1), (2, -1), (1, -2),
        (-1, -2), (-2, -1), (-2, 1), (-1, 2),
    ]

    for col_step, row_step in offsets:
        square = (start[0] + col_step, start[1] + row_step)
        if not in_bounds(square):
            continue

        # A knight can move to an empty square or capture an enemy.
        if not piece_at(state, square, color):
            capture_square = square if piece_at(state, square, enemy) else None
            moves.append(Move(index, start, square, capture_square=capture_square))

    return moves


def king_moves(state, color, index, attacks_only=False):
    """Generate king moves, including castling when allowed."""

    moves = []
    enemy = other_color(color)
    start = state[color]["locations"][index]

    # The king may move one square in any direction.
    for col_step in (-1, 0, 1):
        for row_step in (-1, 0, 1):
            if col_step == 0 and row_step == 0:
                continue

            square = (start[0] + col_step, start[1] + row_step)
            if not in_bounds(square):
                continue

            if not piece_at(state, square, color):
                capture_square = square if piece_at(state, square, enemy) else None
                moves.append(Move(index, start, square, capture_square=capture_square))

    # When checking attacked squares, do not include castling. Castling is not
    # an attack; it is only a special king move.
    if attacks_only:
        return moves

    moves.extend(castling_moves(state, color, index))
    return moves


def castling_moves(state, color, king_index):
    """Generate legal castling moves before king-safety filtering.

    Castling is allowed only if:
    - The king has not moved.
    - The rook has not moved.
    - Squares between the king and rook are empty.
    - The king is not currently in check.
    - The king does not pass through an attacked square.
    """

    moves = []
    row = 0 if color == WHITE else 7
    enemy = other_color(color)
    king_start = state[color]["locations"][king_index]

    if state[color]["pieces"][king_index] != "king":
        return moves
    if state[color]["moved"][king_index]:
        return moves
    if king_in_check(state, color):
        return moves

    # Each tuple means:
    # rook column, king destination column, rook destination column,
    # empty squares between king and rook, squares the king passes through.
    castle_data = [
        (7, 6, 5, [(5, row), (6, row)], [(5, row), (6, row)]),
        (0, 2, 3, [(1, row), (2, row), (3, row)], [(3, row), (2, row)]),
    ]

    for rook_col, king_end_col, rook_end_col, empty_squares, king_path in castle_data:
        rook_square = (rook_col, row)
        rook_info = piece_at(state, rook_square, color)

        if rook_info is None:
            continue

        rook_index = rook_info[1]
        if state[color]["pieces"][rook_index] != "rook":
            continue
        if state[color]["moved"][rook_index]:
            continue
        if any(piece_at(state, square) for square in empty_squares):
            continue
        if any(is_square_attacked(state, square, enemy) for square in king_path):
            continue

        moves.append(Move(king_index, king_start, (king_end_col, row),
                          rook_start=rook_square, rook_end=(rook_end_col, row)))

    return moves


def pseudo_moves_for_piece(state, color, index, attacks_only=False):
    """Generate moves for a piece without checking whether its king is safe.

    These are called "pseudo-legal" moves. They follow the piece movement rules,
    but a later step removes moves that would leave your own king in check.
    """

    piece = state[color]["pieces"][index]

    if piece == "pawn":
        return pawn_moves(state, color, index, attacks_only)
    if piece == "knight":
        return knight_moves(state, color, index)
    if piece == "bishop":
        return sliding_moves(state, color, index, [(1, 1), (1, -1), (-1, 1), (-1, -1)])
    if piece == "rook":
        return sliding_moves(state, color, index, [(1, 0), (-1, 0), (0, 1), (0, -1)])
    if piece == "queen":
        return sliding_moves(state, color, index, [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ])
    if piece == "king":
        return king_moves(state, color, index, attacks_only)

    return []


def is_square_attacked(state, square, by_color):
    """Return True if `by_color` attacks `square`."""

    for index in range(len(state[by_color]["pieces"])):
        for move in pseudo_moves_for_piece(state, by_color, index, attacks_only=True):
            if move.end == square:
                return True
    return False


def king_in_check(state, color):
    """Return True if the given color's king is currently attacked."""

    pieces = state[color]["pieces"]
    locations = state[color]["locations"]

    # If the king is missing, the board is invalid. This should not happen in
    # normal play because kings are never captured; checkmate ends the game.
    if "king" not in pieces:
        return True

    king_square = locations[pieces.index("king")]
    return is_square_attacked(state, king_square, other_color(color))


def apply_move_to_state(state, color, move):
    """Apply a move to a copied state.

    This is used for simulation while checking if a move is legal.
    It does not touch the real global game state.
    """

    enemy = other_color(color)

    # Remove captured enemy piece first.
    if move.capture_square is not None:
        capture_info = piece_at(state, move.capture_square, enemy)
        if capture_info is not None:
            capture_index = capture_info[1]
            state[enemy]["pieces"].pop(capture_index)
            state[enemy]["locations"].pop(capture_index)
            state[enemy]["moved"].pop(capture_index)

    # Move the selected piece.
    state[color]["locations"][move.piece_index] = move.end
    state[color]["moved"][move.piece_index] = True

    # In simulations, promote pawns to queens. The exact promotion choice does
    # not matter for king safety; queen is the strongest simple assumption.
    if move.promotion:
        state[color]["pieces"][move.piece_index] = "queen"

    # If this is castling, move the rook too.
    if move.rook_start and move.rook_end:
        rook_info = piece_at(state, move.rook_start, color)
        if rook_info is not None:
            rook_index = rook_info[1]
            state[color]["locations"][rook_index] = move.rook_end
            state[color]["moved"][rook_index] = True

    # Update en passant availability in the copied state.
    state["en_passant_target"] = None
    moved_piece = state[color]["pieces"][move.piece_index]
    if moved_piece == "pawn" and abs(move.end[1] - move.start[1]) == 2:
        middle_row = (move.start[1] + move.end[1]) // 2
        state["en_passant_target"] = (move.start[0], middle_row)


def legal_moves_for_piece(state, color, index):
    """Return only moves that do not leave the moving side's king in check."""

    legal = []

    for move in pseudo_moves_for_piece(state, color, index):
        test_state = {
            WHITE: {
                "pieces": state[WHITE]["pieces"][:],
                "locations": state[WHITE]["locations"][:],
                "moved": state[WHITE]["moved"][:],
            },
            BLACK: {
                "pieces": state[BLACK]["pieces"][:],
                "locations": state[BLACK]["locations"][:],
                "moved": state[BLACK]["moved"][:],
            },
            "en_passant_target": state["en_passant_target"],
        }

        apply_move_to_state(test_state, color, move)

        # A legal move is one where your own king is safe afterward.
        if not king_in_check(test_state, color):
            legal.append(move)

    return legal


def all_legal_moves(state, color):
    """Return every legal move for one side."""

    moves = []
    for index in range(len(state[color]["pieces"])):
        moves.extend(legal_moves_for_piece(state, color, index))
    return moves


# ---------------------------------------------------------------------------
# Real game-state changes
# ---------------------------------------------------------------------------


def apply_real_move(move):
    """Apply a chosen legal move to the real game."""

    global en_passant_target, promotion_pending

    pieces, locations, moved = current_lists(current_turn)
    enemy = other_color(current_turn)
    enemy_pieces, enemy_locations, enemy_moved = current_lists(enemy)

    # Capture an enemy piece if this move has a capture square.
    if move.capture_square is not None and move.capture_square in enemy_locations:
        capture_index = enemy_locations.index(move.capture_square)
        captured_piece = enemy_pieces.pop(capture_index)
        enemy_locations.pop(capture_index)
        enemy_moved.pop(capture_index)

        if enemy == WHITE:
            captured_white_pieces.append(captured_piece)
        else:
            captured_black_pieces.append(captured_piece)

    # Move the selected piece.
    locations[move.piece_index] = move.end
    moved[move.piece_index] = True

    # Move the rook too if this is a castling move.
    if move.rook_start and move.rook_end:
        rook_index = locations.index(move.rook_start)
        locations[rook_index] = move.rook_end
        moved[rook_index] = True

    # En passant is available only immediately after a pawn moves two squares.
    en_passant_target = None
    if pieces[move.piece_index] == "pawn" and abs(move.end[1] - move.start[1]) == 2:
        middle_row = (move.start[1] + move.end[1]) // 2
        en_passant_target = (move.start[0], middle_row)

    # If a pawn reaches the far side, pause the turn and ask what to promote to.
    if move.promotion:
        promotion_pending = {
            "color": current_turn,
            "piece_index": move.piece_index,
        }


def finish_turn():
    """Switch turns and update checkmate/stalemate status."""

    global current_turn, selected_index, legal_moves, game_result

    current_turn = other_color(current_turn)
    selected_index = None
    legal_moves = []

    state = make_state_copy()
    available_moves = all_legal_moves(state, current_turn)

    if not available_moves:
        if king_in_check(state, current_turn):
            game_result = f"Checkmate! {other_color(current_turn).title()} wins."
        else:
            game_result = "Stalemate! Draw."


def choose_promotion(piece_name):
    """Replace the promoted pawn with the chosen piece."""

    global promotion_pending

    color = promotion_pending["color"]
    piece_index = promotion_pending["piece_index"]
    pieces, _, _ = current_lists(color)
    pieces[piece_index] = piece_name
    promotion_pending = None
    finish_turn()


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def board_to_pixels(square):
    """Convert a board coordinate like (4, 2) into pixel coordinates."""

    return square[0] * SQUARE_SIZE, square[1] * SQUARE_SIZE


def draw_board():
    """Draw the board, panels, grid lines, and status message."""

    # Draw the light squares first by filling the board area.
    pygame.draw.rect(screen, "light gray", [0, 0, BOARD_PIXELS, BOARD_PIXELS])

    # Draw the 32 dark squares.
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if (row + col) % 2 == 1:
                pygame.draw.rect(screen, "dim gray",
                                 [col * SQUARE_SIZE, row * SQUARE_SIZE,
                                  SQUARE_SIZE, SQUARE_SIZE])

    # Bottom panel for messages.
    pygame.draw.rect(screen, "gray", [0, BOARD_PIXELS, WIDTH, BOTTOM_PANEL_HEIGHT])
    pygame.draw.rect(screen, "gold", [0, BOARD_PIXELS, WIDTH, BOTTOM_PANEL_HEIGHT], 5)

    # Right panel for captured pieces and game info.
    pygame.draw.rect(screen, "gray25", [BOARD_PIXELS, 0, SIDE_PANEL_WIDTH, HEIGHT])
    pygame.draw.rect(screen, "gray", [BOARD_PIXELS, 0, SIDE_PANEL_WIDTH, HEIGHT], 5)

    # Draw grid lines on top of the squares.
    for i in range(BOARD_SIZE + 1):
        pygame.draw.line(screen, "black", (0, i * SQUARE_SIZE), (BOARD_PIXELS, i * SQUARE_SIZE), 3)
        pygame.draw.line(screen, "black", (i * SQUARE_SIZE, 0), (i * SQUARE_SIZE, BOARD_PIXELS), 3)

    # If the current king is in check, highlight its square.
    state = make_state_copy()
    if not game_result and king_in_check(state, current_turn):
        pieces, locations, _ = current_lists(current_turn)
        king_square = locations[pieces.index("king")]
        x, y = board_to_pixels(king_square)
        pygame.draw.rect(screen, "orange red", [x + 4, y + 4, SQUARE_SIZE - 8, SQUARE_SIZE - 8], 5)

    # Status text at the bottom.
    if game_result:
        message = f"{game_result} Press R to restart."
    elif promotion_pending:
        message = "Choose a promotion piece on the right."
    elif selected_index is None:
        message = f"{current_turn.title()}: select a piece."
    else:
        message = f"{current_turn.title()}: select a destination."

    screen.blit(big_font.render(message, True, "black"), (20, BOARD_PIXELS + 25))


def draw_pieces():
    """Draw every active piece on the board."""

    for color in (WHITE, BLACK):
        pieces, locations, _ = current_lists(color)

        for index, piece in enumerate(pieces):
            x, y = board_to_pixels(locations[index])

            # Pawns are 65x65, other pieces are 80x80, so the offsets center
            # the images inside a 100x100 square.
            offset = 18 if piece == "pawn" else 10
            screen.blit(piece_images[color][piece], (x + offset, y + offset))

            # Draw a red outline around the currently selected piece.
            if color == current_turn and selected_index == index:
                pygame.draw.rect(screen, "red", [x + 2, y + 2, SQUARE_SIZE - 4, SQUARE_SIZE - 4], 4)


def draw_legal_moves():
    """Draw green circles on squares the selected piece can move to."""

    for move in legal_moves:
        x, y = board_to_pixels(move.end)
        center = (x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2)
        pygame.draw.circle(screen, "spring green", center, 14)
        pygame.draw.circle(screen, "dark green", center, 14, 3)


def draw_captured_pieces():
    """Draw captured pieces in the right panel."""

    screen.blit(font.render("Captured", True, "white"), (825, 20))
    screen.blit(small_font.render("White pieces", True, "white"), (820, 60))

    for index, piece in enumerate(captured_white_pieces):
        x = 820 + (index % 4) * 42
        y = 90 + (index // 4) * 42
        screen.blit(small_piece_images[WHITE][piece], (x, y))

    screen.blit(small_font.render("Black pieces", True, "white"), (820, 260))

    for index, piece in enumerate(captured_black_pieces):
        x = 820 + (index % 4) * 42
        y = 290 + (index // 4) * 42
        screen.blit(small_piece_images[BLACK][piece], (x, y))

    screen.blit(small_font.render("R: restart", True, "white"), (820, 730))
    screen.blit(small_font.render("Esc: quit", True, "white"), (820, 760))


def draw_promotion_menu():
    """Draw promotion choices when a pawn reaches the end of the board."""

    if not promotion_pending:
        return

    color = promotion_pending["color"]
    screen.blit(font.render("Promote to:", True, "white"), (820, 430))

    for index, piece in enumerate(PROMOTION_CHOICES):
        y = 470 + index * 70
        pygame.draw.rect(screen, "white", [820, y, 160, 58], border_radius=6)
        pygame.draw.rect(screen, "black", [820, y, 160, 58], 2, border_radius=6)
        screen.blit(small_piece_images[color][piece], (830, y + 11))
        screen.blit(font.render(piece.title(), True, "black"), (875, y + 17))


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------


def board_square_from_mouse(pos):
    """Convert a mouse position into a board square, or None outside the board."""

    mouse_x, mouse_y = pos

    if mouse_x >= BOARD_PIXELS or mouse_y >= BOARD_PIXELS:
        return None

    return mouse_x // SQUARE_SIZE, mouse_y // SQUARE_SIZE


def handle_board_click(square):
    """Handle clicking on a board square."""

    global selected_index, legal_moves

    if game_result or promotion_pending:
        return

    pieces, locations, _ = current_lists(current_turn)
    state = make_state_copy()

    # Clicking your own piece selects it and calculates its legal moves.
    if square in locations:
        selected_index = locations.index(square)
        legal_moves = legal_moves_for_piece(state, current_turn, selected_index)
        return

    # If a piece is already selected, clicking a legal destination moves it.
    if selected_index is not None:
        for move in legal_moves:
            if move.end == square:
                apply_real_move(move)

                # If promotion is pending, wait for the player to choose the
                # new piece before switching turns.
                if not promotion_pending:
                    finish_turn()
                return

    # Clicking an empty illegal square clears the selection.
    selected_index = None
    legal_moves = []


def handle_promotion_click(pos):
    """Handle clicks inside the promotion menu."""

    if not promotion_pending:
        return

    mouse_x, mouse_y = pos

    if mouse_x < BOARD_PIXELS:
        return

    for index, piece in enumerate(PROMOTION_CHOICES):
        y = 470 + index * 70
        if 820 <= mouse_x <= 980 and y <= mouse_y <= y + 58:
            choose_promotion(piece)
            return


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

def main():
    """Start the game and keep running until the user quits."""

    # Start the first game after all functions exist.
    reset_game()

    running = True

    while running:
        # Keep the loop from running faster than 60 frames per second.
        clock.tick(FPS)

        # Clear the whole screen before drawing the next frame.
        screen.fill("darkgray")

        # Draw order matters: board first, move hints next, pieces on top, then UI.
        draw_board()
        draw_legal_moves()
        draw_pieces()
        draw_captured_pieces()
        draw_promotion_menu()

        # Read every pending event from pygame.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    reset_game()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_promotion_click(event.pos)
                clicked_square = board_square_from_mouse(event.pos)
                if clicked_square is not None:
                    handle_board_click(clicked_square)

        # Flip updates the visible window with everything drawn this frame.
        pygame.display.flip()

    # Shut down pygame cleanly after the window closes.
    pygame.quit()


# This means: only run the game loop when this file is executed directly.
# If another script imports main.py for testing, the game loop will not start.
if __name__ == "__main__":
    main()
