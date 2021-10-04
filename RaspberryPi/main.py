"""
Author: Samuel Clarke
Main Script to control Image Capture, Processing with ML and Transmission with 4G module
Sets the camera up
And then saves a jpeg periodically (delay = x)
name is formed from the current datetime, but this can be easily changed

"""

import cv2
from vimba import *
from typing import Optional
import sys
from time import sleep
from datetime import datetime
import os
import detect
import time
from csv import writer
import csv
from sense_hat import SenseHat
import communications as comm

# create sensehat object and clear screen
sense = SenseHat()
sense.clear()


def abort(reason: str, return_code: int = 1, usage: bool = False):
    print(reason + '\n')

    if usage:
        print_usage()

    sys.exit(return_code)


def print_usage():
    print('Usage:')
    print('    camera_script.py [camera_id]')
    print('    camera_script.py [/h] [-h]')
    print()
    print('Parameters:')
    print('    camera_id   ID of the camera to use (using first camera if not specified)')
    print()


def parse_args() -> Optional[str]:
    args = sys.argv[1:]
    argc = len(args)

    for arg in args:
        if arg in ('/h', '-h'):
            print_usage()
            sys.exit(0)

    if argc > 1:
        abort(reason="Invalid number of arguments. Abort.", return_code=2, usage=True)

    return None if argc == 0 else args[0]


def get_camera(camera_id: Optional[str]) -> Camera:
    with Vimba.get_instance() as vimba:
        if camera_id:
            try:
                return vimba.get_camera_by_id(camera_id)

            except VimbaCameraError:
                abort('Failed to access Camera \'{}\'. Abort.'.format(camera_id))

        else:
            cams = vimba.get_all_cameras()
            if not cams:
                abort('No Cameras accessible. Abort.')

            return cams[0]


def setup_camera(cam: Camera):
    with cam:
        settings_file = "/home/pi/Documents/ViPy_programs/full_continuous_settings.xml"
        # Load camera settings from file.
        cam.load_settings(settings_file, PersistType.All)
        # print("--> Feature values have been loaded from given file '%s'" % settings_file)


def data():
    # capture environmental data in string to write to CSV
    dp = 5
    temp = round(sense.get_temperature(), dp)
    humidity = round(sense.get_humidity(), dp)
    pressure = round(sense.get_pressure(), dp)
    now = datetime.now()
    orient = sense.get_orientation()
    time = now.strftime("%H-%M-%S_%d-%m-%y")
    env_data = [time, temp, humidity, pressure, orient["pitch"], orient["roll"], orient["yaw"]]
    return env_data


def main():
    # open file for saving output
    of = open("/home/pi/Documents/ViPy_programs/camera.out", "w")
    sys.stdout = of
    # Ser screen to Green
    sense.show_letter(str("x"), text_colour=[0, 255, 0], back_colour=[0, 255, 0])
    cam_id = parse_args()
    delay = 0.1
    # Create Images_hh-mm-ss_dd-dd-yy folder in current directory
    now = datetime.now()
    string = now.strftime("%H-%M-%S_%d-%m-%y")
    folder = "Images_" + string
    cwd = os.getcwd()
    dir = os.path.join(cwd, folder)
    if not os.path.exists(dir):
        os.mkdir(dir)
        print(folder, " directory made")
    else:
        print(folder, "directory already exists")

    # set up 4G comms hat
    comm.init_checks()
    comm.ssl_config()
    comm.mqtt_conn()

    # set up file to write environmental data to
    f = open('/home/pi/Documents/ViPy_programs/drone.csv', 'w')
    writer = csv.writer(f)
    writer.writerow(["datetime", "temperature(C)", "humidity", "pressure", "pitch", "roll", "yaw"])

    with Vimba.get_instance():
        with get_camera(cam_id) as cam:
            setup_camera(cam)
            # loop over image capture x times
            for i in range(2):
                # while True:
                now = datetime.now()
                envs = data()
                # print(envs)
                writer.writerow(envs)
                f.flush()
                # Capture image and save as jpg
                frame = cam.get_frame()
                frame.convert_pixel_format(PixelFormat.Mono8)
                string = now.strftime("%H-%M-%S_%d-%m-%y")
                file_name = string + ".jpg"
                path_name = os.path.join(dir, file_name)
                cv2.imwrite(path_name, frame.as_opencv_image())
                print(file_name, " saved")
                # display image number on screen
                sense.show_letter(str(i + 1), text_colour=[0, 255, 0], back_colour=[0, 0, 100])
                lat, lon = comm.gps_getposdummy()  # fake GPS coordinates for testing
                # call ML model
                img, num, results, elaspsed_ms = detect.run_model(file=path_name,
                                                                  model="/home/pi/Documents/ViPy_programs/monochrome.tflite")
                print(results)
                print(num)
                print(elaspsed_ms)
                # send data over 4G
                msgs = comm.imgToChunks(img)
                comm.mqtt_sendimg(msgs, [lat, lon, num, envs])
                sleep(delay)
            comm.mqtt_disc()
            sense.clear()
            of.close()


main()
