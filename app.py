import streamlit as st
import ifcopenshell
import ifcopenshell.api
import tempfile
import os

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="IFC Wall Extractor", page_icon="🏗️")

st.title("🏗️ IFC Wall Extractor")
st.write("Wgraj swój plik IFC, a aplikacja usunie z niego wszystko, co nie jest ścianą (IfcWall), zachowując pełną i poprawną strukturę pliku.")

# 1. Przycisk do wgrywania pliku przez przeglądarkę
uploaded_file = st.file_uploader("Wybierz plik IFC", type=['ifc'])

if uploaded_file is not None:
    st.info(f"Wczytano plik: {uploaded_file.name}")
    
    if st.button("🚀 Uruchom czyszczenie"):
        
        # Streamlit wyświetli kręcące się kółko ładowania
        with st.spinner("Przetwarzanie pliku... (może to potrwać kilka minut w zależności od rozmiaru)"):
            
            # 2. Zapisanie wgranego pliku do pamięci tymczasowej serwera
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_in:
                tmp_in.write(uploaded_file.getvalue())
                tmp_in_path = tmp_in.name
            
            try:
                # 3. Wczytanie modelu z pliku tymczasowego
                model = ifcopenshell.open(tmp_in_path)
                
                # Zbieranie elementów
                wszystkie_elementy = model.by_type("IfcElement")
                do_usuniecia = [el for el in wszystkie_elementy if not el.is_a("IfcWall")]
                
                st.write(f"📊 Znaleziono elementów fizycznych: {len(wszystkie_elementy)}")
                st.write(f"🗑️ Elementów do usunięcia: {len(do_usuniecia)}")
                
                if len(do_usuniecia) > 0:
                    # Pasek postępu Streamlit
                    progress_bar = st.progress(0)
                    total = len(do_usuniecia)
                    
                    # 4. Inteligentne usuwanie przez API
                    for i, element in enumerate(do_usuniecia):
                        try:
                            ifcopenshell.api.run("root.remove_product", model, product=element)
                        except Exception:
                            pass
                            
                        # Aktualizacja paska co 50 elementów
                        if i % 50 == 0:
                            progress_bar.progress(min(i / total, 1.0))
                            
                    progress_bar.progress(1.0)
                
                # 5. Zapis wyniku do nowego pliku tymczasowego
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_out:
                    tmp_out_path = tmp_out.name
                
                model.write(tmp_out_path)
                
                # 6. Wczytanie gotowego pliku, by podać go użytkownikowi
                with open(tmp_out_path, "rb") as f:
                    out_bytes = f.read()
                
                st.success("✅ Generowanie pliku zakończone sukcesem!")
                
                # 7. Magiczny przycisk do pobrania pliku z powrotem na Twój komputer
                st.download_button(
                    label="📥 Pobierz wyczyszczony plik IFC",
                    data=out_bytes,
                    file_name=f"same_sciany_{uploaded_file.name}",
                    mime="application/octet-stream"
                )
                
            except Exception as e:
                st.error(f"Wystąpił błąd podczas przetwarzania: {e}")
                
            finally:
                # Sprzątanie po sobie (usunięcie plików z serwera)
                if os.path.exists(tmp_in_path):
                    os.remove(tmp_in_path)
                if 'tmp_out_path' in locals() and os.path.exists(tmp_out_path):
                    os.remove(tmp_out_path)
