import streamlit as st
import ifcopenshell
import ifcopenshell.util.element
import tempfile
import os
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="IFC Filter", layout="wide")

st.title("🏗️ IFC Filter - Odchudzanie plików BIM")
st.markdown("Wgraj plik IFC, wybierz elementy do zachowania i pobierz nową, lekką wersję.")

# --- FUNKCJE (Z CACHOWANIEM DLA WYDAJNOŚCI) ---

# To jest najważniejsza linijka. Dzięki niej plik ładuje się TYLKO RAZ.
@st.cache_resource 
def load_ifc(file_bytes):
    # Streamlit trzyma plik w pamięci jako bajty, musimy zapisać go tymczasowo na dysk
    # żeby ifcopenshell mógł go otworzyć
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
        tmp.write(file_bytes.getvalue())
        tmp_path = tmp.name
    
    model = ifcopenshell.open(tmp_path)
    return model, tmp_path

def process_ifc(original_model, selected_types):
    # Tworzymy nowy pusty model
    new_model = ifcopenshell.file(schema=original_model.schema)
    
    # Kopiujemy Projekt (jednostki itp.)
    for p in original_model.by_type("IfcProject"):
        ifcopenshell.util.element.copy(new_model, p)
        
    # Pasek postępu
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_elements = 0
    copied_elements = 0
    
    # Zbieramy elementy do skopiowania
    elements_to_copy = []
    for ifc_type in selected_types:
        found = original_model.by_type(ifc_type)
        elements_to_copy.extend(found)
    
    total = len(elements_to_copy)
    
    if total == 0:
        return None
        
    status_text.text(f"Rozpoczynam kopiowanie {total} elementów...")
    
    for i, element in enumerate(elements_to_copy):
        ifcopenshell.util.element.copy(new_model, element)
        
        # Aktualizacja paska postępu co 10 elementów (żeby nie zamulać)
        if i % 10 == 0:
            progress = int((i / total) * 100)
            progress_bar.progress(progress)
            
    progress_bar.progress(100)
    status_text.text("Gotowe! Generowanie pliku do pobrania...")
    
    # Zapisz do tymczasowego pliku stringa
    return new_model.to_string()

# --- INTERFEJS UŻYTKOWNIKA ---

uploaded_file = st.file_uploader("Wybierz plik IFC (max 200MB zalecane)", type=["ifc"])

if uploaded_file is not None:
    st.success(f"Wczytano plik: {uploaded_file.name}")
    
    # Wczytujemy model (z cache!)
    try:
        model, path = load_ifc(uploaded_file)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. Wybierz co chcesz zachować")
            
            # Lista popularnych typów do wyboru
            all_types = ["IfcWall", "IfcSlab", "IfcWindow", "IfcDoor", "IfcRoof", "IfcColumn", "IfcBeam"]
            
            # Checkboxy
            selected_types = []
            for t in all_types:
                # Domyślnie zaznacz IfcWall
                default_val = True if t == "IfcWall" else False
                if st.checkbox(f"Zachowaj {t}", value=default_val):
                    selected_types.append(t)
            
            # Opcja dla zaawansowanych: wpisz własny typ
            other_type = st.text_input("Inny typ (np. IfcFurnishingElement)")
            if other_type:
                selected_types.append(other_type)

        with col2:
            st.subheader("2. Podsumowanie")
            st.write(f"Wybrane typy: {selected_types}")
            
            if st.button("🚀 URUCHOM FILTROWANIE"):
                if not selected_types:
                    st.error("Musisz wybrać przynajmniej jeden typ!")
                else:
                    result_string = process_ifc(model, selected_types)
                    
                    if result_string:
                        st.balloons()
                        st.download_button(
                            label="📥 Pobierz przetworzony plik IFC",
                            data=result_string,
                            file_name=f"filtered_{uploaded_file.name}",
                            mime="application/x-step"
                        )
                    else:
                        st.warning("Nie znaleziono żadnych elementów wybranych typów w tym pliku.")

    except Exception as e:
        st.error(f"Błąd podczas przetwarzania pliku: {e}")
