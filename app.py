# Gallery tab to display processed scenes
with tab2:
    st.header("Scene Gallery")
    
    if not st.session_state.scene_gallery:
        st.info("No scenes have been processed yet. Go to the Process Videos tab to split videos into scenes.")
    else:
        st.success(f"Showing {len(st.session_state.scene_gallery)} scenes from all processed videos")
        
        # Add filter options
        filter_videos = st.multiselect(
            "Filter by source video:",
            options=list(set(scene["source_video"] for scene in st.session_state.scene_gallery)),
            default=list(set(scene["source_video"] for scene in st.session_state.scene_gallery))
        )
        
        # Filter scenes based on selection
        filtered_scenes = [scene for scene in st.session_state.scene_gallery 
                          if scene["source_video"] in filter_videos]
        
        # Add selection functionality
        if 'selected_scenes' not in st.session_state:
            st.session_state.selected_scenes = []
        
        # Batch download button (only show if scenes are selected)
        if st.session_state.selected_scenes:
            # Create a ZIP with selected scenes
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for scene_idx in st.session_state.selected_scenes:
                    scene = st.session_state.scene_gallery[scene_idx]
                    scene_file_name = f"{scene['source_video'].split('.')[0]}_scene{scene['scene_number']}.{scene['format']}"
                    zip_file.writestr(scene_file_name, scene["scene_data"])
            
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"{len(st.session_state.selected_scenes)} scenes selected")
            with col2:
                # Provide download button for ZIP of selected scenes
                zip_size = len(zip_buffer.getvalue()) / (1024*1024)  # Size in MB
                st.download_button(
                    label=f"Download Selected ({zip_size:.1f} MB)",
                    data=zip_buffer.getvalue(),
                    file_name=f"selected_scenes.zip",
                    mime="application/zip",
                    key="download_selected"
                )
            
            # Add clear selection button
            if st.button("Clear Selection"):
                st.session_state.selected_scenes = []
                st.rerun()
        
        # Custom CSS for gallery items
        st.markdown("""
        <style>
        .gallery-item {
            display: flex;
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 8px;
            background-color: #f0f0f0;
        }
        .gallery-thumbnail {
            width: 200px;
            height: 120px;
            object-fit: cover;
            border-radius: 5px;
        }
        .gallery-info {
            margin-left: 15px;
            flex-grow: 1;
        }
        .gallery-actions {
            display: flex;
            align-items: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display scenes in a list format like the image
        for i, scene in enumerate(filtered_scenes):
            scene_idx = st.session_state.scene_gallery.index(scene)
            scene_file_name = f"{scene['source_video'].split('.')[0]}_scene{scene['scene_number']}.{scene['format']}"
            
            col1, col2, col3 = st.columns([2, 5, 1])
            
            with col1:
                # Display thumbnail
                st.image(scene["thumbnail"], width=200)
            
            with col2:
                # Display file name and duration
                st.markdown(f"**{scene_file_name}** // **{scene['duration']:.2f}s**")
                
                # Add a "Play" button/expander
                with st.expander("Preview Scene"):
                    if scene["format"] == "mp4":
                        st.video(scene["scene_data"])
                    else:  # GIF
                        st.image(scene["scene_data"])
            
            with col3:
                # Checkbox to select scene
                is_selected = scene_idx in st.session_state.selected_scenes
                if st.checkbox("", value=is_selected, key=f"select_{scene_idx}"):
                    if scene_idx not in st.session_state.selected_scenes:
                        st.session_state.selected_scenes.append(scene_idx)
                else:
                    if scene_idx in st.session_state.selected_scenes:
                        st.session_state.selected_scenes.remove(scene_idx)
                
                # Download button for this scene
                st.download_button(
                    "↓",
                    data=scene["scene_data"],
                    file_name=scene_file_name,
                    mime=f"video/{scene['format']}" if scene['format'] == "mp4" else "image/gif",
                    key=f"download_single_{scene_idx}"
                )
            
            st.markdown("---")
