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
                progress_val = video_progress_base + (0.05/total_videos if total_videos > 0 else 0.05)
                progress_bar.progress(progress_val)
                
                scenes = detect(temp_file_path, ContentDetector(threshold=threshold))
                
                if not scenes:
                    st.warning(f"No scene changes detected in {video_file.name}. Try lowering the threshold value.")
                    progress_val = video_progress_base + (0.9/total_videos if total_videos > 0 else 0.9)
                    progress_bar.progress(progress_val)
                else:
                    progress_val = video_progress_base + (0.1/total_videos if total_videos > 0 else 0.1)
                    progress_bar.progress(progress_val)
                    
                    # Use ffmpeg to split video
                    status_text.text(f"Splitting {video_file.name} into scenes...")
                    video_scene_files = []
                    base_name = os.path.splitext(os.path.basename(temp_file_path))[0]
                    
                    # Process each scene
                    for idx, (start, end) in enumerate(scenes, start=1):
                        # Calculate the progress within this video's portion
                        scene_portion = 0.8 / total_videos if total_videos > 0 else 0.8
                        scene_progress = (idx / len(scenes)) * scene_portion if len(scenes) > 0 else 0
                        current_progress = min(video_progress_base + (0.1/total_videos if total_videos > 0 else 0.1) + scene_progress, 1.0)
                        progress_bar.progress(current_progress)
                        
                        # Prepare output filename - sanitize base_name to remove problematic characters
                        safe_base_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in base_name)
                        if output_format == "gif":
                            output_file = os.path.join(output_dir, f"{safe_base_name}_scene{idx}.gif")
                        else:
                            output_file = os.path.join(output_dir, f"{safe_base_name}_scene{idx}.mp4")
                        
                        # Prepare ffmpeg command
                        command = [
                            "ffmpeg",
                            "-i", temp_file_path,
                            "-ss", str(start.get_seconds()),
                            "-t", str(end.get_seconds() - start.get_seconds()),
                        ]
                        
                        if output_format == "mp4":
                            command += [
                                "-preset", "fast",
                                "-c:v", "libx264",
                                "-crf", "23",
                            ]
                            if include_audio:
                                command += ["-c:a", "aac"]
                            else:
                                command += ["-an"]
                        else:  # GIF
                            command += [
                                "-vf", "fps=10,scale=480:-1:flags=lanczos",
                                "-loop", "0",
                                "-c:v", "gif"
                            ]
                        
                        command += ["-y", output_file]
                        
                        # Extract a thumbnail for the gallery
                        thumbnail_file = os.path.join(output_dir, f"{safe_base_name}_scene{idx}_thumb.jpg")
                        thumb_cmd = [
                            "ffmpeg",
                            "-i", temp_file_path,
                            "-ss", str(start.get_seconds() + (end.get_seconds() - start.get_seconds()) / 2),  # Middle of scene
                            "-vframes", "1",  # Extract one frame
                            "-q:v", "2",  # High quality
                            "-y", thumbnail_file
                        ]
                        
                        try:
                            # Process scene
                            subprocess.run(command, check=True, capture_output=True)
                            
                            # Generate thumbnail
                            subprocess.run(thumb_cmd, check=True, capture_output=True)
                            
                            # Verify the output file exists and has content
                            if os.path.exists(output_file) and os.path.getsize(output_file) > 10000:
                                video_scene_files.append(output_file)
                                all_scene_files.append(output_file)
                                
                                # Add to gallery data
                                with open(output_file, "rb") as f:
                                    video_bytes = f.read()
                                
                                with open(thumbnail_file, "rb") as f:
                                    thumbnail_bytes = f.read()
                                
                                # Add scene to gallery
                                st.session_state.scene_gallery.append({
                                    "source_video": video_file.name,
                                    "scene_number": idx,
                                    "scene_data": video_bytes,
                                    "thumbnail": thumbnail_bytes,
                                    "start_time": str(start),
                                    "end_time": str(end),
                                    "duration": end.get_seconds() - start.get_seconds(),
                                    "format": output_format
                                })
                                
                                status_text.text(f"Processed scene {idx} of {len(scenes)} for {video_file.name}")
                            else:
                                st.warning(f"Scene {idx} of {video_file.name} may not have processed correctly.")
                        except subprocess.CalledProcessError as e:
                            st.error(f"Error processing scene {idx} of {video_file.name}: {str(e)}")
                    
                    # Update progress to the end of this video's portion
                    progress_val = min((video_idx + 1) / total_videos if total_videos > 0 else 1.0, 1.0)
                    progress_bar.progress(progress_val)
                    
                    # Display summary for this video
                    st.info(f"Successfully processed {len(video_scene_files)} out of {len(scenes)} scenes from {video_file.name}")
            
            except Exception as e:
                st.error(f"Error processing {video_file.name}: {str(e)}")
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text("Processing complete!")
        
        # Create a ZIP with all scenes from all videos
        if all_scene_files:
            st.success(f"Successfully processed {len(all_scene_files)} scenes from {total_videos} videos")
            
            # Create ZIP file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for scene_path in all_scene_files:
                    zip_file.write(scene_path, os.path.basename(scene_path))
            
            # Provide download button for ZIP
            zip_size = len(zip_buffer.getvalue()) / (1024*1024)  # Size in MB
            st.download_button(
                label=f"Download All Scenes as ZIP ({zip_size:.1f} MB)",
                data=zip_buffer.getvalue(),
                file_name=f"all_scenes_{uuid.uuid4().hex[:8]}.zip",
                mime="application/zip",
                key="download_all"
            )
            
            st.success("View all processed scenes in the Gallery tab")
        
        # Clean up temporary files
        shutil.rmtree(temp_dir)
        
        # Reset processing state
        st.session_state.processing = False

# Gallery tab to display processed scenes
with tab2:
    st.header("Scene Gallery")
    
    if not st.session_state.scene_gallery:
        st.info("No scenes have been processed yet. Go to the Process Videos tab to split videos into scenes.")
    else:
        # Add filter options
        filter_videos = st.multiselect(
            "Filter by source video:",
            options=list(set(scene["source_video"] for scene in st.session_state.scene_gallery)),
            default=list(set(scene["source_video"] for scene in st.session_state.scene_gallery))
        )
        
        # Filter scenes based on selection
        filtered_scenes = [scene for scene in st.session_state.scene_gallery 
                          if scene["source_video"] in filter_videos]
        
        # Show batch download only if scenes are selected
        if 'selected_scenes' in st.session_state and st.session_state.selected_scenes:
            selected_count = len(st.session_state.selected_scenes)
            
            # Create a ZIP with selected scenes
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for scene_idx in st.session_state.selected_scenes:
                    scene = st.session_state.scene_gallery[scene_idx]
                    scene_file_name = f"{scene['source_video'].split('.')[0]}_scene{scene['scene_number']}.{scene['format']}"
                    zip_file.writestr(scene_file_name, scene["scene_data"])
            
            # Display info and download button
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"{selected_count} scenes selected")
            
            with col2:
                zip_size = len(zip_buffer.getvalue()) / (1024*1024)  # Size in MB
                st.download_button(
                    label=f"Download Selected ({zip_size:.1f} MB)",
                    data=zip_buffer.getvalue(),
                    file_name=f"selected_scenes.zip",
                    mime="application/zip",
                    key="download_selected"
                )
        
        # Display each scene in a simple row format (image - text - actions)
        for i, scene in enumerate(filtered_scenes):
            scene_idx = st.session_state.scene_gallery.index(scene)
            scene_file_name = f"{scene['source_video'].split('.')[0]}_scene{scene['scene_number']}.{scene['format']}"
            
            # Create a row with 3 columns
            col1, col2, col3 = st.columns([2, 6, 1])
            
            # Column 1: Thumbnail image
            with col1:
                st.image(scene["thumbnail"], use_container_width=True)
            
            # Column 2: File name and duration
            with col2:
                st.markdown(f"**{scene_file_name}** // **{scene['duration']:.2f}s**")
                
                # You can add a hidden expander for preview here if needed
                with st.expander("Preview", expanded=False):
                    if scene["format"] == "mp4":
                        st.video(scene["scene_data"])
                    else:
                        st.image(scene["scene_data"])
            
            # Column 3: Selection checkbox and download button
            with col3:
                # Create a container for the actions
                action_container = st.container()
                
                # Selection checkbox
                is_selected = scene_idx in st.session_state.selected_scenes
                if action_container.checkbox("", value=is_selected, key=f"select_{scene_idx}"):
                    if scene_idx not in st.session_state.selected_scenes:
                        st.session_state.selected_scenes.append(scene_idx)
                else:
                    if scene_idx in st.session_state.selected_scenes:
                        st.session_state.selected_scenes.remove(scene_idx)
                
                # Download button
                action_container.download_button(
                    "↓",
                    data=scene["scene_data"],
                    file_name=scene_file_name,
                    mime=f"video/{scene['format']}" if scene['format'] == "mp4" else "image/gif",
                    key=f"download_single_{scene_idx}"
                )
            
            # Add a separator
            st.markdown("---")
        
        # Show info about total scenes
        st.caption(f"Showing {len(filtered_scenes)} scenes out of {len(st.session_state.scene_gallery)} total")

# Footer
st.markdown("---")
st.caption("Video Scene Splitter - Automatically split videos into scenes")
