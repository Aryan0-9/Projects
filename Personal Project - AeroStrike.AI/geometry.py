#geometry.py
#Provides camera intrinsic modeling, field line feature detection, vanishing point
#estimation, and 2D-image to 3D-world perspective projections.

import math
import cv2
import numpy as np

#Computes camera focal length in pixel units using Horizontal Field of View (HFOV).
def get_dynamic_focal_length(frame_width, hfov_degrees=65.0): #Camera field of view in degrees defaults to 65.0 (hfov_degrees).
    hfov_rad = math.radians(hfov_degrees)
    return (frame_width / 2.0) / math.tan(hfov_rad / 2.0)

#Detects straight structural lines (e.g., soccer field markings)
def detect_field_lines(frame):

    # Convert BGR to Grayscale for edge intensity mapping
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Gaussian blur to suppress fine noise and turf texture
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny edge detection with hysteresis thresholds
    edges = cv2.Canny(blur, 50, 150)

    # Hough Line Transform to detect line segments
    lines = cv2.HoughLinesP(
        edges, 
        rho=1, # Distance resolution in pixels
        theta=np.pi/180, # Angular resolution in radians
        threshold=50, # Minimum number of intersections to detect line
        minLineLength=40, # Minimum line segment length in pixels
        maxLineGap=40 # Maximum allowed gap between points on same line
    )
    return lines

#Filters detected Hough lines based on length and orientation to isolate structural field lines
def filter_field_lines(lines):
    field_lines = []
    if lines is None:
        return field_lines

    for line in lines:
        x1, y1, x2, y2 = line[0]

        #Calculate Euclidean length of line segment
        length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        #Calculate absolute line angle relative to horizontal axis
        angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))

        # Retain lines longer than 50px that align near-horizontal (<20 deg) or near-vertical (70-110 deg)
        if length > 50:
            if angle < 20 or 70 < angle < 110:
                field_lines.append((x1, y1, x2, y2))

    return field_lines

#Computes the 2D intersection coordinate (x, y) of two lines
def line_intersection(line1, line2):
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2

    # Determinant of 2D line linear system
    denominator = ((x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4))

    # Check if lines are parallel 
    if abs(denominator) < 1e-6:
        return None

    # Calculate intersection coordinates
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (y3 * y4 - y3 * x4)) / denominator
    return (int(px), int(py))

#Calculates pairwise intersection points for a collection of lines
def compute_intersections(lines):
    intersections = []

    # Iterate through every unique pair of detected lines without repeating pairs 
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            pt = line_intersection(lines[i], lines[j])
            if pt is not None:
                intersections.append(pt)
    return intersections

#Constructs a 3D rotation matrix
def build_rotation_matrix(yaw_deg, pitch_deg):

    yaw = math.radians(yaw_deg) # Horizontal panning angle
    pitch = math.radians(pitch_deg) #Vertical tilting angle

    # Yaw Rotation Matrix (about Y-axis)
    Ry = np.array([
        [math.cos(yaw), 0, math.sin(yaw)],
        [0, 1, 0],
        [-math.sin(yaw), 0, math.cos(yaw)]
    ])

    # Pitch Rotation Matrix (about X-axis)
    Rx = np.array([
        [1, 0, 0],
        [0, math.cos(pitch), -math.sin(pitch)],
        [0, math.sin(pitch), math.cos(pitch)]
    ])

    return Ry @ Rx

#Estimates depth along camera optical Z-axis.
def estimate_depth_from_perspective(py, frame_width, frame_height, h_vp):

    # Default horizon at 40% frame height if vanishing point is unavailable
    horizon_y = frame_height * 0.4 if h_vp is None else h_vp[1]

    # Distance from horizon line in pixels 
    distance_from_horizon = max(py - horizon_y, 1.0)
    
    focal_length = get_dynamic_focal_length(frame_width)
    camera_height = 1.5 # Assumed static camera mounting height (meters)
    
    depth = (focal_length * camera_height) / distance_from_horizon
    return np.clip(depth, 1.0, 50.0)

#Transforms 2D image pixel coordinates into 3D world coordinates.
def image_to_world_dynamic(px, py, pixel_width, frame_width, frame_height, rotation_matrix, h_vp):
    
    ball_diameter = 0.22  
    focal_length = get_dynamic_focal_length(frame_width)

    # Use ball bounding size for depth if clear, otherwise fall back to horizon perspective
    if pixel_width > 1.5:
        depth = (focal_length * ball_diameter) / pixel_width
    else:
        depth = estimate_depth_from_perspective(px, py, frame_width, frame_height, h_vp)

    # Principal point offset
    cx = frame_width / 2.0
    cy = frame_height / 2.0

    # Pinhole camera coordinate mapping
    X_cam = (px - cx) * depth / focal_length
    Y_cam = -(py - cy) * depth / focal_length  
    Z_cam = depth

    # Apply rotation to align camera coordinates to world coordinates
    camera_point = np.array([X_cam, Y_cam, Z_cam])
    world_point = rotation_matrix @ camera_point

    return world_point[0], world_point[1], world_point[2]

#Derives camera yaw and pitch angles from the horizontal vanishing point offset relative to frame center.
def estimate_camera_orientation(h_vp, frame_width, frame_height):
    
    if h_vp is None:
        return 0.0, 0.0

    cx = frame_width / 2.0
    cy = frame_height / 2.0

    # Calculate camera focal length in pixels using the frame width and expected field-of-view
    focal = get_dynamic_focal_length(frame_width)

    # Offset from principal center point
    dx = h_vp[0] - cx
    dy = h_vp[1] - cy

    # Convert pixel offset from frame center into spatial rotation angles using trigonometry
    yaw = math.degrees(math.atan(dx / focal))
    pitch = math.degrees(math.atan(-dy / focal))
    return yaw, pitch