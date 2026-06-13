import os

import cv2

## -- local imports --##
from services.faceDetect import FaceDetect
from services.faceRecognition import FaceRecog

# tests #
detect_path = "/home/somnath/.insightface/models/buffalo_l/det_10g.onnx"
recog_path = "/home/somnath/.insightface/models/buffalo_l/arc.onnx"

img_path1 = "/home/somnath/Pictures/AI/som2.jpg"
img_path2 = "/home/somnath/Pictures/AI/som4.jpg"


image1 = cv2.imread(img_path1)
image2 = cv2.imread(img_path2)
face_detector = FaceDetect(detect_path)
face_detector.start_session()
img_crp1 = face_detector.get_single_face_cropped(image1)
img_crp2 = face_detector.get_single_face_cropped(image2)
face1 = img_crp1.get("face", None)
face2 = img_crp2.get("face", None)

face_recognizer = FaceRecog(recog_path)
face_recognizer.start_session()
match_val = face_recognizer.match_faces(face1, face2)

print(f"Matching: {match_val}")
