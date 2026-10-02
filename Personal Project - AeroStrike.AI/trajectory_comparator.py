import math

# --- INPUT VECTORS IMPORTED FROM DAY 4 ---
from physics_calculator import velocity_x as vx_initial
from physics_calculator import velocity_y0 as vy_initial
from physics_calculator import pixel_data, FPS, TIME_STEP, METERS_PER_PIXEL, GRAVITY
from sph_kinematics_predictive_model import MASS, RADIUS, AREA, DRAG_COEFF, AIR_DENSITY

# --- REAL-WORLD TRACKED DATA (From your Ball Tracker) ---

# --- PHYSICS CONSTANTS ---   
dt = 0.001            # High-precision simulation step

# Adjust this placeholder to try and match your video's curve later!
SPIN_FACTOR = 0.015  

print("=== DAY 8: ERROR ANALYSIS & CALIBRATION REPORT ===")
print("Frame | Time (s) | Error X (cm) | Error Y (cm)")
print("----------------------------------------------")

x0_pixel, y0_pixel = pixel_data[0][0], pixel_data[0][1]

# Variables to store the sum of squared errors
sum_sq_error_x = 0.0
sum_sq_error_y = 0.0
N = len(pixel_data)

for frame_idx in range(N):
    target_time = frame_idx * TIME_STEP
    
    # Convert Tracked Pixels to Real-World Meters
    tracked_x = (pixel_data[frame_idx][0] - x0_pixel) * METERS_PER_PIXEL
    tracked_y = (y0_pixel - pixel_data[frame_idx][1]) * METERS_PER_PIXEL
    
    # Run Physics Engine up to this exact timestamp
    sim_t = 0.0
    sim_x, sim_y, sim_z = 0.0, 0.0, 0.0
    vx, vy, vz = vx_initial, vy_initial, 0.0
    
    while sim_t < target_time:
        v = math.sqrt(vx**2 + vy**2 + vz**2)
        if v == 0: break
        f_drag = 0.5 * AIR_DENSITY * DRAG_COEFF * AREA * (v ** 2)
        ax = -(f_drag * (vx / v)) / MASS
        ay = -GRAVITY - ((f_drag * (vy / v)) / MASS)
        az = (-(f_drag * (vz / v)) + (SPIN_FACTOR * vx)) / MASS
        
        vx += ax * dt
        vy += ay * dt
        vz += az * dt
        sim_x += vx * dt
        sim_y += vy * dt
        sim_z += vz * dt
        sim_t += dt
        
    # Calculate absolute differences in centimeters
    error_x_cm = (tracked_x - sim_x) * 100
    error_y_cm = (tracked_y - sim_y) * 100
    
    # Accumulate squared errors for RMSE calculation
    sum_sq_error_x += (tracked_x - sim_x) ** 2
    sum_sq_error_y += (tracked_y - sim_y) ** 2
    
    print(str(frame_idx).ljust(5) + " | " + 
          str(round(target_time, 3)).ljust(8) + " | " + 
          str(round(error_x_cm, 1)).ljust(12) + " | " + 
          str(round(error_y_cm, 1)))

# Calculate final RMSE values
rmse_x = math.sqrt(sum_sq_error_x / N) * 100
rmse_y = math.sqrt(sum_sq_error_y / N) * 100

print("----------------------------------------------")
print("HORIZONTAL TRACKING RMSE: " + str(round(rmse_x, 2)) + " cm")
print("VERTICAL TRACKING RMSE:   " + str(round(rmse_y, 2)) + " cm")
print("==============================================")