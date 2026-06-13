import os

import cv2

## -- local imports --##
from services.faceDetect import FaceDetect

# tests #
model_path = "/home/somnath/.insightface/models/buffalo_l/det_10g.onnx"
img_path = "/home/somnath/Pictures/AI/group1.jpg"
output_image_path = "op.jpg"

image = cv2.imread(img_path)
face_detector = FaceDetect(model_path)
face_detector.start_session()
updated_image = face_detector.get_all_faces_marked(image)
cv2.imwrite(output_image_path, image)
