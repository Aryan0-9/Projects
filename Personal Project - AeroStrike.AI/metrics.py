# metrics.py
# Calculates final quantitative performance metrics from simulated trajectories.
import math

#Computes key shot analytics including launch velocity, angle, apex height, range, and flight duration.
def compute_shot_metrics(trajectory, sim_times, vx0, vy0, vz0):

    # 3D Vector Speed Magnitude = sqrt(vx^2 + vy^2 + vz^2)
    launch_speed = math.sqrt(vx0**2 + vy0**2 + vz0**2)

    # 2D Ground plane horizontal speed
    horizontal_speed = math.sqrt(vx0**2 + vz0**2)

    # Vertical Elevation Angle = atan2(vy0, v_horizontal)
    launch_angle = math.degrees(math.atan2(vy0, max(horizontal_speed, 1e-4)))

    # Trajectory Apex (Max Y value)
    max_height = max([p[1] for p in trajectory]) if trajectory else 0.0
    
    # Horizontal Displacement Range = sqrt(dx^2 + dz^2)
    if len(trajectory) > 1:

        # Compute net displacement along the horizontal X-axis (left/right) between final and initial points
        dx = trajectory[-1][0] - trajectory[0][0]

        # Compute net displacement along the depth Z-axis (forward/backward) between final and initial points
        dz = trajectory[-1][2] - trajectory[0][2]

        # Apply 2D Pythagorean theorem to calculate absolute straight-line ground distance: sqrt(dx^2 + dz^2)
        horizontal_distance = math.sqrt(dx**2 + dz**2)
        
    else:
        # Fallback to zero horizontal distance if fewer than 2 trajectory points are recorded
        horizontal_distance = 0.0

    # Total simulated flight time
    flight_time = sim_times[-1] if sim_times else 0.0

    return {
        "launch_speed": launch_speed,
        "launch_angle": launch_angle,
        "max_height": max_height,
        "horizontal_distance": horizontal_distance,
        "flight_time": flight_time
    }