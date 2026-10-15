from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from backend.app.config import ALLOWED_HAZARDS, DEFAULT_REGIONS
from backend.app.services.climate import analyze_climate_hazard, get_default_regions, search_regions as search_region_lookup


@require_GET
def health(request):
    return JsonResponse({"status": "ok", "message": "Healthy"})


@require_GET
def default_regions(request):
    return JsonResponse({"regions": get_default_regions()})


@require_GET
def search_regions(request):
    query = request.GET.get('query', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({"regions": []})
    return JsonResponse({"regions": search_region_lookup(query)})


@require_GET
def analysis(request):
    region_name = request.GET.get('region_name', 'New Delhi')
    latitude_param = request.GET.get('latitude')
    longitude_param = request.GET.get('longitude')
    start_year = int(request.GET.get('start_year', 1990))
    end_year = int(request.GET.get('end_year', 2020))
    hazard = (request.GET.get('hazard', 'heatwave') or '').lower()

    if hazard not in ALLOWED_HAZARDS:
        return JsonResponse({"detail": f"Unsupported hazard type: {hazard}"}, status=400)

    if start_year > end_year:
        return JsonResponse({"detail": "start_year must be less than or equal to end_year"}, status=400)

    latitude = None
    longitude = None
    if latitude_param is not None and longitude_param is not None:
        try:
            latitude = float(latitude_param)
            longitude = float(longitude_param)
        except ValueError:
            return JsonResponse({"detail": "latitude and longitude must be valid numbers"}, status=400)

    if latitude is None or longitude is None:
        match = next((item for item in DEFAULT_REGIONS if item['name'].lower() == region_name.lower()), None)
        if not match:
            region_matches = search_region_lookup(region_name)
            if not region_matches:
                return JsonResponse({"detail": f"No region could be found for '{region_name}'"}, status=404)
            match = region_matches[0]
        latitude = match['latitude']
        longitude = match['longitude']

    result = analyze_climate_hazard(
        hazard=hazard,
        region_name=region_name,
        latitude=float(latitude),
        longitude=float(longitude),
        start_year=start_year,
        end_year=end_year,
    )
    return JsonResponse(result)
