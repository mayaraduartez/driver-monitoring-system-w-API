from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2

model_path = "efficientdet_lite0.tflite"

base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.ObjectDetectorOptions(base_options=base_options,
                                       score_threshold=0.5)
detector = vision.ObjectDetector.create_from_options(options)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    detection_result = detector.detect(mp_image)

    for det in detection_result.detections:
        x1 = int(det.bounding_box.origin_x)
        y1 = int(det.bounding_box.origin_y)
        w  = int(det.bounding_box.width)
        h  = int(det.bounding_box.height)
        label = det.categories[0].category_name
        score = det.categories[0].score

        cv2.rectangle(frame, (x1,y1), (x1+w,y1+h), (0,255,0), 2)
        cv2.putText(frame, f"{label} {score:.2f}", (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

    cv2.imshow("Detector", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
