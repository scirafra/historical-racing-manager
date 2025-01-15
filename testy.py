import tkinter as tk

class ScrollableFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Create a canvas to hold the content
        canvas = tk.Canvas(self)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add vertical and horizontal scrollbars to the canvas
        v_scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        h_scrollbar = tk.Scrollbar(self, orient="horizontal", command=canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure the canvas to work with the scrollbars
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Create a frame inside the canvas to hold the actual content
        self.content_frame = tk.Frame(canvas)
        self.content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tkinter Vertical & Horizontal Scrollable Example")
        self.geometry("400x300")

        # Create the scrollable frame
        scrollable_frame = ScrollableFrame(self)
        scrollable_frame.pack(fill=tk.BOTH, expand=True)

        # Populate the scrollable frame with a grid of content
        for i in range(1, 21):  # 20 rows of content
            for j in range(1, 21):  # 20 columns of content
                tk.Label(scrollable_frame.content_frame, text=f"R{i}C{j}", font=("Arial", 16), borderwidth=1, relief="solid").grid(row=i, column=j, padx=5, pady=5)

if __name__ == "__main__":
    app = App()
    app.mainloop()
