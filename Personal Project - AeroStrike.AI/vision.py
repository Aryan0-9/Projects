# vision.py
#Performs automated computer vision frame analysis, MOG2 background subtraction,
#contour filtering for ball detection, and lateral curve spin estimations.

import math
import cv2
import numpy as np

#Reads a video file to isolate and track a soccer ball using background subtraction and contour geometric properties.
def track_ball_and_calibrate(video_path):

    # Open the video file stream from the given file path 
    cap = cv2.VideoCapture(video_path)

    # Read the video file's frame rate 
    native_fps = cap.get(cv2.CAP_PROP_FPS)

    # If the video file is missing FPS metadata or reports 0, default to a standard 30.0 frames per second to prevent divide by zero errors
    if native_fps is None or native_fps == 0:
        native_fps = 30.0 
        
    points = []
    detected_pixel_widths = []
    
    fgbg = cv2.createBackgroundSubtractorMOG2(history=150, varThreshold=35, detectShadows=False)
    frame_count = 0
    FRAME_SKIP = 3  # Downsample execution rate to boost processing performance
    last_known_center = None
    frame_width, frame_height = 640, 360
    
    # Loop through the video file while the stream remains open
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame is None:
            break
            
        frame_count += 1
        if frame_count % FRAME_SKIP != 0:
            continue
            
        max_width = 640 # Downscale frame for speed and standardized geometry
        if frame.shape[1] > max_width:
            scale_ratio = max_width / frame.shape[1]
            frame = cv2.resize(frame, (max_width, int(frame.shape[0] * scale_ratio)), interpolation=cv2.INTER_AREA)
        
        frame_height, frame_width = frame.shape[:2]

        # Isolate moving objects
        fgmask = fgbg.apply(frame)

        # Remove isolated noise pixels
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
        
        # Extract contour borders
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_ball_contours = []
        
        # Iterate over every detected motion outline (contour) in the current frame
        for c in contours:
            area = cv2.contourArea(c)

            # Filter 1: Area thresholding
            if area > 12:

                # Find the bounding rectangle around the contour to get its width (w) and height (h)
                x, y, w, h = cv2.boundingRect(c)
                aspect_ratio = float(w) / h
                
                # Filter 2: Bounding Box Aspect Ratio (Target ~1.0 for spherical objects)
                if 0.5 <= aspect_ratio <= 1.8:
                    perimeter = cv2.arcLength(c, True)
                    if perimeter > 0:

                        # Filter 3: Circularity Metric = (4 * pi * Area) / (Perimeter^2)
                        circularity = (4 * math.pi * area) / (perimeter ** 2)
                        if circularity > 0.60:
                            try:

                                # Fit ellipse to estimate precise spherical diameter
                                if len(c) >= 5:
                                    ellipse = cv2.fitEllipse(c)
                                    (_, _), (major_axis, minor_axis), angle = ellipse
                                    ball_pixel_dimension = (major_axis + minor_axis) / 2.0
                                else:
                                    (_, _), radius = cv2.minEnclosingCircle(c)
                                    ball_pixel_dimension = radius * 2.0
                            except cv2.error:
                                (_, _), radius = cv2.minEnclosingCircle(c)
                                ball_pixel_dimension = radius * 2.0
                            
                            valid_ball_contours.append((c, area, ball_pixel_dimension))

        # Pick candidate contour closest to previous position           
        if valid_ball_contours:
            best_contour_match = None
            if last_known_center is None:
                best_contour_match = max(valid_ball_contours, key=lambda item: item[1])
            
            # Helper function to compute the 2D distance formula: sqrt((x2 - x1)^2 + (y2 - y1)^2)
            else:
                def distance_from_last_center(item):
                    contour = item[0]

                    # Calculate Spatial Centroid using image moments
                    M = cv2.moments(contour)
                    if M["m00"] != 0:

                        # Centroid pixel coordinates (cX, cY)
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])

                        # Return distance in pixels from the ball's last position
                        return math.sqrt((cX - last_known_center[0])**2 + (cY - last_known_center[1])**2)
                    return float('inf')
                
                # Find the candidate contour closest to the ball's position in the previous frame
                closest_contour = min(valid_ball_contours, key=distance_from_last_center)

                # Spatial distance threshold: accept match only if it moved less than 150 pixels;
                # prevents jumping to a different moving object (like a player's foot)
                if distance_from_last_center(closest_contour) < 150:
                    best_contour_match = closest_contour

            # If a valid ball match was successfully found in this frame
            if best_contour_match:

                # Unpack contour shape geometry (target_contour) and measured pixel diameter (ball_pixel_dimension)
                target_contour = best_contour_match[0]
                ball_pixel_dimension = best_contour_match[2]
                
                M = cv2.moments(target_contour)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    points.append((cX, cY, frame_count, ball_pixel_dimension))
                    detected_pixel_widths.append(ball_pixel_dimension)
                    last_known_center = (cX, cY)
                    
    cap.release()
    
    # Calculate scale factor using Interquartile Range (IQR) filtered mean width
    if detected_pixel_widths:
        q25, q75 = np.percentile(detected_pixel_widths, [25, 75])
        filtered_widths = [w for w in detected_pixel_widths if q25 <= w <= q75]
        avg_pixel_width = np.mean(filtered_widths) if filtered_widths else np.median(detected_pixel_widths)
        computed_scale = 0.22 / max(avg_pixel_width, 1e-4)
    else:
        computed_scale = 0.010722 # Fallback empirical constant
        
    return points, native_fps, computed_scale, FRAME_SKIP, frame_width, frame_height

#Estimates initial Magnus spin coefficient from trajectory lateral curvature using discrete gradients.
def estimate_spin_from_trajectory(points):

    # Need at least 10 tracked positions to measure curve/acceleration accurately 
    # return 0 spin if insufficient motion points were captured
    if len(points) < 10:
        return 0.0
    
    # Convert list of coordinate tuples into a NumPy array for math operations
    pts = np.array(points)

    # Separate array into X coordinates and Y coordinates
    x, y = pts[:, 0], pts[:, 1]

    # Compute change in position over time step 
    vx, vy = np.gradient(x), np.gradient(y)

    # Compute change in velocity over time step clamped to realistic physical limits [-20, 20] m/s^2
    ay = np.clip(np.gradient(vy), -20, 20)
    velocity = np.sqrt(vx**2 + vy**2)
    avg_lat_acc = np.mean(ay)
    avg_vel = np.mean(velocity)

    # If average speed is 0 m/s, return 0 spin to avoid division by zero
    if avg_vel == 0:
        return 0.0

    S = 0.0005 # Empirical Magnus scaling constant
    spin = (avg_lat_acc * 0.43) / (S * avg_vel) 
    return float(np.clip(spin, -60, 60))