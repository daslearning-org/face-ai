import os
import datetime

import cv2
import numpy as np

## -- local imports -- ##
from services.faceDetect import FaceDetect, crop_with_buffer
from services.faceRecognition import FaceRecog

## -- global vars -- ##
detect_path = "/home/somnath/.insightface/models/buffalo_l/det_10g.onnx"
recog_path = "/home/somnath/.insightface/models/buffalo_l/arc.onnx"
out_path = "./outputs"

### --- global functions --- ###
def face_match_draw(img1, faces1, img2, faces2, matches, scores, target_size=[512, 512]): # target_size: (h, w)
    out1 = img1.copy()
    out2 = img2.copy()
    matched_box_color = (0, 255, 0)    # BGR
    mismatched_box_color = (0, 0, 255) # BGR

    # Resize to target size with the same aspect ratio
    padded_out1 = np.zeros((target_size[0], target_size[1], 3)).astype(np.uint8)
    h1, w1, _ = out1.shape
    ratio1 = min(target_size[0] / out1.shape[0], target_size[1] / out1.shape[1])
    new_h1 = int(h1 * ratio1)
    new_w1 = int(w1 * ratio1)
    resized_out1 = cv2.resize(out1, (new_w1, new_h1), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    top = max(0, target_size[0] - new_h1) // 2
    bottom = top + new_h1
    left = max(0, target_size[1] - new_w1) // 2
    right = left + new_w1
    padded_out1[top : bottom, left : right] = resized_out1

    # Draw bbox
    bbox1 = faces1[0][:4] * ratio1
    x, y, w, h = bbox1.astype(np.int32)
    cv2.rectangle(padded_out1, (x + left, y + top), (x + left + w, y + top + h), matched_box_color, 2)

    # Resize to target size with the same aspect ratio
    padded_out2 = np.zeros((target_size[0], target_size[1], 3)).astype(np.uint8)
    h2, w2, _ = out2.shape
    ratio2 = min(target_size[0] / out2.shape[0], target_size[1] / out2.shape[1])
    new_h2 = int(h2 * ratio2)
    new_w2 = int(w2 * ratio2)
    resized_out2 = cv2.resize(out2, (new_w2, new_h2), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    top = max(0, target_size[0] - new_h2) // 2
    bottom = top + new_h2
    left = max(0, target_size[1] - new_w2) // 2
    right = left + new_w2
    padded_out2[top : bottom, left : right] = resized_out2

    # Draw bbox
    if faces2.shape[0] == len(matches) and len(matches) == len(scores):
        for index, match in enumerate(matches):
            bbox2 = faces2[index][:4] * ratio2
            x, y, w, h = bbox2.astype(np.int32)
            box_color = matched_box_color if match else mismatched_box_color
            cv2.rectangle(padded_out2, (x + left, y + top), (x + left + w, y + top + h), box_color, 2)
            score = scores[index]
            text_color = matched_box_color if match else mismatched_box_color
            cv2.putText(padded_out2, "{:.2f}".format(score), (x + left, y + top - 5), cv2.FONT_HERSHEY_DUPLEX, 0.4, text_color)
        return np.concatenate([padded_out1, padded_out2], axis=1)
    else:
        return None

### --- classes --- ###
class FaceAiSvc:
    """
    This class will provide Face AI services like face detection, recognition etc.
    """

    def __init__(self, detect_model_path:str=detect_path, recog_model_path:str=recog_path, out_pth:str=out_path):
        self.detect_onnx = detect_model_path
        self.recog_onnx = recog_model_path
        self.out_path = out_pth
        self.face_detect = None
        self.face_recog = None
        self._threshold_cosine = 0.65
        self._threshold_norml2 = 1.13

    def start_detection_session(self):
        self.face_detect = FaceDetect(self.detect_onnx)
        self.face_detect.start_session()

    def start_recognition_session(self):
        self.face_recog = FaceRecog(self.recog_onnx)
        self.face_recog.start_session()

    def match_two_images_single_face(self, img1_path:str, img2_path:str):
        """
        Match two images with single face on each image. If there is no face or more than one face on any image, it will return None.

        Args:
            img1_path (str): Path of the first image.
            img2_path (str): Path of the second image.

        Returns:
            float | None: if all goes well the compare value will be sent, else None
        """
        if self.face_detect.session is None or self.face_recog.session is None:
            print("Either detection or recognition session(s) is/are not ready")
            return None

        image1 = cv2.imread(img1_path)
        image2 = cv2.imread(img2_path)
        face1 = self.face_detect.get_single_face_cropped(image1)
        face2 = self.face_detect.get_single_face_cropped(image2)
        if face1 is None:
            print("Image 1 does not contain any face or contains more than one face")
            return None
        if face2 is None:
            print("Image 2 does not contain any face or contains more than one face")
            return None
        val_compare = self.face_recog.match_faces(face1, face2)
        return val_compare

    def face_match_group(self, img1_path:str, img2_path:str):
        """
        Find the face from image1 (should be single face image) on image2 (could have multiple faces). 
        If there is no face or more than one face on image1, it will return None.
        If there is no face on image2, it will also return None.

        Args:
            img1_path (str): Path of the first image.
            img2_path (str): Path of the second image.

        Returns:
            path | None: if all goes well it will create a collage with two images of faces marked, else None
        """
        obj_return = {
            "stat": False,
            "msg": "",
            "path": ""
        }
        if self.face_detect.session is None or self.face_recog.session is None:
            print("Either detection or recognition session(s) is/are not ready")
            obj_return["msg"] = "Session is not ready"
            return obj_return

        img1_stat = False
        img2_stat = False

        image1 = cv2.imread(img1_path)
        image2 = cv2.imread(img2_path)

        faces1, point1 = self.face_detect.detect(image1)
        if len(faces1) == 1:
            img1_stat = True
            face1 = crop_with_buffer(image1, faces1[0])
            face1_emb = self.face_recog.get_face_embedding(face1)
        elif len(faces1) >= 2:
            obj_return["msg"] = "More than one face found on image 1"
        else:
            obj_return["msg"] = "No face is found on image 1"
        if not img1_stat:
            return obj_return

        faces2, point2 = self.face_detect.detect(image2)
        if len(faces2) >= 1:
            img2_stat = True
        else:
            obj_return["msg"] = "No face is found in image 2"

        if img2_stat:
            scores = []
            matches = []
            for face in faces2:
                face_crp = crop_with_buffer(image2, face)
                face_emb = self.face_recog.get_face_embedding(face_crp)
                score = np.dot(face1_emb, face_emb)
                scores.append(score)
                matches.append(1 if score >= self._threshold_cosine else 0)
            new_image = face_match_draw(image1, faces1, image2, faces2, matches, scores)
            now = datetime.datetime.now()
            current_time = str(now.strftime("%H%M%S"))
            current_date = str(now.strftime("%Y%m%d"))
            filename = os.path.join(self.out_path, f"fmg_{current_date}_{current_time}.jpg")
            cv2.imwrite(filename, new_image)
            obj_return["msg"] = "Match success"
            obj_return["stat"] = True
            obj_return["path"] = filename
        return obj_return

