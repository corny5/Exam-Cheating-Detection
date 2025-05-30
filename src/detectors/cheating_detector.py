import cv2
import mediapipe as mp
from ultralytics import YOLO
import torch
import numpy as np
from src.utils.pose_analyzer import PoseAnalyzer
from src.utils.object_detector import ObjectDetector


class CheatingDetector:
    def __init__(self):
        self.pose_analyzer = PoseAnalyzer()
        self.object_detector = ObjectDetector()
        self.confidence_threshold = 0.6

    def process_frame(self, frame):
        """
        Process a frame and detect potential cheating behaviors
        Returns a list of detections with confidence scores and behavior types
        """
        detections = []

        # Get pose analysis
        pose_results = self.pose_analyzer.analyze_pose(frame)

        # Get object detections
        object_results = self.object_detector.detect_objects(frame)

        # Get cheating detections from custom model
        cheating_results = self.object_detector.detect_cheating(frame)

        # 1. Check for direct cheating detection from custom model
        for cheating_detection in cheating_results["cheating"]:
            if cheating_detection["confidence"] > self.confidence_threshold:
                detections.append(
                    {
                        "behavior_type": "cheating_detected",
                        "confidence": cheating_detection["confidence"],
                        "bbox": cheating_detection["bbox"],
                        "details": "Student detected cheating by custom model",
                    }
                )

        # 2. Check for looking at other's paper
        if pose_results.get("looking_sideways", False):
            detections.append(
                {
                    "behavior_type": "looking_at_others_paper",
                    "confidence": pose_results["confidence"],
                    "details": "Student detected looking sideways",
                }
            )

        # 3. Check for looking down suspiciously
        if pose_results.get("looking_down", False):
            detections.append(
                {
                    "behavior_type": "looking_down_suspicious",
                    "confidence": pose_results["confidence"],
                    "details": "Student detected looking down suspiciously",
                }
            )

        # 4. Check for phone usage
        phones = object_results["phones"]
        if phones:
            for phone in phones:
                if phone["confidence"] > self.confidence_threshold:
                    detections.append(
                        {
                            "behavior_type": "phone_usage",
                            "confidence": phone["confidence"],
                            "bbox": phone["bbox"],
                            "details": "Phone detected in frame",
                        }
                    )

        # Filter out low confidence detections
        detections = [
            d for d in detections if d["confidence"] > self.confidence_threshold
        ]

        return detections

    def set_confidence_threshold(self, threshold):
        """Set the confidence threshold for detections"""
        self.confidence_threshold = max(
            0.0, min(1.0, threshold)
        )  # Clamp between 0 and 1
