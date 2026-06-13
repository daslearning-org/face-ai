import cv2

## -- local imports -- ##
from services.faceDetect import FaceDetect
from services.faceRecognition import FaceRecog

## -- global vars -- ##
detect_path = "/home/somnath/.insightface/models/buffalo_l/det_10g.onnx"
recog_path = "/home/somnath/.insightface/models/buffalo_l/arc.onnx"

### --- global functions --- ###

### --- classes --- ###
class FaceAiSvc:
    """
    This class will provide Face AI services like face detection, recognition etc.
    """

    def __init__(self, detect_model_path:str=detect_path, recog_model_path:str=recog_path):
        self.detect_onnx = detect_model_path
        self.recog_onnx = recog_model_path
        self.face_detect = None
        self.face_recog = None

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
