const showStream = () => {
    document.querySelector('#selection-page').style.display = 'none';
    document.querySelector('#video-stream').style.display = 'block';
    document.querySelector('#predictions').style.display = 'block';
};

const showUpload = () => {
    document.querySelector('#selection-page').style.display = 'none';
    document.querySelector('#video-upload').style.display = 'block';
    document.querySelector('#predictions').style.display = 'block';
};

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

                if (parseFloat(conf) > 0.55) {
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
            const otherPredictions = data.predictions.slice(1).map(prediction => `<li>${prediction}</li>`).join('');
            predictionList.innerHTML = `
                <li>Detected Cat: <span id="detected-cat">${detectedCat.textContent}</span></li>
                <li>Confidence: <span id="confidence">${confidence.textContent}</span></li>
                <li>Food Door Status: <span id="food-door-status">${foodDoorStatus.textContent}</span></li>
                ${otherPredictions}
            `;
        });
};

document.querySelector('#stream-btn').addEventListener('click', showStream);
document.querySelector('#upload-btn').addEventListener('click', showUpload);

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
                body: formData
            });
        }
    });
});

setInterval(fetchPredictions, 1000);