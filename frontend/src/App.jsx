import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { CalendarRange, Download, Flame, MapPin, TrendingUp } from 'lucide-react'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import './App.css'

const yearRange = Array.from({ length: 31 }, (_, index) => 1990 + index)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const buildApiUrl = (path) => `${API_BASE_URL}${path}`

const defaultMarkerIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
})

const hazardMeta = {
  heatwave: {
    label: 'Heatwave',
    unit: '°C',
    thresholdDescription: 'Local exceedance',
    tooltip: (region, threshold) => `Heatwave threshold for ${region}: ${threshold.toFixed(1)}°C, above which a day is treated as an extreme heat day.`,
  },
  drought: {
    label: 'Drought',
    unit: 'mm',
    thresholdDescription: 'Annual rainfall deficit',
    tooltip: (region, threshold) => `Drought threshold for ${region}: ${threshold.toFixed(1)} mm annual rainfall, below which a year is treated as a dry anomaly.`,
  },
  heavy_rainfall: {
    label: 'Heavy Rainfall',
    unit: 'mm',
    thresholdDescription: 'Extreme precipitation',
    tooltip: (region, threshold) => `Heavy rainfall threshold for ${region}: ${threshold.toFixed(1)} mm, above which a day is treated as an extreme wet event.`,
  },
}

function App() {
  const [regions, setRegions] = useState([])
  const [searchText, setSearchText] = useState('Delhi')
  const [selectedRegion, setSelectedRegion] = useState('New Delhi')
  const [latitude, setLatitude] = useState('28.6139')
  const [longitude, setLongitude] = useState('77.2090')
  const [startYear, setStartYear] = useState(1990)
  const [endYear, setEndYear] = useState(2020)
  const [hazard, setHazard] = useState('heatwave')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const mapCenter = useMemo(
    () => [Number(latitude) || 28.6139, Number(longitude) || 77.209],
    [latitude, longitude],
  )

  useEffect(() => {
    const bootstrapAnalysis = async () => {
      try {
        const response = await fetch(buildApiUrl('/api/default-regions'))
        const payload = await response.json()
        const nextRegions = payload.regions ?? []
        setRegions(nextRegions)

        const defaultRegion = nextRegions.find((region) => region.name === 'New Delhi') ?? nextRegions[0]
        if (!defaultRegion) return

        setSelectedRegion(defaultRegion.name)
        setSearchText(defaultRegion.name)
        setLatitude(String(defaultRegion.latitude))
        setLongitude(String(defaultRegion.longitude))
        await analyzeHazard(defaultRegion.name, defaultRegion.latitude, defaultRegion.longitude, 1990, 2020, hazard)
      } catch (loadError) {
        setError('The region catalog could not be loaded.')
        console.error(loadError)
      }
    }

    void bootstrapAnalysis()
  }, [])

  const analyzeHazard = async (
    regionName,
    latValue,
    lonValue,
    fromYear,
    toYear,
    selectedHazard,
  ) => {
    setLoading(true)
    setError('')

    try {
      const params = new URLSearchParams({
        region_name: regionName,
        latitude: String(latValue),
        longitude: String(lonValue),
        start_year: String(fromYear),
        end_year: String(toYear),
        hazard: selectedHazard,
      })

      const response = await fetch(buildApiUrl(`/api/analysis?${params.toString()}`))
      const payload = await response.json()

      if (!response.ok) {
        throw new Error(payload.detail || 'Unknown server error')
      }

      setResult(payload)
    } catch (analysisError) {
      setError(
        analysisError instanceof Error ? analysisError.message : 'Unable to analyze the selected region right now.',
      )
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchText.trim()) {
      return
    }

    try {
      const response = await fetch(buildApiUrl(`/api/search-regions?query=${encodeURIComponent(searchText)}`))
      const payload = await response.json()
      const nextRegions = payload.regions ?? []
      setRegions(nextRegions)
      if (nextRegions.length > 0) {
        const firstRegion = nextRegions[0]
        setSelectedRegion(firstRegion.name)
        setLatitude(String(firstRegion.latitude))
        setLongitude(String(firstRegion.longitude))
        await analyzeHazard(
          firstRegion.name,
          firstRegion.latitude,
          firstRegion.longitude,
          startYear,
          endYear,
          hazard,
        )
      }
    } catch (lookupError) {
      setError('Unable to load search results for the selected region.')
      console.error(lookupError)
    }
  }

  const selectRegion = async (region) => {
    setSelectedRegion(region.name)
    setLatitude(String(region.latitude))
    setLongitude(String(region.longitude))
    setSearchText(region.name)
    await analyzeHazard(region.name, region.latitude, region.longitude, startYear, endYear, hazard)
  }

  const handleExportCsv = () => {
    if (!result || !result.chart_data?.length) {
      return
    }

    const rows = [
      ['year', 'event_count', 'average_duration_days'],
      ...result.chart_data.map((row) => [String(row.year), String(row.event_count), String(row.average_duration_days)]),
    ]

    const csv = rows.map((row) => row.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${(result.region_name || 'region').replace(/\s+/g, '-').toLowerCase()}-${hazard}-trend.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  const summary = result?.summary
  const chartData = result?.chart_data ?? []
  const currentHazardMeta = hazardMeta[hazard]
  const thresholdUnit = currentHazardMeta.unit
  const riskIndex = summary
    ? Math.min(100, Math.max(20, Math.round(summary.total_event_count * 7 + Math.abs(summary.trend_per_decade) * 12 + summary.threshold_c * 3)))
    : 82
  const riskLevel = riskIndex >= 75 ? 'High' : riskIndex >= 45 ? 'Moderate' : 'Low'
  const riskTooltip = summary
    ? `Composite risk score based on total ${currentHazardMeta.label.toLowerCase()} events (${summary.total_event_count}), trend intensity (${summary.trend_per_decade.toFixed(2)} per decade), and threshold (${summary.threshold_c.toFixed(1)}${thresholdUnit}).`
    : `Composite risk score based on current ${currentHazardMeta.label.toLowerCase()} event count, trend intensity, and local threshold.`

  const analyzeCurrentSelection = async (nextHazard = hazard) => {
    await analyzeHazard(
      selectedRegion || searchText || 'New Delhi',
      Number(latitude),
      Number(longitude),
      startYear,
      endYear,
      nextHazard,
    )
  }

  return (
    <div className="app-shell">
      <header className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Climate Hazard Trend Analyzer</p>
          <h1>{currentHazardMeta.label} risk intelligence</h1>
          <p className="hero-subtitle">Track long-term climate stress with regional context, anomaly detection, and clear trend signals.</p>
        </div>
        <div className="hero-badges">
          <div className="hero-chip">
            <Flame size={16} />
            <select
              className="hazard-select"
              value={hazard}
              onChange={async (event) => {
                const nextHazard = event.target.value
                setHazard(nextHazard)
                await analyzeCurrentSelection(nextHazard)
              }}
            >
              {Object.entries(hazardMeta).map(([value, meta]) => (
                <option key={value} value={value}>
                  {meta.label}
                </option>
              ))}
            </select>
          </div>
          <div className="hero-chip subtle">
            <MapPin size={16} />
            {selectedRegion || 'Location'}
          </div>
          <div className="hero-chip status">
            <span className="status-dot" />
            Risk {riskLevel}
          </div>
        </div>
      </header>

      <section className="overview-strip">
        <div className="mini-metric emphasis has-tooltip">
          <span className="mini-label">Risk index</span>
          <strong>{riskIndex}</strong>
          <small>{riskLevel}</small>
          <span className="custom-tooltip top">{riskTooltip}</span>
        </div>
        <div className="mini-metric has-tooltip">
          <span className="mini-label">Study window</span>
          <strong>{startYear}-{endYear}</strong>
          <small>{summary ? `${summary.region_name}` : 'Selected region'}</small>
          <span className="custom-tooltip top">{`Selected analysis period from ${startYear} to ${endYear} for ${selectedRegion || 'the current region'}.`}</span>
        </div>
        <div className="mini-metric has-tooltip">
          <span className="mini-label">Event threshold</span>
          <strong>{summary ? `${summary.threshold_c.toFixed(1)}${thresholdUnit}` : '—'}</strong>
          <small>{currentHazardMeta.thresholdDescription}</small>
          <span className="custom-tooltip top">{summary ? currentHazardMeta.tooltip(summary.region_name, summary.threshold_c) : `Local ${currentHazardMeta.label.toLowerCase()} threshold used to identify hazardous conditions.`}</span>
        </div>
      </section>

      <section className="controls-panel">
        <div className="field-group field-wide">
          <label htmlFor="region-search">Region search</label>
          <div className="input-row">
            <input
              id="region-search"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Search city, state, or country"
            />
            <button type="button" className="secondary-button" onClick={handleSearch}>
              Search
            </button>
          </div>
        </div>

        <div className="field-group field-inline">
          <label htmlFor="start-year">Start year</label>
          <select id="start-year" value={startYear} onChange={(event) => setStartYear(Number(event.target.value))}>
            {yearRange.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        <div className="field-group field-inline">
          <label htmlFor="end-year">End year</label>
          <select id="end-year" value={endYear} onChange={(event) => setEndYear(Number(event.target.value))}>
            {yearRange.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>
      </section>

      <section className="map-panel">
        <div className="map-heading-row">
          <h2>Geographic view</h2>
          <button type="button" className="secondary-button" onClick={handleExportCsv} disabled={!result}>
            <Download size={16} />
            Export CSV
          </button>
        </div>

        <div className="map-wrapper">
          <MapContainer center={mapCenter} zoom={2} scrollWheelZoom className="map-container">
            <TileLayer
  attribution="Tiles &copy; Esri"
  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
/>

            {regions.map((region) => (
              <Marker
                key={`${region.name}-${region.latitude}-${region.longitude}`}
                position={[region.latitude, region.longitude]}
                icon={defaultMarkerIcon}
                eventHandlers={{
                  click: () => {
                    void selectRegion(region)
                  },
                }}
              >
                <Popup>
                  <strong>{region.name}</strong>
                  <br />
                  {region.country}
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </section>

      <div className="region-grid">
        {regions.map((region) => (
          <button
            key={`${region.name}-${region.latitude}-${region.longitude}`}
            type="button"
            className={`region-card ${selectedRegion === region.name ? 'active' : ''}`}
            onClick={() => {
              void selectRegion(region)
            }}
          >
            <MapPin size={14} />
            <span>{region.name}</span>
            <small>{region.country}</small>
          </button>
        ))}
      </div>

      <div className="manual-coordinates">
        <div className="field-group">
          <label htmlFor="lat">Latitude</label>
          <input id="lat" value={latitude} onChange={(event) => setLatitude(event.target.value)} />
        </div>
        <div className="field-group">
          <label htmlFor="lon">Longitude</label>
          <input id="lon" value={longitude} onChange={(event) => setLongitude(event.target.value)} />
        </div>
      </div>

      <div className="action-row">
        <button
          type="button"
          className="primary-button"
          onClick={() => {
            void analyzeCurrentSelection()
          }}
          disabled={loading}
        >
          {loading ? 'Analyzing…' : `Analyze ${currentHazardMeta.label.toLowerCase()} trend`}
        </button>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      {summary ? (
        <>
          <section className="stats-grid">
            <article className="stat-card has-tooltip">
              <div className="stat-header">
                <Flame size={18} />
                <span>{hazard === 'heatwave' ? 'Heatwave events' : hazard === 'drought' ? 'Drought years' : 'Extreme rain episodes'}</span>
              </div>
              <strong>{summary.total_event_count}</strong>
              <span className="custom-tooltip top">{`${currentHazardMeta.label} event count for ${summary.region_name}: ${summary.total_event_count}. This is the total number of sustained ${currentHazardMeta.label.toLowerCase()} conditions detected in the selected range.`}</span>
            </article>

            <article className="stat-card has-tooltip">
              <div className="stat-header">
                <CalendarRange size={18} />
                <span>Avg. duration</span>
              </div>
              <strong>{summary.average_duration_days} days</strong>
              <span className="custom-tooltip top">{`Average duration of each detected ${currentHazardMeta.label.toLowerCase()} episode in ${summary.region_name}: ${summary.average_duration_days} days.`}</span>
            </article>

            <article className="stat-card has-tooltip">
              <div className="stat-header">
                <TrendingUp size={18} />
                <span>Trend signal</span>
              </div>
              <strong>{summary.trend_label}</strong>
              <span className="custom-tooltip top">{`Trend direction for ${summary.region_name}: ${summary.trend_label}. This summarizes the long-term rise or decline in ${currentHazardMeta.label.toLowerCase()} intensity over the period.`}</span>
            </article>

            <article className="stat-card has-tooltip">
              <div className="stat-header">
                <MapPin size={18} />
                <span>Threshold</span>
              </div>
              <strong>{summary.threshold_c.toFixed(1)}{thresholdUnit}</strong>
              <span className="custom-tooltip top">{`Threshold used for ${currentHazardMeta.label.toLowerCase()} detection in ${summary.region_name}: ${summary.threshold_c.toFixed(1)}${thresholdUnit}.`}</span>
            </article>
          </section>

          <section className="insight-panel">
            <h2>Insight</h2>
            <p>{summary.insight}</p>
          </section>

          <section className="chart-grid">
            <div className="chart-card">
              <h3>{hazard === 'heatwave' ? 'Annual heatwave frequency' : hazard === 'drought' ? 'Annual drought signal' : 'Annual heavy rainfall signal'}</h3>
              <ResponsiveContainer width="100%" height={290}>
                <AreaChart data={chartData} margin={{ top: 16, right: 14, bottom: 8, left: 0 }}>
                  <defs>
                    <linearGradient id="frequencyFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#f97316" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#f97316" stopOpacity={0.04} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="4 4" stroke="#d9e1ef" />
                  <XAxis dataKey="year" tick={{ fill: '#53627d', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#53627d', fontSize: 12 }} />
                  <Tooltip
                    formatter={(value, name) => {
                      const rawValue = Array.isArray(value) ? value[0] : value
                      const safeValue = typeof rawValue === 'number' ? rawValue : Number(rawValue ?? 0)
                      if (String(name) === 'Heatwave count') return [safeValue, hazard === 'heatwave' ? 'Heatwave events' : hazard === 'drought' ? 'Drought years' : 'Extreme rain episodes']
                      return [safeValue, String(name)]
                    }}
                    labelFormatter={(label) => `Year ${label}`}
                    contentStyle={{
                      borderRadius: 12,
                      border: '1px solid rgba(148, 163, 184, 0.45)',
                      boxShadow: '0 12px 24px rgba(15, 23, 42, 0.08)',
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="event_count"
                    stroke="#f97316"
                    fill="url(#frequencyFill)"
                    name={hazard === 'heatwave' ? 'Heatwave count' : hazard === 'drought' ? 'Drought count' : 'Rainfall count'}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3>Average event duration</h3>
              <ResponsiveContainer width="100%" height={290}>
                <BarChart data={chartData} margin={{ top: 12, right: 10, bottom: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="4 4" stroke="#d9e1ef" />
                  <XAxis dataKey="year" tick={{ fill: '#53627d', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#53627d', fontSize: 12 }} />
                  <Tooltip
                    formatter={(value, name) => {
                      const rawValue = Array.isArray(value) ? value[0] : value
                      const safeValue = typeof rawValue === 'number' ? rawValue : Number(rawValue ?? 0)
                      if (String(name) === 'Days') return [`${safeValue} days`, 'Average event duration']
                      return [safeValue, String(name)]
                    }}
                    labelFormatter={(label) => `Year ${label}`}
                    contentStyle={{
                      borderRadius: 12,
                      border: '1px solid rgba(148, 163, 184, 0.45)',
                      boxShadow: '0 12px 24px rgba(15, 23, 42, 0.08)',
                    }}
                  />
                  <Legend />
                  <Bar dataKey="average_duration_days" name="Days" fill="#0f766e" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        </>
      ) : (
        <div className="empty-state">Select a region to generate the {currentHazardMeta.label.toLowerCase()} trend and summary insights.</div>
      )}
    </div>
  )
}

export default App
