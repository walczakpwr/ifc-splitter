import streamlit as st
import ifcopenshell
import ifcopenshell.api
import tempfile
import os

st.set_page_config(page_title="IFC Splitter", layout="wide")

st.title("IFC Splitter")
st.markdown("Upload an IFC file, select entities to keep, and download the filtered file.")

# File Uploader
uploaded_file = st.file_uploader("Choose an IFC file", type=["ifc"])

if uploaded_file is not None:
    # Reset file pointer to be sure
    uploaded_file.seek(0)
    
    # Save uploaded file to temp file
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".ifc")
    tfile.write(uploaded_file.read())
    tfile.close()
    
    file_path = tfile.name
    
    try:
        ifc_file = ifcopenshell.open(file_path)
        st.success(f"Loaded {uploaded_file.name} successfully!")
        
        # Get all IfcProduct types (physical elements)
        products = ifc_file.by_type("IfcProduct")
        
        if not products:
             st.warning("No IfcProduct found in the file.")
             entity_types = []
        else:
             # Get unique types
             entity_types = sorted(list(set([p.is_a() for p in products])))
        
        st.subheader("Filter Entities")
        selected_types = st.multiselect("Select IFC Entities to KEEP:", entity_types, default=entity_types)
        
        if st.button("Generate Filtered IFC"):
            if not selected_types:
                st.warning("Please select at least one entity type.")
            else:
                with st.spinner("Processing..."):
                    
                    always_keep = ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcOpeningElement"]
                    types_to_remove = [t for t in entity_types if t not in selected_types and t not in always_keep]
                    st.write(f"DEBUG: Types selected to remove: {types_to_remove}")
                    st.info("Note: Spatial structure (Project, Site, Building, Storey) and Openings are automatically preserved.")
                    
                    output_path = os.path.join(tempfile.gettempdir(), f"filtered_{uploaded_file.name}")
                    
                    # Re-open fresh
                    f_out = ifcopenshell.open(file_path)
                    
                    count_removed = 0
                    count_found = 0
                    
                    # Optimization: Get all instances of types to remove
                    for type_name in types_to_remove:
                        instances = f_out.by_type(type_name)
                        count_found += len(instances)
                        st.write(f"DEBUG: Found {len(instances)} items of type {type_name}")
                        
                        for inst in instances:
                            # Use API to safely remove product and its relationships
                            try:
                                ifcopenshell.api.run("root.remove_product", f_out, product=inst)
                                count_removed += 1
                            except Exception as e:
                                st.error(f"Error removing {inst}: {e}")
                            
                    f_out.write(output_path)
                    
                    st.success(f"Done! Found {count_found} items to remove. Removed {count_removed} items.")
                    
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="Download Filtered IFC",
                            data=f,
                            file_name=f"filtered_{uploaded_file.name}",
                            mime="application/x-step"
                        )
                        
    except Exception as e:
        st.error(f"Error reading IFC file: {e}")
    finally:
        # Cleanup temp file?
        # os.unlink(file_path) 
        pass
