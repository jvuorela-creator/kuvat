import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import re
import io

# --- ASETUKSET ---
st.set_page_config(page_title="Finna-aikakone", layout="wide")

# --- APUFUNKTIOT ---

def puhdista_vuosiluku(vuosi_str):
    """Etsii tekstistä ensimmäisen järkevän vuosiluvun."""
    if not vuosi_str:
        return None
    match = re.search(r'\d{4}', str(vuosi_str))
    if match:
        return int(match.group())
    return None

@st.cache_data # Tämä estää turhat haut, jos painat nappia vahingossa uudestaan
def hae_data_finnasta(hakusana, maara):
    base_url = "https://api.finna.fi/v1/search"
    params = {
        "lookfor": hakusana,
        "filter[]": "format:0/Image/",
        "fields[]": ["title", "year", "images", "id", "building"],
        "limit": maara,
        "sort": "main_date_str asc"
    }
    
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return None
        
    data = response.json()
    tulokset = data.get("records", [])
    
    rivit = []
    for teos in tulokset:
        otsikko = teos.get("title", "Ei otsikkoa")
        alkuperainen_vuosi = teos.get("year", "")
        puhdas_vuosi = puhdista_vuosiluku(alkuperainen_vuosi)
        
        kuvat = teos.get("images", [])
        kuva_linkki = f"https://api.finna.fi{kuvat[0]}" if kuvat else ""
        finna_sivu = f"https://www.finna.fi/Record/{teos.get('id')}"

        if puhdas_vuosi:
            rivit.append({
                "Vuosi": puhdas_vuosi,
                "Alkuperäinen aikamerkintä": alkuperainen_vuosi,
                "Otsikko": otsikko,
                "Kuva": kuva_linkki,
                "Linkki": finna_sivu
            })
            
    return pd.DataFrame(rivit)

# --- SOVELLUKSEN KÄYTTÖLIITTYMÄ ---

st.title("🕰️ Finna-aikakone")
st.markdown("Hae historiallisia kuvia ja katso ne aikajanalla.")

# 1. Hakukenttä (Korvaa input-komennon)
hakusana = st.text_input("Mitä etsitään? (esim. kylä, talo tai suku)", "")
maara = st.slider("Montako kuvaa haetaan?", 10, 100, 50)

if st.button("Hae kuvia"):
    if not hakusana:
        st.warning("Kirjoita jokin hakusana ensin.")
    else:
        with st.spinner('Haetaan aineistoa Finnasta...'):
            df = hae_data_finnasta(hakusana, maara)

        if df is not None and not df.empty:
            st.success(f"Löydettiin {len(df)} kuvaa aikajanalle!")

            # 2. Piirretään aikajana (Korvaa selaimen avauksen)
            fig = px.scatter(
                df, 
                x="Vuosi", 
                y=[1] * len(df),
                hover_name="Otsikko",
                hover_data=["Alkuperäinen aikamerkintä"],
                title=f"Aikajana: {hakusana}",
                size_max=15,
                height=300
            )
            fig.update_traces(marker=dict(size=12, color='blue', symbol='circle'))
            fig.update_layout(yaxis={'visible': False, 'showticklabels': False})
            
            st.plotly_chart(fig, use_container_width=True)

            # 3. Näytetään data taulukkona
            st.dataframe(df[["Vuosi", "Otsikko", "Alkuperäinen aikamerkintä"]])

            # 4. Excel-latausnappi (Korvaa tiedostoon tallennuksen)
            # Tehdään Excel muistiin (buffer), jotta se voidaan ladata napista
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Kuvat')
                
            st.download_button(
                label="📥 Lataa tulokset Excelinä",
                data=buffer,
                file_name=f"tulokset_{hakusana}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
        else:
            st.error("Ei tuloksia tai vuosilukuja ei tunnistettu.")
