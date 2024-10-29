"""
Script to read in images from folder and detect circles and their alignment

"""

import cv2
import os
import math
import statistics
import numpy as np
import pandas as pd
import h5py

#%% CLASS WITH FUNCTIONS

class ALIGNMENT:
    def __init__(self, path):
        self.path = path
        self.savepath = path + "/processed" # path to save information
        self.data_list = [] # list to store images (name and array)
        self.df_images = pd.DataFrame(columns=["pos", "cell"])
        self.columns = ["s0_coords", "s1_coords", "s2_coords", "s3_coords", "s4_coords", "s5_coords",
                        "s6_coords", "s7_coords", "s8_coords", "s9_coords", "s10_coords", # pixel coordinates
                        "s0_r", "s1_r", "s2_r", "s3_r", "s4_r", "s5_r",
                        "s6_r", "s7_r", "s8_r", "s9_r", "s10_r"] # pixel radius

        # Parameter which might need to be changed if camera position changes
        """Steps:
        0:pressing tool, 1:bottom part, 2:anode, 4:separator, 5:electrolyte,
        6:cathode, 7:spacer, 8:spring, 9:top part, 10:after pressing"""
        self.r_min = {0: 200, 1: 200, 2: 145, 4: 160, 5: 170, 6: 140, 7: 150, 8: 140, 9: 140, 10: 160} # min circle r
        self.r_max = {0: 230, 1: 230, 2: 175, 4: 183, 5: 190, 6: 162, 7: 178, 8: 170, 9: 185, 10: 190}  # max circle r

        """Rectangles constraining the place of the circle for each pressing tool:"""
        self.pos_1 = [(350, 650), (600, 800)] # top left, bottom right corner of rectangle
        self.pos_2 = [(2600, 650), (2760, 800)]
        self.pos_3 = [(4600, 650), (5100, 800)]
        self.pos_4 = [(350, 2800), (650, 3050)]
        self.pos_5 = [(2600, 2800), (2760, 3050)]
        self.pos_6 = [(4600, 2800), (5100, 3050)]
        self.rectangles = [self.pos_1, self.pos_2, self.pos_3, self.pos_4, self.pos_5, self.pos_6]

        """Coordinates for correction of z-distortion due to thickness of parts (from thickness_distortion.py)"""
        self.z_corr_1 = [(0.9, 1.8), (0.0, 1.8), (0.75, 1.8), (0.9, 0.9), (0.0, 0.9), (0.75, 0.9)] # after step 1
        self.z_corr_4 = [(4.65, 9.3), (0.0, 9.3), (3.875, 9.3), (4.65, 4.65), (0.0, 4.65), (3.875, 4.65)] # after step 4
        self.z_corr_7 = [(7.65, 15.3), (0.0, 15.3), (6.375, 15.3), (7.65, 7.65), (0.0, 7.65), (6.375, 7.65)] # after step 7

    # read files in list ----------------------------------------------
    def read_files(self):
        print("\n read files in list")
        for filename in os.listdir(self.path):
            if filename.endswith('.h5'):
                filepath = os.path.join(self.path, filename)
                with h5py.File(filepath, 'r') as f:
                    content = f['image'][:]
                    # convert to 8 bit
                    content = content/np.max(content)*255
                    content = content.astype(np.uint8)
                    try:
                        self.data_list.append((filename, content)) # store filename and image array
                    except:
                        print(f"wrong file name: {filename}")
        return self.data_list

    # get circle coordinates ----------------------------------------------
    def get_coordinates(self) -> pd.DataFrame:
        """Gets coordinates and radius of all parts and stores them in a data frame

        For each image in the list of images, the step as well as the positions and cell numbers
        are extracted and the image processes accordingly (contrast & gaussian blur) for better
        circle detection. Hough transform is applied to detect circles with the defined radius for
        this part. The position of the circle is constraint by the rectangles defined above. The
        extracted coordinates are assigned to each cell and stored in the data frame. The circles as
        well as the constraining rectangle are drawn in the image and saved as jpg.

        Return:
            self.df_images (data frame): stroing position, cell number, coordinate and radius (pixel)
        """
        print("\n detect circles and get circle coordinates")
        positions = [] # create lists & dictionaries to store informaiton
        cell_numbers = []
        coordinates = {0: [], 1: [], 2: [], 4: [], 5:[], 6: [], 7: [], 8: [], 9: [], 10:[]} # stores coordinates for all steps
        radius = {0: [], 1: [], 2: [], 4: [], 5:[], 6: [], 7: [], 8: [], 9: [], 10:[]} # stores radius for all steps

        for name, img in self.data_list:
            try:
                step = int(name.split("_")[0].split("s")[1])
            except:
                step = int(name.split(".")[0].split("s")[1]) # in case there is only cell
                print(f"fewer cells or wrong filename (check folder with files and their names): {name}")
            if step == 0: # assign position and cell number in data frame
                current_positions = []
                img = cv2.convertScaleAbs(img, alpha=1.5, beta=0) # increase contrast
                img = cv2.GaussianBlur(img, (5, 5), 2) # Gaussian blur to image before detecting (to improve detection)
                string = name.split(".")[0]
                for i in range(len(string.split("_"))):
                    if len(string.split("_")) > 1:
                        current_positions.append(str(string.split("_")[i].split("c")[0][-2:]))
                        positions.append(str(string.split("_")[i].split("c")[0][-2:]))
                        cell_numbers.append(str(string.split("_")[i].split("c")[1].split("s")[0]))
                    else:
                        print("only one cell in pressing tools")
                        current_positions.append(str(string.split("c")[0][-2:]))
                        positions.append(str(string.split("c")[0][-2:]))
                        cell_numbers.append(str(string.split("c")[1].split("s")[0]))
            elif step == 2: # increase constrast for the anode
                img = cv2.convertScaleAbs(img, alpha=2, beta=0)
                img = cv2.GaussianBlur(img, (5, 5), 2) # Gaussian blur to image before detecting (to improve detection)
            elif step == 6: # no contrast change for cathode
                img = cv2.GaussianBlur(img, (5, 5), 2) # Gaussian blur to image before detecting (to improve detection)
            elif step == 8:
                img = cv2.convertScaleAbs(img, alpha=1.25, beta=0) # increase contrast
            else:
                img = cv2.convertScaleAbs(img, alpha=1.25, beta=0) # increase contrast
                img = cv2.GaussianBlur(img, (5, 5), 2) # Gaussian blur to image before detecting (to improve detection)

            # Apply Hough transform
            detected_circles = cv2.HoughCircles(img,
                            cv2.HOUGH_GRADIENT,
                            dp = 1,
                            minDist = 100,
                            param1 = 30, param2 = 50,
                            minRadius = self.r_min[step], maxRadius = self.r_max[step])

            # Extract center points and their pressing tool position
            coords_buffer_dict = {}
            r_buffer_dict = {}
            if detected_circles is not None:
                detected_circles = np.uint16(np.around(detected_circles))
                for circle in detected_circles[0, :]:
                    # assign circle pressing tool
                    # constrain to avoid too many circles
                    if (circle[1] > self.pos_4[0][1]) & (circle[1] < self.pos_4[1][1]): # position 4, 5, 6
                        if (circle[0] > self.pos_4[0][0]) & (circle[0] < self.pos_4[1][0]): # position 4
                            if "04" in current_positions:
                                coords_buffer_dict[4] = [circle[0], circle[1]]  # (x, y) coordinates
                                r_buffer_dict[4] = circle[2] # radius
                        elif (circle[0] > self.pos_5[0][0]) & (circle[0] < self.pos_5[1][0]): # position 5
                            if "05" in current_positions:
                                coords_buffer_dict[5] = [circle[0], circle[1]]  # (x, y) coordinates
                                r_buffer_dict[5] = circle[2] # radius
                        elif (circle[0] > self.pos_6[0][0]) & (circle[0] < self.pos_6[1][0]): # position 6
                            if "06" in current_positions:
                                coords_buffer_dict[6] = [circle[0], circle[1]]  # (x, y) coordinates
                                r_buffer_dict[6] = circle[2] # radius
                        else: 
                            print(f"\n circle in lower row couldnt be assigned: ({circle[0]}, {circle[1]})")
                            # Create a mask that identifies incorrectly positioned circles to be remove
                            mask = ~np.all(np.isin(detected_circles, circle), axis=-1)  # axis=-1 to compare along the last dimension
                            detected_circles = np.array(detected_circles[mask]).reshape(1, -1, 3)  # Reshape

                    elif (circle[1] > self.pos_1[0][1]) & (circle[1] < self.pos_1[1][1]): # position 1, 2, 3
                        if (circle[0] > self.pos_1[0][0]) & (circle[0] < self.pos_1[1][0]): # position 1
                            if "01" in current_positions:
                                coords_buffer_dict[1] = [circle[0], circle[1]]  # (x, y) coordinates
                                r_buffer_dict[1] = circle[2] # radius
                        elif (circle[0] > self.pos_2[0][0]) & (circle[0] < self.pos_2[1][0]): # position 2
                            if "02" in current_positions:
                                coords_buffer_dict[2] = [circle[0], circle[1]]  # (x, y) coordinates
                                r_buffer_dict[2] = circle[2] # radius
                        elif (circle[0] > self.pos_3[0][0]) & (circle[0] < self.pos_3[1][0]): # position 3
                            if "03" in current_positions:
                                coords_buffer_dict[3] = [circle[0], circle[1]]  # (x, y) coordinates
                                r_buffer_dict[3] = circle[2] # radius
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
                for rect in self.rectangles: # Draw constraining rectagles for pressing tool position area
                    cv2.rectangle(img, rect[0], rect[1], (0, 0, 255), 10) # Red rectangle with 10-pixel thickness
                resized_img = cv2.resize(img, (1200, 800))
                # if folder doesn't exist, create it
                if not os.path.exists(self.savepath + "/detected_circles"):
                    os.makedirs(self.savepath + "/detected_circles")
                cv2.imwrite(self.savepath + f"/detected_circles/{name.split(".")[0]}.jpg", resized_img) # Save the image with detected circles

                # add circles which were not detected with zeros
                current_positions_int = [int(pos) for pos in current_positions] # Convert `current_positions` entries to integers
                for pos in current_positions_int: # Check each position in `current_positions_int`
                    if pos not in coords_buffer_dict:
                        coords_buffer_dict[pos] = [0, 0]
                    if pos not in r_buffer_dict:
                        r_buffer_dict[pos] = 0
                # Create a new dictionary with keys sorted by the specified order, skipping missing keys
                key_order = [1, 3, 5, 2, 4, 6] # order of pressing tool positions in string name of image file
                coords_buffer_dict = {key: coords_buffer_dict[key] for key in key_order if key in coords_buffer_dict}
                r_buffer_dict = {key: r_buffer_dict[key] for key in key_order if key in r_buffer_dict}
                # Create a list of all values without the keys
                coords_buffer_list = list(coords_buffer_dict.values())
                r_buffer_list = list(r_buffer_dict.values())
                # add values to list to collect values
                c = coordinates[step]
                c.extend(coords_buffer_list)
                coordinates[step] = c
                r = radius[step]
                r.extend(r_buffer_list)
                radius[step] = r
            else: # check if there are no cells in the pressing tools, or if just no part could be detected
                print("detected circles is none")
                if len(current_positions) != 0:
                    coords_buffer_list = [[0, 0] for _ in range(len(current_positions))] # add zeros per default
                    r_buffer_list = [0 for _ in range(len(current_positions))]
                    c = coordinates[step]
                    c.extend(coords_buffer_list)
                    coordinates[step] = c
                    r = radius[step]
                    r.extend(r_buffer_list)
                    radius[step] = r

        # fill values into dataframe
        for num, column in enumerate(self.df_images.columns.tolist()):
            if column == "pos":
                self.df_images[column] = positions
            elif column == "cell":
                self.df_images[column] = cell_numbers
            elif num < 13:
                key = num - 2
                if key != 3:
                    self.df_images[column] = coordinates[key]
            elif (num < 24) & (num > 12):
                key = num - 13
                if key != 3:
                    self.df_images[column] = radius[key]
        self.df_images= self.df_images.drop(columns=["s3_coords", "s3_r"]) # drop non existing step
        self.df_images['pos'] = self.df_images['pos'].astype(int) # get cell number and position as integers not string
        self.df_images['cell'] = self.df_images['cell'].astype(int)
        return self.df_images

    # get alignment numbers ----------------------------------------------
    def alignment_number(self):
        print("determine alignment in pixel")
        for index, row in self.df_images.iterrows():
            x_ref = row["s0_coords"][0]
            y_ref = row["s0_coords"][1]

            # correct distortion for step 1, 4, 7 (bottom, separator, spacer)
            pos = row["pos"]
            """
            self.z_corr_1 = [(0.9, 1.8), (0.0, 1.8), (0.75, 1.8), (0.9, 0.9), (0.0, 0.9), (0.75, 0.9)]
            self.z_corr_4 = [(4.65, 9.3), (0.0, 9.3), (3.875, 9.3), (4.65, 4.65), (0.0, 4.65), (3.875, 4.65)]
            self.z_corr_7 = [(7.65, 15.3), (0.0, 15.3), (6.375, 15.3), (7.65, 7.65), (0.0, 7.65), (6.375, 7.65)]
            """

            for i, col_name in enumerate(self.df_images.columns.tolist()[3:12]):
                n = self.df_images.columns.tolist()[-18:][i] # column name of alignment entry

                # correct for z distortion
                step = n.split("_")[0].split("s")[1]


                x = int(x_ref) - int(row[col_name][0])
                y = int(y_ref) - int(row[col_name][1])
                z = round(math.sqrt(x**2 + y**2), 1) # round number to one digit
                self.df_images._set_value(index, str(n), (x, y, z))
        return self.df_images

    # convert pixel to mm ----------------------------------------------
    def pixel_to_mm(self, with_radius = True): # decide whether to convert by radius or rectangle coordinates
        print("\n convert pixel values to mm")
        if with_radius:
            pixel = (sum(self.df_images["s0_r"].to_list())/len(self.df_images["s0_r"].to_list()) * 2) # pixel
            mm = 20 # mm
            pixel_to_mm = mm/pixel
            print("pixel to mm: " + str(pixel_to_mm) + " mm/pixel")
        else:
            pos_4_coords = self.df_images[self.df_images["pos"] == 4]["s0_coords"].tolist()
            pos_6_coords = self.df_images[self.df_images["pos"] == 6]["s0_coords"].tolist()
            pixel = statistics.median([abs(item4[0] - item6[0]) for item4, item6 in zip(pos_4_coords, pos_6_coords)])
            mm = 190 # mm
            pixel_to_mm = mm/pixel
            print("pixel to mm: " + str(pixel_to_mm) + " mm/pixel")
        # missalignment to mm
        for i in list(range(1, 11)):
            if i != 3:
                self.df_images[f"s{i}_align_mm"] = [(round(x * pixel_to_mm, 3), round(y * pixel_to_mm, 3),
                                                       round(z * pixel_to_mm, 3)) for x, y, z in self.df_images[f"s{i}_align"].to_list()] # add alignment in mm
        # radius to mm
        for i in list(range(0, 11)):
            if i != 3:
                self.df_images[f"s{i}_r_mm"] = [round(r * pixel_to_mm, 3) for r in self.df_images[f"s{i}_r"].to_list()] # add radius in mm

        # Save data
        images_alignment_mm.sort_values(by="cell", inplace=True)
        if not os.path.exists(self.savepath + "/data"):
            os.makedirs(self.savepath + "/data")
        images_alignment_mm.to_excel(self.savepath + "/data/data.xlsx")

        return self.df_images

#%% RUN CODE

# PARAMETER
path = "G:/Limit/Lina Scholz/robot_files_gen14"

# EXECUTE
obj = ALIGNMENT(path)
imgages = obj.read_files() # list with all images given as a list
images_detected = obj.get_coordinates() # get coordinates of all circles
images_alignment = obj.alignment_number() # get alignment
images_alignment_mm = obj.pixel_to_mm() # get alignment number in mm

print(images_detected.head())
print(images_alignment.head())
print(images_alignment_mm.head())

#%% SAVE

# images_alignment_mm.sort_values(by="cell", inplace=True)
# if not os.path.exists(path + "/data"):
#     os.makedirs(path + "/data")
# images_alignment_mm.to_excel(path + "/data/data.xlsx")


