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
    fetch('/api/get-destination')
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