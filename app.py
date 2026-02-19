import streamlit as st
import ifcopenshell
import tempfile
import os
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="IFC Wall Extractor (Bezpieczny)", page_icon="🧱", layout="centered")

st.title("🧱 IFC Wall Extractor")
st.markdown("Ta wersja buduje **całkowicie czysty plik IFC od zera**, przenosząc do niego tylko ściany, ich geometrię oraz niezbędny szkielet budynku (piętra, materiały).")

uploaded_file = st.file_uploader("Wybierz plik IFC (Zalecane mniejsze pliki dla Streamlit)", type=['ifc'])

if uploaded_file is not None:
    st.info(f"Wczytano plik: {uploaded_file.name}")
    
    if st.button("🚀 Wyodrębnij ściany"):
        
        # Puste miejsce na komunikaty o statusie
        status_text = st.empty()
        progress_bar = st.progress(0)
        start_time = time.time()
        
        # 1. Zapisujemy wgrany plik do pamięci tymczasowej serwera
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_in:
            tmp_in.write(uploaded_file.getvalue())
            tmp_in_path = tmp_in.name
            
        try:
            status_text.info("1/5 Wczytywanie pliku wejściowego...")
            f = ifcopenshell.open(tmp_in_path)
            progress_bar.progress(20)
            
            status_text.info("2/5 Inicjalizacja nowego, czystego pliku...")
            g = ifcopenshell.file(schema=f.schema)
            
            status_text.info("3/5 Odbudowa szkieletu projektu (Project, Building, Storey)...")
            for cls in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"]:
                for item in f.by_type(cls):
                    g.add(item)
            progress_bar.progress(40)
                    
            status_text.info("4/5 Kopiowanie ścian i wycinanie otworów...")
            walls = f.by_type("IfcWall")
            for wall in walls:
                g.add(wall) # To automatycznie zaciąga też geometrię ściany
                
            # Wycinamy otwory w skopiowanych ścianach
            for rel in f.by_type("IfcRelVoidsElement"):
                if rel.RelatingBuildingElement.is_a("IfcWall"):
                    g.add(rel)
            progress_bar.progress(60)
            
            status_text.info("5/5 Łatanie grafu (przywracanie relacji i materiałów)...")
            # Pobieramy ID elementów, które zostały przeniesione, aby nie kopiować śmieci
            keep_ids = {e.id() for e in g}
            
            # Podpięcie ścian do pięter
            for rel in f.by_type("IfcRelContainedInSpatialStructure"):
                if rel.RelatingStructure.id() in keep_ids:
                    valid = [e for e in rel.RelatedElements if e.id() in keep_ids]
                    if valid:
                        rel.RelatedElements = valid
                        g.add(rel)
                        
            # Relacje hierarchiczne
            for rel in f.by_type("IfcRelAggregates"):
                if rel.RelatingObject.id() in keep_ids:
                    valid = [e for e in rel.RelatedObjects if e.id() in keep_ids]
                    if valid:
                        rel.RelatedObjects = valid
                        g.add(rel)
                        
            # Właściwości i materiały
            for rel_class in ["IfcRelDefinesByProperties", "IfcRelDefinesByType", "IfcRelAssociatesMaterial"]:
                for rel in f.by_type(rel_class):
                    if hasattr(rel, "RelatedObjects"):
                        valid = [e for e in rel.RelatedObjects if e.id() in keep_ids]
                        if valid:
                            rel.RelatedObjects = valid
                            g.add(rel)
                            
            # Warstwy (Layers)
            for rel in f.by_type("IfcPresentationLayerAssignment"):
                if hasattr(rel, "AssignedItems"):
                    valid = [e for e in rel.AssignedItems if e.id() in keep_ids]
                    if valid:
                        rel.AssignedItems = valid
                        g.add(rel)

            # Połączenia między ścianami
            for rel in f.by_type("IfcRelConnectsPathElements"):
                if rel.RelatingElement.id() in keep_ids and rel.RelatedElement.id() in keep_ids:
                    g.add(rel)
            progress_bar.progress(90)
            
            status_text.info("Zapisywanie pliku wynikowego...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_out:
                tmp_out_path = tmp_out.name
                
            g.write(tmp_out_path)
            progress_bar.progress(100)
            
            # Wczytujemy zapisany plik do pamięci, by móc go pobrać
            with open(tmp_out_path, "rb") as file:
                out_bytes = file.read()
                
            status_text.success(f"✅ Gotowe! Operacja zajęła {time.time() - start_time:.1f} sekundy.")
            st.balloons()
            
            st.download_button(
                label="📥 Pobierz plik (Tylko Ściany)",
                data=out_bytes,
                file_name=f"sciany_{uploaded_file.name}",
                mime="application/octet-stream"
            )

        except Exception as e:
            st.error(f"Wystąpił błąd podczas przetwarzania: {e}")
            
        finally:
            # Czyszczenie plików tymczasowych z serwera
            if os.path.exists(tmp_in_path):
                os.remove(tmp_in_path)
            if 'tmp_out_path' in locals() and os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)
