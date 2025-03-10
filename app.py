import streamlit as st
import cv2
import tempfile
import os
import subprocess
import shutil
from scenedetect import detect, ContentDetector
import zipfile
from io import BytesIO
import uuid

# Set page title
st.set_page_config(page_title="Video Scene Splitter", layout="wide")

# App title and description
st.title("Video Scene Splitter")
st.write("Upload videos to automatically split them into scenes.")

# Initialize session state for storing videos and scenes
if 'uploaded_videos' not in st.session_state:
    st.session_state.uploaded_videos = []
    st.session_state.video_names = []
    st.session_state.processing = False
    st.session_state.scene_gallery = []  # Store processed scenes info

# Add selected scenes to session state if not present
if 'selected_scenes' not in st.session_state:
    st.session_state.selected_scenes = []

# Initialize tabs
tab1, tab2 = st.tabs(["Process Videos", "Gallery"])

with tab1:
    # File uploader with immediate display of uploaded files
    uploaded_files = st.file_uploader("Upload videos", 
                                  type=["mp4", "mov", "avi", "mkv"], 
                                  accept_multiple_files=True)
    
    # Add newly uploaded files to session state
    if uploaded_files:
        for file in uploaded_files:
            # Check if file is not already in the list
            if file.name not in st.session_state.video_names:
                st.session_state.uploaded_videos.append(file)
                st.session_state.video_names.append(file.name)
    
    # Display list of uploaded files with X to remove
    if st.session_state.uploaded_videos:
        st.write("Uploaded Videos:")
        
        for i, video_file in enumerate(st.session_state.uploaded_videos):
            col1, col2 = st.columns([20, 1])
            with col1:
                file_size_mb = len(video_file.getvalue()) / (1024 * 1024)
                st.text(f"{video_file.name}  {file_size_mb:.1f}MB")
            with col2:
                if st.button("❌", key=f"x_{i}", help="Remove this video"):
                    st.session_state.uploaded_videos.pop(i)
                    st.session_state.video_names.pop(i)
                    st.rerun()
    
    # Advanced options
    with st.expander("Advanced Options"):
        threshold = st.slider("Scene detection sensitivity", 15, 30, 27, 1, 
                             help="Lower values create more scenes (more sensitive)")
        include_audio = st.checkbox("Include audio in output", value=False)  # Default is now False
        output_format = st.selectbox("Output format", ["mp4", "gif"], index=0)
    
    # Debug: show current state of scene gallery
    if st.session_state.scene_gallery:
        st.write(f"Debug: {len(st.session_state.scene_gallery)} scenes in gallery")
    
    # Process button (only enabled if videos are uploaded and not currently processing)
    process_button = st.button("Process Videos", 
                              disabled=len(st.session_state.uploaded_videos) == 0 or st.session_state.processing,
                              type="primary")
    
    if process_button:
        st.session_state.processing = True
        st.session_state.scene_gallery = []  # Reset gallery when processing new videos
        st.session_state.selected_scenes = []  # Reset selections
        
        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create temp directory for processing
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, "scenes")
        os.makedirs(output_dir, exist_ok=True)
        
        all_scene_files = []
        total_videos = len(st.session_state.uploaded_videos)
        
        # Process each video
        for video_idx, video_file in enumerate(st.session_state.uploaded_videos):
            # Calculate base progress percentage for this video (0-1 scale)
            video_progress_base = video_idx / total_videos if total_videos > 0 else 0
            status_text.text(f"Processing video {video_idx+1}/{total_videos}: {video_file.name}")
            
            # Save file temporarily
            temp_file_path = os.path.join(temp_dir, video_file.name)
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(video_file.getbuffer())
            
            try:
                # Detect scenes
                status_text.text(f"Detecting scenes in {video_file.name}...")
                progress_bar.progress(video_progress_base + 0.05/total_videos if total_videos > 0 else 0.05)
                
                scenes = detect(temp_file_path, ContentDetector(threshold=threshold))
                
                if not scenes:
                    st.warning(f"No scene changes detected in {video_file.name}. Try lowering the threshold value.")
                    progress_bar.progress(video_progress_base + 0.9/total_videos if total_videos > 0 else 0.9)
                else:
                    progress_bar.progress(video_progress_base + 0.1/total_videos
