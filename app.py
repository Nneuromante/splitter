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
        
        # Style for the gallery
        st.markdown("""
        <style>
        .scene-container {
            display: flex;
            align-items: center;
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        .thumbnail {
            width: 180px;
            height: 100px;
            object-fit: cover;
            border-radius: 4px;
        }
        .info {
            flex-grow: 1;
            margin-left: 20px;
            font-size: 16px;
        }
        .actions {
            display: flex;
            align-items: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
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
                st.image(scene["thumbnail"], use_column_width=True)
            
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
