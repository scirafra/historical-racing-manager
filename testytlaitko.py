import tkinter as tk

# Function to be called when a square is clicked
def on_square_click(square_id):
    print(f"Square {square_id} clicked!")

# Number of squares
num_squares = 7  # Change this value to create more or fewer squares

# Size of each square
square_size = 50

# Spacing between squares
spacing = 10

# Calculate the canvas size
canvas_size = (square_size + spacing) * num_squares

# Create the main window
root = tk.Tk()
root.title("Clickable Squares")

# Create a canvas to draw the squares
canvas = tk.Canvas(root, width=canvas_size, height=square_size + spacing * 2)
canvas.pack()

# Draw the squares with text
for i in range(num_squares):
    x1 = spacing + i * (square_size + spacing)
    y1 = spacing
    x2 = x1 + square_size
    y2 = y1 + square_size
    square = canvas.create_rectangle(x1, y1, x2, y2, fill="blue")

    # Add text to the center of the square
    text = canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=f"Square {i+1}", fill="white")

    # Group the square and text together and bind them to the click event
    canvas.tag_bind(square, "<Button-1>", lambda event, sq_id=i+1: on_square_click(sq_id))
    canvas.tag_bind(text, "<Button-1>", lambda event, sq_id=i+1: on_square_click(sq_id))

# Start the Tkinter event loop
root.mainloop()
