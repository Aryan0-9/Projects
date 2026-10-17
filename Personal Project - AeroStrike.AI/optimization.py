#optimization.py
#Estimates initial flight velocities via polynomial regression and solves for optimal
#aerodynamic properties (Cd, Magnus spin) using L-BFGS-B optimization.
import numpy as np
from scipy.optimize import minimize
from physics import run_3d_simulation

#Derives initial velocity components (vx0, vy0, vz0) by fitting polynomials to spatial point tracks.
def extract_physics_based_velocities_dynamic(world_pts, video_native_fps, video_source_type, capture_fps, frame_skip_used):
    
    # Convert tracking points into a NumPy matrix and count total frames detected
    pts = np.array(world_pts)
    n = len(pts)
    
    # Fallback default values if tracking buffer is too short
    if n < 3:
        return 28.0, 7.0, 2.0  

    # Normalize real frame delta time (dt) based on high-speed capture rates
    if video_source_type == "Broadcast Super Slow-Mo (e.g. Phantom Cam)":
        true_capture_fps = capture_fps
    else:
        true_capture_fps = video_native_fps

    # Compute the elapsed time corresponding to each tracked data point
    dt_step = frame_skip_used / max(true_capture_fps, 1.0)
    t_arr = np.array([i * dt_step for i in range(n)])

    # Fit 1st-degree polynomial for constant X, Z velocities, and 2nd-degree for parabolic Y motion
    poly_x = np.polyfit(t_arr, pts[:, 0], 1)
    poly_y = np.polyfit(t_arr, pts[:, 1], 2)
    poly_z = np.polyfit(t_arr, pts[:, 2], 1)

    # Initial velocities computed from the slope at t = 0
    vx_est = float(poly_x[0])
    vy_est = float(poly_y[1])
    vz_est = float(poly_z[0])

    return vx_est, vy_est, vz_est

#Solves for optimal Drag Coefficient (Cd) and Spin Coefficient via bounded L-BFGS-B optimization.
def fit_aerodynamic_parameters(calc_vx, calc_vy, calc_vz, detected_spin, real_world_cv_points, estimated_full_flight_time):
    
    # Set baseline starting values for optimization: default drag coefficient (0.28) and vision-detected spin
    initial_guesses = [0.28, detected_spin]

    # Parameter bounds: Cd constrained to [0.15, 0.45], Spin constrained to [-60, 60]
    bounds = [(0.15, 0.45), (-60.0, 60.0)]

    #Mean Squared Error (MSE) objective function comparing simulated vs observed points.
    def loss_function(params):
        cd_g, spin_g = params
        sim_pts, _, _, _, _ = run_3d_simulation(
            vx0=calc_vx, vy0=calc_vy, vz0=calc_vz,
            cd_val=cd_g, spin_val=spin_g,
            total_time=estimated_full_flight_time
        )

        # Convert simulated and computer vision trajectory points to NumPy arrays for comparison
        sim_arr = np.array(sim_pts)
        real_arr = np.array(real_world_cv_points)

        # Truncate both trajectories to match length, returning a large penalty if fewer than 2 points exist
        min_len = min(len(sim_arr), len(real_arr))
        if min_len < 2:
            return 1e9

        # Return Mean Squared Error across overlapping temporal points
        return np.mean((sim_arr[:min_len] - real_arr[:min_len]) ** 2)

    # Minimize Mean Squared Error using L-BFGS-B bounded optimizer
    res = minimize(loss_function, initial_guesses, bounds=bounds, method='L-BFGS-B')
    opt_Cd, opt_spin = res.x
    return opt_Cd, opt_spin