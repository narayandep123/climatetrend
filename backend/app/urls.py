from django.urls import path

from .views import analysis, default_regions, health, search_regions

urlpatterns = [
    path('', health, name='health-root'),
    path('api/health', health, name='health-no-slash'),
    path('api/health/', health, name='health'),
    path('api/default-regions', default_regions, name='default-regions-no-slash'),
    path('api/default-regions/', default_regions, name='default-regions'),
    path('api/search-regions', search_regions, name='search-regions-no-slash'),
    path('api/search-regions/', search_regions, name='search-regions'),
    path('api/analysis', analysis, name='analysis-no-slash'),
    path('api/analysis/', analysis, name='analysis'),
]
