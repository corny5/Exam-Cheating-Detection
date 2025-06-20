// Function to format timestamp
function formatTimestamp(timestamp) {
    try {
        // Create a date object from the timestamp
        const date = new Date(timestamp);
        
        // Check if the date is valid
        if (isNaN(date.getTime())) {
            console.error('Invalid timestamp:', timestamp);
            return 'Invalid Date';
        }

        // Get the user's timezone
        const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        
        // Format the date in the user's local timezone
        return new Intl.DateTimeFormat('en-US', {
            timeZone: timeZone,
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
            timeZoneName: 'short'
        }).format(date);
    } catch (error) {
        console.error('Error formatting timestamp:', error);
        return 'Error formatting date';
    }
}

// Function to update detections
function updateDetections() {
    const behaviorFilter = document.getElementById('behaviorFilter');
    const selectedBehavior = behaviorFilter.value;
    
    const endpoint = selectedBehavior === 'all' ? '/alerts' : `/api/detections/${selectedBehavior}`;
    
    fetch(endpoint)
        .then(response => response.json())
        .then(alerts => {
            const alertsListElement = document.getElementById('alerts-list');
            alertsListElement.innerHTML = '';
            
            console.log('Received alerts:', alerts); // Debug log for all alerts
            
            alerts.forEach(detection => {
                console.log('Processing timestamp:', detection.timestamp); // Debug log for each timestamp
                const formattedTime = formatTimestamp(detection.timestamp);
                console.log('Formatted timestamp:', formattedTime); // Debug log for formatted time
                
                const confidenceClass = getConfidenceClass(detection.confidence);
                const detectionElement = document.createElement('div');
                detectionElement.className = `detection-item ${confidenceClass}`;
                
                detectionElement.innerHTML = `
                    <h3>${formatBehaviorType(detection.behavior_type)}</h3>
                    <p>Confidence: ${(detection.confidence * 100).toFixed(1)}%</p>
                    <p>Time: ${formattedTime}</p>
                    ${detection.details ? `<p>${detection.details}</p>` : ''}
                `;
                
                // Add click event listener to show the image
                if (detection.frame_path) {
                    detectionElement.addEventListener('click', () => {
                        showAlertImage(detection.frame_path);
                    });
                }
                
                alertsListElement.appendChild(detectionElement);
            });
        })
        .catch(error => console.error('Error fetching alerts:', error));
}

// Function to display the selected alert image
function showAlertImage(framePath) {
    console.log('Showing image with path:', framePath); // Debug log
    const imageContainer = document.getElementById('selected-alert-image');
    const imageUrl = `/detected_frames/${framePath.split('/').pop()}`; // Get just the filename
    console.log('Constructed image URL:', imageUrl); // Debug log
    
    const img = document.createElement('img');
    img.src = imageUrl;
    img.alt = 'Alert Detection';
    img.style.display = 'block';
    img.style.maxWidth = '100%';
    img.style.height = 'auto';
    img.style.marginTop = '1rem';
    
    // Clear previous content and add new image
    imageContainer.innerHTML = '';
    imageContainer.appendChild(img);
    
    // Add load and error event handlers
    img.onload = () => console.log('Image loaded successfully');
    img.onerror = (e) => console.error('Error loading image:', e);
}

// Update detections every 5 seconds
setInterval(updateDetections, 5000);

// Initial update
updateDetections();

function getConfidenceClass(confidence) {
    if (confidence > 0.8) return 'confidence-high';
    if (confidence > 0.6) return 'confidence-medium';
    return 'confidence-low';
}

function formatBehaviorType(type) {
    // Custom formatting for specific behavior types
    const behaviorLabels = {
        'looking_at_others_paper': "Looking at Others' Paper",
        'looking_down_suspicious': 'Suspicious Downward Gaze',
        'phone_detected': 'Phone Usage Detected',
        'potential_talking': 'Potential Talking Detected'
    };

    return behaviorLabels[type] || type
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Video source control
document.addEventListener('DOMContentLoaded', function() {
    const liveCameraBtn = document.getElementById('liveCameraBtn');
    const uploadVideoBtn = document.getElementById('uploadVideoBtn');
    const uploadSection = document.getElementById('uploadSection');
    const videoFeed = document.getElementById('videoFeed');
    const behaviorFilter = document.getElementById('behaviorFilter');
    const cameraControlBtn = document.getElementById('cameraControlBtn');

    // Initially hide the video feed
    videoFeed.style.display = 'none';

    // Handle camera control
    let isCameraRunning = false;
    cameraControlBtn.addEventListener('click', () => {
        if (!isCameraRunning) {
            // Start camera
            videoFeed.style.display = 'block';
            videoFeed.src = '/video_feed?source=camera';
            cameraControlBtn.textContent = 'Stop Camera';
            cameraControlBtn.style.backgroundColor = '#ff4444';
            isCameraRunning = true;
        } else {
            // Stop camera
            videoFeed.style.display = 'none';
            videoFeed.src = '';
            cameraControlBtn.textContent = 'Start Camera';
            cameraControlBtn.style.backgroundColor = '';
            isCameraRunning = false;
        }
    });

    // Add event listener for behavior filter
    behaviorFilter.addEventListener('change', updateDetections);
    const uploadForm = document.getElementById('videoUploadForm');
    const progressSection = document.getElementById('uploadProgress');
    const progressBar = document.querySelector('.progress');
    const progressText = document.getElementById('progressText');

    // Switch between live camera and upload
    liveCameraBtn.addEventListener('click', () => {
        liveCameraBtn.classList.add('active');
        uploadVideoBtn.classList.remove('active');
        uploadSection.style.display = 'none';
        if (isCameraRunning) {
            videoFeed.style.display = 'block';
            videoFeed.src = '/video_feed?source=camera';
        }
    });
    
    uploadVideoBtn.addEventListener('click', () => {
        uploadVideoBtn.classList.add('active');
        liveCameraBtn.classList.remove('active');
        uploadSection.style.display = 'block';
        videoFeed.style.display = 'none';
        videoFeed.src = '';
    });

    // Handle video upload
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('videoFile');
        const file = fileInput.files[0];

        if (!file) {
            alert('Please select a video file first.');
            return;
        }

        const formData = new FormData();
        formData.append('video', file);

        try {
            progressSection.style.display = 'block';
            const response = await fetch('/upload-video', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }
            
            // Show processed video feed and start polling for progress
            videoFeed.style.display = 'block';
            videoFeed.src = '/video_feed?source=processed';
            
            // Start polling for both progress and alerts
            pollProcessingStatus();
            
            // Increase alert polling frequency during video processing
            const alertUpdateInterval = setInterval(updateDetections, 1000); // Update every second
            
            // Once processing is complete, revert to normal polling frequency
            const checkComplete = setInterval(() => {
                fetch('/processing-status')
                    .then(response => response.json())
                    .then(data => {
                        if (!data.active) {
                            clearInterval(alertUpdateInterval);
                            clearInterval(checkComplete);
                            // Revert to normal polling frequency
                            setInterval(updateDetections, 5000);
                        }
                    });
            }, 1000);

        } catch (error) {
            console.error('Error uploading video:', error);
            alert('Failed to upload video. Please try again.');
            progressSection.style.display = 'none';
            videoFeed.style.display = 'none';
        }
    });

    // Poll for processing status
    function pollProcessingStatus() {
        const interval = setInterval(async () => {
            try {
                const response = await fetch('/processing-status');
                const data = await response.json();

                progressBar.style.width = `${data.progress}%`;
                progressText.textContent = `${data.progress}% - ${data.status}`;

                if (!data.active && data.progress === 100) {
                    clearInterval(interval);
                    alert('Video processing complete!');
                    progressSection.style.display = 'none';
                    // Refresh alerts to show new detections
                    updateDetections();
                } else if (!data.active) {
                    clearInterval(interval);
                    alert('Video processing failed: ' + data.status);
                    progressSection.style.display = 'none';
                }
            } catch (error) {
                console.error('Error checking processing status:', error);
                clearInterval(interval);
                progressSection.style.display = 'none';
            }
        }, 1000); // Check every second
    }
});
