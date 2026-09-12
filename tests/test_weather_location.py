import io
import json
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from pi_environment_panel.config import WeatherConfig
from pi_environment_panel.models import GPSReading
from pi_environment_panel.collectors.weather import collect

DATA = {'current': {'temperature_2m': 22, 'weather_code': 0},
        'daily': {'temperature_2m_min': [15], 'temperature_2m_max': [25]},
        'hourly': {'precipitation_probability': [10, 30]}}


class WeatherLocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg=WeatherConfig(enabled=True, location_source='gps')
        self.fix=GPSReading(ok=True, latitude=-33.85, longitude=151.2)

    def response(self, *args, **kwargs):
        return io.BytesIO(json.dumps(DATA).encode())

    def test_no_fix_never_fetches_zero_zero(self):
        with patch('urllib.request.urlopen') as fetch:
            result=collect(self.cfg, self.tmp.name, GPSReading(error='GPS waiting for fix'))
            self.assertFalse(result.ok)
            fetch.assert_not_called()

    def test_gps_coordinates_used_cache_invalidated_on_move(self):
        with patch('urllib.request.urlopen', side_effect=self.response) as fetch:
            self.assertTrue(collect(self.cfg,self.tmp.name,self.fix).ok)
            query=parse_qs(urlparse(fetch.call_args.args[0].full_url).query)
            self.assertEqual(query['latitude'], ['-33.85'])
            self.assertEqual(query['longitude'], ['151.2'])
            self.assertTrue(collect(self.cfg,self.tmp.name,self.fix).ok)
            self.assertEqual(fetch.call_count, 1)
            moved=GPSReading(ok=True, latitude=-34.0, longitude=151.2)
            self.assertTrue(collect(self.cfg,self.tmp.name,moved).ok)
            self.assertEqual(fetch.call_count,2)

    def test_no_fix_does_not_use_previous_weather(self):
        with patch('urllib.request.urlopen',side_effect=self.response):
            collect(self.cfg,self.tmp.name,self.fix)
        self.assertFalse(collect(self.cfg,self.tmp.name,GPSReading()).ok)

    def test_stale_cache_only_same_location_within_bound(self):
        with patch('urllib.request.urlopen',side_effect=self.response):
            collect(self.cfg,self.tmp.name,self.fix)
        self.cfg.cache_seconds=0
        with patch('urllib.request.urlopen',side_effect=OSError('offline')):
            result=collect(self.cfg,self.tmp.name,self.fix)
            self.assertTrue(result.ok)
            self.assertTrue(result.stale)
            moved=GPSReading(ok=True,latitude=40,longitude=20)
            self.assertFalse(collect(self.cfg,self.tmp.name,moved).ok)
            self.cfg.max_stale_seconds=0
            self.assertFalse(collect(self.cfg,self.tmp.name,self.fix).ok)
