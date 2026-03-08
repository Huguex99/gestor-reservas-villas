import streamlit as st
from datetime import datetime, timedelta
import requests
from icalendar import Calendar
import pandas as pd

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Gestor Villas Pro", page_icon="🏠")

# LINK DO GOOGLE SHEETS
SHEET_ID = "1Izx6YxFvOckGvtUpFMXehOFj2VH4tt1-QFBaLg35OgI"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# 2. DADOS DAS PROPRIEDADES (Com Preços)
PROPRIEDADES = {
    "Villa Emilly": {
        "icals": [
            "https://ical.booking.com/v1/export?t=41734955-cc72-4bd6-822f-5a11e335478f",
            "https://www.airbnb.pt/calendar/ical/1201617111880855308.ics?t=1b9285d74bb64a769ae5ef2a43716f09"
        ],
        "p_noite": 350, "d_normal": 1500, "d_pico": 1700
    },
    "Villa Judy": {
        "icals": [], 
        "p_noite": 350, "d_normal": 1500, "d_pico": 1700
    },
    "Apartamento Onda Verde": {
        "icals": ["https://www.airbnb.pt/calendar/ical/20960093.ics?t=2606be55c25c461f9f62f4582634f5e4"],
        "p_noite": 260, "d_normal": 1300, "d_pico": 1600
    }
}

def verificar_disponibilidade(casa_sel, checkin, checkout):
    conflitos = []
    # iCals
    for url in PROPRIEDADES[casa_sel]["icals"]:
        try:
            res = requests.get(url, timeout=5)
            gcal = Calendar.from_ical(res.text)
            for component in gcal.walk('VEVENT'):
                s = component.get('dtstart').dt
                e = component.get('dtend').dt
                if isinstance(s, datetime): s = s.date()
                if isinstance(e, datetime): e = e.date()
                if checkin < e and checkout > s:
                    origem = "Booking" if "booking" in url else "Airbnb"
                    conflitos.append(f"🔴 {origem}: {s} a {e}")
        except: continue

    # Google Sheets
    try:
        df = pd.read_csv(SHEET_URL)
        for _, row in df.iterrows():
            if str(row['casa']) == casa_sel:
                s = pd.to_datetime(row['checkin']).date()
                e = pd.to_datetime(row['checkout']).date()
                if checkin < e and checkout > s:
                    conflitos.append(f"📝 Google Sheets: {s} a {e}")
    except: pass
    return conflitos

# 3. INTERFACE
st.title("🏨 Gestor de Reservas")

casa = st.sidebar.selectbox("Villas", list(PROPRIEDADES.keys()))
canal = st.sidebar.radio("Tipo de Reserva", ["Plataforma (Booking/Airbnb)", "Direto / OLX"])

col1, col2 = st.columns(2)
checkin_in = col1.date_input("Check-in", datetime.now().date())
checkout_in = col2.date_input("Check-out", (datetime.now() + timedelta(days=7)).date())

if st.button("Verificar Disponibilidade e Preço"):
    erros = verificar_disponibilidade(casa, checkin_in, checkout_in)
    
    if erros:
        st.error("🚨 Datas Indisponíveis!")
        for e in erros: st.info(e)
    else:
        st.success("✅ Datas Disponíveis!")
        
        # CÁLCULO DE PREÇO
        noites = (checkout_in - checkin_in).days
        dados = PROPRIEDADES[casa]
        
        if canal == "Direto / OLX":
            # Se for Julho (7) ou Agosto (8), usa preço de pico
            preco_semana = dados["d_pico"] if checkin_in.month in [7, 8] else dados["d_normal"]
            total = (noites / 7) * preco_semana
            st.metric("Total Direto (Preço Semanal)", f"{total:.2f} €")
            st.caption(f"Base: {preco_semana}€ por semana")
        else:
            total = noites * dados["p_noite"]
            st.metric("Total Plataforma (Preço por Noite)", f"{total:.2f} €")
            st.caption(f"Base: {dados['p_noite']}€ por noite")

# 4. BLOQUEIO
st.divider()
st.write("### ⚠️ Como Bloquear Datas")
st.link_button("Abrir Google Sheets para Gravar Bloqueio", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

