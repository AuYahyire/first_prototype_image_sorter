import sys
import os
import shutil
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QLabel,
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
                             QScrollArea, QSlider, QCheckBox, QShortcut)
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtCore import Qt


class ImageSorter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Sorter")
        self.setGeometry(100, 100, 1920, 1080)
        self.showMaximized()

        self.settings_file = "settings.json"
        self.current_directory = self.load_last_directory()
        self.image_files = []
        self.current_image_index = 0
        self.zoom_factor = 1.0
        self.undo_stack = []
        self.show_filename = True

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_label)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        # Filename display checkbox
        self.show_filename_checkbox = QCheckBox("Show Filename")
        self.show_filename_checkbox.stateChanged.connect(self.toggle_filename_display)
        main_layout.addWidget(self.show_filename_checkbox)

        # Zoom slider
        zoom_layout = QHBoxLayout()
        zoom_label = QLabel("Zoom:")
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        zoom_layout.addWidget(zoom_label)
        zoom_layout.addWidget(self.zoom_slider)
        main_layout.addLayout(zoom_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.select_folder_btn = QPushButton("Select Folder")
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.approve_btn = QPushButton("Approve (↑)")
        self.approve_btn.clicked.connect(self.approve_image)
        self.edit_btn = QPushButton("Need Edits (E)")
        self.edit_btn.clicked.connect(self.edit_image)
        self.reject_btn = QPushButton("Reject (↓)")
        self.reject_btn.clicked.connect(self.reject_image)
        self.undo_btn = QPushButton("Undo (Ctrl+Z)")
        self.undo_btn.clicked.connect(self.undo_action)

        button_layout.addWidget(self.select_folder_btn)
        button_layout.addWidget(self.approve_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.reject_btn)
        button_layout.addWidget(self.undo_btn)
        main_layout.addLayout(button_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_Up), self, self.approve_image)
        QShortcut(QKeySequence(Qt.Key.Key_Down), self, self.reject_image)
        QShortcut(QKeySequence(Qt.Key.Key_E), self, self.edit_image)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.previous_image)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.next_image)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo_action)

        # If a directory is stored, load images
        if self.current_directory:
            self.load_images()

    def load_last_directory(self):
        """Load the last opened directory from a settings file."""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as file:
                settings = json.load(file)
                path = settings.get("last_directory", "")
                # Verify if last_directory exists
                if os.path.exists(path):
                    return path
        return ""

    def save_last_directory(self):
        """Save the currently open directory to a settings file."""
        with open(self.settings_file, "w") as file:
            json.dump({"last_directory": self.current_directory}, file)

    def select_folder(self):
        """Open a folder dialog and load the images."""
        self.current_directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if self.current_directory:
            self.save_last_directory()
            self.load_images()

    def load_images(self):
        """Recursively load image files from the selected directory and subdirectories."""
        self.image_files = []
        excluded_dirs = {"Approved", "Need editions", "Rejected"}

        for root, directories, files in os.walk(self.current_directory):
            directories[:] = [d for d in directories if d not in excluded_dirs]

            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    self.image_files.append(os.path.join(root, f))

        if self.image_files:
            self.current_image_index = 0
            self.display_image()
        else:
            self.image_label.setText("No images found in the selected directory.")

    def display_image(self):
        """Display the current image with optional filename."""
        if self.image_files:
            image_path = self.image_files[self.current_image_index]
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(self.image_label.size() * self.zoom_factor,
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)

            if self.show_filename:
                self.setWindowTitle(f"Image Sorter - {os.path.basename(image_path)}")
            else:
                self.setWindowTitle("Image Sorter")

    def toggle_filename_display(self):
        """Toggle the display of the filename in the window title."""
        self.show_filename = self.show_filename_checkbox.isChecked()
        self.display_image()

    def update_zoom(self):
        """Update the zoom level based on the slider value."""
        self.zoom_factor = self.zoom_slider.value() / 100
        self.display_image()

    def move_image(self, destination_folder):
        """Move the current image to the specified destination folder within its parent folder."""
        if self.image_files:
            source = self.image_files[self.current_image_index]
            destination_path = os.path.join(os.path.dirname(source), destination_folder)
            if not os.path.exists(destination_path):
                os.makedirs(destination_path)
            destination = os.path.join(destination_path, os.path.basename(source))
            shutil.move(source, destination)
            self.undo_stack.append(("move", source, destination))
            self.image_files.pop(self.current_image_index)
            if self.image_files:
                self.current_image_index %= len(self.image_files)
                self.display_image()
            else:
                self.image_label.clear()
                self.image_label.setText("No more images in the directory.")

    def approve_image(self):
        self.move_image("Approved") #testing commit

    def edit_image(self):
        self.move_image("Need editions")

    def reject_image(self):
        """Move the rejected image to the 'Rejected' folder."""
        self.move_image("Rejected")

    def undo_action(self):
        """Undo the last action, including moving or deleting files, while keeping the current index."""
        if self.undo_stack:
            current_image_name = os.path.basename(self.image_files[self.current_image_index]) if self.image_files else None
            action = self.undo_stack.pop()

            if action[0] == "move":
                shutil.move(action[2], action[1])  # Move the image back

            # Refresh the list of images
            self.load_images()

            # Try to set the current image index to the previously viewed image
            if current_image_name in (os.path.basename(f) for f in self.image_files):
                self.current_image_index = next(
                    i for i, f in enumerate(self.image_files) if os.path.basename(f) == current_image_name
                )
            else:
                self.current_image_index = min(self.current_image_index, len(self.image_files) - 1)

            self.display_image()

    def previous_image(self):
        """Move to the previous image."""
        if self.image_files:
            self.current_image_index = (self.current_image_index - 1) % len(self.image_files)
            self.display_image()

    def next_image(self):
        """Move to the next image."""
        if self.image_files:
            self.current_image_index = (self.current_image_index + 1) % len(self.image_files)
            self.display_image()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageSorter()
    window.show()
    sys.exit(app.exec())
