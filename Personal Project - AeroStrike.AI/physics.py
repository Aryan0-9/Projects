#physics.py
#Defines dynamic equations governing soccer ball flight trajectory (Gravity, Aerodynamic Drag, and Magnus Lift) 
#and integrates them via SciPy's RK45 ODE solver.
import math
import numpy as np
from scipy.integrate import solve_ivp

# Physical Constants
G = 9.81           # Acceleration due to gravity (m/s^2)
RHO = 1.225        # Ambient air density at sea level (kg/m^3)
R_BALL = 0.11      # Radius of standard Size 5 soccer ball (meters)
M_BALL = 0.43      # Mass of standard Size 5 soccer ball (kilograms)
A = math.pi * (R_BALL ** 2)  # Cross-sectional surface area (m^2)

#Simulates 3D projectile flight dynamics considering drag, gravity, and Magnus spin forces.
def run_3d_simulation(vx0, vy0, vz0, cd_val, spin_val, total_time):
    x0, y0, z0 = 0.0, 0.05, 0.0 # Initial spatial offset (m)
    omega = np.array([spin_val, 0.0, 0.0]) # Angular velocity spin vector
    initial_state = [x0, y0, z0, vx0, vy0, vz0]

    #Computes rates of change for position
    def physics(t, state):
        
        x, y, z, vx, vy, vz = state  # Unpacks all 6 values cleanly
        velocity = np.array([vx, vy, vz])
        speed = np.linalg.norm(velocity)

        # Zero Motion Check: If the ball's total speed is practically zero (< 0.00001 m/s),
        # stop all acceleration calculations and return zero rates of change for all 6 state variables
        # to prevent divide-by-zero errors when calculating direction vectors
        if speed < 1e-5:
            return np.zeros(6)

        # 1. Aerodynamic Quadratic Drag Force Vector Calculation
        drag_force = -0.5 * RHO * cd_val * A * speed * velocity
        drag_acc = drag_force / M_BALL

        # 2. Magnus Force Vector Calculation via Cross Product (omega x v)
        omega_mag = np.linalg.norm(omega)
        if omega_mag > 1e-6:
            CL = 0.25 # Lift Coefficient for spinning sphere
            magnus_dir = np.cross(omega, velocity) / (omega_mag * speed + 1e-8)
            magnus_force = 0.5 * RHO * A * CL * (speed**2) * magnus_dir
        else:
            magnus_force = np.array([0.0, 0.0, 0.0])

        magnus_acc = magnus_force / M_BALL

        # 3. Downward Acceleration from Gravity
        gravity = np.array([0.0, -G, 0.0])

        # Net Acceleration Vector
        acceleration = drag_acc + magnus_acc + gravity
        return [vx, vy, vz, acceleration[0], acceleration[1], acceleration[2]]

    #Event function to detect ground impact (Y = 0).
    def ground_event(t, state):
        return state[1]
    
    ground_event.terminal = True   # Stop integration when event triggers
    ground_event.direction = -1    # Only trigger when moving downwards

    t_eval_steps = np.linspace(0, total_time, 100)

    # Solve Initial Value Problem using explicit Runge-Kutta order 5(4)
    solution = solve_ivp(
        physics, [0, total_time], initial_state,
        t_eval=t_eval_steps, events=ground_event, method='RK45'
    )

    # Extract spatial trajectories
    trajectory, actual_times = [], []

    # Loop through each time step computed by the differential equation solver
    for i in range(len(solution.t)):
        x_val = float(solution.y[0][i]) # Extract the horizontal X-position (meters) at time step i
        y_val = float(solution.y[1][i]) # Extract the vertical Y-position (height above ground in meters) at time step i
        z_val = float(solution.y[2][i]) # Extract the depth Z-position (meters) at time step i

        # Ground Collision Check: Stop recording trajectory points if the ball drops below the ground (Y < 0.0m)
        # after the initial launch phase (i > 2 steps) to prevent tracking beneath the pitch surface
        if y_val < 0.0 and i > 2:
            break

        trajectory.append((x_val, max(0.0, y_val), z_val))
        actual_times.append(solution.t[i])

    # Reconstruct instant force scalar magnitudes for reporting
    drag_history, magnus_history, gravity_history = [], [], []

    # Iterate through each step along the calculated flight trajectory to extract instantaneous forces
    for i in range(len(trajectory)):
        vx = solution.y[3][i] # Extract the horizontal X-velocity component (m/s) at step i from the ODE solution matrix
        vy = solution.y[4][i] # Extract the vertical Y-velocity component (m/s) at step i from the ODE solution matrix
        vz = solution.y[5][i] # Extract the depth Z-velocity component (m/s) at step i from the ODE solution matrix
        vel = np.array([vx, vy, vz]) # Combine the individual velocity components into a 3D velocity vector [vx, vy, vz]
        speed = np.linalg.norm(vel) # Compute total scalar speed (magnitude of the velocity vector) using the Pythagorean theorem: sqrt(vx^2 + vy^2 + vz^2)
        
        # Calculate the magnitude of the fluid drag force in Newtons using the fluid dynamic equation: F_drag = 0.5 * density * Cd * Area * speed^2
        f_drag_mag = 0.5 * RHO * cd_val * A * (speed**2)

        # Compute the magnitude of the ball's angular spin rate (rad/s)
        omega_mag = np.linalg.norm(omega)
        
        # Check if the ball is spinning (spin > 0) and in motion (speed > 0) to determine if Magnus lift force applies
        if omega_mag > 1e-6 and speed > 1e-5:
            CL = 0.25 # Lift coefficient constant for a spinning spherical ball
            f_magnus_mag = 0.5 * RHO * A * CL * (speed**2) # Calculate Magnus force magnitude in Newtons: F_magnus = 0.5 * density * Area * CL * speed^2
        else:
            f_magnus_mag = 0.0
            
        drag_history.append(float(f_drag_mag))
        magnus_history.append(float(f_magnus_mag))
        gravity_history.append(float(M_BALL * G))

    return trajectory, actual_times, drag_history, magnus_history, gravity_history