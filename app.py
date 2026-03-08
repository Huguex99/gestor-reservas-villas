import streamlit as st
from datetime import datetime, timedelta
import requests
from icalendar import Calendar
import pandas as pd

# CONFIGURAÇÃO
st.set_page_config(page_title="Gestor Villas", page_icon="🏠")

# O TEU LINK DO GOOGLE SHEETS (Convertido para formato CSV)
SHEET_ID = "1Izx6YxFvOckGvtUpFMXehOFj2VH4tt1-QFBaLg35OgI"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

PROPRIEDADES = {
    "Villa Emilly": {
        "icals": [
            "https://ical.booking.com/v1/export?t=41734955-cc72-4bd6-822f-5a11e335478f",
            "https://www.airbnb.pt/calendar/ical/1201617111880855308.ics?t=1b9285d74bb64a769ae5ef2a43716f09"
        ],
        "d_normal": 1500
    },
    "Villa Judy": {"icals": [], "d_normal": 1500},
    "Apartamento Onda Verde": {
        "icals": ["https://www.airbnb.pt/calendar/ical/20960093.ics?t=2606be55c25c461f9f62f4582634f5e4"],
        "d_normal": 1300
    }
}

def verificar_disponibilidade(casa_sel, checkin, checkout):
    conflitos = []
    # 1. iCals
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
                    conflitos.append(f"🔴 Plataforma: {s} a {e}")
        except: continue

    # 2. Google Sheets (Leitura Simples)
    try:
        df = pd.read_csv(SHEET_URL)
        for _, row in df.iterrows():
            if str(row['casa']) == casa_sel:
                s = pd.to_datetime(row['checkin']).date()
                e = pd.to_datetime(row['checkout']).date()
                if checkin < e and checkout > s:
                    conflitos.append(f"📝 Manual: {s} a {e}")
    except: pass
    return conflitos

st.title("🏨 Gestor de Reservas")
casa = st.sidebar.selectbox("Villas", list(PROPRIEDADES.keys()))
checkin = st.date_input("Check-in", datetime.now().date())
checkout = st.date_input("Check-out", (datetime.now() + timedelta(days=7)).date())

if st.button("Verificar"):
    erros = verificar_disponibilidade(casa, checkin, checkout)
    if erros:
        for e in erros: st.error(e)
    else:
        st.success("✅ Disponível!")

st.divider()
st.write("### ⚠️ Como Bloquear Datas")
st.write("Como o Streamlit é gratuito, para gravar permanentemente, clica no link abaixo e escreve a reserva diretamente na folha de cálculo:")
st.link_button("Abrir Google Sheets para Gravar", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")



