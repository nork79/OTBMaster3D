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
    color = QColor("black") if background is not None and QColor(background).lightness() >= 240 else QColor("white")
    painter.setPen(QPen(color, 4))
    painter.drawLine(19, 12, 19, 53)
    painter.setBrush(color)
    painter.drawPolygon(QPolygonF([QPointF(21, 14), QPointF(49, 14), QPointF(43, 24),
                                  QPointF(49, 34), QPointF(21, 34)]))
    painter.end()
    return QIcon(pixmap)


def engine_icon(enabled, color):
    """A microchip crossed out when the engine is off."""
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(color, 3))
    painter.drawRoundedRect(12, 12, 24, 24, 3, 3)
    painter.drawRect(19, 19, 10, 10)
    for offset in (17, 24, 31):
        painter.drawLine(offset, 6, offset, 12)
        painter.drawLine(offset, 36, offset, 42)
        painter.drawLine(6, offset, 12, offset)
        painter.drawLine(36, offset, 42, offset)
    if not enabled:
        painter.setPen(QPen(QColor('#e36d65'), 4))
        painter.drawLine(7, 7, 41, 41)
        painter.drawLine(41, 7, 7, 41)
    painter.end()
    return QIcon(pixmap)


def clock_engine_label(game, color):
    manager = game.engine_manager
    if not getattr(game, "engine_enabled", True) or manager.engine is None or game.engine_side_var.get() != ("White" if color else "Black"):
        return ""
    config = manager.loaded_configuration or {}
    family = config.get("engine_id", "")
    name = {"fairy-stockfish": "Fairy-Stockfish", "stockfish": "Stockfish", "rodent": "Rodent"}.get(family, config.get("name", "Engine"))
    strength = game.cfg.get("engine_elo")
    if family == "rodent":
        from otb_chess.services.personalities import PERSONALITIES
        key = config.get("settings", {}).get("rodent", {}).get("personality", "default")
        label = PERSONALITIES.get(key, (key, ""))[0].split(" — ")[0]
        return f"{label} · {'~' + str(strength) if strength is not None else 'Full'}"
    return f"{name} * {strength if strength is not None else 'Full'}"
