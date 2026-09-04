import cv2
import os

def detect_and_crop_face(image_path, padding=50):
    """
    Detects a face in the image and returns a cropped (and padded) version of the face.
    If no face is detected, returns the original image.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Failed to load image with OpenCV.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Load Haar cascade
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    if len(faces) == 0:
        return img, False

    # Take the first detected face
    x, y, w, h = faces[0]
    
    # Add padding
    x_start = max(0, x - padding)
    y_start = max(0, y - padding)
    x_end = min(img.shape[1], x + w + padding)
    y_end = min(img.shape[0], y + h + padding)
    
    cropped = img[y_start:y_end, x_start:x_end]
    return cropped, True
