"""Chess-piece and flag icons shared by compact desktop controls."""
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QIcon, QImage, QPixmap, QPainter, QColor, QPen, QPolygonF
from otb_chess.graphics.board_2d import flat_piece_image


def promotion_icon(game, piece_type, color):
    style = game.flat_piece_set if game.board_mode == "2D" else "textbook"
    spec = game.piece_sets[game.piece_set]
    material = spec.white if color else spec.black
    image = flat_piece_image(style, piece_type, material, color)
    rgba = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGBA8888).copy()
    return QIcon(QPixmap.fromImage(rgba))


def flag_icon(background=None):
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor("#409cff") if background is not None and QColor(background).lightness() < 16 else QColor("black")
    painter.setPen(QPen(color, 4))
    painter.drawLine(19, 12, 19, 53)
    painter.setBrush(color)
    painter.drawPolygon(QPolygonF([QPointF(21, 14), QPointF(49, 14), QPointF(43, 24),
                                  QPointF(49, 34), QPointF(21, 34)]))
    painter.end()
    return QIcon(pixmap)


def clock_engine_label(game, color):
    manager = game.engine_manager
    if manager.engine is None or game.engine_side_var.get() != ("White" if color else "Black"):
        return ""
    config = manager.loaded_configuration or {}
    family = config.get("engine_id", "")
    name = {"maia": "Maia", "stockfish": "Stockfish", "rodent": "Rodent"}.get(family, config.get("name", "Engine"))
    if family == "maia":
        from otb_chess.services.difficulty import DIFFICULTIES
        preset = DIFFICULTIES.get(config.get("profile"))
        strength = preset.rating if preset and preset.engine == "maia" else config.get("settings", {}).get("model")
    else:
        strength = game.cfg.get("engine_elo")
    return f"{name} * {strength if strength is not None else 'Full'}"
