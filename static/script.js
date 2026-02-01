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

function initMap() {
    const place = (window.MAP_PLACE || '').toString();
    const qs = place ? `?place=${encodeURIComponent(place)}` : '';
    fetch('/api/get-destination' + qs)
        .then(response => response.json())
        .then(data => {
            destinationCoords = {lat: data.latitude, lng: data.longitude};
            const destination = destinationCoords;

            const map = new google.maps.Map(document.getElementById("map"), {
                zoom: 14,
                center: destination,
            });

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

    // hook up place buttons
    function goToPlace(place){
        // navigate to map with place query param
        window.location.href = `/map?place=${encodeURIComponent(place)}`;
    }

    document.querySelectorAll('.visit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const p = btn.getAttribute('data-place');
            goToPlace(p);
        });
    });

    // make clicking the whole card navigate as well
    document.querySelectorAll('.place-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // avoid double-firing when button clicked
            if (e.target.closest('.visit-btn')) return;
            const p = card.getAttribute('data-place');
            goToPlace(p);
        });
    });
});