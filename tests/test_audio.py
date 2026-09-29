"""Short clips and fast replies must reach output without truncation."""
import array
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from otb_chess.services import audio
from otb_chess.services.wave_audio import Mixer, SoundPlayer, read_clip


class SoundPlaybackTests(unittest.TestCase):
    def test_reply_overlaps_without_truncating_first_move(self):
        mixer = Mixer()
        mixer.play([1000] * 8)
        self.assertEqual(array.array('h', mixer.render(3)).tolist(), [1000] * 3)
        mixer.play([2000] * 2)
        self.assertEqual(array.array('h', mixer.render(5)).tolist(), [3000, 3000, 1000, 1000, 1000])
        self.assertEqual(array.array('h', mixer.render(2)).tolist(), [0, 0])

    def test_each_remaining_profile_reaches_mixer_unchanged_on_both_moves(self):
        self.assertNotIn('02_Crisp_Chesscom_Like', audio.SOUND_PROFILES)
        for profile in audio.SOUND_PROFILES:
            for event, path in audio.ensure_sounds(profile).items():
                with self.subTest(profile=profile, event=event):
                    samples = read_clip(path)
                    self.assertGreater(max(map(abs, samples)), 1000)
                    mixer = Mixer()
                    mixer.play(samples)
                    self.assertEqual(mixer.render(len(samples)), samples.tobytes())
                    mixer.play(samples)
                    self.assertEqual(mixer.render(len(samples)), samples.tobytes())

    def test_mixing_clamps_overflow_and_mute_clears_pending_samples(self):
        mixer = Mixer()
        mixer.play([30000, -30000, 100])
        mixer.play([30000, -30000, 100])
        self.assertEqual(array.array('h', mixer.render(2)).tolist(), [32767, -32768])
        mixer.clear()
        self.assertEqual(array.array('h', mixer.render(2)).tolist(), [0, 0])

    def test_play_does_not_wait_for_output_device_and_uses_one_worker(self):
        entered, release = threading.Event(), threading.Event()
        device = Mock()
        def open_device():
            entered.set()
            release.wait(2)
            return device
        player = SoundPlayer(open_device)
        try:
            with patch('otb_chess.services.wave_audio.read_clip', return_value=[100, 200]):
                player.play(Path('white.wav'))
                self.assertTrue(entered.wait(1))
                worker = player.thread
                player.play(Path('black.wav'))
                self.assertIs(worker, player.thread)
                self.assertEqual(len(player.mixer.voices), 2)
        finally:
            release.set()
            player.close()
        device.close.assert_called_once()

    def test_output_device_failure_is_reported_without_interrupting_moves(self):
        player = SoundPlayer(Mock(side_effect=OSError('No audio device')))
        with self.assertLogs('otb_chess.services.wave_audio', level='WARNING'):
            player.start()
            player.thread.join(1)
        self.assertIn('No audio device', player.error)
        player.close()

    def test_missing_file_is_reported_without_interrupting_moves(self):
        with patch.object(audio, '_player', Mock(play=Mock(side_effect=OSError('Missing WAV')))):
            with self.assertLogs(audio.__name__, level='WARNING'):
                audio.play_sound(Path('missing.wav'))

    def test_missing_windows_backend_is_harmless(self):
        with patch.object(audio, '_player', None):
            audio.play_sound(Path('move.wav'))
            audio.prepare_sounds(audio.DEFAULT_SOUND_PROFILE)
            audio.stop_sounds()

    def test_removed_profile_falls_back_to_audible_default(self):
        self.assertEqual(audio.ensure_sounds('02_Crisp_Chesscom_Like'), audio.ensure_sounds())
