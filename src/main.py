#!/usr/bin/env python3

import sys
import os
import json
import random
import markdown
import base64
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.extra import ExtraExtension
from markdown.extensions.toc import TocExtension
import html
import requests
from PySide6.QtWidgets import QApplication, QWidget, QMenu, QDialog, QVBoxLayout, QLineEdit, QSpacerItem, QSizePolicy, QSizeGrip
from PySide6.QtCore import Qt, QTimer, QPoint, QThread, QObject, Signal, Slot
from PySide6.QtGui import QPainter, QPixmap, QAction, QPolygon, QColor, QDesktopServices
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
import pygame.mixer

# Get absolute path to assets directory
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

PROMPT_MENU_WIDTH = 300
PROMPT_MENU_HEIGHT = 400 

def load_asset(filename):
	"""Returns the full path to an asset file."""
	return os.path.join(ASSETS_DIR, filename)

def load_animations(json_path, sheet_columns):
	"""Load animations.json and return dict: name -> {'Frames': [...], 'Loops': [...]}"""
	with open(json_path, 'r', encoding='utf-8') as f:
		data = json.load(f)

	animations = {}
	for animation in data:
		name = animation['Name']
		frames = []
		last_col, last_row = 0, 0
		for frame in animation['Frames']:
			duration = frame.get('Duration', 100)
			offsets = frame.get('ImagesOffsets')
			sound = frame.get('Sound')

			if offsets:
				col = offsets.get('Column', 0)
				row = offsets.get('Row', 0)
				last_col, last_row = col, row
			else:
				print(f"Warning: Missing ImagesOffsets for animation '{name}', frame {len(frames)}. Using last known offset.")
				# reuse previous valid offset
				col, row = last_col, last_row

			index = row * sheet_columns + col
			sound_path = load_asset(sound) if sound else None
			frames.append((index, duration, sound_path))

		# Get the loops list if present
		loops = animation.get("Loops", [])

		animations[name] = {"Frames": frames, "Loops": loops}

	return animations

def prompt_chatgpt(prompt, system_message, history, api_key, model):
	"""Send a prompt to OpenAI's ChatGPT API."""
	messages=[]

	# Construct the message part of the API request
	if system_message != '':
		messages.append({"role": "system", "content": system_message})

	for i in range(len(history)):
		messages.append({"role": "assistant", "content": history[i]})

	messages.append({"role": "user", "content": prompt})

	request_data = {"model": model, "messages": messages}
	request_header = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}", "OpenAI-Beta": "assistants=v1"}

	try:
		# Send the request to the API
		api_response = requests.post('https://api.openai.com/v1/chat/completions', json=request_data, headers=request_header)

		# Raise HTTPError for bad responses
		api_response.raise_for_status()

		return api_response.json()
	except requests.exceptions.HTTPError as http_err:
		print(f"HTTP error occured: {http_err}")
		return {"error": f"HTTP error: {response.status_code} - {response.text}"}
	except requests.exceptions.ConnectionError:
		print(f"Connection error: Failed to reach API")
		return {"error": "Connection error: Unable to reach API."}
	except requests.exceptions.Timeout:
		print("Timeout error: API response took too long.")
		return {"error": "Timeout error: The API took too long to respond."}
	except requests.exceptions.RequestException as req_err:
		print(f"Request error occurred: {req_err}")
		return {"error": f"Request error: {req_err}"}

class ClippyWindow(QWidget):
	def __init__(self):
		super().__init__()

		self.exiting = False
		self.dialog = None
		self.prompting = False
		
		# Remove window border and make background transparent
		self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
		self.setAttribute(Qt.WA_TranslucentBackground)
		
		# Load sprite sheet
		self.sprite_sheet = QPixmap(load_asset("clippy-map.png"))
		self.sprite_width = 124
		self.sprite_height = 93
		self.cols = 27
		self.rows = 34
		self.frames = self.extract_frames()

		# Load animations from JSON
		self.animations = load_animations(load_asset("animations.json"), self.cols)
		if "Idle" not in self.animations:
			self.animations["Idle"] = [(0, 1000, None)]

		self.current_animation = "Idle"
		self.frame_index = 0

		# Animation timer (will be updated every frame)
		self.timer = QTimer()
		self.timer.timeout.connect(self.next_frame)
		self.start_current_frame_timer()

		# Idle timer
		self.idle_timer = QTimer()
		self.idle_timer.timeout.connect(self.play_idle_animation)
		self.start_idle_timer()

		# Set window size
		self.resize(self.sprite_width, self.sprite_height)
		
		# For handling mouse dragging
		self.dragging = False
		self.offset = None

		# Create sound effects player
		pygame.mixer.init()

		# Pick a geeting animation at random and play it.
		greetings = ["Show", "Greeting_1", "Greeting_2"]
		self.set_animation(greetings[random.randint(0, len(greetings) - 1)])

	def extract_frames(self):
		"""Extract frames from sprite sheet."""
		frames = []
		for row in range(self.rows):
			for col in range(self.cols):
				x = col * self.sprite_width
				y = row * self.sprite_height
				frame = self.sprite_sheet.copy(x, y, self.sprite_width, self.sprite_height)
				frames.append(frame)
		return frames

	def start_current_frame_timer(self):
		"""Start timer for the current frame's duration."""
		if self.current_animation in self.animations:
			animation_seq = self.animations[self.current_animation]["Frames"]
			_, duration, _ = animation_seq[self.frame_index]
			self.timer.start(max(duration, 10))

	def next_frame(self):
		"""Advance to the next frame while keeping track of loops and sounds."""
		if self.current_animation in self.animations:
			animation_obj = self.animations[self.current_animation]
			animation_seq = animation_obj["Frames"]
			loops = animation_obj.get("Loops", [])
			loop_controls = getattr(self, "loop_controls", {}) if hasattr(self, "loop_controls") else {}

			# Warn if loop_controls contains idices for non-existent loops
			if loop_controls:
				for idx in loop_controls:
					if idx >= len(loops):
						print(f"Warning: loop_controls specifies loop index of {idx} which does not exist in animation '{self.current_animation}'.")
	
			# Track per-loop active position (only if looping)
			if not hasattr(self, "active_loop_positions"):
				self.active_loop_positions = {}
	
			next_index = self.frame_index + 1
			handled_loop = False
	
			if loop_controls:
				for loop_idx, loop in enumerate(loops):
					loop_entry = loop["LoopEntry"]
					loop_frames = loop["LoopFrames"]
					loop_exit = loop["LoopExit"]
	
					# Entering the loop
					if self.frame_index == loop_entry:
						count = self.loop_counters.get(loop_idx, 0)
						max_loops = loop_controls.get(loop_idx, 0)
						if count < max_loops:
							self.loop_counters[loop_idx] = count + 1
							self.active_loop_positions[loop_idx] = 0
							next_index = loop_frames[0]
							handled_loop = True
						else:
							# Remove active loop position when done
							self.active_loop_positions.pop(loop_idx, None)
							next_index = loop_exit
							handled_loop = True
						break
	
					# Inside a loop
					if loop_idx in self.active_loop_positions and self.frame_index in loop_frames:
						pos = self.active_loop_positions[loop_idx]
						if pos < len(loop_frames) - 1:
							pos += 1
							self.active_loop_positions[loop_idx] = pos
							next_index = loop_frames[pos]
							handled_loop = True
						else:
							count = self.loop_counters.get(loop_idx, 0)
							max_loops = loop_controls.get(loop_idx, 0)
							if count < max_loops:
								self.loop_counters[loop_idx] = count + 1
								self.active_loop_positions[loop_idx] = 0
								next_index = loop_frames[0]
								handled_loop = True
							else:
								self.active_loop_positions.pop(loop_idx, None)
								next_index = loop_exit
								handled_loop = True
						break
	
			if not handled_loop and next_index >= len(animation_seq):
				if hasattr(self, "exiting") and self.exiting:
					QApplication.instance().quit()
				elif self.current_animation != "Idle":
					self.set_animation("Idle")
				else:
					self.frame_index = 0
			else:
				self.frame_index = next_index
	
			# Play sound if present
			frame = animation_seq[self.frame_index]
			sound_path = None
			if isinstance(frame, dict):
				sound_path = frame.get("Sound")
			elif isinstance(frame, tuple) and len(frame) > 2:
				sound_path = frame[2]
			if sound_path:
				self.play_sound(sound_path)
	
			self.update()
			self.start_current_frame_timer()

	def set_animation(self, name, loop_controls=None):
		"""Set the animation."""
		if name in self.animations:
			self.current_animation = name
			self.frame_index = 0

			# Loop controls
			self.loop_controls = loop_controls if loop_controls is not None else {}
			self.loop_counters = {}

			self.update()
			self.start_current_frame_timer()
		else:
			print("Warning: Could not find animation", name)

	def play_sound(self, sound_path):
		"""Play sound effect."""
		sound = pygame.mixer.Sound(sound_path)
		sound.play()

	def start_idle_timer(self):
		"""Set random idle animation time."""
		delay = random.randint(20, 45) * 1000
		self.idle_timer.start(delay)

	def play_idle_animation(self):
		"""Pick random idle animation and play it."""
		if self.current_animation == "Idle":
			animations = ["LookRight", "Explain", "IdleRopePile", "IdleAtom", "LookUpRight", "IdleSideToSide", "LookLeft", "IdleHeadScratch", "LookUpLeft", "IdleFingerTap", "IdleSnooze", "LookDownRight", "LookDown", "LookUp", "LookDownLeft"]
			animation = random.choice(animations)

			if animation == "LookRight" or animation == "LookUpRight" or animation == "LookLeft" or animation == "LookUpLeft" or animation == "LookDownRight" or animation == "LookDown" or animation == "LookUp" or animation == "LookDownLeft":
				loop_times = random.randint(1, 5)
				self.set_animation(animation, {0:loop_times})
			elif animation == "IdleRopePile":
				loop_controls = {}
				for i in range(0, 4):
					loop_times = random.randint(1, 75)
					loop_controls[i] = loop_times

				self.set_animation(animation, loop_controls)
			elif animation == "IdleAtom":
				loop_times = random.randint(1, 8)
				self.set_animation(animation, {0:loop_times})
			elif animation == "IdleSideToSide":
				loop_controls = {}
				for i in range(0, 11):
					loop_times = random.randint(1, 75)
					loop_controls[i] = loop_times

				self.set_animation(animation, loop_controls)
			elif animation == "IdleHeadScratch": # Something seems wrong with the part where we exit the second loop
				loop_controls = {}
				for i in range(0, 1):
					loop_times = random.randint(1, 10)
					loop_controls[i] = loop_times

				self.set_animation(animation, loop_controls)
			elif animation == "IdleFingerTap":
				loop_times = random.randint(1, 75)
				self.set_animation(animation, {0:loop_times})
			elif animation == "IdleSnooze":
				loop_controls = {}

				loop_times = random.randint(1, 75)
				loop_controls[0] = loop_times

				loop_times = random.randint(1, 4)
				loop_controls[1] = loop_times

				self.set_animation(animation, loop_controls)
			else:
				self.set_animation(animation)

			self.start_idle_timer()

	def play_random_animation(self):
		"""Pick random animation and play it."""
		# TODO: Implement looping logic for the animations that need it.
		animations = ["Congratulate", "SendMail", "Thinking", "Print", "GetAttention", "Save", "GestureUp", "Processing", "Alert", "CheckingSomething", "Hearing", "GestureLeft", "Wave", "GestureRight", "Writing", "GetArtsy", "Searching", "EmptyTrash", "GestureDown"]
		animation = random.choice(animations)

		self.set_animation(animation)
		self.start_idle_timer()

	def toggle_prompt_menu(self):
		"""Open / Close the dialog box / prompt menu"""
		if not self.prompting:
			# Create dialog box if it does not exist
			if not hasattr(self, 'dialog') or self.dialog is None:
				self.dialog = DialogBox(self)
				
				dialog_width = self.dialog.width()
				dialog_height = self.dialog.height()
				self.dialog.move(self.pos().x() - (dialog_width - 235),	self.pos().y() - (dialog_height - 15))

			self.dialog.show()
			self.prompting = True
		else:
			if self.dialog is not None:
				self.dialog.hide()
			self.prompting = False

	def adjust_dialog_position(self):
		"""Keep dialog box positioned near character."""
		if not self.dialog:
			return
	
		dialog_width = self.dialog.width()
		dialog_height = self.dialog.height()
	
		p_left = self.dialog.padding_left
		p_right = self.dialog.padding_right
		p_bottom = self.dialog.padding_bottom
	
		# Clippy's top-center point
		clippy_center_x = self.pos().x() + self.width() // 2
		clippy_top_y = self.pos().y()
	
		# Dialog pointer tip wants to land on Clippy's top-center
		dialog_x = clippy_center_x - (dialog_width - p_left - p_right) // 2 - p_left
		dialog_y = clippy_top_y - dialog_height + p_bottom - 20  # 20 is pointer height
	
		self.dialog.move(dialog_x, dialog_y)

	def reposition_clippy_from_dialog(self):
		if not self.dialog:
			return
	
		# Pointer location from DialogBox
		dialog_pos = self.dialog.frameGeometry().topLeft()
		dialog_width = self.dialog.width()
		dialog_height = self.dialog.height()
		p_left = self.dialog.padding_left
		p_right = self.dialog.padding_right
		p_bottom = self.dialog.padding_bottom
	
		# Calculate pointer tip position
		pointer_x = dialog_pos.x() + p_left + (dialog_width - p_left - p_right) // 2
		pointer_y = dialog_pos.y() + dialog_height - p_bottom + 20  # 20 is the pointer tip offset
	
		# Move Clippy so its top-center aligns with pointer
		clippy_new_x = pointer_x - self.width() // 2
		clippy_new_y = pointer_y
	
		self.move(clippy_new_x, clippy_new_y)

	def goodbye(self):
		"""Pick a random exit animation and then exit."""
		if self.dialog:
			self.dialog.shutdown()
			self.dialog.close()

		animations = ["Hide", "GoodBye_1", "GoodBye_2"]
		self.set_animation(animations[random.randint(0, len(animations) - 1)])
		self.exiting = True

	def paintEvent(self, event):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)

		# Draw the current frame.
		if self.current_animation in self.animations:
			animation_seq = self.animations[self.current_animation]["Frames"]
			frame_index, _, _ = animation_seq[self.frame_index]
			frame = self.frames[frame_index]
			painter.drawPixmap(0, 0, frame)

	def keyPressEvent(self, event):
		if event.key() == Qt.Key_Escape:
			if self.prompting == True:
				self.toggle_prompt_menu()

	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton:
			self.dragging = True
			self.offset = event.globalPosition().toPoint() - self.pos()

	def mouseMoveEvent(self, event):
		if self.dragging:
			self.move(event.globalPosition().toPoint() - self.offset)
			self.adjust_dialog_position()

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.LeftButton:
			self.dragging = False

	def contextMenuEvent(self, event):
		menu = QMenu(self)

		# Create menu actions
		if self.prompting == False:
			prompt_action = QAction("Prompt", self)
		else:
			prompt_action = QAction("Hide Prompt", self)

		animate_action = QAction("Animate", self)
		exit_action = QAction("Exit", self)

		# Assign functions to actions
		prompt_action.triggered.connect(self.toggle_prompt_menu)
		animate_action.triggered.connect(self.play_random_animation)
		exit_action.triggered.connect(self.goodbye)

		# Add actions to menu
		menu.addAction(prompt_action)
		menu.addAction(animate_action)
		menu.addAction(exit_action)

		# Display menu at mouse click location
		menu.exec(event.globalPos())

	def closeEvent(self, event):
		self.goodbye()
		event.accept()

class DialogBox(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)

		self.active_threads = []
		self.active_workers = []

		self.default_system_message = "You are a paperclip named Clippy. Your job is to assist the user. You use markdown."
		self.default_model = "gpt-4o-mini"
		self.api_key = os.getenv("OPENAI_API_KEY")

		self.greetings = ["How's life? All work and no play?", "Hey, there. What's the word?"]
		self.greeting = random.choice(self.greetings)
		self.chat_history = [f"Chatbot: {self.greeting}"]

		self.greeting_html = f"<div class='message bot'>{self.greeting}</div>"

		# Window Styling
		self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
		self.setAttribute(Qt.WA_TranslucentBackground)
		self.resize(PROMPT_MENU_WIDTH, PROMPT_MENU_HEIGHT)

		# Dimensions for the dialog bubble.
		self.padding_left = 10
		self.padding_top = 30
		self.padding_right = 10
		self.padding_bottom = 30

		# Layout settings
		layout = QVBoxLayout()
		layout.setContentsMargins(self.padding_left + 10, self.padding_top + 10, self.padding_right + 10, self.padding_bottom + 10)
		layout.setSpacing(0)

		# Resize handle
		size_grip = QSizeGrip(self)
		layout.addWidget(size_grip, 0, Qt.AlignTop| Qt.AlignLeft)

		# Web Engine settings
		self.label = QWebEngineView()
		self.label.setAttribute(Qt.WA_TranslucentBackground)
		self.label.setPage(ExternalLinkPage(self.label))
		self.label.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
		self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		self.label.setHtml(self.generate_html(self.greeting_html))

		# More specific Web Engine settings.
		engine_settings = self.label.page().settings()
		engine_settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
		engine_settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, False)
		engine_settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
		engine_settings.setAttribute(QWebEngineSettings.WebGLEnabled, False)
		engine_settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, False)

		spacer = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)

		# Input field
		self.input_field = QLineEdit()
		self.input_field.setPlaceholderText("Type your response...")
		self.input_field.setStyleSheet("""
			background: rgba(255, 255, 255, 0.8);
			border: 1px solid #aaa;
			border-radius: 5px;
			padding: 4px;
			font-size: 10pt;
		""")
		self.input_field.returnPressed.connect(self.handle_input)

		layout.addWidget(self.label)
		layout.addItem(spacer)
		layout.addWidget(self.input_field)
		self.setLayout(layout)

	def generate_html(self, message):
		"""Generate full HTML structure for displaying messages."""
		return f"""
		<html>
			<head>
				<style>
					body {{
						font-size: 10pt;
						background-color: rgb(255, 255, 204);
						overflow-y: scroll;
						overflow-wrap: break-word;
						max-height: 100vh;
					}}
					.message {{
						padding: 5px;
						border-radius: 5px;
						margin-bottom: 5px;
					}}
					.user {{
						text-align: right;
						font-style: italic;
					}}
					.bot {{
						text-align: left;
					}}
					.codehilite pre {{
						overflow-x: auto;
						white-space: pre;
						display: block;
						max-width: 100%;
					}}
					.codehilite code {{
						display: block;
						overflow-x: auto;
						white-space: pre;
						background-color: #f8f8f8;
						padding: 5px;
						border-radius: 5px;
					}}
				</style>
			</head>
			<body>
				{message}
				<script>
				window.scrollTo(0, document.body.scrollHeight);
				</script>
			</body>
		</html>
		"""

	def handle_input(self):
		input_text = self.input_field.text()

		# Return if empty input
		if not input_text.strip():
			return

		# Sanitize input.
		safe_text = html.escape(input_text)

		# Update UI
		self.label.page().runJavaScript(f"""
			var chatWindow = document.body;
			var newMessage = document.createElement('div');
			newMessage.className = "message user";
			newMessage.innerHTML = "{safe_text}";
			chatWindow.appendChild(newMessage);
			window.scrollTo(0, document.body.scrollHeight);
		""")

		# Display loading message
		gif_base64 = self.get_base64_gif(load_asset("loading.gif"))
		loading_html = f"""
			var loadingMessage = document.createElement('div');
			loadingMessage.id = "loading";
			loadingMessage.className = "message bot";
		
			var img = document.createElement('img');
			img.src = "data:image/gif;base64,{gif_base64}";
			img.alt = "Loading...";
			img.style.display = "block";
		
			loadingMessage.appendChild(img);
			document.body.appendChild(loadingMessage);
			window.scrollTo(0, document.body.scrollHeight);
		"""
		
		self.label.page().runJavaScript(loading_html)

		# Create thread and worker
		thread = QThread()
		worker = ChatWorker(input_text, self.default_system_message, self.chat_history, self.api_key, self.default_model)
		worker.moveToThread(thread)
		
		# Maintain reference
		self.active_threads.append(thread)
		self.active_workers.append(worker)
		
		# Connect signals
		worker.finished.connect(self.display_bot_response)
		worker.error.connect(self.display_error)
		
		def on_finished_or_error():
			thread.quit()
			thread.wait()
			if thread in self.active_threads:
				self.active_threads.remove(thread)
			if worker in self.active_workers:
				self.active_workers.remove(worker)
		
		thread.finished.connect(on_finished_or_error)
		
		# Start the thread
		thread.started.connect(worker.run)
		thread.start()

		self.input_field.clear()


	def display_bot_response(self, prompt, md_reply):
		self.chat_history.append(f"User: {prompt}\nChatbot: {md_reply}")

		html_reply = markdown.markdown(md_reply, extensions=[ExtraExtension(), CodeHiliteExtension(noclasses=True), FencedCodeExtension(), TocExtension(baselevel=2)])
		safe_html = html_reply.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'").replace("`", "\\`").replace("\n", "\\n").replace("{", "\\{").replace("}", "\\}").replace("$", "\\$")

		self.label.page().runJavaScript(f"""
			var loading = document.getElementById('loading');
			if (loading) loading.remove();
	
			var response = document.createElement('div');
			response.className = "message bot";
			response.innerHTML = `{safe_html}`;
			document.body.appendChild(response);
			response.scrollIntoView({{ behavior: "smooth", block: "start" }});
		""")

	def display_error(self, error_msg):
		print(f"[ERROR] {error_msg}")

		self.label.page().runJavaScript(f"""
			var loading = document.getElementById('loading');
			if (loading) loading.remove();
	
			var errorDiv = document.createElement('div');
			errorDiv.className = "message bot";
			errorDiv.innerHTML = "Error: {html.escape(error_msg)}";
			document.body.appendChild(errorDiv);
			window.scrollTo(0, document.body.scrollHeight);
		""")

	def get_base64_gif(self, path):
		with open(path, "rb") as f:
			data = f.read()
			return base64.b64encode(data).decode("utf-8")

	def shutdown(self):
		# Gracefully close all active threads
		for thread in self.active_threads:
			thread.quit()
			thread.wait()
	
		self.active_threads.clear()
		self.active_workers.clear()

	def paintEvent(self, event):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)

		# Bubble color
		bubble_fill_color = QColor(255, 255, 204)
		bubble_outline_color = QColor(0, 0, 0)
		painter.setBrush(bubble_fill_color)
		painter.setPen(bubble_outline_color)

		# Bubble shape
		bubble_rect = self.rect().adjusted(self.padding_left, self.padding_top, -self.padding_right, -self.padding_bottom)
		painter.drawRoundedRect(bubble_rect, 20, 20)

		# Pointer
		bubble_center_x = bubble_rect.center().x()
		pointer = QPolygon([
			QPoint(bubble_center_x, bubble_rect.bottom()), # Left point
			QPoint(bubble_center_x, bubble_rect.bottom() + 20), # Tip
			QPoint(bubble_center_x + 15, bubble_rect.bottom()), # Right Point
		])
		painter.drawPolygon(pointer)

		# Cover up the part where the pointer and bubble meet.
		painter.setPen(bubble_fill_color)
		painter.drawRect(pointer[0].x(), pointer[0].y() - 1, pointer[2].x() - pointer[0].x(), 2)

	def resizeEvent(self, event):
		super().resizeEvent(event)
		if self.parent() and hasattr(self.parent(), "reposition_clippy_from_dialog"):
			self.parent().reposition_clippy_from_dialog()

class ExternalLinkPage(QWebEnginePage):
	def acceptNavigationRequest(self, url, nav_type, is_main_frame):
		if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
			QDesktopServices.openUrl(url)
			return False
		return super().acceptNavigationRequest(url, nav_type, is_main_frame)

class ChatWorker(QObject):
	finished = Signal(str, str)
	error = Signal(str)

	def __init__(self, prompt, system_message, history, api_key, model):
		super().__init__()
		self.prompt = prompt
		self.system_message = system_message
		self.history = history
		self.api_key = api_key
		self.model = model

	@Slot()
	def run(self):
		try:
			response = prompt_chatgpt(self.prompt, self.system_message, self.history, self.api_key, self.model)
			if "error" in response:
				self.error.emit(response["error"])
			elif "choices" in response and response["choices"]:
				md_reply = response["choices"][0]["message"]["content"]
				self.finished.emit(self.prompt, md_reply)
			else:
				self.error.emit("Unexpected API response format.")
		except Exception as e:
			self.error.emit(f"Unhandled exception in worker: {str(e)}")

if __name__ == '__main__':
	app = QApplication(sys.argv)
	window = ClippyWindow()
	window.show()
	sys.exit(app.exec())
