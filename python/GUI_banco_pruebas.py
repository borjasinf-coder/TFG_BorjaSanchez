import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time

# -----------------------
# Variables de comunicación
# -----------------------
ser = None
running = False
current_test = 1
test_running = False

# -----------------------
# Funciones Serial
# -----------------------
def list_com_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

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
    running = False
    test_running = False
    if ser and ser.is_open:
        ser.close()
    btn_connect.config(state=tk.NORMAL)
    btn_disconnect.config(state=tk.DISABLED)
    btn_start_test.config(state=tk.NORMAL)
    btn_stop_test.config(state=tk.DISABLED)
    led_label.config(text="Prueba Inactiva", fg="red")
    messagebox.showinfo("Info", "Puerto desconectado")

# Lectura serie
def read_serial():
    global running
    while running:
        try:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8').strip()
                if not test_running:
                    continue  # ignorar datos si la prueba no está activa
                # Prueba 1: VOLT
                if current_test == 1:
                    if line.startswith("VOLT:"):
                        volt = float(line.split(":")[1])
                        update_test1(volt)
                # Prueba 2: VOLT + I
                elif current_test == 2:
                    if line.startswith("VOLT:") and "," in line:
                        parts = line.split(",")
                        volt = float(parts[0].split(":")[1])
                        current = float(parts[1].split(":")[1])
                        update_test2(volt, current)
        except Exception as e:
            print("Error lectura serie:", e)
        time.sleep(0.05)

# -----------------------
# Actualización GUI
# -----------------------
def update_test1(volt):
    label_vmon_test1.config(text=f"V Zener: {volt:.3f} V")
    progress_vmon_test1['value'] = volt * 100

def update_test2(volt, current):
    label_vmon_test2.config(text=f"V prog: {volt:.3f} V")
    progress_vmon_test2['value'] = volt * 100
    label_ifugas.config(text=f"I fugas: {current:.6f} A")
    progress_ifugas['value'] = current * 1000  # escalado ejemplo

# -----------------------
# Selección de prueba
# -----------------------
def select_test1():
    global current_test
    current_test = 1
    frame_test1.pack(pady=10)
    frame_test2.pack_forget()
    label_test_title.config(text="Prueba 1 - Tensión Zener")

def select_test2():
    global current_test
    current_test = 2
    frame_test2.pack(pady=10)
    frame_test1.pack_forget()
    label_test_title.config(text="Prueba 2 - Corriente de fugas")

# -----------------------
# Iniciar / Parar prueba
# -----------------------
def start_test():
    global test_running
    if ser is None or not ser.is_open:
        messagebox.showwarning("Aviso", "Conecta primero al ESP32")
        return
    test_running = True
    btn_start_test.config(state=tk.DISABLED)
    btn_stop_test.config(state=tk.NORMAL)
    led_label.config(text="Prueba Activa", fg="green")
    # Enviar comando START al ESP32
    ser.write(f"START{current_test}\n".encode())

def stop_test():
    global test_running
    test_running = False
    btn_start_test.config(state=tk.NORMAL)
    btn_stop_test.config(state=tk.DISABLED)
    led_label.config(text="Prueba Inactiva", fg="red")
    # Enviar comando STOP al ESP32
    ser.write(f"STOP{current_test}\n".encode())

# -----------------------
# Crear ventana
# -----------------------
root = tk.Tk()
root.title("TFG Electrónica - GUI Final")
root.geometry("550x450")



# Frame Conexión
frame_conn = tk.Frame(root)
frame_conn.pack(pady=10)
tk.Label(frame_conn, text="Puerto COM:").grid(row=0, column=0, padx=5)
combo_ports = ttk.Combobox(frame_conn, values=list_com_ports(), width=10)
combo_ports.grid(row=0, column=1, padx=5)
btn_connect = tk.Button(frame_conn, text="Conectar", command=connect)
btn_connect.grid(row=0, column=2, padx=5)
btn_disconnect = tk.Button(frame_conn, text="Desconectar", command=disconnect, state=tk.DISABLED)
btn_disconnect.grid(row=0, column=3, padx=5)
btn_refresh = tk.Button(frame_conn, text="Actualizar puertos", command=lambda: combo_ports.config(values=list_com_ports()))
btn_refresh.grid(row=0, column=4, padx=5)

# Frame selección pruebas + control
frame_select = tk.Frame(root)
frame_select.pack(pady=10)
btn_test1 = tk.Button(frame_select, text="Prueba 1 - Tensión Zener", command=select_test1)
btn_test1.grid(row=0, column=0, padx=10)
btn_test2 = tk.Button(frame_select, text="Prueba 2 - Corriente de fugas", command=select_test2)
btn_test2.grid(row=0, column=1, padx=10)
btn_start_test = tk.Button(frame_select, text="Iniciar prueba", command=start_test)
btn_start_test.grid(row=0, column=2, padx=10)
btn_stop_test = tk.Button(frame_select, text="Parar prueba", command=stop_test, state=tk.DISABLED)
btn_stop_test.grid(row=0, column=3, padx=10)
led_label = tk.Label(frame_select, text="Prueba Inactiva", fg="red", font=("Arial", 12))
led_label.grid(row=1, column=0, columnspan=4, pady=5)
label_test_title = tk.Label(root, text="Prueba 1 - Tensión Zener", font=("Arial", 14, "bold"))
label_test_title.pack(pady=5)

# -----------------------
# Frame Prueba 1
# -----------------------
frame_test1 = tk.Frame(root)
label_vmon_test1 = tk.Label(frame_test1, text="V Zener: -- V", font=("Arial", 14))
label_vmon_test1.pack(pady=5)
progress_vmon_test1 = ttk.Progressbar(frame_test1, length=350, maximum=3.3)
progress_vmon_test1.pack(pady=5)

# -----------------------
# Frame Prueba 2
# -----------------------
frame_test2 = tk.Frame(root)
label_vmon_test2 = tk.Label(frame_test2, text="V prog: -- V", font=("Arial", 14))
label_vmon_test2.pack(pady=5)
progress_vmon_test2 = ttk.Progressbar(frame_test2, length=350, maximum=3.3)
progress_vmon_test2.pack(pady=5)
label_ifugas = tk.Label(frame_test2, text="I fugas: -- A", font=("Arial", 14))
label_ifugas.pack(pady=5)
progress_ifugas = ttk.Progressbar(frame_test2, length=350, maximum=10)
progress_ifugas.pack(pady=5)

# Inicialmente prueba 1 visible
select_test1()

# Ejecutar GUI
root.mainloop()
