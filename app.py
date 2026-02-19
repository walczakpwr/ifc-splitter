import ifcopenshell
import ifcopenshell.api
import time
import os
import tkinter as tk
from tkinter import filedialog

def main():
    print("--- START PROGRAMU ---")
    
    # 1. Przygotowanie okienka wyboru pliku
    root = tk.Tk()
    root.withdraw() # Ukrywamy główne okno programu (żeby nie wisiało puste tło)
    root.attributes('-topmost', True) # Wymuszamy, żeby okienko wyboru pojawiło się na wierzchu
    
    print("Otwieram okno wyboru pliku... (sprawdź pasek zadań, jeśli go nie widzisz)")
    
    # Wywołanie systemowego okienka
    sciezka_wejsciowa = filedialog.askopenfilename(
        title="Wybierz plik IFC do przetworzenia",
        filetypes=[("Pliki IFC", "*.ifc"), ("Wszystkie pliki", "*.*")]
    )
    
    # Jeśli zamkniesz okienko bez wyboru pliku (Anuluj)
    if not sciezka_wejsciowa:
        print("\nNie wybrano pliku. Zamykam program.")
        input("Naciśnij ENTER, aby wyjść...")
        return

    # 2. Generowanie nazwy pliku wyjściowego
    # Skrypt sam wyciągnie folder i nazwę, np. "C:/budynek.ifc" -> "C:/budynek_tylko_sciany.ifc"
    folder = os.path.dirname(sciezka_wejsciowa)
    nazwa_pliku = os.path.basename(sciezka_wejsciowa)
    nazwa_bez_rozszerzenia = os.path.splitext(nazwa_pliku)[0]
    
    sciezka_wyjsciowa = os.path.join(folder, f"{nazwa_bez_rozszerzenia}_tylko_sciany.ifc")

    print(f"\nWybrano plik: {sciezka_wejsciowa}")
    print("Otwieranie pliku (to może potrwać przy dużym modelu)...")
    start = time.time()
    
    try:
        model = ifcopenshell.open(sciezka_wejsciowa)
    except Exception as e:
        print(f"\nBŁĄD otwarcia pliku IFC: {e}")
        input("Naciśnij ENTER, aby wyjść...")
        return

    print("\nSzukanie obiektów do usunięcia...")
    wszystkie_elementy = model.by_type("IfcElement")
    
    do_usuniecia = []
    for element in wszystkie_elementy:
        # Jeśli coś nie jest ścianą (IfcWall) -> idzie na listę do usunięcia
        if not element.is_a("IfcWall"):
            do_usuniecia.append(element)
            
    print(f"Liczba wszystkich elementów fizycznych: {len(wszystkie_elementy)}")
    print(f"Liczba elementów, które zostaną USUNIĘTE: {len(do_usuniecia)}")
    
    if len(do_usuniecia) == 0:
        print("Brak elementów do usunięcia (plik składa się z samych ścian).")
        input("\nNaciśnij ENTER, aby wyjść...")
        return

    print("\nRozpoczynam usuwanie zbędnych elementów...")
    print("Czekaj, pasek postępu aktualizuje się co 50 sztuk.")
    
    # 3. Inteligentne usuwanie (usuwa obiekty, ich geometrię i łata relacje)
    for i, element in enumerate(do_usuniecia):
        try:
            ifcopenshell.api.run("root.remove_product", model, product=element)
        except Exception as e:
            pass # Ignorujemy błędy przy nietypowych powiązaniach
            
        if i % 50 == 0:
            print(f"   Postęp: usunięto {i} / {len(do_usuniecia)}...", end="\r")

    print(f"\n\nZapisywanie czystego pliku do:\n{sciezka_wyjsciowa}")
    model.write(sciezka_wyjsciowa)
    
    print(f"\nGOTOWE! Całość zajęła {time.time() - start:.2f} s")
    
    # 4. Blokada przed zamknięciem okna konsoli
    input("\nNaciśnij ENTER, aby zamknąć program...")

if __name__ == "__main__":
    main()
