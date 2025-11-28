import tkinter as tk
from tkinter import ttk, messagebox

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("test2")
        self.geometry("600x400")
        
        # Create UI
        self.create_widgets()
    
    def create_widgets(self):
        # Title
        title = ttk.Label(self, text="test2", font=("Arial", 20))
        title.pack(pady=20)
        
        # Input frame
        input_frame = ttk.Frame(self)
        input_frame.pack(pady=10)
        
        ttk.Label(input_frame, text="Enter text:").grid(row=0, column=0, padx=5)
        self.entry = ttk.Entry(input_frame, width=30)
        self.entry.grid(row=0, column=1, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Submit", command=self.on_submit).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear", command=self.on_clear).pack(side=tk.LEFT, padx=5)
        
        # Output
        self.output = tk.Text(self, height=10, width=60)
        self.output.pack(pady=10)
    
    def on_submit(self):
        text = self.entry.get()
        if text:
            self.output.insert(tk.END, f"You entered: {text}\n")
            messagebox.showinfo("Success", "Text submitted!")
        else:
            messagebox.showwarning("Warning", "Please enter some text")
    
    def on_clear(self):
        self.entry.delete(0, tk.END)
        self.output.delete(1.0, tk.END)

if __name__ == "__main__":
    app = App()
    app.mainloop()
