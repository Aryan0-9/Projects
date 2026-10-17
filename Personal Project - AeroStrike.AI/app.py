# app.py
# Main execution script for Aerostrike-AI.
# Integrates computer vision trajectory points, physics-based ODE solving, 
# Aerodynamic parameter optimization, and flight metric evaluation.
import os
import cv2
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Custom local modules handling the core pipeline
from geometry import (
    detect_field_lines, filter_field_lines, compute_intersections,
    estimate_camera_orientation, build_rotation_matrix, image_to_world_dynamic
)
from vision import track_ball_and_calibrate, estimate_spin_from_trajectory
from physics import run_3d_simulation
from optimization import extract_physics_based_velocities_dynamic, fit_aerodynamic_parameters
from metrics import compute_shot_metrics

# Page setup & initial interface structure  
st.set_page_config(page_title="AeroStrike AI Dashboard", layout="wide")
st.title("AeroStrike AI: Direct Video Analytics Engine")
st.markdown("*Automated ball tracking and physical vector scaling pipeline using SPH3U/SPH4U mechanics.*")
st.markdown("---")

# Sidebar controls(Inputs, calibration & dynamics tuning)
st.sidebar.header("Video Ingestion Portal")

# File uploader widget accepting raw soccer video recordings
uploaded_video = st.sidebar.file_uploader("Upload Raw Soccer Strike Video", type=["mp4", "mov", "avi"])

st.sidebar.markdown("---")
st.sidebar.subheader("Spatial Scale Calibration")

# Choose between automated ball diameter pixel tracking or manual meters-per-pixel override
calibration_mode = st.sidebar.selectbox(
    "Calibration Basis", 
    ["Automated Ball-Size Tracking", "Manual Scale Calibration Override"]
)

# Baseline spatial scale factor converting 2D pixel distances into physical 3D meters
custom_scale = 0.010722
if calibration_mode == "Manual Scale Calibration Override":
    custom_scale = st.sidebar.number_input(
        "Known Scalar (Meters per Pixel):", 
        min_value=0.0001, max_value=0.1000, value=0.010722, format="%.6f"
    )

st.sidebar.markdown("---")
st.sidebar.subheader("Camera Temporal Calibration")

# Configure recording frame rate settings for time-step velocity calculations
video_source_type = st.sidebar.selectbox(
    "Video Recording Type", 
    ["Standard Video (Real-time playback)", "Broadcast Super Slow-Mo (e.g. Phantom Cam)"]
)

# Set default recording frame rates to compute the actual physical time elapsed between frames
capture_fps, playback_fps = 240.0, 30.0

# Adjust temporal scaling if the source video is broadcast in high-speed slow motion
if video_source_type == "Broadcast Super Slow-Mo (e.g. Phantom Cam)":

    # Specify the true high-speed camera frame rate to calculate accurate time deltas (dt)
    capture_fps = st.sidebar.number_input("True Capture Frame Rate (FPS):", min_value=30.0, value=240.0, step=30.0)
    playback_fps = st.sidebar.number_input("Broadcast Playback Frame Rate (FPS):", min_value=24.0, value=30.0, step=1.0)

# Resolution adjustment toggle to correct spatial scaling when resizing HD videos
apply_resolution_scalar = st.sidebar.checkbox("Apply 1080p-to-640p Scaling Compensation?", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Dynamics Tuning Parameters (Forces)")

# Sliders allowing direct user overrides for fluid drag and Magnus spin force scalars
C_d = st.sidebar.slider("Drag Coefficient (Cd)", 0.1, 0.6, 0.3, 0.01)
spin_rate = st.sidebar.slider("Magnus Spin Coefficient (F_magnus scale)", -50.0, 50.0, 0.0, 1.0)

# Camera orientation & ball tracking
# Initialize baseline 3D transformation defaults (identity matrix and zero orientation angles)
rotation_matrix = np.eye(3)
h_vp = None
yaw, pitch = 0.0, 0.0
frame_width, frame_height = 640, 360

if uploaded_video is not None:
    # Save uploaded video binary stream to a temporary local disk file for OpenCV processing
    temp_filename = "temp_user_video.mp4"
    with open(temp_filename, "wb") as f:
        f.write(uploaded_video.read())
    
    # Read frame to extract pitch geometry and estimate camera tilt/pan angles
    cap_test = cv2.VideoCapture(temp_filename)
    cap_test.set(cv2.CAP_PROP_POS_FRAMES, 10)
    ret, test_frame = cap_test.read()

    if ret:
        # Standardize frame resolution to 640px width for consistent computer vision processing
        if test_frame.shape[1] > 640:
            scale_ratio = 640 / test_frame.shape[1]
            test_frame = cv2.resize(test_frame, (640, int(test_frame.shape[0] * scale_ratio)), interpolation=cv2.INTER_AREA)

        frame_height, frame_width = test_frame.shape[:2]

        # Detect linear field markings and extract horizontal pitch lines
        lines = detect_field_lines(test_frame)
        filtered_lines = filter_field_lines(lines)

        # Filter near-horizontal field lines (<20 degrees) to locate horizontal vanishing point
        horizontal_lines = [l for l in filtered_lines if abs(np.degrees(np.arctan2(l[3]-l[1], l[2]-l[0]))) < 20]
        horizontal_intersections = compute_intersections(horizontal_lines)
        if horizontal_intersections:
            h_vp = (int(np.mean([p[0] for p in horizontal_intersections])), 
                    int(np.mean([p[1] for p in horizontal_intersections])))

        # Calculate camera orientation (yaw and pitch angle offsets relative to the pitch)
        if h_vp is not None:
            yaw, pitch = estimate_camera_orientation(h_vp, frame_width, frame_height)

    cap_test.release()

    # Construct 3D coordinate transformation matrix using estimated yaw and pitch angles
    rotation_matrix = build_rotation_matrix(yaw, pitch)
        
    st.info("⚙️ Extracting kinematic displacement vectors dynamically...")

    # Track ball position frame-by-frame and compute scale factor from apparent ball diameter
    pixel_data, video_fps, auto_meters_per_pixel, frame_skip_used, frame_width, frame_height = track_ball_and_calibrate(temp_filename)
    
    # Remove temporary video file after processing to free memory and disk space
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
    
    # Use manual scale override value if requested by the user
    if calibration_mode == "Manual Scale Calibration Override":
        auto_meters_per_pixel = custom_scale
    
    # Verify tracking buffer captured enough points (>6 frames) for reliable motion analysis
    if len(pixel_data) > 6:
        st.sidebar.success("Scale Factor Finalized!")
        st.sidebar.metric("Target Scale Factor", f"{round(auto_meters_per_pixel, 5)} m/px")
    else:
        st.sidebar.error("Tracking buffer empty. Reverting to baseline default values.")
        video_fps = 30.0
        frame_skip_used = 3
        pixel_data = [(899, 858, 0, 28), (919, 856, 1, 28), (935, 855, 2, 27)]
        auto_meters_per_pixel = 0.010722
else:
    # Set default synthetic tracking data when no video is uploaded
    video_fps = 30.0
    frame_skip_used = 3
    auto_meters_per_pixel = custom_scale if calibration_mode == "Manual Scale Calibration Override" else 0.010722
    st.info("Upload a raw video file in the sidebar to run live velocity extractions.")
    pixel_data = [(899, 858, 0, 28), (919, 856, 1, 28), (935, 855, 2, 27)]

# Project 2D pixel coordinates into 3D camera-space world coordinates (meters)
raw_world_points = [
    image_to_world_dynamic(item[0], item[1], item[3], frame_width, frame_height, rotation_matrix, h_vp)
    for item in pixel_data
]

# Re-center trajectory coordinates relative to initial launch origin (0, 0, 0)
real_world_cv_points = []
if len(raw_world_points) > 0:
    x_base, y_base, z_base = raw_world_points[0]
    for pt in raw_world_points:
        real_world_cv_points.append((pt[0] - x_base, abs(pt[1] - y_base), pt[2] - z_base))

# Estimate Magnus spin rate (rad/s) from lateral trajectory curvature
detected_spin = estimate_spin_from_trajectory(real_world_cv_points)

#Kinematics & optimization engine
st.info("Running Optimization Engine to solve aerodynamic properties...")

# Calculate launch velocity vector components [vx0, vy0, vz0] from early tracking frame sequence
calc_vx, calc_vy, calc_vz = extract_physics_based_velocities_dynamic(
    real_world_cv_points, video_fps, video_source_type, capture_fps, frame_skip_used
)

# Estimate total flight duration based on vertical launch velocity component under gravity
estimated_full_flight_time = max(2.2 * (calc_vy / 9.81), 1.0)

# Fit drag coefficient (Cd) and spin rate using L-BFGS-B optimization to match real CV points
opt_Cd, opt_spin = fit_aerodynamic_parameters(
    calc_vx, calc_vy, calc_vz, detected_spin, real_world_cv_points, estimated_full_flight_time
)

# Execute full 3D RK45 numerical physics simulation using fitted velocity and aerodynamic values
optimized_trajectory, sim_times, drag_history, magnus_history, gravity_history = run_3d_simulation(
    vx0=calc_vx, vy0=calc_vy, vz0=calc_vz, 
    cd_val=opt_Cd, spin_val=opt_spin, 
    total_time=estimated_full_flight_time
)

# Compute scalar flight performance metrics (launch speed, peak height, distance, flight duration)
metrics = compute_shot_metrics(optimized_trajectory, sim_times, calc_vx, calc_vy, calc_vz)

# Visualization & metrics display
# Render uploaded video playback window if video source is active
if uploaded_video is not None:
    st.subheader("Input Video Playback")
    st.video(uploaded_video)

# 1. Construct 3D Interactive Trajectory Chart comparing raw CV points against simulated flight path
fig = go.Figure()
cv_df = pd.DataFrame(real_world_cv_points, columns=['X', 'Y', 'Z'])

# Plot raw 3D spatial points extracted from computer vision tracking as distinct scattered markers
fig.add_trace(go.Scatter3d(
    x=cv_df['X'], y=cv_df['Y'], z=cv_df['Z'], 
    mode='markers', marker=dict(size=5, color='#EC4899', opacity=0.8),
    name='Live Video Track Data'
))

# Format simulated RK45 physics coordinates into a DataFrame for Plotly 3D rendering
sim_df = pd.DataFrame(optimized_trajectory, columns=['X', 'Y', 'Z'])

# Overlay the optimized continuous physics trajectory as a smooth 3D curve
fig.add_trace(go.Scatter3d(
    x=sim_df['X'], y=sim_df['Y'], z=sim_df['Z'],
    mode='lines', line=dict(color='#06B6D4', width=5),
    name='Optimized Aerodynamic Fit'
))

# Label 3D axes in meters and render interactive Plotly trajectory chart in Streamlit
fig.update_layout(scene=dict(xaxis_title='Horizontal (m)', yaxis_title='Vertical (m)', zaxis_title='Depth (m)'))
st.plotly_chart(fig, use_container_width=True)

# 2. Construct Instantaneous Forces Chart (Drag Force, Magnus Force, Gravity) over time
force_fig = go.Figure()

# Generate an evenly spaced array of time values (0 to total flight duration) matching force history samples
time_stamps = np.linspace(0, metrics['flight_time'], len(drag_history))

# Add line plots comparing the magnitude of Drag, Magnus (spin curve), and Gravity forces over time
force_fig.add_trace(go.Scatter(x=time_stamps, y=drag_history, mode="lines", name="Drag (N)"))
force_fig.add_trace(go.Scatter(x=time_stamps, y=magnus_history, mode="lines", name="Magnus (N)"))
force_fig.add_trace(go.Scatter(x=time_stamps, y=gravity_history, mode="lines", name="Gravity (N)"))

# Configure axis labels in metric units and render force dynamics chart in Streamlit
force_fig.update_layout(xaxis_title="Time (s)", yaxis_title="Force Magnitude (N)")
st.plotly_chart(force_fig, use_container_width=True)

# 3. Summary Metric Cards displaying key kinematic results
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Launch Speed", f"{metrics['launch_speed']:.1f} m/s")
col2.metric("Launch Angle", f"{metrics['launch_angle']:.1f}°")
col3.metric("Peak Height", f"{metrics['max_height']:.2f} m")
col4.metric("Distance", f"{metrics['horizontal_distance']:.2f} m")
col5.metric("Flight Time", f"{metrics['flight_time']:.2f} s")