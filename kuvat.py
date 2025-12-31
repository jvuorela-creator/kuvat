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

def parsi_koordinaatit(geo_data):
    """Yrittää kaivaa koordinaatit (lat, lon) Finna-datasta."""
    # Finnan geo-kenttä on usein lista, jossa on sanakirja
    if not geo_data:
        return None, None
    
    try:
        # Jos data on lista (esim. [{'lat': 60.1, 'lon': 24.9}])
        if isinstance(geo_data, list) and len(geo_data) > 0:
            kohde = geo_data[0]
            if isinstance(kohde, dict):
                return kohde.get('lat'), kohde.get('lon')
            
        # Joskus data voi olla merkkijonona
        elif isinstance(geo_data, str):
            osat = geo_data.split(',')
            if len(osat) == 2:
                return float(osat[0]), float(osat[1])
                
    except Exception:
        return None, None
        
    return None, None

@st.cache_data
def hae_data_finnasta(hakusana, maara):
    base_url = "https://api.finna.fi/v1/search"
    # Lisätään hakuun 'geo'-kenttä koordinaatteja varten
    params = {
        "lookfor": hakusana,
        "filter[]": "format:0/Image/",
        "fields[]": ["title", "year", "images", "id", "building", "geo"],
        "limit": maara,
        "sort": "main_date_str asc"
    }
    
    try:
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
            
            # Kuvien ja sivujen linkit
            kuvat = teos.get("images", [])
            kuva_url = f"https://api.finna.fi{kuvat[0]}" if kuvat else ""
            finna_sivu = f"https://www.finna.fi/Record/{teos.get('id')}"

            # Koordinaatit
            lat, lon = parsi_koordinaatit(teos.get("geo"))

            if puhdas_vuosi:
                rivit.append({
                    "Vuosi": puhdas_vuosi,
                    "Otsikko": otsikko,
                    "Alkuperäinen aikamerkintä": alkuperainen_vuosi,
                    "Kuvalinkki": kuva_url,    # Suora linkki JPG-kuvaan
                    "Finna-sivu": finna_sivu,  # Linkki tietosivulle
                    "lat": lat,                # Karttaa varten
                    "lon": lon                 # Karttaa varten
                })
                
        return pd.DataFrame(rivit)
        
    except Exception as e:
        st.error(f"Virhe haussa: {e}")
        return None

# --- SOVELLUKSEN KÄYTTÖLIITTYMÄ ---

st.title("🕰️ Finna-aikakone")
st.markdown("Hae historiallisia kuvia, katso ne aikajanalla ja kartalla.")

col1, col2 = st.columns([3, 1])
with col1:
    hakusana = st.text_input("Mitä etsitään? (esim. Helsinki, kirkko, koulu)", "")
with col2:
    maara = st.slider("Hakutulosten määrä", 10, 100, 50)

if st.button("Hae kuvia"):
    if not hakusana:
        st.warning("Kirjoita hakusana.")
    else:
        with st.spinner('Haetaan aineistoa ja koordinaatteja...'):
            df = hae_data_finnasta(hakusana, maara)

        if df is not None and not df.empty:
            st.success(f"Löydettiin {len(df)} kuvaa!")

            # --- VÄLILEHDET (Aikajana, Kartta, Taulukko) ---
            tab1, tab2, tab3 = st.tabs(["📅 Aikajana", "🗺️ Kartta", "📋 Taulukko & Linkit"])

            with tab1:
                st.subheader(f"Aikajana: {hakusana}")
                fig = px.scatter(
                    df, 
                    x="Vuosi", 
                    y=[1] * len(df),
                    hover_name="Otsikko",
                    hover_data=["Alkuperäinen aikamerkintä"],
                    height=350,
                    size_max=15
                )
                fig.update_traces(marker=dict(size=14, color='blue', opacity=0.6))
                fig.update_layout(yaxis={'visible': False, 'showticklabels': False})
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader(f"Kartta: {hakusana}")
                # Suodatetaan pois rivit, joissa ei ole koordinaatteja
                kartta_df = df.dropna(subset=['lat', 'lon'])
                
                if not kartta_df.empty:
                    st.markdown(f"*Kartalla näkyy {len(kartta_df)} kuvaa, joissa oli sijaintitiedot.*")
                    # Käytetään st.map -komponenttia (yksinkertainen ja toimiva)
                    st.map(kartta_df, latitude='lat', longitude='lon', size=20, color='#0044ff')
                else:
                    st.info("Haetuille kuville ei valitettavasti löytynyt koordinaattitietoja Finnasta.")

            with tab3:
                st.subheader("Tiedot ja linkit")
                
                # Konfiguroidaan sarakkeet niin, että linkit ovat klikattavia
                st.dataframe(
                    df[["Vuosi", "Otsikko", "Finna-sivu", "Kuvalinkki"]],
                    column_config={
                        "Finna-sivu": st.column_config.LinkColumn(
                            "Avaa Finna-sivu", display_text="Siirry 🔗"
                        ),
                        "Kuvalinkki": st.column_config.LinkColumn(
                            "Katso kuva", display_text="Avaa kuva 🖼️"
                        ),
                        "Vuosi": st.column_config.NumberColumn(
                            "Vuosi", format="%d"
                        )
                    },
                    hide_index=True
                )

                # Excel-lataus
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Kuvat')
                
                st.download_button(
                    label="📥 Lataa Excel-tiedosto",
                    data=buffer,
                    file_name=f"tulokset_{hakusana}.xlsx",
                    mime="application/vnd.ms-excel"
                )
            
        else:
            st.error("Ei tuloksia. Kokeile eri hakusanaa.")
