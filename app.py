import ifcopenshell
import ifcopenshell.api
import time

# --- KONFIGURACJA ---
INPUT_FILE = "twoj_duzy_plik.ifc" # Wpisz nazwę oryginalnego pliku!
OUTPUT_FILE = "poprawne_sciany.ifc"
# --------------------

def main():
    print(f"Otwieranie pliku {INPUT_FILE}...")
    start = time.time()
    
    try:
        model = ifcopenshell.open(INPUT_FILE)
    except Exception as e:
        print(f"Błąd otwarcia pliku: {e}")
        return

    print("Zbieranie elementów do usunięcia...")
    
    # Interesują nas tylko obiekty fizyczne (IfcElement). 
    # To omija bezpiecznie "szkielet" budynku (piętra, osie itp.)
    wszystkie_elementy = model.by_type("IfcElement")
    
    do_usuniecia = []
    for element in wszystkie_elementy:
        # Jeśli element NIE JEST ścianą, trafia na listę gilotyny
        if not element.is_a("IfcWall"):
            do_usuniecia.append(element)
            
    print(f"Znaleziono {len(wszystkie_elementy)} fizycznych elementów.")
    print(f"Zostawiamy same ściany. Zostanie USUNIĘTYCH: {len(do_usuniecia)} obiektów.")
    
    # BEZPIECZNE USUWANIE
    # Używamy oficjalnego API biblioteki. Dba ono o to, by przy usunięciu
    # elementu, usunąć też jego osieroconą geometrię i uniknąć "pomieszania ID".
    print("Rozpoczynam inteligentne usuwanie (to może potrwać kilka minut)...")
    
    for i, element in enumerate(do_usuniecia):
        try:
            ifcopenshell.api.run("root.remove_product", model, product=element)
        except Exception as e:
            # W rzadkich przypadkach dziwnych powiązań pomijamy błąd
            pass
            
        if i % 100 == 0:
            print(f"   Przetworzono {i}/{len(do_usuniecia)}...", end="\r")

    print(f"\nZapisywanie czystego pliku: {OUTPUT_FILE}...")
    # Zapisujemy wyczyszczony graf do nowego pliku
    model.write(OUTPUT_FILE)
    print(f"Gotowe w {time.time() - start:.2f} s!")

if __name__ == "__main__":
    main()
