import tkinter as tk 
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time

# TFG Desarrollo de aplicaciones electrónicas. Borja Sánchez Rodríguez.
# Diseño de una GUI en Python para la comunicación serie con placa ESP32.
# Preparado para el manejo de los test y visualización de resultados.

# ================== Variables globales ==================
ser         = None
running     = False
current_test = 1
test_running = False

# ================== Serial ==================
# Funciones para la conexión serie entre placa y PC
def list_com_ports():
    # Devuelve la lista de puertos serie disponibles
    return [p.device for p in serial.tools.list_ports.comports()]

def connect():
    global ser, running
    port = combo_ports.get()
    if not port:
        messagebox.showwarning("Aviso", "Selecciona un puerto COM")
        return
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        running = True
        threading.Thread(target=read_serial, daemon=True).start()
        btn_connect.config(state=tk.DISABLED)
        btn_disconnect.config(state=tk.NORMAL)
        messagebox.showinfo("Info", f"Conectado a {port}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo conectar: {e}")

def disconnect():
    global ser, running, test_running
    running      = False
    test_running = False
    if ser and ser.is_open:
        ser.close()
    btn_connect.config(state=tk.NORMAL)
    btn_disconnect.config(state=tk.DISABLED)
    btn_start_test.config(state=tk.NORMAL)
    btn_stop_test.config(state=tk.DISABLED)
    led_label.config(text="Prueba Inactiva", fg="red")
    messagebox.showinfo("Info", "Puerto desconectado")

# ================== Lectura de datos serie ==================
# Se leen los datos enviados por la placa ESP32 por serie. 
# Han de coincidir los prompts enviados por esta para poder leerlos correctamente.
def read_serial():
    global running
    while running:
        try:
            if ser and ser.in_waiting:
                line = ser.readline().decode('utf-8').strip()
                if not test_running:
                    continue
                if current_test == 1:
                    if line.startswith("VOLT:") and "," not in line:
                        vz = float(line.split(":")[1])
                        root.after(0, refresh_test1, vz)
                elif current_test == 2:
                    if line.startswith("VOLT:") and "," in line:
                        parts   = line.split(",")
                        vprog    = float(parts[0].split(":")[1])
                        iz     = float(parts[1].split(":")[1])
                        root.after(0, refresh_test2, vprog, iz)
        except Exception as e:
            print("Error lectura serie:", e)
        time.sleep(0.05)

# ================== Refresh ==================
# Funciones para actualizazr los valores medidos por los tests.
def refresh_test1(vz):
    label_vmon_test1.config(text=f"V Zener: {vz:.2f} V")
    # Barra escalada 0-75 V
    progress_vmon_test1['value'] = vz

def refresh_test2(vprog, iz):
    label_vmon_test2.config(text=f"V prog: {vprog:.2f} V")
    progress_vmon_test2['value'] = vprog
    label_ifugas.config(text=f"I fugas: {iz:.3f} µA")
    progress_ifugas['value'] = iz

# ================== Tests ==================
# Funciones para seleccionar cada test.
def select_test1():
    global current_test
    #Parar prueba si ya hay una activa
    if test_running:
        stop_test()
    current_test = 1
    frame_test1.pack(pady=10)
    frame_test2.pack_forget()
    label_test_title.config(text="Prueba 1 – Tensión Zener")

def select_test2():
    global current_test
    if test_running:
        stop_test()
    current_test = 2
    frame_test2.pack(pady=10)
    frame_test1.pack_forget()
    label_test_title.config(text="Prueba 2 – Corriente de fugas")

# ================== StartStop Test ==================
# Funciones para iniciar y para los test.
def get_diode_suffix():
    """Devuelve _GREEN o _BLUE según el desplegable."""
    return "_GREEN" if combo_diode.get() == "Diodo Verde" else "_BLUE"

def start_test():
    global test_running
    if ser is None or not ser.is_open:
        messagebox.showwarning("Aviso", "Conecta primero al ESP32")
        return
    test_running = True
    btn_start_test.config(state=tk.DISABLED)
    btn_stop_test.config(state=tk.NORMAL)
    led_label.config(text="Prueba Activa", fg="green")
    cmd = f"START{current_test}{get_diode_suffix()}\n"
    ser.write(cmd.encode())

def stop_test():
    global test_running
    test_running = False
    btn_start_test.config(state=tk.NORMAL)
    btn_stop_test.config(state=tk.DISABLED)
    led_label.config(text="Prueba Inactiva", fg="red")
    ser.write(b"STOP\n")

# ======================= GUI =========================
# A partir de aquí se crea la interfaz gráfica con la extensión Tkinter.
root = tk.Tk()
root.title("TFG Electrónica – GUI")
root.geometry("600x530")

# --- Conexión ---
frame_conn = tk.Frame(root)
frame_conn.pack(pady=10)
tk.Label(frame_conn, text="Puerto COM:").grid(row=0, column=0, padx=5)
combo_ports = ttk.Combobox(frame_conn, values=list_com_ports(), width=10)
combo_ports.grid(row=0, column=1, padx=5)
btn_connect = tk.Button(frame_conn, text="Conectar", command=connect)
btn_connect.grid(row=0, column=2, padx=5)
btn_disconnect = tk.Button(frame_conn, text="Desconectar", command=disconnect,
                           state=tk.DISABLED)
btn_disconnect.grid(row=0, column=3, padx=5)
tk.Button(frame_conn, text="↻ Puertos",
          command=lambda: combo_ports.config(values=list_com_ports())
          ).grid(row=0, column=4, padx=5)

# --- Selección de diodo ---
# Despleglabe para elegir el diodo en prueba de la lista de los disponibles.
# Si se quieren crear nuevos tipos, habría que añadirlos aquí y en el ESP32.
frame_diode = tk.Frame(root)
frame_diode.pack(pady=5)
tk.Label(frame_diode, text="Tipo de diodo:", font=("Arial", 11)).grid(row=0, column=0, padx=8)
combo_diode = ttk.Combobox(frame_diode,
                            values=["Diodo Verde", "Diodo Azul"],
                            state="readonly", width=14,
                            font=("Arial", 11))
combo_diode.current(0)   # Diodo verde por defecto
combo_diode.grid(row=0, column=1, padx=8)

# --- Selección y control de prueba ---
# Botones para seleccionar pruebas, comenzar o detenerlas.
frame_select = tk.Frame(root)
frame_select.pack(pady=8)
tk.Button(frame_select, text="Prueba 1 – Tensión Zener",
          command=select_test1).grid(row=0, column=0, padx=10)
tk.Button(frame_select, text="Prueba 2 – Corriente de fugas",
          command=select_test2).grid(row=0, column=1, padx=10)
btn_start_test = tk.Button(frame_select, text="▶ Iniciar", command=start_test,
                           bg="#2ecc71", fg="white", font=("Arial", 10, "bold"))
btn_start_test.grid(row=0, column=2, padx=10)
btn_stop_test = tk.Button(frame_select, text="■ Parar", command=stop_test,
                          bg="#e74c3c", fg="white", font=("Arial", 10, "bold"),
                          state=tk.DISABLED)
btn_stop_test.grid(row=0, column=3, padx=10)

led_label = tk.Label(frame_select, text="Prueba Inactiva", fg="red",
                     font=("Arial", 12, "bold"))
led_label.grid(row=1, column=0, columnspan=4, pady=5)

label_test_title = tk.Label(root, text="Prueba 1 – Tensión Zener",
                            font=("Arial", 14, "bold"))
label_test_title.pack(pady=5)

# --- Test 1 Vz ---
# Visionado de los resultados del test 1. Barra de progreso con los límites de la fuente.
frame_test1 = tk.Frame(root)
label_vmon_test1 = tk.Label(frame_test1, text="V Zener: -- V", font=("Arial", 14))
label_vmon_test1.pack(pady=5)
progress_vmon_test1 = ttk.Progressbar(frame_test1, length=420,
                                       maximum=75)   
progress_vmon_test1.pack(pady=5)
tk.Label(frame_test1, text="0 V                    37.5 V                   75 V",
         font=("Arial", 8), fg="gray").pack()

# --- Test 2 Iz ---
# Visionado de los resultados del test 2. Barra de progreso con los límites de la fuente.
frame_test2 = tk.Frame(root)
label_vmon_test2 = tk.Label(frame_test2, text="V prog: -- V", font=("Arial", 14))
label_vmon_test2.pack(pady=5)
progress_vmon_test2 = ttk.Progressbar(frame_test2, length=420, maximum=75)
progress_vmon_test2.pack(pady=5)
tk.Label(frame_test2, text="0 V                    37.5 V                   75 V",
         font=("Arial", 8), fg="gray").pack()
label_ifugas = tk.Label(frame_test2, text="I fugas: -- µA", font=("Arial", 14))
label_ifugas.pack(pady=5)
progress_ifugas = ttk.Progressbar(frame_test2, length=420, maximum=1000)
progress_ifugas.pack(pady=5)
tk.Label(frame_test2, text="0 µA                   500 µA                1000 µA",
         font=("Arial", 8), fg="gray").pack()

# Se inicializa la interfaz mostrando el test 1 por defecto.
select_test1()
root.mainloop()