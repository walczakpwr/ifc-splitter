import streamlit as st
import ifcopenshell
import tempfile
import os
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="IFC Extractor", page_icon="🏗️", layout="wide")

st.title("🏗️ IFC Extractor")
st.markdown("Wybierz, co chcesz zostawić w pliku. Reszta zostanie bezpiecznie wycięta, a struktura budynku zachowana.")

# --- INTERFEJS WYBORU TYPÓW ---
col1, col2 = st.columns(2)

with col1:
    popularne_typy = [
        "IfcWall", "IfcSlab", "IfcColumn", "IfcBeam", 
        "IfcWindow", "IfcDoor", "IfcRoof", "IfcStair"
    ]
    # IfcWall jest wybrane domyślnie
    wybrane_typy = st.multiselect(
        "Zaznacz elementy do zachowania:", 
        options=popularne_typy, 
        default=["IfcWall"]
    )

with col2:
    dodatkowe_typy = st.text_input(
        "Inne typy (jeśli brakuje na liście, wpisz po przecinku np. IfcFurnishingElement):"
    )

uploaded_file = st.file_uploader("Wybierz plik IFC", type=['ifc'])

if uploaded_file is not None:
    if st.button("🚀 Wyodrębnij wybrane elementy"):
        
        # Przygotowanie listy typów do zachowania
        typy_do_zachowania = set(wybrane_typy)
        if dodatkowe_typy:
            # Rozdzielamy po przecinku i usuwamy białe znaki
            typy_do_zachowania.update([t.strip() for t in dodatkowe_typy.split(",") if t.strip()])
            
        if not typy_do_zachowania:
            st.warning("Musisz wybrać przynajmniej jeden typ do zachowania!")
            st.stop()
            
        st.info(f"Filtruję plik pod kątem: {', '.join(typy_do_zachowania)}")
        
        status_text = st.empty()
        progress_bar = st.progress(0)
        start_time = time.time()
        
        # Zapis pliku do pamięci tymczasowej
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_in:
            tmp_in.write(uploaded_file.getvalue())
            tmp_in_path = tmp_in.name
            
        try:
            status_text.info("1/5 Wczytywanie pliku wejściowego...")
            f = ifcopenshell.open(tmp_in_path)
            progress_bar.progress(20)
            
            status_text.info("2/5 Inicjalizacja czystego pliku...")
            g = ifcopenshell.file(schema=f.schema)
            
            status_text.info("3/5 Odbudowa szkieletu projektu...")
            for cls in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"]:
                for item in f.by_type(cls):
                    g.add(item)
            progress_bar.progress(40)
                    
            status_text.info("4/5 Kopiowanie wybranych elementów i otworów...")
            
            # Kopiowanie tylko tych typów, które wybrał użytkownik
            for ifc_type in typy_do_zachowania:
                try:
                    elementy = f.by_type(ifc_type)
                    for el in elementy:
                        g.add(el)
                except Exception:
                    pass # Jeśli danego typu nie ma w pliku, pomijamy
                
            # Wycinanie otworów dla zachowanych elementów
            for rel in f.by_type("IfcRelVoidsElement"):
                if rel.RelatingBuildingElement.is_a() in typy_do_zachowania:
                    g.add(rel)
            progress_bar.progress(60)
            
            status_text.info("5/5 Łatanie grafu relacji...")
            keep_ids = {e.id() for e in g}
            
            for rel in f.by_type("IfcRelContainedInSpatialStructure"):
                if rel.RelatingStructure.id() in keep_ids:
                    valid = [e for e in rel.RelatedElements if e.id() in keep_ids]
                    if valid:
                        rel.RelatedElements = valid
                        g.add(rel)
                        
            for rel in f.by_type("IfcRelAggregates"):
                if rel.RelatingObject.id() in keep_ids:
                    valid = [e for e in rel.RelatedObjects if e.id() in keep_ids]
                    if valid:
                        rel.RelatedObjects = valid
                        g.add(rel)
                        
            for rel_class in ["IfcRelDefinesByProperties", "IfcRelDefinesByType", "IfcRelAssociatesMaterial"]:
                for rel in f.by_type(rel_class):
                    if hasattr(rel, "RelatedObjects"):
                        valid = [e for e in rel.RelatedObjects if e.id() in keep_ids]
                        if valid:
                            rel.RelatedObjects = valid
                            g.add(rel)
                            
            for rel in f.by_type("IfcPresentationLayerAssignment"):
                if hasattr(rel, "AssignedItems"):
                    valid = [e for e in rel.AssignedItems if e.id() in keep_ids]
                    if valid:
                        rel.AssignedItems = valid
                        g.add(rel)

            for rel in f.by_type("IfcRelConnectsPathElements"):
                if rel.RelatingElement.id() in keep_ids and rel.RelatedElement.id() in keep_ids:
                    g.add(rel)
            progress_bar.progress(90)
            
            status_text.info("Zapisywanie pliku wynikowego...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_out:
                tmp_out_path = tmp_out.name
                
            g.write(tmp_out_path)
            progress_bar.progress(100)
            
            with open(tmp_out_path, "rb") as file:
                out_bytes = file.read()
                
            status_text.success(f"✅ Gotowe! Operacja zajęła {time.time() - start_time:.1f} s.")
            
            # Bezpieczna nazwa pliku bez polskich znaków
            safe_name = uploaded_file.name.replace(" ", "_")
            
            st.download_button(
                label="📥 Pobierz przefiltrowany plik",
                data=out_bytes,
                file_name=f"filtered_{safe_name}",
                mime="application/octet-stream"
            )

        except Exception as e:
            st.error(f"Wystąpił błąd podczas przetwarzania: {e}")
            
        finally:
            if os.path.exists(tmp_in_path):
                os.remove(tmp_in_path)
            if 'tmp_out_path' in locals() and os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)
