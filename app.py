import streamlit as st
from datetime import datetime, timedelta
import requests
from icalendar import Calendar
import os
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gestor Reservas Pro", page_icon="🏠")

# 2. LIGAÇÃO AO GOOGLE SHEETS
# Nota: Configura o link da folha nos "Secrets" do Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. DADOS DAS PROPRIEDADES
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

# 4. FUNÇÃO DE VERIFICAÇÃO
def verificar_disponibilidade(casa_sel, checkin, checkout):
    conflitos = []
    
    # A. Verificar iCals das plataformas
    for url in PROPRIEDADES[casa_sel]["icals"]:
        try:
            response = requests.get(url, timeout=10)
            gcal = Calendar.from_ical(response.text)
            for component in gcal.walk():
                if component.name == "VEVENT":
                    e_start = component.get('dtstart').dt
                    e_end = component.get('dtend').dt
                    if isinstance(e_start, datetime): e_start = e_start.date()
                    if isinstance(e_end, datetime): e_end = e_end.date()
                    
                    if checkin < e_end and checkout > e_start:
                        resumo = str(component.get('summary'))
                        origem = "Booking" if "booking" in url else ("Airbnb" if "airbnb" in url else "VRBO")
                        conflitos.append(f"🔴 {origem}: {resumo} ({e_start} a {e_end})")
        except: continue

    # B. Verificar no Google Sheets (Reservas Manuais)
    try:
        df = conn.read(ttl=0) # ttl=0 força a leitura de dados novos
        if not df.empty:
            for _, row in df.iterrows():
                if str(row['casa']) == casa_sel:
                    # Converter datas da folha para comparação
                    s_d = pd.to_datetime(row['checkin']).date()
                    e_d = pd.to_datetime(row['checkout']).date()
                    if checkin < e_d and checkout > s_d:
                        conflitos.append(f"📝 Google Sheets: Bloqueio Manual ({s_d} a {e_d})")
    except Exception as e:
        st.sidebar.warning("Ainda não existem reservas no Google Sheets.")

    return conflitos

# 5. INTERFACE
st.title("🏨 Gestor de Reservas Cloud")
casa = st.sidebar.selectbox("Propriedade", list(PROPRIEDADES.keys()))
canal = st.sidebar.radio("Canal", ["Plataforma", "Direto / OLX"])

col1, col2 = st.columns(2)
checkin_input = col1.date_input("Check-in", datetime.now().date())
checkout_input = col2.date_input("Check-out", (datetime.now() + timedelta(days=7)).date())

if st.button("Verificar Disponibilidade"):
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

# 6. REGISTO NO GOOGLE SHEETS
st.divider()
with st.expander("📝 Registar Bloqueio Permanente"):
    st.write("Isto guarda a reserva diretamente na tua folha de cálculo Google.")
    if st.button("Confirmar e Gravar no Google Sheets"):
        try:
            # Tentar ler dados existentes, se falhar, cria um DataFrame vazio
            try:
                df_atual = conn.read(ttl=0)
            except:
                df_atual = pd.DataFrame(columns=["casa", "checkin", "checkout"])
            
            # Criar nova linha
            nova_reserva = pd.DataFrame([{
                "casa": casa, 
                "checkin": str(checkin_input), 
                "checkout": str(checkout_input)
            }])
            
            # Limpar dados vazios e juntar
            df_final = pd.concat([df_atual, nova_reserva], ignore_index=True).dropna(how='all')
            
            # Gravar
            conn.update(data=df_final)
            st.success("Reserva gravada para sempre!")
            st.balloons() # Os balões só aparecem se chegar aqui sem erro
        except Exception as e:
            st.error(f"Erro técnico: {e}")
            st.info("Verifica se a folha está Partilhada como EDITOR para qualquer pessoa com o link.")

