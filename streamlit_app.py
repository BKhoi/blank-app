import streamlit as st
import aiohttp
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_token = os.getenv("CHUTE_API_TOKEN")
if not api_token:
    raise ValueError("API token not found. Set CHUTE_API_TOKEN in .env file.")

async def invoke_chute(prompt, messages, max_tokens=500, temperature=0.7):
    if not prompt.strip():
        st.error("Hey, give me a driving question or something to roll with!")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    # Define DriveWise's personality
    system_prompt = (
        "You are DriveWise, a friendly, no-nonsense traffic and driving coach. "
        "Answer traffic-related questions with clear, short tips, facts, or rules in an engaging tone, like a seasoned driving instructor. "
        "For basic conversational questions (e.g., 'How are you?', 'Who are you?'), respond briefly with a driving-themed reply, like: "
        "'I’m DriveWise, cruising smoothly and ready to help with traffic tips. How about you?' or 'I’m DriveWise, your road guide. Got a driving question?' "
        
    )
    
    # Build message history with system prompt
    api_messages = [{"role": "system", "content": system_prompt}]
    if messages:
        api_messages.extend([{"role": m["role"], "content": m["content"]} for m in messages])
    api_messages.append({"role": "user", "content": prompt})
    
    body = {
        "model": "deepseek-ai/DeepSeek-V3-0324",
        "messages": api_messages,
        "stream": True,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    reply = ""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                "https://llm.chutes.ai/v1/chat/completions",
                headers=headers,
                json=body
            ) as response:
                if response.status != 200:
                    st.error(f"API error: {response.status} - {await response.text()}")
                    return None
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    async for line in response.content:
                        # Check if stop button was pressed
                        if st.session_state.get("stop_response", False):
                            st.session_state.stop_response = False  # Reset the flag
                            break
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data.strip())
                                delta = chunk["choices"][0]["delta"]
                                if "content" in delta and delta["content"] is not None:
                                    reply += delta["content"]
                                    placeholder.markdown(reply)
                            except Exception as e:
                                st.error(f"Error parsing response: {e}")
                                return None
    except asyncio.TimeoutError:
        st.error("API took too long to respond. Try again later.")
        return None
    except Exception as e:
        st.error(f"Something broke: {e}")
        return None
    return reply

def main():
    st.title("DriveWise: Your Traffic Coach")
    st.write("Yo, I'm DriveWise, your go-to for traffic rules and driving tips. Hit me with a road question or just say hi!")
    
    st.sidebar.header("DriveWise Settings")
    max_tokens = st.sidebar.slider("Max Response Length", 100, 2000, 500)
    temperature = st.sidebar.slider("Creativity", 0.1, 2.0, 0.7)
    
    # Add reset button
    if st.sidebar.button("Reset Chat"):
        st.session_state.messages = []
        st.success("Chat reset! DriveWise is ready to hit the road.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask DriveWise a traffic question or say hi!")
    if prompt:
        # Initialize stop_response flag
        st.session_state.stop_response = False
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.spinner("DriveWise is checking the road..."):
            # Add stop button during response streaming
            stop_button_placeholder = st.empty()
            if stop_button_placeholder.button("Stop Response", key="stop_response_button"):
                st.session_state.stop_response = True
            response = asyncio.run(invoke_chute(prompt, st.session_state.messages, max_tokens, temperature))
            # Remove stop button after response is complete or stopped
            stop_button_placeholder.empty()
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()