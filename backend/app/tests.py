import json
from unittest.mock import patch

import requests
from django.test import RequestFactory, SimpleTestCase

from backend.app.services.climate import fetch_daily_temperature_series
from backend.app.views import analysis


class ClimateServiceGracefulFallbackTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('backend.app.services.climate.requests.get', side_effect=requests.RequestException('upstream failed'))
    def test_temperature_fetch_returns_empty_when_upstream_fails(self, _mock_get):
        self.assertEqual(fetch_daily_temperature_series(28.6139, 77.209, 2020, 2020), [])

    def test_analysis_view_returns_json_error_when_source_is_unavailable(self):
        request = self.factory.get('/api/analysis', {
            'region_name': 'New Delhi',
            'latitude': '28.6139',
            'longitude': '77.2090',
            'start_year': '2020',
            'end_year': '2020',
            'hazard': 'heatwave',
        })

        with patch('backend.app.views.analyze_climate_hazard', side_effect=RuntimeError('source unavailable')):
            response = analysis(request)

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertIn('detail', payload)
