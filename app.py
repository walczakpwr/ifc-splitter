import streamlit as st
import ifcopenshell
import tempfile
import os

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="IFC Wall Extractor (Wersja Turbo)", page_icon="⚡")

st.title("⚡ IFC Wall Extractor (Wersja Turbo)")
st.write("Wersja z zaawansowanym algorytmem 'Białej Listy'. Przetwarza duże pliki w sekundy zamiast godzin.")

uploaded_file = st.file_uploader("Wybierz plik IFC", type=['ifc'])

if uploaded_file is not None:
    st.info(f"Wczytano plik: {uploaded_file.name}")
    
    if st.button("🚀 Uruchom Błyskawiczne Czyszczenie"):
        
        with st.spinner("Błyskawiczna analiza struktury grafu IFC... (to potrwa zaledwie chwilę)"):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_in:
                tmp_in.write(uploaded_file.getvalue())
                tmp_in_path = tmp_in.name
            
            try:
                model = ifcopenshell.open(tmp_in_path)
                
                keep = set() # Nasza Biała Lista

                # 1. Szkielet projektu (Projekt, Piętra, Budynek)
                for cls in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"]:
                    for item in model.by_type(cls):
                        keep.update(model.traverse(item))
                        keep.add(item)
                        
                # 2. Tylko Ściany (IfcWall)
                for item in model.by_type("IfcWall"):
                    keep.update(model.traverse(item))
                    keep.add(item)
                    
                # 3. Otwory w ścianach (Zostawiamy dziury po usuniętych oknach/drzwiach)
                for rel in model.by_type("IfcRelVoidsElement"):
                    if rel.RelatingBuildingElement in keep:
                        keep.add(rel.RelatedOpeningElement)
                        keep.update(model.traverse(rel.RelatedOpeningElement))
                        keep.update(model.traverse(rel))
                        keep.add(rel)

                # 4. Łatanie kluczowych relacji
                for rel in model.by_type("IfcRelContainedInSpatialStructure"):
                    kept_elements = [e for e in rel.RelatedElements if e in keep]
                    if kept_elements:
                        rel.RelatedElements = kept_elements
                        keep.update(model.traverse(rel))
                        keep.add(rel)

                for rel in model.by_type("IfcRelAggregates"):
                    if rel.RelatingObject in keep:
                        kept_objects = [e for e in rel.RelatedObjects if e in keep]
                        if kept_objects:
                            rel.RelatedObjects = kept_objects
                            keep.update(model.traverse(rel))
                            keep.add(rel)

                for rel_class in ["IfcRelDefinesByProperties", "IfcRelDefinesByType", "IfcRelAssociatesMaterial"]:
                    for rel in model.by_type(rel_class):
                        if hasattr(rel, "RelatedObjects"):
                            kept_objects = [e for e in rel.RelatedObjects if e in keep]
                            if kept_objects:
                                rel.RelatedObjects = kept_objects
                                keep.update(model.traverse(rel))
                                keep.add(rel)

                # 5. Brutalne usunięcie całej reszty (poza Białą Listą)
                all_entities = set(model)
                to_remove = all_entities - keep
                
                st.write(f"📊 Elementów bezpiecznych do zachowania: {len(keep)}")
                st.write(f"🗑️ Elementów do szybkiego wycięcia: {len(to_remove)}")
                
                # Sortowanie ułatwia bezpieczne usuwanie (usuwa od najwyższych ID do najniższych)
                to_remove_sorted = sorted(list(to_remove), key=lambda x: x.id(), reverse=True)
                
                progress_bar = st.progress(0)
                total = len(to_remove_sorted)
                
                # Szybka iteracja gilotyny
                for i, entity in enumerate(to_remove_sorted):
                    try:
                        model.remove(entity)
                    except:
                        pass
                    # Odświeżanie paska rzadziej, co jeszcze bardziej przyspiesza Python!
                    if i % 3000 == 0 and total > 0:
                        progress_bar.progress(min(i / total, 1.0))
                        
                progress_bar.progress(1.0)
                
                # Zapis gotowego pliku
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_out:
                    tmp_out_path = tmp_out.name
                
                model.write(tmp_out_path)
                
                with open(tmp_out_path, "rb") as f:
                    out_bytes = f.read()
                
                st.success("✅ Generowanie zakończone! Trwało to zaledwie ułamek czasu starej metody.")
                
                st.download_button(
                    label="📥 Pobierz Błyskawiczny Plik IFC",
                    data=out_bytes,
                    file_name=f"same_sciany_turbo_{uploaded_file.name}",
                    mime="application/octet-stream"
                )
                
            except Exception as e:
                st.error(f"Wystąpił błąd podczas przetwarzania: {e}")
                
            finally:
                if os.path.exists(tmp_in_path):
                    os.remove(tmp_in_path)
                if 'tmp_out_path' in locals() and os.path.exists(tmp_out_path):
                    os.remove(tmp_out_path)
