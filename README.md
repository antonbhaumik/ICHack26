# ICHack 26

A Flask web app that helps users find the best A&E option nearby by combining travel time with a lightweight wait-time predictor. It also supports finding nearby vets.

## Features
- Find nearby A&E hospitals using NHS search results
- Rank hospitals by travel time plus predicted wait time
- Interactive map view with Google Maps
- Vet finder with optional pre-geocoded data

## Tech Stack
- Python, Flask
- Google Maps Directions + Geocoding APIs
- BeautifulSoup (NHS search page parsing)
- Pandas/Numpy/Scipy for wait-time modeling

## Project Structure
- `app.py` Flask app and API routes
- `data/hospital_data.csv` Base average wait-time data
- `data/ae_wait_predictor.py` Wait-time multiplier model
- `data/vets_data_geocoded.csv` Vet list with optional coordinates
- `templates/` HTML templates
- `static/` JS/CSS

## Setup
1) Install dependencies:
```bash
pip install -r requirements.txt
```

2) Set environment variables:
```bash
set GOOGLE_API_KEY=YOUR_KEY
```

3) Run the app:
```bash
python app.py
```

Open `http://localhost:5000` in your browser.

## Notes
- The hospital list is scraped from the NHS service-search results page.
- The wait-time predictor is a heuristic model; it uses `hospital_data.csv` as a base.
- Google API usage may incur costs depending on your account and quotas.

## API Endpoints (high level)
- `POST /api/find-hospital` Find and rank nearby hospitals
- `POST /api/find-vet` Find nearby vets
- `GET /api/alternative-hospitals` List alternatives
- `POST /api/select-hospital` Switch selection
- `GET /api/get-origin` User origin from session
- `GET /api/get-destination` Selected destination details
