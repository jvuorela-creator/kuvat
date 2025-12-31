import requests
import pandas as pd
import plotly.express as px
import re
import webbrowser
import os

def puhdista_vuosiluku(vuosi_str):
    """
    Etsii tekstistä (esim. "n. 1920" tai "1920-1930") ensimmäisen järkevän vuosiluvun.
    Tämä on tärkeää, jotta aikajana ymmärtää sijoittaa kuvan oikeaan kohtaan.
    """
    if not vuosi_str:
        return None
    # Etsitään regexillä 4 peräkkäistä numeroa
    match = re.search(r'\d{4}', str(vuosi_str))
    if match:
        return int(match.group())
    return None

def luo_sovellus(hakusana, maara=20):
    # 1. MÄÄRITELLÄÄN HAKU
    base_url = "https://api.finna.fi/v1/search"
    params = {
        "lookfor": hakusana,
        "filter[]": "format:0/Image/",
        "fields[]": ["title", "year", "images", "id", "building"],
        "limit": maara,
        "sort": "main_date_str asc" # Järjestetään vanhimmasta uusimpaan
    }

    print(f"Haetaan aineistoa hakusanalla: '{hakusana}'...")
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        tulokset = data.get("records", [])

        if not tulokset:
            print("Ei tuloksia.")
            return

        # 2. KÄSITELLÄÄN DATA (Munnetaan API-vastaus siistiksi listaksi)
        rivit = []
        for teos in tulokset:
            otsikko = teos.get("title", "Ei otsikkoa")
            alkuperainen_vuosi = teos.get("year", "")
            
            # Luodaan "puhdas vuosi" aikajanaa varten
            puhdas_vuosi = puhdista_vuosiluku(alkuperainen_vuosi)
            
            # Rakennetaan kuvalinkki
            kuvat = teos.get("images", [])
            kuva_linkki = f"https://api.finna.fi{kuvat[0]}" if kuvat else ""
            finna_sivu = f"https://www.finna.fi/Record/{teos.get('id')}"

            # Lisätään rivi listaan, jos vuosi on tiedossa (aikajana vaatii vuoden)
            if puhdas_vuosi:
                rivit.append({
                    "Vuosi (puhdistettu)": puhdas_vuosi,
                    "Alkuperäinen aikamerkintä": alkuperainen_vuosi,
                    "Otsikko": otsikko,
                    "Kuvalinkki": kuva_linkki,
                    "Finna-sivu": finna_sivu
                })

        # Muutetaan lista DataFrameksi (taulukoksi)
        df = pd.DataFrame(rivit)

        if df.empty:
            print("Löytyi aineistoa, mutta niistä ei saatu tunnistettua vuosilukuja aikajanalle.")
            return

        # 3. VIENTI EXCELIIN
        excel_nimi = f"tulokset_{hakusana}.xlsx"
        df.to_excel(excel_nimi, index=False)
        print(f"✅ Tiedot tallennettu Exceliin: {excel_nimi}")

        # 4. LUODAAN AIKAJANA (Plotly)
        # Tehdään "Scatter plot", jossa X-akseli on vuosi.
        fig = px.scatter(
            df, 
            x="Vuosi (puhdistettu)", 
            y=[1] * len(df), # Kaikki pisteet samalle "korkeudelle" (tai voitaisiin hajauttaa)
            hover_name="Otsikko",
            hover_data=["Alkuperäinen aikamerkintä"],
            title=f"Aikajana: {hakusana}",
            labels={"Vuosi (puhdistettu)": "Vuosi"},
            size_max=15
        )

        # Hienosäädetään ulkoasua
        fig.update_traces(marker=dict(size=12, color='blue', symbol='circle'))
        fig.update_layout(
            yaxis={'visible': False, 'showticklabels': False}, # Piilotetaan turha Y-akseli
            xaxis=dict(title='Vuosi'),
            height=300 # Ei tehdä kuvaajasta liian korkeaa
        )

        # Tallennetaan HTML-tiedostoksi ja avataan se
        html_nimi = f"aikajana_{hakusana}.html"
        fig.write_html(html_nimi)
        print(f"✅ Aikajana luotu: {html_nimi}")
        
        # Avataan aikajana automaattisesti selaimessa
        full_path = "file://" + os.path.abspath(html_nimi)
        webbrowser.open(full_path)

    except Exception as e:
        print(f"Tapahtui virhe: {e}")

# --- PÄÄOHJELMA ---
if __name__ == "__main__":
    haku = input("Mitä etsitään (esim. paikkakunta tai suku)? ")
    luo_sovellus(haku, maara=50)