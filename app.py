from flask import (
    Flask,
    render_template,
    Response,
    jsonify,
    send_from_directory,
    request,
    session,
    redirect,
    url_for,
)
import cv2
from src.detectors.cheating_detector import CheatingDetector
from src.database.db_manager import DBManager
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import threading
import time
import queue
import secrets

app = Flask(__name__)
# Session configuration
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key for sessions
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    hours=5
)  # Session expires after 5 hours

detector = CheatingDetector()
db_manager = DBManager()

# Global state variables
video_source = {"type": "camera", "active": False}
camera = None  # Global camera object

# Hardcoded credentials (in a real application, these should be stored securely)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"


def login_required(f):
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    # If user is already logged in, redirect to index
    if session.get("logged_in"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            session.permanent = True  # Make the session persistent
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


# Configure upload settings
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Global variables for video processing
current_video_path = None
frame_queue = queue.Queue(maxsize=30)  # Buffer for processed frames
processing_complete = threading.Event()

# Ensure directories exist
for directory in [UPLOAD_FOLDER, "detected_frames"]:
    if not os.path.exists(directory):
        os.makedirs(directory)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Store processing status
video_processing = {"active": False, "progress": 0, "status": ""}


# Home page route
@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")


def generate_frames():
    global camera, video_source

    # If we're processing an uploaded video, don't start the camera
    if video_source["type"] == "video":
        return

    video_source["type"] = "camera"
    video_source["active"] = True

    camera_indices = [0, 1]

    # Create detected_frames directory if it doesn't exist
    if not os.path.exists("detected_frames"):
        os.makedirs("detected_frames")

    for index in camera_indices:
        try:
            camera = cv2.VideoCapture(index)
            if camera is not None and camera.isOpened():
                # Set resolution to standard dimensions
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print(f"Successfully opened camera at index {index}")
                break
        except Exception as e:
            print(f"Error with camera index {index}: {str(e)}")
            continue

    if camera is None or not camera.isOpened():
        print("Error: Could not open webcam")
        return

    try:
        while True:
            if not video_source["active"] or video_source["type"] != "camera":
                break

            success, frame = camera.read()
            if not success:
                print("Error: Could not read frame")
                break

            try:
                # Ensure frame dimensions are consistent
                frame = cv2.resize(frame, (640, 480))

                # Process frame and detect cheating behaviors
                detections = detector.process_frame(frame)

                # Draw detection boxes on frame and store detections
                if detections:
                    draw_detection_boxes(frame, detections)
                    # Store each detection in the database
                    for detection in detections:
                        if detection["confidence"] > float(
                            os.getenv("DETECTION_CONFIDENCE", 0.6)
                        ):
                            timestamp = datetime.now()
                            frame_path = os.path.join(
                                "detected_frames",
                                f"frame_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg",
                            )
                            # Save the frame
                            cv2.imwrite(frame_path, frame)
                            # Store in database with all required fields
                            db_manager.store_detection(
                                timestamp=timestamp,
                                behavior_type=detection["behavior_type"],
                                confidence=detection["confidence"],
                                frame_path=frame_path,
                            )

                # Encode the frame for streaming
                ret, buffer = cv2.imencode(".jpg", frame)
                if not ret:
                    print("Error: Could not encode frame")
                    continue

                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )

            except Exception as e:
                print(f"Error processing frame: {str(e)}")
                continue

    except Exception as e:
        print(f"Error in generate_frames: {str(e)}")

    finally:
        if camera is not None:
            camera.release()
            video_source["active"] = False


# Single video feed route that handles both camera and processed video
@app.route("/video_feed")
def video_feed():
    """Route to stream video - either from camera or processed video"""
    global video_source

    if video_source["type"] == "video":
        return Response(
            generate_processed_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
    else:
        return Response(
            generate_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )


@app.route("/alerts")
def get_alerts():
    alerts = db_manager.get_recent_alerts()
    return jsonify(alerts)


@app.route("/api/detections/recent")
@login_required
def get_recent_detections():
    """Get recent detections"""
    detections = db_manager.get_recent_detections(limit=50)
    return jsonify(detections)


@app.route("/api/detections/<behavior_type>")
def get_detections_by_type(behavior_type):
    """Get detections filtered by behavior type"""
    detections = db_manager.get_detections_by_type(behavior_type, limit=50)
    return jsonify(detections)


@app.route("/detected_frames/<filename>")
def serve_detected_frame(filename):
    return send_from_directory("detected_frames", filename)


def draw_detection_boxes(frame, detections):
    """Draw bounding boxes for detected objects"""
    for detection in detections:
        if "bbox" in detection:
            bbox = detection["bbox"]
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(
                frame,
                f"{detection['behavior_type']}: {detection['confidence']:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2,
            )


@app.route("/upload-video", methods=["POST"])
def upload_video():
    global video_source, camera

    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        # Stop the camera feed if it's running
        video_source["type"] = "video"
        video_source["active"] = False
        if camera is not None:
            camera.release()
            camera = None

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Start processing in background
        threading.Thread(target=process_video_file, args=(filepath,)).start()

        return jsonify({"message": "Video uploaded successfully, processing started"})

    return jsonify({"error": "Invalid file type"}), 400


@app.route("/processing-status")
def get_processing_status():
    return jsonify(video_processing)


def process_frame_with_detections(frame):
    """Process a single frame and return it with detection boxes"""
    try:
        # Ensure frame dimensions are consistent
        frame = cv2.resize(frame, (640, 480))

        # Process frame and detect cheating behaviors
        detections = detector.process_frame(frame)

        # Draw detection boxes on frame and store detections
        if detections:
            draw_detection_boxes(frame, detections)
            # Store each detection in the database
            for detection in detections:
                if detection["confidence"] > float(
                    os.getenv("DETECTION_CONFIDENCE", 0.6)
                ):
                    timestamp = datetime.now()
                    frame_path = os.path.join(
                        "detected_frames",
                        f"frame_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg",
                    )
                    # Save the frame with detection boxes
                    cv2.imwrite(frame_path, frame)
                    # Store in database immediately
                    db_manager.store_detection(
                        timestamp=timestamp,
                        behavior_type=detection["behavior_type"],
                        confidence=detection["confidence"],
                        frame_path=frame_path,
                    )
                    print(
                        f"Stored detection: {detection['behavior_type']} with confidence {detection['confidence']}"
                    )

        return frame
    except Exception as e:
        print(f"Error processing frame: {str(e)}")
        return frame


def generate_processed_frames():
    """Generator for processed video frames"""
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            ret, buffer = cv2.imencode(".jpg", frame)
            if ret:
                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
        elif processing_complete.is_set():
            break
        else:
            time.sleep(0.01)  # Small delay to prevent CPU overload


def process_video_file(video_path):
    """Process uploaded video file"""
    global video_source
    try:
        video_processing["active"] = True
        video_processing["progress"] = 0
        video_processing["status"] = "Processing started"
        video_source["type"] = "video"
        video_source["active"] = True
        processing_complete.clear()

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        processed_frames = 0

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            # Process frame with detections
            processed_frame = process_frame_with_detections(frame)

            # Add to queue for streaming
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()  # Remove oldest frame if queue is full
                except queue.Empty:
                    pass
            frame_queue.put(processed_frame)

            processed_frames += 1
            video_processing["progress"] = int((processed_frames / total_frames) * 100)
            video_processing["status"] = (
                f"Processing frame {processed_frames}/{total_frames}"
            )

        cap.release()  # Clean up
        video_processing["active"] = False
        video_processing["status"] = "Processing complete"
        video_processing["progress"] = 100
        video_source["type"] = "camera"  # Reset back to camera mode
        video_source["active"] = False
        processing_complete.set()

        # Clean up the uploaded video
        os.remove(video_path)

    except Exception as e:
        video_processing["status"] = f"Error: {str(e)}"
        video_processing["active"] = False
        processing_complete.set()


if __name__ == "__main__":
    app.run(debug=True)
