# Copyright (C) 2026 nork79
# SPDX-License-Identifier: GPL-3.0-only
"""Independent internal chess vocabulary and rules boundary."""

from .board import Board
from .move import Move
from .piece import Piece

__all__ = ['Board', 'Move', 'Piece']
