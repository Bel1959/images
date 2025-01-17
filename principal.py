import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ExifTags
import threading
import dlib
import os

# Assurez-vous que ce fichier est dans le même dossier que votre script
predictor_path = "shape_predictor_81_face_landmarks.dat"
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(predictor_path)

def enhance_image_opencv(input_image):
    img = cv2.cvtColor(np.array(input_image), cv2.COLOR_RGB2BGR)

    # Convertir en LAB
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # Appliquer CLAHE avec une limite de clip plus basse
    clahe = cv2.createCLAHE(clipLimit=0.5, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    # Filtrage pour réduire la netteté
    kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
    enhanced = cv2.filter2D(enhanced, -1, kernel)

    # Réduction du bruit
    enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 3, 3, 7, 21)

    # Correction gamma pour adoucir l'image
    gamma = 1.1
    look_up_table = np.array([((i / 255.0) ** gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    enhanced = cv2.LUT(enhanced, look_up_table)

    # Détecter les visages
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    for face in faces:
        landmarks = predictor(gray, face)

        # Améliorer les visages sans ajouter de points bleus visibles
        for n in range(81):
            x = landmarks.part(n).x
            y = landmarks.part(n).y
            # Au lieu de dessiner des cercles, nous pouvons appliquer un léger flou gaussien
            # autour de chaque point de repère pour adoucir la peau
            roi = enhanced[y-2:y+2, x-2:x+2]
            blurred_roi = cv2.GaussianBlur(roi, (3, 3), 0)
            enhanced[y-2:y+2, x-2:x+2] = blurred_roi

    return enhanced

class ImageEnhancerApp:
    def __init__(self, master):
        self.master = master
        master.title("Améliorateur d'Image")
        master.geometry("600x600") 
        master.resizable(False, False)

        self.select_button = tk.Button(master, text="Sélectionner une image", command=self.select_image)
        self.select_button.pack(pady=10)

        self.enhance_button = tk.Button(master, text="Améliorer l'image", command=self.start_enhancement, state=tk.DISABLED)
        self.enhance_button.pack(pady=10)

        self.status_label = tk.Label(master, text="")
        self.status_label.pack(pady=5)

        self.save_button = tk.Button(master, text="Sauvegarder l'image améliorée", command=self.save_image, state=tk.DISABLED)
        self.save_button.pack(pady=10)

        self.image_label = tk.Label(master)
        self.image_label.pack(pady=10)

        self.input_image = None
        self.input_image_full = None
        self.enhanced_image_full = None
        self.enhanced_image_display = None

    def select_image(self):
        input_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if input_path:
            self.input_image_full = Image.open(input_path)
            self.input_image = self.input_image_full.copy()

            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                exif = dict(self.input_image._getexif().items())

                if exif[orientation] == 3:
                    self.input_image = self.input_image.rotate(180, expand=True)
                    self.input_image_full = self.input_image_full.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    self.input_image = self.input_image.rotate(270, expand=True)
                    self.input_image_full = self.input_image_full.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    self.input_image = self.input_image.rotate(90, expand=True)
                    self.input_image_full = self.input_image_full.rotate(90, expand=True)
            except (AttributeError, KeyError, IndexError):
                pass

            # Redimensionner l'image pour l'affichage
            self.input_image.thumbnail((800, 800))
            self.show_image(self.input_image)
            self.enhance_button['state'] = tk.NORMAL
            self.status_label.config(text="")

    def start_enhancement(self):
        self.enhance_button['state'] = tk.DISABLED
        self.status_label.config(text="Veuillez patienter, amélioration en cours...")
        self.master.update()

        threading.Thread(target=self.enhance_image, daemon=True).start()

    def enhance_image(self):
        if self.input_image:
            # Traitez l'image redimensionnée pour un traitement plus rapide
            self.enhanced_image_display = enhance_image_opencv(self.input_image)
            
            # Traitez l'image originale en arrière-plan
            self.enhanced_image_full = enhance_image_opencv(self.input_image_full)
            
            self.master.after(0, self.finish_enhancement)

    def finish_enhancement(self):
        self.show_image(Image.fromarray(cv2.cvtColor(self.enhanced_image_display, cv2.COLOR_BGR2RGB)))
        self.save_button['state'] = tk.NORMAL
        self.enhance_button['state'] = tk.NORMAL
        self.status_label.config(text="Amélioration terminée !")

    def save_image(self):
        if self.enhanced_image_full is not None:
            save_path = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG files", "*.jpg")])
            if save_path:
                enhanced_image_rgb = cv2.cvtColor(self.enhanced_image_full, cv2.COLOR_BGR2RGB)
                Image.fromarray(enhanced_image_rgb).save(save_path, quality=95)
                messagebox.showinfo("Sauvegarde réussie", f"Image améliorée sauvegardée : {save_path}")

    def show_image(self, image):
        photo = ImageTk.PhotoImage(image)
        self.image_label.config(image=photo)
        self.image_label.image = photo

def process_images(image_paths, scale):
    for idx, image_path in enumerate(image_paths):
        image = cv2.imread(image_path)
        if image is None:
            continue
        
        # Mise à l'échelle
        new_width = int(image.shape[1] * scale)
        new_height = int(image.shape[0] * scale)
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

        # Enregistrer l'image traitée
        filename, ext = os.path.splitext(image_path)
        output_path = f"{filename}_resized_{scale}x{ext}"
        cv2.imwrite(output_path, resized_image)
    
    # Message de fin
    messagebox.showinfo("Terminé", "Traitement et enregistrement terminé")

class ImageResizerApp:
    def __init__(self, master):
        self.master = master
        master.title("Agrandissement d'images")
        master.geometry("600x600") 
        master.resizable(False, False)

        self.selected_images = tk.StringVar()

        tk.Button(master, text="Sélectionner des images", command=self.select_images).pack(pady=20)
        tk.Entry(master, textvariable=self.selected_images, width=50).pack(pady=10)
        tk.Button(master, text="Agrandir les images 2X", command=lambda: self.start_processing(2)).pack(pady=10)
        tk.Button(master, text="Agrandir les images 3X", command=lambda: self.start_processing(3)).pack(pady=10)
        tk.Button(master, text="Agrandir les images 4X", command=lambda: self.start_processing(4)).pack(pady=10)

    def select_images(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg;*.png")])
        self.selected_images.set(";".join(file_paths))

    def start_processing(self, scale):
        image_paths = self.selected_images.get().split(";")
        if not image_paths or image_paths[0] == '':
            messagebox.showwarning("Aucune image sélectionnée", "Veuillez sélectionner une ou plusieurs images à traiter.")
            return

        threading.Thread(target=lambda: process_images(image_paths, scale)).start()

class MainApp:
    def __init__(self, master):
        self.master = master
        master.title("Traitement d'images")
        master.geometry("600x600")
        master.resizable(False, False)  

        tk.Button(master, text="Améliorer photos", command=self.open_enhancer).pack(pady=20)
        tk.Button(master, text="Agrandissement photos", command=self.open_resizer).pack(pady=20)

    def open_enhancer(self):
        enhancer_window = tk.Toplevel(self.master)
        enhancer_window.geometry("600x600")
        enhancer_window.resizable(False, False)
        ImageEnhancerApp(enhancer_window)

    def open_resizer(self):
        resizer_window = tk.Toplevel(self.master)
        resizer_window.geometry("600x600")
        resizer_window.resizable(False, False)
        ImageResizerApp(resizer_window)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
