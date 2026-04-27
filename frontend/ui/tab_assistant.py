"""Onglet Assistant — Chatbot IA NidBuyer."""

import pandas as pd
import streamlit as st
import requests

API_URL = "http://localhost:8000"

def post_chat(question: str, history: list[dict], n_context: int = 5) -> dict:
    try:
        r = requests.post(
            f"{API_URL}/api/chat", 
            json={"question": question, "history": history, "n_context": n_context}, 
            timeout=45
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "reponse": f"Erreur API : {e}. Assurez-vous que le backend FastAPI est lancé (fastapi dev backend/main.py).", 
            "profil_detecte": {}, 
            "biens_trouves": [], 
            "n_biens_contexte": 0
        }

def render_assistant(df_scored: pd.DataFrame) -> None:
    st.markdown("### 🤖 Assistant IA NidBuyer")
    st.markdown(
        "Discutez avec votre agent immobilier intelligent. Il interroge la base de données (Supabase) "
        "en temps réel pour vous trouver les meilleures opportunités selon vos critères."
    )
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Bonjour ! Je suis NidBuyer, votre conseiller immobilier IA à Toulon. Quel est votre projet ?"}
        ]
        
    st.markdown(
        '<div class="chat-wrap" style="max-width: 800px; margin: 0 auto; padding: 20px; '
        'background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">', 
        unsafe_allow_html=True
    )
    
    for msg in st.session_state.chat_history:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("biens_trouves"):
                with st.expander(f"📋 {len(msg['biens_trouves'])} bien(s) ciblé(s) pour vous"):
                    for b in msg["biens_trouves"]:
                        p = f"{b.get('prix', 0):,.0f} €" if b.get("prix") else "N/C"
                        s = f"{b.get('surface', '?'):.0f} m²" if b.get("surface") else "?"
                        url = b.get("lien", "")
                        lien_html = f'<a href="{url}" target="_blank" style="font-size: 12px;">🔗 Voir l\'annonce</a>' if url else ""
                        
                        st.markdown(
                            f'<div style="background: #F8FAFC; padding: 12px; margin-bottom: 8px; '
                            f'border-radius: 8px; border: 1px solid #E2E8F0;">'
                            f'<b style="font-size:14px;color:#1B2B4B;">{b.get("titre","Annonce")}</b><br>'
                            f'📍 <span style="color:#64748B;">{b.get("quartier","?")}</span> | '
                            f'💰 <span style="color:#E8714A;font-weight:bold;">{p}</span> | '
                            f'📐 <span style="color:#64748B;">{s}</span><br>'
                            f'<div style="margin-top:6px;">{lien_html}</div>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )

    if question := st.chat_input("Ex: Je cherche un T3 à Toulon Ouest avec terrasse pour 250k€…"):
        api_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="👤"): 
            st.markdown(question)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("NidBuyer réfléchit et fouille la base de données…"):
                result = post_chat(question, api_history, n_context=5)
            
            reponse = result.get("reponse", "Erreur inattendue.")
            st.markdown(reponse)
            biens_trouves = result.get("biens_trouves", [])
            
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": reponse, 
            "biens_trouves": biens_trouves
        })
        st.rerun()
        
    st.markdown('</div>', unsafe_allow_html=True)
