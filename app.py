import streamlit as st
from datetime import datetime, timedelta
import requests
from icalendar import Calendar
import os

st.set_page_config(page_title="Gestor Reservas Pro", page_icon="🏠")

# --- CONFIGURAÇÃO ---
PROPRIEDADES = {
    "Villa Emilly": {
        "icals": [
            "https://ical.booking.com/v1/export?t=41734955-cc72-4bd6-822f-5a11e335478f",
            "https://www.airbnb.pt/calendar/ical/1201617111880855308.ics?t=1b9285d74bb64a769ae5ef2a43716f09",
            "http://www.vrbo.com/icalendar/8de0a01b8e354e54aea7e2c9a630d85a.ics"
        ],
        "p_noite": 350, "d_normal": 1500, "d_pico": 1700
    },
    "Villa Judy": {
        "icals": [], "p_noite": 0, "d_normal": 1500, "d_pico": 1700
    },
    "Apartamento Onda Verde": {
        "icals": [
            "https://www.airbnb.pt/calendar/ical/20960093.ics?t=2606be55c25c461f9f62f4582634f5e4",
            "http://www.vrbo.com/icalendar/8de0a01b8e354e54aea7e2c9a630d85a.ics"
        ],
        "p_noite": 260, "d_normal": 1300, "d_pico": 1600
    }
}

DB_FILE = "reservas_manuais.csv"

def verificar_disponibilidade(casa, checkin, checkout):
    conflitos = []
    
    # 1. Verificar iCals Online
    for url in PROPRIEDADES[casa]["icals"]:
        try:
            response = requests.get(url, timeout=10)
            gcal = Calendar.from_ical(response.text)
            for component in gcal.walk():
                if component.name == "VEVENT":
                    # Extrair datas e garantir que são apenas 'date' e não 'datetime'
                    e_start = component.get('dtstart').dt
                    e_end = component.get('dtend').dt
                    
                    if isinstance(e_start, datetime): e_start = e_start.date()
                    if isinstance(e_end, datetime): e_end = e_end.date()
                    
                    # Testar sobreposição
                    if checkin < e_end and checkout > e_start:
                        resumo = str(component.get('summary'))
                        origem = "Booking" if "booking" in url else ("Airbnb" if "airbnb" in url else "VRBO")
                        conflitos.append(f"🔴 {origem}: {resumo} ({e_start} a {e_end})")
        except Exception as e:
            st.error(f"Erro ao ler link: {url[:30]}... -> {e}")

    # 2. Verificar Manuais
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            for line in f:
                try:
                    c, s, e = line.strip().split(",")
                    if c == casa:
                        s_d = datetime.strptime(s, "%Y-%m-%d").date()
                        e_d = datetime.strptime(e, "%Y-%m-%d").date()
                        if checkin < e_d and checkout > s_d:
                            conflitos.append(f"📝 Manual: {s_d} a {e_d}")
                except: continue

    return conflitos

# --- INTERFACE ---
st.title("🏨 Gestor de Reservas")
casa = st.sidebar.selectbox("Propriedade", list(PROPRIEDADES.keys()))
canal = st.sidebar.radio("Canal", ["Plataforma", "Direto / OLX"])

col1, col2 = st.columns(2)
# Garantimos que os inputs do Streamlit são tratados como objetos 'date'
checkin_input = col1.date_input("Check-in", datetime.now().date())
checkout_input = col2.date_input("Check-out", (datetime.now() + timedelta(days=7)).date())

if st.button("Verificar Disponibilidade"):
    # Passamos as datas para a função
    conflitos = verificar_disponibilidade(casa, checkin_input, checkout_input)
    
    if conflitos:
        st.error("🚨 Datas Ocupadas!")
        for c in conflitos:
            st.info(c)
    else:
        st.success("✅ Disponível!")
        noites = (checkout_input - checkin_input).days
        dados = PROPRIEDADES[casa]
        if canal == "Direto / OLX":
            preco = dados["d_pico"] if checkin_input.month in [7,8] else dados["d_normal"]
            total = (noites/7) * preco
            st.write(f"Preço Semanal aplicado: **{preco}€**")
        else:
            total = noites * dados["p_noite"]
            st.write(f"Preço por Noite aplicado: **{dados['p_noite']}€**")
        
        st.metric("Total da Estadia", f"{total:.2f} €")

st.divider()
with st.expander("Registar Bloqueio Manual (OLX/Direto)"):
    if st.button("Bloquear estas datas"):
        with open(DB_FILE, "a") as f:
            f.write(f"{casa},{checkin_input},{checkout_input}\n")
        st.success("Reserva manual registada!")
        