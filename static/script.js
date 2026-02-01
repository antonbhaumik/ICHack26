function showLoading() {
    const loadingScreen = document.getElementById('loadingScreen');
    if (loadingScreen) {
        loadingScreen.style.display = 'flex';
    }
}

function hideLoading() {
    const loadingScreen = document.getElementById('loadingScreen');
    if (loadingScreen) {
        loadingScreen.style.display = 'none';
    }
}

function findHospital() {
    showLoading();
    
    const addressInput = document.getElementById('customAddressInput');
    const customAddress = addressInput ? addressInput.value.trim() : '';
    
    // Use custom address if provided, otherwise use GPS location
    const locationPromise = customAddress ? 
        geocodeAddress(customAddress) : 
        getCurrentLocation();
    
    locationPromise
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
            alert(customAddress ? 'Unable to find that address.' : 'Unable to get your location. Please enable location services.');
        });
}

function toggleCustomAddress() {
    const section = document.getElementById('customAddressSection');
    if (section.style.display === 'none') {
        section.style.display = 'flex';
        document.getElementById('customAddressInput').focus();
    } else {
        section.style.display = 'none';
    }
}

function geocodeAddress(address) {
    return fetch(`https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(address)}&key=${window.GOOGLE_API_KEY || ''}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'OK' && data.results && data.results.length > 0) {
                const location = data.results[0].geometry.location;
                return {
                    latitude: location.lat,
                    longitude: location.lng
                };
            } else {
                throw new Error('Address not found');
            }
        });
}

function findVet() {
    showLoading();
    
    const addressInput = document.getElementById('customAddressInput');
    const customAddress = addressInput ? addressInput.value.trim() : '';
    
    // Use custom address if provided, otherwise use GPS location
    const locationPromise = customAddress ? 
        geocodeAddress(customAddress) : 
        getCurrentLocation();
    
    locationPromise
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
            hideLoading();
            console.error('Error:', error);
            alert(customAddress ? 'Unable to find that address.' : 'Unable to get your location. Please enable location services.');
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
let pageLoadTime = Date.now();
let alternativeMarkers = [];
let destinationCoords = null;
let currentInfoWindow = null;

// Helper function to format wait time in hours and minutes
function formatWaitTime(minutes) {
    if (minutes === undefined || minutes === null) {
        return null;
    }
    
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    
    if (hours === 0) {
        return `${mins}m`;
    } else if (mins === 0) {
        return `${hours}h`;
    } else {
        return `${hours}h${mins}m`;
    }
}

// Update the "last updated" timestamp every minute
function updateLastUpdatedText() {
    const lastUpdatedEl = document.getElementById('lastUpdated');
    if (!lastUpdatedEl) return;
    
    const minutesAgo = Math.floor((Date.now() - pageLoadTime) / 60000);
    
    if (minutesAgo === 0) {
        lastUpdatedEl.textContent = 'Last updated just now';
    } else if (minutesAgo === 1) {
        lastUpdatedEl.textContent = 'Last updated 1 minute ago';
    } else {
        lastUpdatedEl.textContent = `Last updated ${minutesAgo} minutes ago`;
    }
}

// Update every minute
setInterval(updateLastUpdatedText, 60000);

window.actualInitMap = function() {
    // Hide loading indicator
    const loadingEl = document.getElementById('mapLoading');
    if (loadingEl) loadingEl.style.display = 'none';
    
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
            const directionsRenderer = new google.maps.DirectionsRenderer({
                suppressMarkers: true // We'll add custom markers
            });
            directionsRenderer.setMap(map);

            // Get origin from session (either GPS location or custom address)
            fetch('/api/get-origin')
                .then(response => response.json())
                .then(originData => {
                    if (originData.latitude && originData.longitude) {
                        const origin = {
                            lat: originData.latitude,
                            lng: originData.longitude
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
                                    
                                    // Add custom origin marker (blue circle for current location)
                                    new google.maps.Marker({
                                        position: origin,
                                        map: map,
                                        icon: {
                                            path: google.maps.SymbolPath.CIRCLE,
                                            scale: 8,
                                            fillColor: '#4285F4',
                                            fillOpacity: 1,
                                            strokeColor: '#FFFFFF',
                                            strokeWeight: 2
                                        },
                                        zIndex: 1000
                                    });
                                    
                                    // Add custom destination marker (red pin)
                                    new google.maps.Marker({
                                        position: destination,
                                        map: map,
                                        zIndex: 1000
                                    });
                                } else {
                                    console.error('Directions request failed:', status);
                                    alert('Unable to calculate route. Please try again.');
                                }
                            }
                        );
                    }
                })
                .catch(error => {
                    console.error('Error getting origin:', error);
                    // Fallback to geolocation if session origin fails
                    if (navigator.geolocation) {
                        navigator.geolocation.getCurrentPosition(
                            (position) => {
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
                                        } else {
                                            console.error('Directions request failed:', status);
                                            alert('Unable to calculate route. Please try again.');
                                        }
                                    }
                                );
                            },
                            (error) => {
                                console.error('Geolocation failed:', error);
                                alert('Unable to get your location. Please enable location services.');
                            },
                            {
                                timeout: 10000,
                                maximumAge: 300000
                            }
                        );
                    } else {
                        alert('Geolocation is not supported by your browser.');
                    }
                });
        })
        .catch(error => {
            console.error('Error loading destination:', error);
            const loadingEl = document.getElementById('mapLoading');
            if (loadingEl) {
                loadingEl.innerHTML = `
                    <div style="color: #d32f2f; text-align: center;">
                        <p>Unable to load destination</p>
                        <button onclick="location.reload()" style="
                            padding: 10px 20px;
                            background: #4CAF50;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 14px;
                        ">Retry</button>
                    </div>
                `;
            }
        });
    
    // Load alternative hospitals into the burger menu
    loadAlternativeHospitals();
    
    // Plot alternative hospital markers on the map
    plotAlternativeLocations();
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

function plotAlternativeLocations() {
    // Clear existing alternative markers
    alternativeMarkers.forEach(marker => marker.setMap(null));
    alternativeMarkers = [];
    
    // Fetch alternative hospitals
    fetch('/api/alternative-hospitals')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.hospitals && data.hospitals.length > 0) {
                // For each alternative hospital, geocode and add a marker
                data.hospitals.forEach((hospital, index) => {
                    // Geocode the hospital address
                    const geocoder = new google.maps.Geocoder();
                    geocoder.geocode({ address: hospital.address }, (results, status) => {
                        if (status === 'OK' && results[0]) {
                            const position = results[0].geometry.location;
                            
                            // Create a marker for this alternative location
                            const marker = new google.maps.Marker({
                                position: position,
                                map: mapInstance,
                                title: hospital.hospital,
                                label: {
                                    text: String(index + 2), // Label as 2, 3, 4, 5 (since 1 is the main destination)
                                    color: 'white',
                                    fontSize: '13px',
                                    fontWeight: '600'
                                },
                                icon: {
                                    path: google.maps.SymbolPath.CIRCLE,
                                    scale: 11,
                                    fillColor: '#EF5350', // Red for alternatives
                                    fillOpacity: 0.9,
                                    strokeColor: '#D32F2F',
                                    strokeWeight: 1.5
                                }
                            });
                            
                            // Create info window
                            const durationMin = Math.round(hospital.duration / 60);
                            const distanceKm = (hospital.distance / 1000).toFixed(1);
                            let waitTimeDisplay = '';
                            if (hospital.wait_time !== undefined && hospital.wait_time !== null) {
                                const formattedWaitTime = formatWaitTime(hospital.wait_time);
                                waitTimeDisplay = `<br><strong>Wait time:</strong> ~${formattedWaitTime}`;
                            }
                            
                            const serviceType = window.SERVICE_TYPE || 'hospital';
                            const serviceName = serviceType === 'vet' ? 'vet' : 'hospital';
                            
                            const infoWindow = new google.maps.InfoWindow({
                                content: `
                                    <div style="padding: 0 8px 8px 8px; max-width: 250px;">
                                        <h3 style="margin: 0 0 8px 0; font-size: 16px;">${hospital.hospital}</h3>
                                        <p style="margin: 0 0 6px 0; font-size: 12px; color: #666;">${hospital.address}</p>
                                        <p style="margin: 0; font-size: 13px;">
                                            ${waitTimeDisplay}
                                            <br><strong>Travel:</strong> ~${durationMin} min
                                            <br><strong>Distance:</strong> ${distanceKm} km
                                        </p>
                                        <button onclick="navigateToHospital(${index + 1})" style="
                                            margin-top: 10px;
                                            padding: 8px 16px;
                                            background: #4CAF50;
                                            color: white;
                                            border: none;
                                            border-radius: 4px;
                                            cursor: pointer;
                                            font-size: 13px;
                                        ">Go to this ${serviceName}</button>
                                    </div>
                                `
                            });
                            
                            // Show info window on click
                            marker.addListener('click', () => {
                                // If this info window is already open, close it
                                if (currentInfoWindow === infoWindow) {
                                    currentInfoWindow.close();
                                    currentInfoWindow = null;
                                } else {
                                    // Close any previously open info window
                                    if (currentInfoWindow) {
                                        currentInfoWindow.close();
                                    }
                                    // Open this info window
                                    infoWindow.open(mapInstance, marker);
                                    currentInfoWindow = infoWindow;
                                }
                            });
                            
                            alternativeMarkers.push(marker);
                        }
                    });
                });
            }
        })
        .catch(error => {
            console.error('Error loading alternative locations:', error);
        });
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
            const formattedWaitTime = formatWaitTime(data.wait_time);
            details.push(`Wait: ${formattedWaitTime}`);
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
    const serviceType = window.SERVICE_TYPE || 'hospital';
    const serviceName = serviceType === 'vet' ? 'Vet' : 'Hospital';
    const serviceNamePlural = serviceType === 'vet' ? 'Vets' : 'Hospitals';
    
    fetch('/api/alternative-hospitals')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('alternativeHospitalsContainer');
            if (!container) return;

            if (data.status === 'success' && data.hospitals && data.hospitals.length > 0) {
                container.innerHTML = `<h2 style="margin-bottom: 12px; font-size: 18px;">Alternative ${serviceNamePlural}</h2>`;
                
                data.hospitals.forEach((hospital, index) => {
                    const durationMin = Math.round(hospital.duration / 60);
                    const distanceKm = (hospital.distance / 1000).toFixed(1);
                    
                    // Build wait time display
                    let waitTimeDisplay = '';
                    if (hospital.wait_time !== undefined && hospital.wait_time !== null) {
                        const formattedWaitTime = formatWaitTime(hospital.wait_time);
                        waitTimeDisplay = `<strong>Wait time:</strong> ~${formattedWaitTime} | `;
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
                        <button class="visit-btn" data-hospital-index="${index + 1}">Go to this ${serviceName.toLowerCase()}</button>
                    `;
                    
                    container.appendChild(card);
                });

                // Add click handlers for the hospital cards
                setupHospitalClickHandlers();
            } else {
                container.innerHTML = `<p style="text-align: center; color: var(--muted); padding: 20px;">No alternative ${serviceNamePlural.toLowerCase()} available</p>`;
            }
        })
        .catch(error => {
            console.error('Error loading alternative hospitals:', error);
            const container = document.getElementById('alternativeHospitalsContainer');
            const serviceNamePlural = (window.SERVICE_TYPE === 'vet' ? 'Vets' : 'Hospitals').toLowerCase();
            if (container) {
                container.innerHTML = `<p style="text-align: center; color: var(--muted); padding: 20px;">Error loading ${serviceNamePlural}</p>`;
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

    // Get origin from session to use custom address if provided
    fetch('/api/get-origin')
        .then(response => response.json())
        .then(originData => {
            if (originData.latitude && originData.longitude) {
                const origin = `${originData.latitude},${originData.longitude}`;
                const url = `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${dest}&travelmode=driving`;
                window.open(url, '_blank');
            } else {
                // Fallback to "your location" if no session origin
                const url = `https://www.google.com/maps/dir/?api=1&origin=your location&destination=${dest}&travelmode=driving`;
                window.open(url, '_blank');
            }
        })
        .catch(error => {
            console.error('Error getting origin:', error);
            // Fallback to "your location"
            const url = `https://www.google.com/maps/dir/?api=1&origin=your location&destination=${dest}&travelmode=driving`;
            window.open(url, '_blank');
        });
}

function openUber() {
    if (!destinationCoords) {
        alert('Destination not loaded yet.');
        return;
    }

    // Try to get origin from session first (custom address), fallback to GPS
    fetch('/api/get-origin')
        .then(response => response.json())
        .then(originData => {
            if (originData.latitude && originData.longitude) {
                const url = `https://m.uber.com/go/product-selection?drop[0]={"latitude"%3A${destinationCoords.lat}%2C"longitude"%3A${destinationCoords.lng}%2C"provider"%3A"uber_places"}&pickup={"latitude"%3A${originData.latitude}%2C"longitude"%3A${originData.longitude}%2C"provider"%3A"uber_places"}`;
                window.open(url, '_blank');
            } else {
                throw new Error('No session origin, using GPS');
            }
        })
        .catch(error => {
            // Fallback to GPS location
            getCurrentLocation()
                .then(origin => {
                    const url = `https://m.uber.com/go/product-selection?drop[0]={"latitude"%3A${destinationCoords.lat}%2C"longitude"%3A${destinationCoords.lng}%2C"provider"%3A"uber_places"}&pickup={"latitude"%3A${origin.latitude}%2C"longitude"%3A${origin.longitude}%2C"provider"%3A"uber_places"}`;
                    window.open(url, '_blank');
                })
                .catch(error => {
                    console.error('Error getting location:', error);
                    alert('Unable to get your location');
                });
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