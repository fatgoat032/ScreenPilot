ScreenPilot
An AI agent that controls a Linux desktop (Wayland/DBus) and web browsers (CDP).

I recently updated the browser parser to use CDP instead of just relying on OCR. It's way more reliable for extracting DOM elements and typing into forms. I also swapped out EasyOCR for PaddleOCR, which is a lot more accurate and faster for the desktop vision side of things.

That said, this project is currently full of bugs. It's a work in progress, and I'm actively working on fixing it.
