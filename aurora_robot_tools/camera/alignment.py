
"""
Script to read in images from folder and detect circles

"""

import cv2
import os
import numpy as np
import pandas as pd
import h5py
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt

#%% CLASS WITH FUNCTIONS

class ALIGNMENT:
    def __init__(self, path):
        self.path = path
        self.df_images = pd.DataFrame(columns=["batch", "step", "content", 
                                               "c0_pxl", "c1_pxl", "c2_pxl", "c3_pxl", "c4_pxl", "c5_pxl",
                                               "r_c0", "r_c1", "r_c2", "r_c3", "r_c4", "r_c5",
                                               "c0_pxl/mm", "c1_pxl/mm", "c2_pxl/mm", "c3_pxl/mm", "c4_pxl/mm", "c5_pxl/mm"])
        # 0:pressing tool, 1:bottom part, 2:anode, 3:separator, 4:electrolyte, 5:cathode, 6:spacer, 7:spring, 8:top part, 9:after pressing
        self.r_min = {0: 210, 1: 200, 2: 140, 4: 170, 5: 170, 6: 125, 7: 140, 8: 140, 9: 140, 10: 160} # TODO: improve
        self.r_max = {0: 265, 1: 250, 2: 180, 4: 190, 5: 190, 6: 168, 7: 198, 8: 175, 9: 185, 10: 190} # TODO: improve

    # read images from folder ----------------------------------------------
    def read_files(self):
        print("\n read images from folder")
        for filename in os.listdir(self.path):
            #print(filename)
            #print(type(filename))
            if filename.endswith('.h5'):
                filepath = os.path.join(self.path, filename)
                try:
                    step = int(filename.split("_")[3])
                    #print(step)
                    batch = int(filename.split("_")[5].split(".")[0])
                    #print(batch)
                    with h5py.File(filepath, 'r') as f:
                        content = f['image'][:]
                        # convert to 8 bit
                        content = content/np.max(content)*255
                        content = content.astype(np.uint8)
                        self.df_images = self.df_images._append({"batch": batch, "step": step, "content": content, 
                                            "c0_pxl": "NaN", "c1_pxl": "NaN", "c2_pxl": "NaN", "c3_pxl": "NaN", "c4_pxl": "NaN", "c5_pxl": "NaN",
                                            "r_c0": "NaN", "r_c1": "NaN", "r_c2": "NaN", "r_c3": "NaN", "r_c4": "NaN", "r_c5": "NaN",
                                            "c0_pxl/mm": "NaN", "c1_pxl/mm": "NaN", "c2_pxl/mm": "NaN", "c3_pxl/mm": "NaN", "c4_pxl/mm": "NaN", "c5_pxl/mm": "NaN"}, 
                                            ignore_index=True) 
                except:
                    print(f"\n file name not valid: {filename}")
        return self.df_images
        
    # read information from data base if not included in file name ----------------------------------------------
    def read_database(self):
        print("\n reading SQL data base")

    # detect circles ----------------------------------------------
    def detect_circles(self):
        print("\n detect circles in each image")
        for index, row in self.df_images.iterrows():
            img = cv2.GaussianBlur(row["content"], (9, 9), 2) # Apply a Gaussian blur to the image before detecting circles (to improve detection)
            # Apply Hough transform
            detected_circles = cv2.HoughCircles(img,  
                            cv2.HOUGH_GRADIENT, 
                            dp = 1, 
                            minDist = 100, 
                            param1 = 30, param2 = 50, 
                            minRadius = self.r_min[row["step"]], maxRadius = self.r_max[row["step"]]) 
            
            # Extract center points and their pressing tool position
            if detected_circles is not None:
                detected_circles = np.uint16(np.around(detected_circles))
                for circle in detected_circles[0, :]:
                    # assign circle pressing tool
                    # TODO: constrain more to avoid too many circles
                    if (circle[1] > 2850) & (circle[1] < 3000):
                        if (circle[0] < 600) & (circle[0] > 400):
                            self.df_images._set_value(index, 'c3_pxl', [circle[0], circle[1]])  # (x, y) coordinates
                            self.df_images._set_value(index, 'r_c3', circle[2])
                        elif (circle[0] > 2600) & (circle[0] < 2760):
                            self.df_images._set_value(index, 'c4_pxl', [circle[0], circle[1]])
                            self.df_images._set_value(index, 'r_c4', circle[2])
                        elif (circle[0] > 4730) & (circle[0] < 4950):
                            self.df_images._set_value(index, 'c5_pxl', [circle[0], circle[1]])
                            self.df_images._set_value(index, 'r_c5', circle[2])
                        else: 
                            print(f"\n circle in lower row couldnt be assigned: ({circle[0]}, {circle[1]})")
                            # Create a mask that identifies incorrectly positioned circles to be remove
                            mask = ~np.all(np.isin(detected_circles, circle), axis=-1)  # axis=-1 to compare along the last dimension
                            detected_circles = np.array(detected_circles[mask]).reshape(1, -1, 3)  # Reshape

                    elif (circle[1] < 800) & (circle[1] > 650):
                        if (circle[0] < 600) & (circle[0] > 400):
                            self.df_images._set_value(index, 'c0_pxl', [circle[0], circle[1]])
                            self.df_images._set_value(index, 'r_c0', circle[2])
                        elif (circle[0] > 2600) & (circle[0] < 2760):
                            self.df_images._set_value(index, 'c1_pxl', [circle[0], circle[1]])
                            self.df_images._set_value(index, 'r_c1', circle[2])
                        elif (circle[0] > 4730) & (circle[0] < 4950):
                            self.df_images._set_value(index, 'c2_pxl', [circle[0], circle[1]])
                            self.df_images._set_value(index, 'r_c2', circle[2])
                        else: 
                            print(f"\n circle in upper row couldnt be assigned: ({circle[0]}, {circle[1]})")
                            # Create a mask that identifies incorrectly positioned circles to be remove
                            mask = ~np.all(np.isin(detected_circles, circle), axis=-1)  # axis=-1 to compare along the last dimension
                            detected_circles = np.array(detected_circles[mask]).reshape(1, -1, 3)  # Reshape
                    else:
                        print(f"\n circle couldnt be assigned for any pressing tool: ({circle[0]}, {circle[1]})") 
                        # Create a mask that identifies incorrectly positioned circles to be remove
                        mask = ~np.all(np.isin(detected_circles, circle), axis=-1)  # axis=-1 to compare along the last dimension
                        detected_circles = np.array(detected_circles[mask]).reshape(1, -1, 3)  # Reshape

                # Draw all detected circles and save image to check quality of detection
                for pt in detected_circles[0, :]:
                    a, b, r = pt[0], pt[1], pt[2]
                    cv2.circle(img, (a, b), r, (0, 0, 255), 10) # Draw the circumference of the circle
                    cv2.circle(img, (a, b), 1, (0, 0, 255), 10) # Show center point drawing a small circle
                desired_width = 1200 # Change image size
                desired_height = 800
                resized_img = cv2.resize(img, (desired_width, desired_height))
                # if folder doesn't exist, create it
                if not os.path.exists(self.path + "/detected_circles"):
                    os.makedirs(self.path + "/detected_circles")
                cv2.imwrite(self.path + f"/detected_circles/centers_step{row["step"]}_batch{row["batch"]}.jpg", resized_img) # Save the image with detected circles

        return self.df_images
        
    # convert pixel to mm ----------------------------------------------
    def pixel_to_mm(self):
        print("\n getting pixel coordinates and transform to mm")
        a_mm = c_mm = 100 # mm
        b_mm = d_mm = 190 # mm

        # TODO
        # filter for step 0 
        # determine conversion of pxl to mm for each point
        
    def consider_height(self):
        print("\n account for height of parts which changes the position of the center for the pressing tools which are not directly below the camera")

#%% RUN CODE

# PARAMETER
path = "G:/Limit/Lina Scholz/robot_files_20241004"

# EXECUTE
obj = ALIGNMENT(path)
imgages = obj.read_files() # list with all images given as a list of the following: batch, step, array
centers = obj.detect_circles() # add detected center points to images data frame

#%% CHECK

print(centers.head())

#%% SAVE

if not os.path.exists(path + "/data"):
    os.makedirs(path + "/data")
centers.to_excel(path + "/data/data.xlsx")


