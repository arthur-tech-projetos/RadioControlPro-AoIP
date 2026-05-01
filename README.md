# 📻 Radio Control Pro - AoIP Engine

Um motor de **Áudio sobre IP (AoIP)** de ultra-baixa latência e qualidade de estúdio (48kHz), construído puramente em Python. Projetado para substituir links físicos caros (STL) entre estúdios Windows e servidores de processamento/streaming Linux.

![Status](https://img.shields.io/badge/Status-Ativo-success)
![Plataformas](https://img.shields.io/badge/Plataformas-Windows%20%7C%20Linux-blue)
![Licença](https://img.shields.io/badge/License-MIT-green)

## 🚀 Principais Features

- **Zero Lag (UDP):** O áudio é transmitido em pacotes brutos na rede local, garantindo corte imediato.
- **Qualidade de Estúdio:** Áudio processado em 16-bit estéreo (48000 Hz) sem compressão destrutiva.
- **V.U. Meter UI-Sync:** Interface gráfica imune a travamentos, com medidor estéreo independente (L e R).
- **Background Mode:** Rodagem invisível na bandeja do sistema (Systray) para servidores 24/7.
- **SaaS Aesthetics:** Painel com design Dark Premium construído via CustomTkinter.

## ☁️ Nosso Site

**https://radiocontrolpro-aoip.lovable.app/**

## 💻 Instalação e Uso

### 1. Transmissor (Windows)
Este módulo captura o áudio da sua placa de som/cabo virtual e injeta na rede.

**Pré-requisitos:**
```bash
pip install customtkinter pyaudio numpy pystray Pillow
