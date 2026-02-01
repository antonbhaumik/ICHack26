function findHospital() {
    getCurrentLocation()
        .then(location => {
            return fetch('/api/find-hospital', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(location)
            });
        })
        .then(response => response.json())
        .then(data => {
            window.location.href = '/map';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Unable to get your location. Please enable location services.');
        });
}

function findVet() {
    getCurrentLocation()
        .then(location => {
            return fetch('/api/find-vet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(location)
            });
        })
        .then(response => response.json())
        .then(data => {
            window.location.href = '/map';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Unable to get your location. Please enable location services.');
        });
}

function callTaxi() {
    fetch('/api/call-taxi', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        // To be implemented
        console.log('Calling taxi...');
    })
    .catch(error => console.error('Error:', error));
}

function call999() {
    // To be implemented - actual emergency calling functionality
    if (confirm('Call 999 Emergency Services?')) {
        console.log('Emergency call initiated');
    }
}

function callRSPCA() {
    // To be implemented - RSPCA calling functionality
    if (confirm('Call RSPCA?')) {
        console.log('RSPCA call initiated');
    }
}

function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported by your browser'));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                });
            },
            (error) => {
                reject(error);
            },
            {
                enableHighAccuracy: true,
                timeout: 50000,
                maximumAge: 0
            }
        );
    });
}

let trafficLayer = null;
let mapInstance = null;
let trafficEnabled = false;

function initMap() {
    const place = (window.MAP_PLACE || '').toString();
    const qs = place ? `?place=${encodeURIComponent(place)}` : '';
    fetch('/api/get-destination' + qs)
        .then(response => response.json())
        .then(data => {
            destinationCoords = {lat: data.latitude, lng: data.longitude};
            const destination = destinationCoords;

            // Update current hospital banner
            updateCurrentHospitalBanner(data);

            const map = new google.maps.Map(document.getElementById("map"), {
                zoom: 14,
                center: destination,
            });
            mapInstance = map;

            // Create traffic layer but don't show it by default
            trafficLayer = new google.maps.TrafficLayer();

            const directionsService = new google.maps.DirectionsService();
            const directionsRenderer = new google.maps.DirectionsRenderer();
            directionsRenderer.setMap(map);

            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition((position) => {
                    const origin = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };

                    directionsService.route(
                        {
                            origin: origin,
                            destination: destination,
                            travelMode: google.maps.TravelMode.DRIVING,
                        },
                        (result, status) => {
                            if (status === "OK") {
                                directionsRenderer.setDirections(result);
                            }
                        }
                    );
                });
            }
        });
    
    // Load alternative hospitals into the burger menu
    loadAlternativeHospitals();
}

function toggleTraffic() {
    if (!trafficLayer || !mapInstance) return;
    
    trafficEnabled = !trafficEnabled;
    trafficLayer.setMap(trafficEnabled ? mapInstance : null);
    
    const statusEl = document.getElementById('trafficStatus');
    if (statusEl) {
        statusEl.textContent = trafficEnabled ? 'ON' : 'OFF';
    }
}

function updateCurrentHospitalBanner(data) {
    const banner = document.getElementById('currentHospitalBanner');
    if (!banner) return;

    const nameEl = banner.querySelector('.hospital-name');
    const detailsEl = banner.querySelector('.hospital-details');

    if (data.name) {
        nameEl.textContent = data.name;
        
        // Build details string with travel time and wait time
        let details = [];
        
        if (data.duration) {
            const durationMin = Math.round(data.duration / 60);
            details.push(`Travel: ${durationMin} min`);
        }
        
        if (data.wait_time !== undefined && data.wait_time !== null) {
            details.push(`Wait: ${data.wait_time} min`);
        }
        
        if (data.distance) {
            const distanceKm = (data.distance / 1000).toFixed(1);
            details.push(`${distanceKm} km`);
        }
        
        detailsEl.textContent = details.join(' · ');
    } else {
        banner.style.display = 'none';
    }
}

function loadAlternativeHospitals() {
    fetch('/api/alternative-hospitals')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('alternativeHospitalsContainer');
            if (!container) return;

            if (data.status === 'success' && data.hospitals && data.hospitals.length > 0) {
                container.innerHTML = '<h2 style="margin-bottom: 12px; font-size: 18px;">Alternative Hospitals</h2>';
                
                data.hospitals.forEach((hospital, index) => {
                    const durationMin = Math.round(hospital.duration / 60);
                    const distanceKm = (hospital.distance / 1000).toFixed(1);
                    
                    // Build wait time display
                    let waitTimeDisplay = '';
                    if (hospital.wait_time !== undefined && hospital.wait_time !== null) {
                        waitTimeDisplay = `<strong>Wait time:</strong> ~${hospital.wait_time} min | `;
                    }
                    
                    const card = document.createElement('div');
                    card.className = 'place-card';
                    card.setAttribute('data-hospital-index', index + 1);
                    card.setAttribute('tabindex', '0');
                    
                    card.innerHTML = `
                        <h3>${hospital.hospital}</h3>
                        <p class="place-desc">${hospital.address}</p>
                        <p class="place-meta">
                            ${waitTimeDisplay}<strong>Travel:</strong> ~${durationMin} min | 
                            <strong>Distance:</strong> ${distanceKm} km
                        </p>
                        <button class="visit-btn" data-hospital-index="${index + 1}">Go to this hospital</button>
                    `;
                    
                    container.appendChild(card);
                });

                // Add click handlers for the hospital cards
                setupHospitalClickHandlers();
            } else {
                container.innerHTML = '<p style="text-align: center; color: var(--muted); padding: 20px;">No alternative hospitals available</p>';
            }
        })
        .catch(error => {
            console.error('Error loading alternative hospitals:', error);
            const container = document.getElementById('alternativeHospitalsContainer');
            if (container) {
                container.innerHTML = '<p style="text-align: center; color: var(--muted); padding: 20px;">Error loading hospitals</p>';
            }
        });
}

function setupHospitalClickHandlers() {
    // Add click handlers for visit buttons
    document.querySelectorAll('.visit-btn[data-hospital-index]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const index = parseInt(btn.getAttribute('data-hospital-index'));
            navigateToHospital(index);
        });
    });

    // Make clicking the whole card navigate as well
    document.querySelectorAll('.place-card[data-hospital-index]').forEach(card => {
        card.addEventListener('click', (e) => {
            if (e.target.closest('.visit-btn')) return;
            const index = parseInt(card.getAttribute('data-hospital-index'));
            navigateToHospital(index);
        });
    });
}

function navigateToHospital(hospitalIndex) {
    // hospitalIndex is 1-based (for alternatives), need to convert to 0-based absolute index
    // Alternative hospitals are at indices 1-4 in the session array (0 is the best/current one)
    const absoluteIndex = hospitalIndex; // hospitalIndex already represents the session array index
    
    // Call backend to switch the selected hospital to the front
    fetch('/api/select-hospital', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ hospital_index: absoluteIndex })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close the menu and reload the page to show the new route
            toggleMenu();
            window.location.reload();
        } else {
            alert('Failed to switch hospital');
        }
    })
    .catch(error => {
        console.error('Error selecting hospital:', error);
        alert('Error switching hospital');
    });
}

function openGoogleMaps() {
    if (!destinationCoords) {
        alert('Destination not loaded yet');
        return;
    }

    const dest = `${destinationCoords.lat},${destinationCoords.lng}`;

    // Open Google Maps with navigation
    const url = `https://www.google.com/maps/dir/?api=1&origin=your location&destination=${dest}&travelmode=driving`;
    window.open(url, '_blank');
}

function openUber() {
    if (!destinationCoords) {
        alert('Destination not loaded yet.');
        return;
    }

    getCurrentLocation()
        .then(origin => {
            const url = `https://m.uber.com/go/product-selection?drop[0]={"latitude"%3A${destinationCoords.lat}%2C"longitude"%3A${destinationCoords.lng}%2C"provider"%3A"uber_places"}&pickup={"latitude"%3A${origin.latitude}%2C"longitude"%3A${origin.longitude}%2C"provider"%3A"uber_places"}`;
            window.open(url, '_blank');
        })
        .catch(error => {
            console.error('Error getting location:', error);
            alert('Unable to get your current location');
        });
}

// --- Burger / Side menu toggle ---
function toggleMenu() {
    const menu = document.getElementById('sideMenu');
    const overlay = document.getElementById('menuOverlay');
    const btn = document.getElementById('burgerBtn');
    if (!menu || !overlay || !btn) return;

    const willOpen = !menu.classList.contains('open');
    menu.classList.toggle('open', willOpen);
    overlay.classList.toggle('open', willOpen);
    menu.setAttribute('aria-hidden', String(!willOpen));
    overlay.setAttribute('aria-hidden', String(!willOpen));
    btn.setAttribute('aria-expanded', String(willOpen));
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('burgerBtn');
    const close = document.getElementById('closeMenu');
    const overlay = document.getElementById('menuOverlay');
    btn && btn.addEventListener('click', toggleMenu);
    close && close.addEventListener('click', toggleMenu);
    overlay && overlay.addEventListener('click', toggleMenu);

    // close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const menu = document.getElementById('sideMenu');
            if (menu && menu.classList.contains('open')) toggleMenu();
        }
    });
});