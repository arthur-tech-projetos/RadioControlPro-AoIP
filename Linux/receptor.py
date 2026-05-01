import customtkinter as ctk
import pyaudio
import socket
import threading
import numpy as np
from ctypes import *
import sys
import pystray
from PIL import Image, ImageDraw

# =======================================================
# SILENCIADOR DO ALSA
# =======================================================
if sys.platform.startswith('linux'):
    ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
    def py_error_handler(filename, line, function, err, fmt): pass
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    try:
        asound = cdll.LoadLibrary('libasound.so.2')
        asound.snd_lib_error_set_handler(c_error_handler)
    except OSError: pass

# =======================================================
# CONFIGURAÇÕES DE ESTILO
# =======================================================
BG_COLOR = "#0F1219"
CARD_COLOR = "#1A1E29"
TEXT_COLOR = "#FFFFFF"
MUTED_TEXT = "#8B949E"
GREEN_BTN = "#2ECC71"
RED_BTN = "#E74C3C"
FONT_FAMILY = "monospace" 

# =======================================================
# APLICATIVO PRINCIPAL
# =======================================================
class ReceptorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Radio Control Pro - Receptor AoIP")
        self.geometry("600x480")
        self.minsize(500, 400)
        self.configure(fg_color=BG_COLOR)
        
        self.is_receiving = False
        self.audio_thread = None
        self.pyaudio_instance = pyaudio.PyAudio()
        self.tray_icon = None
        self.ultima_largura = 0 
        
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.esconder_na_bandeja)
        self.after(500, self.iniciar_receptor)

    # --- FUNÇÕES DA BANDEJA (SYSTRAY) ---
    def criar_imagem_icone(self):
        imagem = Image.new('RGB', (64, 64), color=BG_COLOR)
        draw = ImageDraw.Draw(imagem)
        cor = GREEN_BTN if self.is_receiving else RED_BTN
        draw.ellipse((16, 16, 48, 48), fill=cor)
        return imagem

    def esconder_na_bandeja(self):
        self.withdraw()
        menu = pystray.Menu(
            pystray.MenuItem("Restaurar App", self.restaurar_da_bandeja),
            pystray.MenuItem("Sair Totalmente", self.sair_do_app)
        )
        self.tray_icon = pystray.Icon("AoIP_RX", self.criar_imagem_icone(), "AoIP Receiver - RX", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def restaurar_da_bandeja(self, icon, item):
        icon.stop()
        self.after(0, self.deiconify)

    def sair_do_app(self, icon, item):
        icon.stop()
        self.is_receiving = False
        self.after(0, self.destroy)

    # --- INTERFACE ---
    def setup_ui(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(self.header_frame, text="AoIP Receiver", font=(FONT_FAMILY, 24, "bold"), text_color=TEXT_COLOR).pack(side="left")
        self.status_badge = ctk.CTkLabel(self.header_frame, text="● OFFLINE", font=(FONT_FAMILY, 12, "bold"), text_color=RED_BTN)
        self.status_badge.pack(side="right")

        self.config_card = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=10)
        self.config_card.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(self.config_card, text="Aguardando conexão em:", font=(FONT_FAMILY, 12), text_color=MUTED_TEXT).pack(anchor="w", padx=20, pady=(15, 0))
        
        self.ip_frame = ctk.CTkFrame(self.config_card, fg_color="transparent")
        self.ip_frame.pack(fill="x", padx=20, pady=(5, 15))
        self.ip_entry = ctk.CTkEntry(self.ip_frame, font=(FONT_FAMILY, 14))
        self.ip_entry.insert(0, "0.0.0.0 (Todas as redes)")
        self.ip_entry.configure(state="disabled")
        self.ip_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.port_entry = ctk.CTkEntry(self.ip_frame, width=100, font=(FONT_FAMILY, 14))
        self.port_entry.insert(0, "5005")
        self.port_entry.pack(side="right")

        self.control_card = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=10)
        self.control_card.pack(fill="both", expand=True, padx=20, pady=10)

        self.btn_frame = ctk.CTkFrame(self.control_card, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=15)
        self.btn_ligar = ctk.CTkButton(self.btn_frame, text="▶ Escutar", font=(FONT_FAMILY, 14, "bold"), fg_color=GREEN_BTN, hover_color="#27ae60", command=self.iniciar_receptor)
        self.btn_ligar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.btn_parar = ctk.CTkButton(self.btn_frame, text="■ Parar", font=(FONT_FAMILY, 14, "bold"), fg_color=BG_COLOR, border_color=RED_BTN, border_width=2, text_color=RED_BTN, state="disabled", command=self.parar_receptor)
        self.btn_parar.pack(side="right", fill="x", expand=True)

        ctk.CTkLabel(self.control_card, text="Sinal Recebido Estéreo (RX)", font=(FONT_FAMILY, 12), text_color=MUTED_TEXT).pack(anchor="w", padx=20)
        
        self.vu_canvas = ctk.CTkCanvas(self.control_card, bg=BG_COLOR, highlightthickness=0, height=60)
        self.vu_canvas.pack(fill="x", padx=20, pady=(5, 20))
        self.vu_canvas.bind("<Configure>", self.redimensionar_vu)
        
        self.total_segments = 40
        self.vu_rects_l = []
        self.vu_rects_r = []

    def desenhar_retangulo_arredondado(self, canvas, x1, y1, x2, y2, r, **kwargs):
        pontos = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return canvas.create_polygon(pontos, smooth=True, **kwargs)

    def redimensionar_vu(self, event=None):
        largura_total = self.vu_canvas.winfo_width()
        if largura_total < 50: return
        if self.ultima_largura == largura_total: return
        self.ultima_largura = largura_total

        self.vu_canvas.delete("all")
        self.vu_rects_l.clear()
        self.vu_rects_r.clear()

        espaco = 3 
        largura_seg = (largura_total - 30) / self.total_segments - espaco
        offset_x = 30
        
        y1_l, y2_l = 5, 22
        y1_r, y2_r = 33, 50
        
        self.vu_canvas.create_text(10, (y1_l+y2_l)/2, text="L", fill=MUTED_TEXT, font=(FONT_FAMILY, 10, "bold"))
        self.vu_canvas.create_text(10, (y1_r+y2_r)/2, text="R", fill=MUTED_TEXT, font=(FONT_FAMILY, 10, "bold"))

        for i in range(self.total_segments):
            x1 = offset_x + (i * (largura_seg + espaco))
            x2 = x1 + largura_seg
            self.vu_rects_l.append(self.desenhar_retangulo_arredondado(self.vu_canvas, x1, y1_l, x2, y2_l, 4, fill="#2A2D3E", outline=""))
            self.vu_rects_r.append(self.desenhar_retangulo_arredondado(self.vu_canvas, x1, y1_r, x2, y2_r, 4, fill="#2A2D3E", outline=""))

    def atualizar_vu(self, vol_l, vol_r):
        if not self.vu_rects_l: return
        active_l = int((vol_l / 100) * self.total_segments)
        active_r = int((vol_r / 100) * self.total_segments)
        for i in range(self.total_segments):
            if i < 25: color = "#00FF00"
            elif i < 35: color = "#FFFF00"
            else: color = "#FF0000"
            self.vu_canvas.itemconfig(self.vu_rects_l[i], fill=color if i < active_l else "#2A2D3E")
            self.vu_canvas.itemconfig(self.vu_rects_r[i], fill=color if i < active_r else "#2A2D3E")

    def iniciar_receptor(self):
        if self.is_receiving: return
        self.is_receiving = True
        self.btn_ligar.configure(state="disabled", fg_color=BG_COLOR, text_color=GREEN_BTN, border_color=GREEN_BTN, border_width=2)
        self.btn_parar.configure(state="normal", fg_color=RED_BTN, text_color=TEXT_COLOR)
        self.status_badge.configure(text="● ESCUTANDO", text_color=GREEN_BTN)
        
        porta = int(self.port_entry.get())
        self.audio_thread = threading.Thread(target=self.motor_audio, args=(porta,))
        self.audio_thread.daemon = True
        self.audio_thread.start()

    def parar_receptor(self):
        self.is_receiving = False
        self.btn_ligar.configure(state="normal", fg_color=GREEN_BTN, text_color=TEXT_COLOR, border_width=0)
        self.btn_parar.configure(state="disabled", fg_color=BG_COLOR, text_color=RED_BTN)
        self.status_badge.configure(text="● OFFLINE", text_color=RED_BTN)
        self.atualizar_vu(0, 0)

    def motor_audio(self, porta):
        CHUNK, FORMAT, CHANNELS, RATE, HOST = 1024, pyaudio.paInt16, 2, 48000, "0.0.0.0"
        try:
            stream = self.pyaudio_instance.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((HOST, porta))
            sock.settimeout(0.5) 
            
            fps_sync = 0 # Inicia o controle de frames do V.U.
            
            while self.is_receiving:
                try:
                    data, addr = sock.recvfrom(65536)
                    stream.write(data, exception_on_underflow=False)
                    
                    fps_sync += 1
                    # Atualiza a interface gráfica apenas a cada 3 pacotes (Alivia a CPU do Linux)
                    if fps_sync % 3 == 0:
                        audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                        canal_l, canal_r = audio_array[0::2], audio_array[1::2]
                        
                        rms_l = np.sqrt(np.mean(canal_l**2)) if len(canal_l) > 0 else 0
                        rms_r = np.sqrt(np.mean(canal_r**2)) if len(canal_r) > 0 else 0
                        
                        # Trava Anti-Corrupção Matemática
                        vol_l = 0 if np.isnan(rms_l) else min(100, (rms_l / 32768.0) * 300)
                        vol_r = 0 if np.isnan(rms_r) else min(100, (rms_r / 32768.0) * 300)
                        
                        self.after(0, self.atualizar_vu, vol_l, vol_r)
                        
                        # Reseta o contador para não consumir memória
                        if fps_sync >= 60: fps_sync = 0
                        
                except socket.timeout:
                    self.after(0, self.atualizar_vu, 0, 0)
                    continue
        except Exception as e: print(f"Erro: {e}")
        finally:
            if 'stream' in locals(): stream.close()
            if 'sock' in locals(): sock.close()

if __name__ == "__main__":
    app = ReceptorApp()
    app.mainloop()