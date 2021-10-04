"""
Author: David Jorge

This library acts as an API for running the trained object detection model on a raspberry pi, using tflite.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import time
import numpy as np
import cv2
import glob
from tflite_runtime.interpreter import Interpreter

MODEL_INPUT_WIDTH = 300
MODEL_INPUT_HEIGHT = 300


def set_input_tensor(interpreter, image):
    """
    Sets model input tensor (Input to model).

    :param interpreter: tflite model interpreter object.
    :param image: Input image.
    """
    tensor_index = interpreter.get_input_details()[0]['index']
    input_tensor = interpreter.tensor(tensor_index)()[0]
    input_tensor[:, :] = image


def get_output_tensor(interpreter, index):
    """
    Gets model output tensor (Output of model).

    :param interpreter: tflite model interpreter object.
    :param index: Index of output data.
    :return: Model output at index.
    """
    output_details = interpreter.get_output_details()[index]
    tensor = np.squeeze(interpreter.get_tensor(output_details['index']))
    return tensor


def detect_objects(interpreter, image, threshold):
    """
    Runs model inference for object detection on target image.

    :param interpreter: tflite model interpreter object.
    :param image: Target image for model inference.
    :param threshold: Model threshold.
    :return: Model inference output for target image.
    """
    set_input_tensor(interpreter, image)
    interpreter.invoke()

    # output details
    boxes = get_output_tensor(interpreter, 0)
    classes = get_output_tensor(interpreter, 1)
    scores = get_output_tensor(interpreter, 2)
    count = int(get_output_tensor(interpreter, 3))

    results = []
    for i in range(count):
        if scores[i] >= threshold:
            result = {
                'bounding_box': boxes[i],
                'class_id': classes[i],
                'score': scores[i]
            }
            results.append(result)
    return results


def draw_rect(image, box):
    """
    Helper function for drawing bonding boxes on image.

    :param image: Target image.
    :param box: Bounding box coordinates.
    """
    y_min = int(max(1, (box[0] * MODEL_INPUT_HEIGHT)))
    x_min = int(max(1, (box[1] * MODEL_INPUT_WIDTH)))
    y_max = int(min(MODEL_INPUT_HEIGHT, (box[2] * MODEL_INPUT_HEIGHT)))
    x_max = int(min(MODEL_INPUT_WIDTH, (box[3] * MODEL_INPUT_WIDTH)))

    # draw a rectangle on the image
    cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (255, 255, 255), 2)


def run_model(model="final_model.tflite", threshold=0.05, file="Images/*.jpg"):
    """
    Runs the trained model on an image file.

    :param model: Model file name.
    :param threshold: Model inference threshold.
    :param file: Relative path to image.
    :return: Output JPEG compressed Image as bytearray, number of detections, results, total elapsed time
    """
    # Initialize interpreter class instance for the trained tflite model
    interpreter = Interpreter(model)
    interpreter.allocate_tensors()
    _, input_height, input_width, _ = interpreter.get_input_details()[0]['shape']

    images = glob.glob(file)  # change to another directory if you need
    for img in images:
        # image = Image.open(img).resize((300,300), Image.ANTIALIAS)
        cv_img = cv2.imread(img, 0)
        cv_img = cv2.resize(cv_img, (300, 300), interpolation=cv2.INTER_AREA)
        # img_3c = cv2.applyColorMap(cv_img, 8, cv_img)
        img_3c = cv2.merge((cv_img, cv_img, cv_img))
        start_time = time.monotonic()
        results = detect_objects(interpreter, img_3c, threshold)
        elapsed_ms = (time.monotonic() - start_time) * 1000
        if results:
            print(results[0])
        for res in results:
            draw_rect(cv_img, res["bounding_box"])
        print(elapsed_ms)
        res, payload = cv2.imencode('.jpg', cv_img, [cv2.IMWRITE_JPEG_QUALITY, 50])
        print(payload.shape)
        print(len(results))
        # cv2.imshow("image", cv_img)
        # cv2.waitKey(0)

        return payload.tobytes(), len(results), results, elapsed_ms


if __name__ == '__main__':
    run_model()
