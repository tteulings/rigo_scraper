# 🏠 Airbnb Scraper

Eenvoudige, modulaire tool om Airbnb listings per gemeente te scrapen met beschikbaarheidsanalyse.

## 🎉 NEW: Web Dashboards (NEDERLANDS!)

**Kies uit twee moderne, Nederlandse web interfaces voor het bekijken en maken van scraping runs!**

### 🎨 NiceGUI Dashboard (NIEUW!)
Modern, responsive dashboard met geavanceerde UI componenten.

```bash
# Start NiceGUI dashboard
python run_nicegui_dashboard.py
# Browser opent op http://localhost:8080
```

### 📊 Streamlit Dashboard
Data science gerichte dashboard met snelle prototyping.

```bash
# Start Streamlit dashboard
python run_dashboard.py
# Browser opent op http://localhost:8501
```

### ✨ Dashboard Features:
- 🇳🇱 **Volledig Nederlands** - alle tekst en interface in het Nederlands
- 📊 **Resultaten overzicht** - bekijk historische runs met filtering
- 🗺️ **Gemeente kaart** - interactieve kaart voor gemeente selectie
- 📅 **Flexibele planning** - interval, weekdagen, of maandelijks
- 📋 **Data export** - download resultaten als Excel
- 🔐 **Login bescherming** - beveiligde toegang

👉 **Zie [NICEGUI_README.md](NICEGUI_README.md) voor NiceGUI documentatie!**  
👉 **Zie [DASHBOARD_NL_README.md](DASHBOARD_NL_README.md) voor Streamlit documentatie!**

## ✨ Features

- ✅ **NiceGUI & Streamlit Dashboards** - keuze uit twee moderne web interfaces (NEW!)
- ✅ **⚡ Parallel scraping** - automatisch 5x sneller met multi-threading
- ✅ **⏱️ Gedetailleerde timing** - zie exact waar je tijd naartoe gaat (NEW!)
- ✅ **💾 Auto-checkpoints** - tussentijds opslaan elke 10 scans (NEW!)
- ✅ **Parallelle API calls** met automatische retry logic voor maximale dekking
- ✅ **Progress bars** voor real-time voortgang tracking
- ✅ **Logging** voor debugging en monitoring
- ✅ **Type hints** voor betere code kwaliteit
- ✅ **Modulaire architectuur** - herbruikbare, goed georganiseerde code
- ✅ **Automatische deduplicatie** van listings
- ✅ **Ruimtelijk filter** (binnen gemeentegrenzen)
- ✅ **Beschikbaarheidsanalyse** over tijd
- ✅ **Interactieve kaart** visualisatie
- ✅ **Prijsanalyse** per accommodatietype
- ✅ **Excel export** met meerdere sheets


## 📁 Project Structuur

```
airbnb/
├── nicegui_dashboard_nl.py       # 🎨 NiceGUI web dashboard (NEW!)
├── run_nicegui_dashboard.py      # NiceGUI launcher script (NEW!)
├── NICEGUI_README.md             # NiceGUI documentatie (NEW!)
├── streamlit_dashboard_nl.py     # 📊 Streamlit web dashboard
├── run_dashboard.py              # Streamlit launcher script
├── DASHBOARD_NL_README.md        # Streamlit documentatie
├── bnb_scraper.ipynb             # Hoofdnotebook (configuratie + visualisatie)
├── requirements.txt              # Python dependencies (updated!)
├── README.md                     # Deze file
├── .gitignore                    # Git ignore rules
│
├── src/                          # Clean, modular code
│   ├── core/
│   │   ├── scraper_core.py       # Main scraping orchestration
│   │   ├── api_client.py         # API calls met retry logic
│   │   └── room_classifier.py    # Room type classificatie
│   ├── config/
│   │   └── room_type_config.py   # Type mapping configuratie
│   ├── data/
│   │   ├── data_processor.py     # Data processing functies
│   │   └── exporter.py           # Excel export (updated!)
│   └── visualization/
│       ├── map_creator.py        # Interactieve kaarten
│       └── graph_creator.py      # Grafieken en plots
│
├── data/                         # Output folder voor scraping runs
│   └── run_GEMEENTE_TIMESTAMP/   # Per-run directory
│       ├── config.json           # Run configuratie
│       ├── *.xlsx                # Excel resultaten
│       ├── map.html              # Interactieve kaart
│       └── *.png                 # Grafieken
│
├── archive/                      # Oude analyse scripts
└── BestuurlijkeGebieden_2025.gpkg  # Gemeentegrenzen data
```

## 🚀 Quick Start

### Optie A: Web Dashboard (Aanbevolen!) 🌟

Kies je favoriete dashboard interface:

```bash
# 1. Installeer dependencies
pip install -r requirements.txt

# 2a. Start NiceGUI dashboard (Modern UI)
python run_nicegui_dashboard.py
# Browser opent op http://localhost:8080

# OF 2b. Start Streamlit dashboard (Data Science UI)
python run_dashboard.py
# Browser opent op http://localhost:8501

# 3. Login met wachtwoord: Ruijterkade
# 4. Configureer via de web interface en start scraping!
```

### ⚠️ Rate Limit Bescherming

**Veilige instellingen** (aanbevolen om IP bans te voorkomen):
```python
MAX_WORKERS = 2-3              # Niet te veel parallel
NUM_REPEAT_CALLS = 2           # Maximaal 2-3 herhalingen
DELAY_BETWEEN_SCANS = 1.0      # 1 seconde tussen scans
DELAY_BETWEEN_CALLS = 0.5      # 0.5 seconde tussen API calls
```

Als je een **429 error** krijgt:
1. Stop direct met scrapen
2. Wacht 30-60 minuten
3. Gebruik nog conservatievere instellingen (Workers=1, Delays=2.0)


### Optie B: Jupyter Notebook (Klassiek)

```bash
# 1. Installeer dependencies
pip install -r requirements.txt

# 2. Start Jupyter
jupyter notebook bnb_scraper.ipynb

# 3. Configureer parameters in de notebook:
GEMEENTEN = ["Schagen"]          # Welke gemeenten
PERIOD_START = "2025-12-01"      # Start datum
PERIOD_END = "2025-12-05"        # Eind datum
MEASUREMENT_INTERVAL = 1         # Dagen tussen metingen
NIGHTS_VARIATIONS = [1, 3, 7]    # Verblijfslengtes
GUESTS_VARIATIONS = [1, 3, 6]    # Aantallen gasten

# 4. Run alle cellen!
```

## 📊 Output

Het script **exporteert automatisch** naar Excel in de `data/` folder met 3 sheets:

1. **Alle Data** - Alle scrape resultaten met volledige details
2. **Beschikbaarheid** - Beschikbaarheid metrieken per listing
3. **Beschikbaarheid over tijd** - Timeline analyse per dag

**Alles gebeurt automatisch in één cel!** Geen aparte export stappen nodig.

## 📚 Module Documentatie

### `src/scraper_core.py`
Hoofdorchestratie van scraping:
- `generate_scan_combinations()` - Genereer scan combinaties voor periode
- `scrape_gemeente()` - Scrape één gemeente
- `scrape_all()` - Scrape alle gemeenten met progress bar
- `process_raw_results()` - Verwerk API resultaten
- `apply_spatial_filter()` - Filter binnen gemeentegrenzen

### `src/api_client.py`
API communicatie met retry logic:
- `make_api_call()` - Enkele API call met exponential backoff retry
- `make_parallel_api_calls()` - Parallelle calls voor betere dekking

### `src/room_classifier.py`
Intelligente classificatie van accommodatietypes:
- `extract_room_type()` - Detecteer type uit titel/naam/category

### `src/room_type_config.py`
Mapping naar Airbnb standaard categorieën:
- `map_to_airbnb_standard()` - Map gedetecteerd type naar standaard

### `src/data_processor.py`
Data verwerking functies:
- `calculate_availability()` - Bereken beschikbaarheid metrieken
- `calculate_availability_timeline()` - Timeline analyse
- `prepare_export_data()` - Prepareer data voor export
- `print_summary_stats()` - Print samenvatting statistieken

### `src/exporter.py`
**Automatische export functionaliteit:**
- `auto_export_results()` - Automatisch export naar Excel met alle sheets
  - Berekent beschikbaarheid
  - Genereert timeline
  - Exporteert naar Excel
  - Print beschikbaarheid stats
  - Alles in één functie!

### `src/utils.py`
Helper functies:
- `extract_beds_info()` - Extraheer slaapkamer/bed info
- `extract_price()` - Extraheer prijs
- `extract_rating()` - Extraheer rating en reviews
- `extract_coordinates()` - Extraheer lat/lon
- `setup_logging()` - Setup logging configuratie

## 📝 Belangrijke Inzichten

### API Strategie
De Airbnb API retourneert **willekeurige subsets** (~250-280 listings) per call. Door **3 herhaalde calls** te maken met dezelfde parameters en te dedupliceren, krijgen we ~98% dekking van alle beschikbare listings.

### Retry Logic
API calls kunnen falen. We implementeren exponential backoff retry (1s, 2s, 4s) met maximaal 3 pogingen per call voor betrouwbaarheid.

### Logging Levels
- `WARNING` - Normaal gebruik (standaard) - Clean progress bar, only warnings/errors
- `INFO` - Detailed output - Logs saved to file (recommended for debugging)
- `DEBUG` - Very detailed - Voor development only
- `ERROR` - Only errors

### Verbosity Control
In the notebook configuration cell, set:
```python
VERBOSE = False  # Clean progress bar (default)
VERBOSE = True   # Detailed logs to data/scraper.log
```

## 🔧 Geavanceerd Gebruik

### Custom Logging

**Option 1: Verbose mode (logs to file)**
```python
# In notebook config cell
VERBOSE = True  # Logs detailed info to data/scraper.log
```

**Option 2: Manual setup**
```python
from utils import setup_logging
import logging

# Log to file (keeps progress bar clean)
setup_logging(level=logging.INFO, log_file='data/scraper.log')

# Or debug to console (will interfere with progress bar)
setup_logging(level=logging.DEBUG)
```

### Programmatisch Gebruik
```python
from scraper_core import scrape_all, generate_scan_combinations
from data_processor import export_to_excel
import logging

# Setup
logging.basicConfig(level=logging.INFO)

# Scrape
scan_combinations, _ = generate_scan_combinations(
    "2025-12-01", "2025-12-05", [1, 3, 7], [1, 3, 6], 1
)

df_all = scrape_all(
    gemeenten=["Amsterdam"],
    scan_combinations=scan_combinations,
    gpkg_path="BestuurlijkeGebieden_2025.gpkg",
    num_repeat_calls=3,
    zoom_value=10,
    price_min=0,
    price_max=0,
    amenities=[],
    currency="EUR",
    language="nl",
    proxy_url="",
    measurement_date=datetime.now().isoformat(),
)

# Verwerk en export
# ... zie notebook voor voorbeeld
```

## 🐛 Troubleshooting

### API Errors
Als je veel API errors krijgt:
1. Check je internet connectie
2. Verhoog `max_retries` in `api_client.py`
3. Verklein het aantal parallelle calls (`NUM_REPEAT_CALLS`)

### Geen Resultaten
Als een gemeente geen resultaten geeft:
1. Check of de naam exact overeenkomt met `BestuurlijkeGebieden_2025.gpkg`
2. Check de logs voor error messages
3. Probeer een grotere zoom value

### Memory Issues
Voor grote scrapes (veel gemeenten/lange periodes):
1. Verklein de periode
2. Scrape gemeenten één voor één
3. Verhoog je systeem memory

## 📌 Dependencies

- `pyairbnb` - Airbnb API client
- `pandas` - Data processing
- `geopandas` - Spatial data handling
- `folium` - Interactive maps
- `shapely` - Geometric operations
- `openpyxl` - Excel export
- `matplotlib` - Plotting
- `tqdm` - Progress bars
- `pyyaml` - Configuration (optioneel)

## 🤝 Contributing

Dit is een hobby project, maar suggesties zijn welkom! Open een issue of pull request.

## 📄 License

MIT License - vrij te gebruiken voor eigen doeleinden.

---

**Made with ❤️ for data analysis**
