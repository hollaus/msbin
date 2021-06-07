import subprocess
import re
import os
import glob
import cv2
import numpy as np
import tqdm
import errno
import dibco_measure
import f_measure
import argparse
import csv
import constants

def get_image_files(path):
    extensions = ('*.png', '*.tiff')
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(path, ext)))

    # filter out pseudo images (these are just for probability visualization):
    files = [f for f in files if 'pseudo' not in f]        
        
    return files

def convert_img(path_in, path_out, invert_imgs=False, msbin_gt=False, msbin_path_gt='', fg_type: constants.FGType = constants.FGType.REGULAR):

    image = cv2.imread(path_in)

    if not msbin_gt:
        
        if fg_type == constants.FGType.MSBIN_FG_2:
            fg = image[:,:,2]
            fg = np.where(fg == 255, 255, 0)
        else:
            fg = image[:,:,1]
            fg = np.where(fg == 255, 255, 0)
    else:
        if fg_type == constants.FGType.MSBIN_FG_1:
            fg = np.where((image[:,:,0] == 255) * (image[:,:,1] == 255) * (image[:,:,2] == 255), 255, 0)
        elif fg_type == constants.FGType.MSBIN_FG_2:
            fg = np.where((image[:,:,0] == 122), 255, 0)
            # skip files that do not contain MSBIN_FG_2:
            if np.sum(fg) == 0:
                return

    if invert_imgs:
        fg = 255 - fg

    if msbin_path_gt:
        # Mask out regions that are uncertain (blue) in the GT:
        file_name = os.path.basename(path_in)
        gt = cv2.imread(os.path.join(msbin_path_gt, file_name))
        if fg_type == constants.FGType.MSBIN_FG_2:
            red_ink_gt = (gt[:,:,2] == 122)
            # Skip the file if it does not contain red ink:
            if np.sum(red_ink_gt) == 0:
                return
            
        certain = np.where((gt[:,:,0] == 255) * (gt[:,:,1] == 0) * (gt[:,:,2] == 0), 0, 255)
        fg = fg * certain + np.abs(certain-255)



        
    path_name = os.path.join(path_out, os.path.basename(path_in))
    cv2.imwrite(path_name, fg)        

    return path_name

# class ImgConverter:

#     def __init__(self, path_in, path_out, path_gt='',invert_imgs = False):
#         """Initialize the converter. 
#         In case of MSBin path_gt is required for encoding unknown regions."""
#         self.path_in = path_in
#         self.path_out = path_out
#         self.path_gt = path_gt
#         self.invert_imgs = invert_imgs

#     def batch_convert(self):
#         files = get_image_files(self.path_in)
#         if not files:
#             print('No suitable file found.')
#             return -1

#         for f in files:
#             convert_img(f, self.path_out, self.invert_imgs)

class Converter:

    def __init__(self, path_in, path_out, path_dibco_bin='', invert_imgs = False, msbin_gt = False, msbin_path_gt='', fg_type: constants.FGType = constants.FGType.REGULAR):
        self.path_in = path_in
        self.path_out = path_out
        self.path_dibco_bin = path_dibco_bin
        if self.path_dibco_bin:
            self.path_dibco_bin = os.path.join(path_dibco_bin, "BinEvalWeights.exe")
        self.invert_imgs = invert_imgs
        self.msbin_gt = msbin_gt
        self.msbin_path_gt = msbin_path_gt
        self.fg_type = fg_type

    def batch_convert(self):

        def save_weights():
            args = [self.path_dibco_bin, file_out_name]
            p = subprocess.Popen(args, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output = p.stdout.read().decode("utf8")
            done_msg = '\r\nStarting 7 stages procedure:\r\n1. Loading GT and CC Detection\r\n2. Skeleton and Contour\r\n3. Distance Weights for Recall\r\n4. Loading Inverted GT and CC Detection\r\n5. Skeleton\r\n6. Distance Weights for Precision\r\n7. Releasing Mem and Terminating\r\n'
            if (output != done_msg):
                print(output)

        files = get_image_files(self.path_in)
        if not files:
            print('No suitable file found.')
            return -1

        for f in tqdm.tqdm(files):
            
            img_base_name = os.path.splitext(os.path.basename(f))[0]
            # print(img_base_name)
            removed_list = ['BT44', 'BT50', 'EA0', 'EA1', 'EA47', 'EA59', 'EA60', 'EA62', 'EA63', 'EA64']
            # if any(img_base_name in r for r in removed_list):
            if img_base_name in removed_list:
            # if img_base_name == 'EA47' or img_base_name == 'EA62' or '':
                continue

            file_out_name = convert_img(f, self.path_out, self.invert_imgs, self.msbin_gt, self.msbin_path_gt, self.fg_type)
            if self.path_dibco_bin:
                save_weights()

def main():  

    parser = argparse.ArgumentParser()
    parser.add_argument("path_in", help="input path")
    parser.add_argument("path_out", help="output path")
    # parser.add_argument("-gt", "--ground_truth", help="the images are ground truth images")
    parser.add_argument("--msbin_gt", help="the images are msbin ground truth images", action="store_true")
    parser.add_argument("-i", "--invert_imgs", help="invert input images", action="store_true")
    parser.add_argument("--path_dibco_bin", nargs="?", const="", default="")
    parser.add_argument("--msbin_path_gt", nargs="?", const="", default="")
    parser.add_argument('-fg_type', nargs='?', const=0, default=0, type=int)

    args = parser.parse_args()

    # path_dibco_weights = "C:\\cvl\\msi\\code\\BinEvalWeights"
    gt_converter = Converter(args.path_in, args.path_out, args.path_dibco_bin, args.invert_imgs, args.msbin_gt, args.msbin_path_gt, constants.map_fg_type(args.fg_type))
    gt_converter.batch_convert()

if __name__ == "__main__":
    main()  