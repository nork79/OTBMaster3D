"""Defaults and validation for editable PGN identity fields."""
from datetime import date
import re

FIELDS = ('Event', 'Site', 'Date', 'White', 'Black', 'Round')


def defaults(game, *, include_ratings=False):
    cfg = getattr(game, 'cfg', {})
    player = cfg.get('player_name', '') or '?'
    fields = dict(Event='Casual game', Site='?', Date=date.today().strftime('%Y.%m.%d'),
                  White=player, Black='?', Round='?')
    manager = getattr(game, 'engine_manager', None)
    side = getattr(game, 'engine_side', None)
    if side is not None and getattr(game, 'engine_enabled', True) and manager and manager.engine is not None:
        config = getattr(manager, 'loaded_configuration', None)
        config = config if isinstance(config, dict) else {}
        identity = getattr(manager.engine, 'id', {})
        identity = identity if isinstance(identity, dict) else {}
        name = identity.get('name') or config.get('name') or config.get('engine_id') or 'Engine'
        rating = cfg.get('engine_elo')
        color = 'White' if side else 'Black'
        strength = f'{rating} Elo' if rating is not None else 'Full strength'
        if config.get('engine_id') == 'stockfish':
            from otb_chess.services.difficulty import DIFFICULTIES
            preset = DIFFICULTIES.get(config.get('profile'))
            if preset and preset.skill is not None:
                strength = f'Practice skill {preset.skill}/20; uncalibrated'
                rating = None
        fields[color] = f'{name} ({strength})'
        if include_ratings and rating is not None:
            fields[color + 'Elo'] = str(rating)
        fields['Black' if side else 'White'] = player
    return fields


def validate(fields):
    cleaned = {}
    for key in FIELDS:
        value = fields.get(key, '').strip() or ('????.??.??' if key == 'Date' else '?')
        if any(ord(c) < 32 for c in value) or '"' in value or '\\' in value:
            raise ValueError(f'{key} cannot contain quotes, backslashes or control characters.')
        cleaned[key] = value
    value = cleaned['Date']
    if not re.fullmatch(r'(\d{4}|\?{4})\.(\d{2}|\?{2})\.(\d{2}|\?{2})', value):
        raise ValueError('Use YYYY.MM.DD for Date, or ? for unknown parts (e.g. 2026.??.??).')
    year, month, day = value.split('.')
    try:
        date(int(year) if year.isdigit() else 2000,
             int(month) if month.isdigit() else 1,
             int(day) if day.isdigit() else 1)
    except ValueError:
        raise ValueError('Date is not a valid calendar date.') from None
    return cleaned
