import mediapipe as mp
import numpy as np
import cv2


class PoseAnalyzer:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_face_mesh = mp.solutions.face_mesh
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1,
        )
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            refine_landmarks=True,
        )
        # For temporal smoothing
        self.last_n_detections = []
        self.detection_window = 5  # Number of frames to consider
        self.looking_sideways_threshold = (
            0.7  # Increased threshold to reduce false positives
        )

    def analyze_pose(self, frame):
        """Analyze pose and face landmarks in the frame"""
        height, width = frame.shape[:2]
        results = {
            "confidence": 0.0,
            "face_proximity_confidence": 0.0,
            "pose_landmarks": None,
            "face_landmarks": None,
            "looking_sideways": False,
            "looking_down": False,
            "image_width": width,
            "image_height": height,
        }

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Get pose landmarks
        pose_results = self.pose.process(rgb_frame)
        face_results = self.face_mesh.process(rgb_frame)

        if pose_results.pose_landmarks:
            results["pose_landmarks"] = pose_results.pose_landmarks
            results["confidence"] = max(
                [lm.visibility for lm in pose_results.pose_landmarks.landmark]
            )

        if face_results.multi_face_landmarks:
            results["face_landmarks"] = face_results.multi_face_landmarks[0]
            scaled_landmarks = self._scale_landmarks_to_image(
                results["face_landmarks"],
                width,
                height,
            )

            # Get the head rotation state
            looking_sideways = self._check_looking_sideways(scaled_landmarks)

            # Add to temporal window
            self.last_n_detections.append(looking_sideways)
            if len(self.last_n_detections) > self.detection_window:
                self.last_n_detections.pop(0)

            # Only mark as looking sideways if majority of recent frames show it
            results["looking_sideways"] = (
                sum(self.last_n_detections) / len(self.last_n_detections)
                > self.looking_sideways_threshold
            )

            results["looking_down"] = self._check_looking_down(scaled_landmarks)

        return results

    def _scale_landmarks_to_image(self, landmarks, width, height):
        """Scale normalized landmarks to actual image dimensions"""
        scaled = []
        for landmark in landmarks.landmark:
            scaled.append(
                {
                    "x": int(landmark.x * width),
                    "y": int(landmark.y * height),
                    "z": landmark.z,
                    "visibility": (
                        landmark.visibility if hasattr(landmark, "visibility") else 1.0
                    ),
                }
            )
        return scaled

    def _check_looking_sideways(self, landmarks):
        """Enhanced check for looking sideways using multiple facial features"""
        nose = landmarks[1]  # Nose tip
        left_ear = landmarks[234]  # Left ear
        right_ear = landmarks[454]  # Right ear
        left_eye = landmarks[33]  # Left eye outer corner
        right_eye = landmarks[263]  # Right eye outer corner

        # Calculate ear-to-nose distances
        left_dist = np.sqrt(
            (nose["x"] - left_ear["x"]) ** 2 + (nose["y"] - left_ear["y"]) ** 2
        )
        right_dist = np.sqrt(
            (nose["x"] - right_ear["x"]) ** 2 + (nose["y"] - right_ear["y"]) ** 2
        )

        # Calculate eye distances
        eye_dist = np.sqrt(
            (left_eye["x"] - right_eye["x"]) ** 2
            + (left_eye["y"] - right_eye["y"]) ** 2
        )

        # Calculate relative distances
        ear_ratio = min(left_dist, right_dist) / max(left_dist, right_dist)

        # Use Z-coordinate for depth perception
        nose_z = nose["z"]
        left_ear_z = left_ear["z"]
        right_ear_z = right_ear["z"]

        # Check if head is rotated (one ear is significantly closer than the other)
        z_diff = abs(left_ear_z - right_ear_z)

        # Combine multiple factors for more accurate detection
        is_looking_sideways = (
            ear_ratio < 0.75  # Relaxed ratio threshold
            and z_diff > 0.05  # Significant depth difference
            and eye_dist < 100  # Eyes are not fully visible (indicating head turn)
        )

        return is_looking_sideways

    def _check_looking_down(self, landmarks):
        """Enhanced check for looking down"""
        forehead = landmarks[10]  # Forehead center
        chin = landmarks[152]  # Chin center
        nose = landmarks[1]  # Nose tip

        # Calculate angle between vertical and face orientation
        face_vector = np.array([chin["x"] - forehead["x"], chin["y"] - forehead["y"]])
        vertical_vector = np.array([0, 1])

        # Normalize vectors
        face_vector = face_vector / np.linalg.norm(face_vector)
        vertical_vector = vertical_vector / np.linalg.norm(vertical_vector)

        # Calculate angle
        angle = np.arccos(np.clip(np.dot(face_vector, vertical_vector), -1.0, 1.0))
        angle_degrees = np.degrees(angle)

        # Check nose position relative to face
        face_length = np.sqrt(
            (chin["y"] - forehead["y"]) ** 2 + (chin["x"] - forehead["x"]) ** 2
        )
        nose_position = (nose["y"] - forehead["y"]) / face_length

        return angle_degrees > 30 and nose_position > 0.6

    def detect_close_faces(self, pose_results):
        """Detect if multiple faces are close to each other (potential talking)"""
        if not pose_results.get("face_landmarks"):
            return False
        return False  # Simplified for now to avoid errors
