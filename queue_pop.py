"""
WIP, lisannbecker 

What is it?
When my script detects a queue pop in any of the video games I play, my 
philips hue lights turn on an pulse green. Queue pop detection with template 
matching within ROI. Architecture: PH Bridge (to connect to lights), Pi.
"""

#TODO 1 switch to Raspberry Pi 
#TODO 2 trigger (end) script by game launch (end)
#TODO 3 smarter queue pop detection than vision-based, explore apis

from phue import Bridge
import cv2
from time import sleep
import os
import sys
import threading
import psutil

#import subprocess <<< switch to once Pi is there
# run on Pi ssh keane@192.168.2.106 "tasklist | findstr LeagueClient.exe" <<< no, rework


DEBUGGING = True
pulse_e = threading.Event()

def check_games(games):
    #all_processes = list(set(p.name() for p in psutil.process_iter())) #remove
    #print(all_processes) #remove
    running_games = list(set(p.name().lower().replace('.exe', '') for p in psutil.process_iter() if p.name().lower().replace('.exe', '') in games))

    return running_games or []

def get_queue_pop_images(running_games): 
    imgs = []
    image_folder = 'queue_shots'
    for file in os.listdir(image_folder):
        if file.endswith(('.png', '.jpg', '.jpeg')) and os.path.splitext(file)[0] in running_games: #only get images of games that are running LeageClient cs2
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

    if not pulse_e.is_set():
        pulse_e.set()
        pulse_thread = threading.Thread(target=pulse_lights, args=(b, ), daemon=True) #does args still need to be a tuple? #TODO
        pulse_thread.start()

    return True, pre_pop_settings

def pulse_lights(b):
    lights = b.get_light_objects()

    while any(l.on for l in lights):
        for l in lights:
            if l.on:
                l.brightness = 254
        sleep(.5)

        for l in lights:
            if l.on:
                l.brightness = 150
        sleep(.5)

def restore_lights(b, previous_settings):
    pulse_e.clear()

    if not previous_settings:
        return False
    
    lights = b.get_light_objects()
    for l in lights:
        l_settings = previous_settings.get(l.name) #get value for lamp which is the dict from above
        l.on = l_settings['on']
        l.brightness = l_settings['brightness']
        l.xy = l_settings['xy']

    return False

def detect_queue_pop(b, cap, queue_pop_images, skip_frame = 5, res = (320, 240)):
    pop_flag = False
    frame_cnt = 0
    timeout = 0

    while cap.isOpened():
        running_games = check_games(["LeagueClient.exe", "cs2.exe"])
        if running_games:

            ret, frame = cap.read() #frame is np array
            while not ret: #handle no video input
                print(f'No HDMI input, attempt to reconnect {timeout+1}...')
                ret, frame = cap.read()
                sleep(10)
                timeout += 1 
                if timeout == 10:
                    print("No HDMI input detected after 10 attempts. Exiting program.")
                    cap.release()
                    sys.exit(1)

            if frame_cnt % skip_frame != 0: #only process nth frame
                frame_cnt += 1
                continue

            roi = preprocess_frame(frame, res)
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
        
        else:
            cap.release()
            break

def preprocess_frame(frame, res):
    x, y = res
    downsampled_frame = cv2.resize(frame, (x, y), interpolation=cv2.INTER_AREA) #lower res with area interpolation (weighted average of neighbouring pixels, neighbourhood size depends on scale of downsampling)
    gray_frame = cv2.cvtColor(downsampled_frame, cv2.COLOR_BGR2GRAY) 
    roi = gray_frame[int(y*0.25):int(y*0.75), int(x*0.25):int(x*0.75)] #take middle 50% of the screen to reduce compute - might not work if moving window... TODO 3

    return roi

def main():
    with open("games.txt", "r", ecoding="utf-8") as game_names:
        games = [l.strip().lower().replace('.exe', '') for l in game_names]

    running_games=None
    
    while True:
        while not running_games: #TODO 2 
            running_games = check_games(games) #check if game is running
            sleep(20)

        #delay initialising capture card until game is running
        b = Bridge('FILL-IP') #TODO enter IP of bridge 
        cap = cv2.VideoCapture(0) # video stream from hdmi capture card

        #dont think this will work - downsizing and lowering res of actual video stream. remove if doesnt work
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320) # res to 320x240
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            cap.set(cv2.CAP_PROP_FPS, 3) #set fps to 3

            if DEBUGGING == True:
                print(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                print(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(cap.get(cv2.CAP_PROP_FPS))
        
        except:
            pass

        imgs = get_queue_pop_images(running_games)
        detect_queue_pop(b, cap, imgs, 10, (320, 240)) #checks every 10th frame (~ 3 p sec - 30 FPS capture card), downsampling res 320 240

main()