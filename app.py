import ifcopenshell
import ifcopenshell.api
import time
import os
import tkinter as tk
from tkinter import filedialog

def main():
    print("--- START PROGRAMU ---")
    
    # 1. Wywołanie okienka wyboru pliku
    root = tk.Tk()
    root.withdraw() # Ukrywamy puste okienko w tle, zostawiamy tylko okno wyboru
    
    # Okienko zawsze na wierzchu (żeby nie uciekło pod inne okna)
    root.attributes('-topmost', True) 
    
    print("Otwieram okno wyboru pliku... (może mignąć na pasku zadań)")
    
    sciezka_wejsciowa = filedialog.askopenfilename(
        title="Wybierz duży plik IFC",
        filetypes=[("Pliki IFC", "*.ifc"), ("Wszystkie pliki", "*.*")]
    )
    
    # Jeśli użytkownik zamknie okienko bez wyboru pliku
    if not sciezka_wejsciowa:
        print("\nNie wybrano żadnego pliku. Przerywam działanie.")
        input("\nNaciśnij ENTER, aby zamknąć...")
        return

    # 2. Dynamiczne tworzenie nazwy pliku wyjściowego
    # Np. "C:/Projekty/budynek.ifc" -> "C:/Projekty/budynek_tylko_sciany.ifc"
    folder = os.path.dirname(sciezka_wejsciowa)
    nazwa_pliku = os.path.basename(sciezka_wejsciowa)
    nazwa_bez_rozszerzenia = os.path.splitext(nazwa_pliku)[0]
    
    sciezka_wyjsciowa = os.path.join(folder, f"{nazwa_bez_rozszerzenia}_tylko_sciany.ifc")

    print(f"\nWybrano plik: {nazwa_pliku}")
    print("Otwieranie pliku (to potrwa dłuższą chwilę przy dużym IFC)...")
    start = time.time()
    
    # 3. Wczytanie modelu
    try:
        model = ifcopenshell.open(sciezka_wejsciowa)
    except Exception as e:
        print(f"\nBŁĄD otwarcia pliku IFC: {e}")
        input("\nNaciśnij ENTER, aby wyjść...")
        return

    print("\nSzukanie obiektów, które nie są ścianami...")
    wszystkie_elementy = model.by_type("IfcElement")
    
    do_usuniecia = []
    for element in wszystkie_elementy:
        # Zostawiamy tylko IfcWall
        if not element.is_a("IfcWall"):
            do_usuniecia.append(element)
            
    print(f"Liczba wszystkich elementów fizycznych: {len(wszystkie_elementy)}")
    print(f"Liczba elementów do USUNIĘCIA: {len(do_usuniecia)}")
    
    if len(do_usuniecia) == 0:
        print("Plik składa się z samych ścian lub nie ma obiektów. Nie ma czego usuwać.")
        input("\nNaciśnij ENTER, aby wyjść...")
        return

    print("\nRozpoczynam inteligentne usuwanie (API ifcopenshell)...")
    print("Proszę czekać, pasek postępu aktualizuje się co 50 elementów.")
    
    # 4. Inteligentne usuwanie (usuwa obiekty wraz z ich "pustą" geometrią i relacjami)
    for i, element in enumerate(do_usuniecia):
        try:
            ifcopenshell.api.run("root.remove_product", model, product=element)
        except Exception as e:
            # Pomiń błędy przy rzadkich typach relacji
            pass
            
        if i % 50 == 0:
            print(f"   Postęp: usunięto {i} / {len(do_usuniecia)}...", end="\r")

    print(f"\n\nZapisywanie czystego pliku do:\n{sciezka_wyjsciowa}")
    model.write(sciezka_wyjsciowa)
    
    print(f"\nGOTOWE! Operacja zajęła {time.time() - start:.2f} sekund.")
    print("Możesz teraz otworzyć nowy plik w BIM Vision.")
    
    input("\nNaciśnij ENTER, aby zamknąć program...")

if __name__ == "__main__":
    main()
