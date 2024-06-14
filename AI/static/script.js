document.querySelector('#stream-btn').addEventListener('click', () => {
    document.querySelector('#selection-page').style.display = 'none';
    document.querySelector('#video-stream').style.display = 'block';
    document.querySelector('#video').src = "/video_feed"; // Set the source of the video feed
});

document.querySelector('#upload-btn').addEventListener('click', () => {
    document.querySelector('#selection-page').style.display = 'none';
    document.querySelector('#video-upload').style.display = 'block';
});

document.querySelector('#back-to-selection-stream').addEventListener('click', () => {
    document.querySelector('#video-stream').style.display = 'none';
    document.querySelector('#selection-page').style.display = 'block';
});

document.querySelector('#back-to-selection-upload').addEventListener('click', () => {
    document.querySelector('#video-upload').style.display = 'none';
    document.querySelector('#selection-page').style.display = 'block';
});

document.querySelector('#upload-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const videoFile = document.querySelector('#video-file').files[0];
            const videoElement = document.querySelector('#uploaded-video');
            videoElement.src = URL.createObjectURL(videoFile);
            videoElement.style.display = 'block';
            videoElement.play();
            fetch('/process_video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ filename: data.filename })
            });
        }
    });
});

const fetchPredictions = () => {
    fetch('/predictions')
        .then(response => response.json())
        .then(data => {
            const detectedCat = document.querySelector('#detected-cat');
            const confidence = document.querySelector('#confidence');
            const foodDoorStatus = document.querySelector('#food-door-status');

            if (data.predictions.length > 0) {
                const [label, conf] = data.predictions[0].split(': ');
                detectedCat.textContent = label;
                confidence.textContent = conf;

                if (parseFloat(conf) > parseFloat(confThreshold.value)) {
                    foodDoorStatus.textContent = `Open for ${label}`;
                } else {
                    foodDoorStatus.textContent = 'Closed';
                }
            } else {
                detectedCat.textContent = 'None';
                confidence.textContent = '0.00';
                foodDoorStatus.textContent = 'Closed';
            }

            const predictionList = document.querySelector('#prediction-list');
            const otherPredictions = data.predictions.slice(1).map(prediction => `<li class="list-group-item">${prediction}</li>`).join('');
            predictionList.innerHTML = `
                <li class="list-group-item">Detected Cat: <span id="detected-cat">${detectedCat.textContent}</span></li>
                <li class="list-group-item">Confidence: <span id="confidence">${confidence.textContent}</span></li>
                <li class="list-group-item">Food Door Status: <span id="food-door-status">${foodDoorStatus.textContent}</span></li>
                ${otherPredictions}
            `;
        });
};

const fetchUploadPredictions = () => {
    fetch('/predictions')
        .then(response => response.json())
        .then(data => {
            const detectedCat = document.querySelector('#detected-cat-upload');
            const confidence = document.querySelector('#confidence-upload');
            const foodDoorStatus = document.querySelector('#food-door-status-upload');

            if (data.predictions.length > 0) {
                const [label, conf] = data.predictions[0].split(': ');
                detectedCat.textContent = label;
                confidence.textContent = conf;

                if (parseFloat(conf) > parseFloat(confThresholdUpload.value)) {
                    foodDoorStatus.textContent = `Open for ${label}`;
                } else {
                    foodDoorStatus.textContent = 'Closed';
                }
            } else {
                detectedCat.textContent = 'None';
                confidence.textContent = '0.00';
                foodDoorStatus.textContent = 'Closed';
            }

            const predictionList = document.querySelector('#prediction-list-upload');
            const otherPredictions = data.predictions.slice(1).map(prediction => `<li class="list-group-item">${prediction}</li>`).join('');
            predictionList.innerHTML = `
                <li class="list-group-item">Detected Cat: <span id="detected-cat-upload">${detectedCat.textContent}</span></li>
                <li class="list-group-item">Confidence: <span id="confidence-upload">${confidence.textContent}</span></li>
                <li class="list-group-item">Food Door Status: <span id="food-door-status-upload">${foodDoorStatus.textContent}</span></li>
                ${otherPredictions}
            `;
        });
};

document.querySelector('#confidence-threshold').addEventListener('input', (e) => {
    document.querySelector('#confidence-threshold-value').textContent = e.target.value;
    confThreshold.value = e.target.value;
    fetch('/set_threshold', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ threshold: e.target.value })
    });
});

document.querySelector('#confidence-threshold-upload').addEventListener('input', (e) => {
    document.querySelector('#confidence-threshold-value-upload').textContent = e.target.value;
    confThresholdUpload.value = e.target.value;
    fetch('/set_threshold', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ threshold: e.target.value })
    });
});

setInterval(fetchPredictions, 1000);
setInterval(fetchUploadPredictions, 1000);
