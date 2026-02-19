import streamlit as st
import ifcopenshell
import tempfile
import os
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="IFC Extractor - Pro", page_icon="🏗️", layout="wide")

st.title("🏗️ IFC Extractor (Z naprawą struktury Tekli)")
st.markdown("Wybierz typy do zachowania. Skrypt automatycznie naprawi błędy z 'niewidzialnymi' elementami (np. osieroconymi ścianami z Tekla Structures).")

# --- INTERFEJS WYBORU TYPÓW ---
col1, col2 = st.columns(2)

with col1:
    popularne_typy = [
        "IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcColumn", "IfcBeam", 
        "IfcWindow", "IfcDoor", "IfcRoof", "IfcElementAssembly"
    ]
    wybrane_typy = st.multiselect(
        "Zaznacz elementy do zachowania:", 
        options=popularne_typy, 
        default=["IfcWall", "IfcWallStandardCase"] # Dodano typ StandardCase!
    )

with col2:
    dodatkowe_typy = st.text_input("Inne typy (po przecinku):")

uploaded_file = st.file_uploader("Wybierz plik IFC", type=['ifc'])

if uploaded_file is not None:
    if st.button("🚀 Wyodrębnij wybrane elementy"):
        
        typy_do_zachowania = set(wybrane_typy)
        if dodatkowe_typy:
            typy_do_zachowania.update([t.strip() for t in dodatkowe_typy.split(",") if t.strip()])
            
        status_text = st.empty()
        progress_bar = st.progress(0)
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_in:
            tmp_in.write(uploaded_file.getvalue())
            tmp_in_path = tmp_in.name
            
        try:
            status_text.info("1/5 Wczytywanie pliku wejściowego...")
            f = ifcopenshell.open(tmp_in_path)
            progress_bar.progress(20)
            
            status_text.info("2/5 Odbudowa struktury budynku...")
            g = ifcopenshell.file(schema=f.schema)
            
            # Kopiowanie czystych pięter i budynków
            for cls in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"]:
                for item in f.by_type(cls):
                    g.add(item)
                    
            # Odtworzenie relacji między samymi piętrami a budynkiem
            for rel in f.by_type("IfcRelAggregates"):
                if rel.RelatingObject.is_a() in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey"]:
                    valid = [c for c in rel.RelatedObjects if c.is_a() in ["IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"]]
                    if valid:
                        rel.RelatedObjects = valid
                        g.add(rel)
            progress_bar.progress(40)
                    
            status_text.info("3/5 Mapowanie oryginalnych lokalizacji elementów (Detektyw)...")
            container_map = {}
            parent_map = {}
            
            # Zbieramy informacje gdzie co było przed usunięciem
            for rel in f.by_type("IfcRelContainedInSpatialStructure"):
                for el in rel.RelatedElements:
                    container_map[el.id()] = rel.RelatingStructure
            for rel in f.by_type("IfcRelAggregates"):
                for child in rel.RelatedObjects:
                    parent_map[child.id()] = rel.RelatingObject
                    
            def get_spatial_container(elem_id):
                if elem_id in container_map: return container_map[elem_id]
                if elem_id in parent_map: return get_spatial_container(parent_map[elem_id].id())
                return None

            status_text.info("4/5 Kopiowanie elementów i wiązanie ich z piętrami...")
            containment_groups = {}
            default_struct = f.by_type("IfcBuilding")[0] if f.by_type("IfcBuilding") else None
            
            # Kopiujemy elementy z wybranych typów
            for ifc_type in typy_do_zachowania:
                try:
                    for el in f.by_type(ifc_type):
                        g.add(el)
                        # Szukamy do jakiego piętra powinny należeć
                        struct = get_spatial_container(el.id())
                        if not struct: struct = default_struct
                        if struct: containment_groups.setdefault(struct.id(), []).append(el)
                except Exception:
                    pass
            progress_bar.progress(60)
            
            status_text.info("5/5 Tworzenie nowych, czystych relacji w pliku...")
            # Przypisujemy wybrane elementy bezpośrednio do właściwych pięter!
            for struct_id, elements in containment_groups.items():
                struct = f.by_id(struct_id)
                g.createIfcRelContainedInSpatialStructure(
                    GlobalId=ifcopenshell.guid.new(),
                    OwnerHistory=struct.OwnerHistory if hasattr(struct, 'OwnerHistory') else None,
                    Name="Naprawiona Struktura",
                    RelatedElements=elements,
                    RelatingStructure=struct
                )
                
            # Wycinanie otworów w ścianach
            for rel in f.by_type("IfcRelVoidsElement"):
                if rel.RelatingBuildingElement.is_a() in typy_do_zachowania:
                    g.add(rel)
            
            # Przywracanie materiałów i relacji elementów zachowanych
            keep_ids = {e.id() for e in g}
            for rel_class in ["IfcRelDefinesByProperties", "IfcRelDefinesByType", "IfcRelAssociatesMaterial"]:
                for rel in f.by_type(rel_class):
                    if hasattr(rel, "RelatedObjects"):
                        valid = [e for e in rel.RelatedObjects if e.id() in keep_ids]
                        if valid:
                            rel.RelatedObjects = valid
                            g.add(rel)
            progress_bar.progress(90)
            
            status_text.info("Zapisywanie naprawionego pliku wynikowego...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_out:
                tmp_out_path = tmp_out.name
                
            g.write(tmp_out_path)
            progress_bar.progress(100)
            
            with open(tmp_out_path, "rb") as file:
                out_bytes = file.read()
                
            status_text.success(f"✅ Sukces! Czas naprawy: {time.time() - start_time:.1f} s.")
            st.balloons()
            
            st.download_button(
                label="📥 Pobierz Poprawiony Plik",
                data=out_bytes,
                file_name=f"poprawiony_{uploaded_file.name}",
                mime="application/octet-stream"
            )

        except Exception as e:
            st.error(f"Wystąpił błąd: {e}")
            
        finally:
            if os.path.exists(tmp_in_path): os.remove(tmp_in_path)
            if 'tmp_out_path' in locals() and os.path.exists(tmp_out_path): os.remove(tmp_out_path)
