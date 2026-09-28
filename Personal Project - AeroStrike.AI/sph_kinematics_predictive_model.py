import math

# --- INPUT VECTORS IMPORTED FROM DAY 4 ---
from physics_calculator import velocity_x as vx_ideal
from physics_calculator import velocity_y0 as vy_ideal

# --- FIFA REGULATION PHYSICAL CONSTANTS (SPH4U) ---
MASS = 0.43           # kg
RADIUS = 0.11         # meters
AREA = math.pi * (RADIUS ** 2)
DRAG_COEFF = 0.25     # Cd for a standard soccer ball
AIR_DENSITY = 1.2     # kg/m^3
GRAVITY = 9.80665     # m/s^2

# Simulation Parameters
dt = 0.001            # Tiny time step for high accuracy numerical integration (seconds)

# --- MODEL 1: IDEAL SIMULATION (NO DRAG) ---
t_ideal = 0.0
x_ideal = 0.0
y_ideal = 0.0
max_y_ideal = 0.0

curr_vy_ideal = vy_ideal
while y_ideal >= 0:
    x_ideal += vx_ideal * dt
    y_ideal += curr_vy_ideal * dt
    if y_ideal > max_y_ideal:
        max_y_ideal = y_ideal
    curr_vy_ideal -= GRAVITY * dt
    t_ideal += dt

# --- MODEL 2: REAL SIMULATION (WITH DRAG) ---
t_drag = 0.0
x_drag = 0.0
y_drag = 0.0
vx_drag = vx_ideal
vy_drag = vy_ideal
max_y_drag = 0.0

while y_drag >= 0:
    v = math.sqrt(vx_drag**2 + vy_drag**2)
    if v == 0: break
    
    f_drag = 0.5 * AIR_DENSITY * DRAG_COEFF * AREA * (v ** 2)
    f_drag_x = f_drag * (vx_drag / v)
    f_drag_y = f_drag * (vy_drag / v)
    
    ax_drag = -f_drag_x / MASS
    ay_drag = -GRAVITY - (f_drag_y / MASS)
    
    x_drag += vx_drag * dt
    y_drag += vy_drag * dt
    vx_drag += ax_drag * dt
    vy_drag += ay_drag * dt
    
    if y_drag > max_y_drag:
        max_y_drag = y_drag
    t_drag += dt

# ==================================================
# --- DAY 6: MODEL 3: 3D TRAJECTORY (WITH DRAG & SPIN) ---
# ==================================================
t_spin = 0.0
x_spin = 0.0
y_spin = 0.0
z_spin = 0.0  # New lateral (sideways) axis tracking!

vx_spin = vx_ideal
vy_spin = vy_ideal
vz_spin = 0.0  # Starts with 0 sideways velocity

max_y_spin = 0.0

# SPIN_FACTOR represents side-spin intensity. 
# Positive values curve right (+Z), negative values curve left (-Z).
SPIN_FACTOR = 0.015 

while y_spin >= 0:
    # 3D Pythagorean Theorem for net speed
    v_3d = math.sqrt(vx_spin**2 + vy_spin**2 + vz_spin**2)
    if v_3d == 0: break
    
    # 3D Drag Force magnitude
    f_drag_3d = 0.5 * AIR_DENSITY * DRAG_COEFF * AREA * (v_3d ** 2)
    
    # Resolve drag components across all 3 axes
    f_drag_x3d = f_drag_3d * (vx_spin / v_3d)
    f_drag_y3d = f_drag_3d * (vy_spin / v_3d)
    f_drag_z3d = f_drag_3d * (vz_spin / v_3d)
    
    # Magnus Force: simple lateral acceleration proportional to downfield velocity
    f_magnus_z = SPIN_FACTOR * vx_spin
    
    # Accelerations (Newton's 2nd Law)
    ax_spin = -f_drag_x3d / MASS
    ay_spin = -GRAVITY - (f_drag_y3d / MASS)
    az_spin = (-f_drag_z3d + f_magnus_z) / MASS  # Drag opposes vz, Magnus generates vz
    
    # Step forward using Euler's Method
    x_spin += vx_spin * dt
    y_spin += vy_spin * dt
    z_spin += vz_spin * dt
    
    vx_spin += ax_spin * dt
    vy_spin += ay_spin * dt
    vz_spin += az_spin * dt
    
    if y_spin > max_y_spin:
        max_y_spin = y_spin
    t_spin += dt
    
# --- CALCULATE LIVE INITIAL STATE FROM IMPORTS ---
initial_velocity = math.sqrt(vx_ideal**2 + vy_ideal**2)
launch_angle = math.degrees(math.atan2(vy_ideal, vx_ideal))

# --- OUTPUT REPORT ---
print("=== DAY 6: ADVANCED DYNAMICS 3D REPORT ===")
print("Initial State: Velocity = " + str(round(initial_velocity, 2)) + " m/s | Angle = " + str(round(launch_angle, 1)) + " degrees\n")

print("--- MODEL 1: IDEAL TRAJECTORY (VACUUM) ---")
print("Max Peak Height (Apex):  " + str(round(max_y_ideal, 3)) + " meters")
print("Predicted Total Range:  " + str(round(x_ideal, 2)) + " meters")
print("Total Flight Duration:  " + str(round(t_ideal, 3)) + " seconds\n")

print("--- MODEL 2: AERODYNAMIC DRAG TRAJECTORY ---")
print("Max Peak Height (Apex):  " + str(round(max_y_drag, 3)) + " meters")
print("Predicted Total Range:  " + str(round(x_drag, 2)) + " meters")
print("Total Flight Duration:  " + str(round(t_drag, 3)) + " seconds\n")

print("--- MODEL 3: 3D MAGNUS EFFECT TRAJECTORY ---")
print("Max Peak Height (Apex):  " + str(round(max_y_spin, 3)) + " meters")
print("Predicted Total Range:  " + str(round(x_spin, 2)) + " meters")
curve_direction = " (Right)" if z_spin >= 0 else " (Left)"
print("Total Sideways Curve:   " + str(round(abs(z_spin), 2)) + " meters" + curve_direction)
print("Total Flight Duration:  " + str(round(t_spin, 3)) + " seconds\n")

print("--- COMPONENT ANALYSIS ---")
delta_range = max(0.0, x_ideal - x_drag)
print("Air Resistance shortened the kick by: " + str(round(delta_range * 100, 1)) + " cm")
print("==================================================")