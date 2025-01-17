"""
Author: lisannbecker
Status: WIP

What is it?
I'm streaming my screen to a Raspberry Pi (hdmi capture card). When it detects a queue pop in any of the video games I play, my philips hue lights turn on green. Queue pop detection with template matching within ROI.
I'll never miss a queue pop when I'm in the kitchen.
"""
#TODO check if games stop running
#TODO switch to Raspberry Pi game detection

from phue import Bridge
import cv2
from time import sleep
import os

import psutil
#import subprocess <<< switch to once Pi is there
# run on Pi ssh keane@192.168.2.106 "tasklist | findstr LeagueClient.exe" 



def check_games(games):
    everything = list(set(p.name() for p in psutil.process_iter()))
    print(everything)
    running_games = list(set(p.name() for p in psutil.process_iter() if p.name() in games))

    if running_games:
        return running_games
    else:
        return

def get_queue_pop_images(running_games): #TODO only get images of games that are running
    imgs = []
    image_folder = 'queues'
    for file in os.listdir(image_folder):
        if file.endswith('.png') or file.endswith('.jpg'):
            image_path = os.path.join(image_folder, file)
            queue_pop_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            imgs.append(queue_pop_image)
    return imgs

def queue_pop_alert(b): #TODO make lights pulse - after MVP works
    lights = b.get_light_objects()
    pre_pop_settings = {}

    for l in lights:
        pre_pop_settings[l.name] = {
            'on': l.on,
            'brightness': l.brightness,
            'xy': l.xy
        }

        l.on = True
        l.brightness = 150 #1 to 254
        l.xy = [0.2345, 0.7279] #green tone
    return True, pre_pop_settings

def restore_lights(b, previous_settings):
    if not previous_settings:
        return False
    
    lights = b.get_light_objects()
    for l in lights:
        l_settings = previous_settings.get(l.name) #get value for lamp which is the dict from above
        l.on = l_settings['on']
        l.brightness = l_settings['brightness']
        l.xy = l_settings['xy']
    return False

def track_screen(b, cap, queue_pop_images):
    pop_flag = False
    while cap.isOpened():
        ret, frame = cap.read() #frame is np array
        if ret: 
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) 
            x, y = 320, 240
            roi = gray_frame[int(y*0.25):int(y*0.75), int(x*0.25):int(x*0.75)] #take middle 50% of the screen - might not work if moving window... FIXME
            
            match_found = False

            for img in queue_pop_images:
                result = cv2.matchTemplate(roi, img, cv2.TM_CCOEFF_NORMED) #compare queue pop template to screen - assumes template is subsection of screen
                max_val = cv2.minMaxLoc(result)[1] #best match to template (output of minMaxLoc = min_val, max_val, min_loc, max_loc)

                if max_val > 0.8 and pop_flag == False: #if best match found has over 80% correlation pop lights on - if they aren't already
                    pop_flag, pre_pop_settings = queue_pop_alert(b)
                    match_found = True
                    break

                elif max_val > 0.8: #queue is still popped but lights are on already
                    match_found = True

            if not match_found and pop_flag: #no match found but lights are turned on: restore lights
                pop_flag = restore_lights(b, pre_pop_settings)
        sleep(0.2)


def main():

    running_games = check_games(["LeagueClient.exe", "cs2.exe"]) #check which game is running

    b = Bridge('FILL-IP') #TODO enter IP philips hue bridge connect

    cap = cv2.VideoCapture(0) # video stream from hdmi capture card
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320) #set res to 320x240
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 5) #set fps to 5

    imgs = get_queue_pop_images(running_games)
    track_screen(b, cap, imgs)

main()