function findHospital() {
    fetch('/api/find-hospital', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        // To be implemented - navigate to map view
        window.location.href = '/map';
    })
    .catch(error => console.error('Error:', error));
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
