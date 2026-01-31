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

function findSpecialist(type) {
    fetch('/api/find-specialist', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ type: type })
    })
    .then(response => response.json())
    .then(data => {
        // To be implemented - navigate to map view
        window.location.href = '/map';
    })
    .catch(error => console.error('Error:', error));
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
