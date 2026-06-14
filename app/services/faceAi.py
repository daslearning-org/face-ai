import os
import datetime

import cv2
import numpy as np

## -- local imports -- ##
from services.faceDetect import FaceDetect, crop_with_buffer, draw_corners
from services.faceRecognition import FaceRecog

## -- global vars -- ##
detect_path = "/home/somnath/.insightface/models/buffalo_l/det_10g.onnx"
recog_path = "/home/somnath/.insightface/models/buffalo_l/arc.onnx"
out_path = ""

### --- global functions --- ###

def write_text(image, bbox, text:str, colour=(255, 0, 0)):
    original_height, original_width = image.shape[:2]

    thickness = 2
    if original_width >= 4000:
        text_size = 2.0
        thickness = 4
    elif original_width >= 3000:
        text_size = 1.8
        thickness = 3
    elif original_width >= 2500:
        text_size = 1.5
    elif original_width >= 2000:
        text_size = 1.2
    elif original_width >= 1500:
        text_size = 1.0
    elif original_width >= 800:
        text_size = 0.8
        thickness = 2
    else:
        text_size = 0.5
        thickness = 1

    x1, y1, x2, y2 = bbox[:4].astype(np.int32)
    cv2.putText(image, text, (x1, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, text_size, colour, thickness)

def face_match_draw(img1, faces1, img2, faces2, matches, scores, target_size=[512, 512]): # target_size: (h, w)
    out1 = img1.copy()
    out2 = img2.copy()
    matched_box_color = (0, 255, 0)    # BGR
    mismatched_box_color = (0, 0, 255) # BGR

    # draw on face1
    draw_corners(out1, faces1[0], matched_box_color)

    # Draw on face2
    if faces2.shape[0] == len(matches) and len(matches) == len(scores):
        for index, match in enumerate(matches):
            score = scores[index]*100
            if match == 1:
                draw_corners(out2, faces2[index], matched_box_color)
                write_text(out2, faces2[index], "{:.2f}".format(score), matched_box_color)
            else:
                draw_corners(out2, faces2[index], mismatched_box_color)
                write_text(out2, faces2[index], "{:.2f}".format(score), mismatched_box_color)
        return out1, out2
    else:
        return None, None
    #return np.concatenate([padded_out1, padded_out2], axis=1)

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
            "src": "",
            "trgt": ""
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
            new_image1, new_image2 = face_match_draw(image1, faces1, image2, faces2, matches, scores)
            now = datetime.datetime.now()
            current_time = str(now.strftime("%H%M%S"))
            current_date = str(now.strftime("%Y%m%d"))
            filename1 = os.path.join(self.out_path, f"fmg1_{current_date}_{current_time}.jpg")
            filename2 = os.path.join(self.out_path, f"fmg2_{current_date}_{current_time}.jpg")
            cv2.imwrite(filename1, new_image1)
            cv2.imwrite(filename2, new_image2)
            obj_return["msg"] = "Match success"
            obj_return["stat"] = True
            obj_return["src"] = filename1
            obj_return["trgt"] = filename2
        return obj_return

