from ultralytics import YOLO
import torch


class ObjectDetector:
    def __init__(self):
        # Initialize general object detection model
        self.general_model = YOLO(
            "yolov8n.pt"
        )  # Using the smallest YOLOv8 model for speed

        # Initialize cheating detection model
        self.cheating_model = YOLO("best.pt")  # Custom model for cheating detection

        # Classes we're interested in (from COCO dataset)
        self.target_classes = {"cell phone": 67, "book": 73, "person": 0}

        # Custom model classes
        self.cheating_classes = {
            "person": 0,
            "students_cheating": 1,
            "students_not_cheating": 2,
        }

    def detect_objects(self, frame):
        """Detect objects in the frame using YOLO"""
        results = self.general_model(frame)
        detections = {"phones": [], "books": [], "people": []}

        boxes = results[0].boxes
        for box in boxes:
            cls_id = int(box.cls)
            conf = float(box.conf)
            bbox = box.xyxy[0].tolist()  # Convert to normal list

            detection = {"confidence": conf, "bbox": bbox}

            if cls_id == self.target_classes["cell phone"]:
                detections["phones"].append(detection)
            elif cls_id == self.target_classes["book"]:
                detections["books"].append(detection)
            elif cls_id == self.target_classes["person"]:
                detections["people"].append(detection)

        return detections

    def detect_cheating(self, frame):
        """Detect cheating behavior using the custom model"""
        results = self.cheating_model(frame)
        detections = {"cheating": [], "not_cheating": [], "people": []}

        boxes = results[0].boxes
        for box in boxes:
            cls_id = int(box.cls)
            conf = float(box.conf)
            bbox = box.xyxy[0].tolist()

            detection = {"confidence": conf, "bbox": bbox}

            if cls_id == self.cheating_classes["students_cheating"]:
                detections["cheating"].append(detection)
            elif cls_id == self.cheating_classes["students_not_cheating"]:
                detections["not_cheating"].append(detection)
            elif cls_id == self.cheating_classes["person"]:
                detections["people"].append(detection)

        return detections

    def detect_phones(self, frame):
        """Extract phone detections from frame"""
        detections = self.detect_objects(frame)
        return detections["phones"]

    def detect_books(self, frame):
        """Extract book detections from frame"""
        detections = self.detect_objects(frame)
        return detections["books"]

    def get_person_count(self, frame):
        """Count number of people in frame"""
        detections = self.detect_objects(frame)
        return len(detections["people"])
